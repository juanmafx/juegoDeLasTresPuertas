import sqlite3
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from types import NoneType, TracebackType
from typing import Any, Self

from monty_hall.domain.models import ConfigurationError
from monty_hall.simulation.runner import SimulationResult

SELECT_SCHEMA_OBJECTS = """
SELECT type, name, tbl_name, sql
FROM sqlite_schema
WHERE lower(tbl_name) IN ('simulation_runs', 'simulation_run_rates')
"""

INSERT_RUN = """
INSERT INTO simulation_runs (
    doors, opened_doors, host_policy, seed, requested_trials, valid_games, stay_wins, switch_wins
) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
"""

SELECT_RECENT_RUNS = """
SELECT id, created_at, doors, opened_doors, host_policy, seed, valid_games,
       stay_win_rate, switch_win_rate
FROM simulation_run_rates
ORDER BY id DESC
LIMIT ?
"""


@dataclass(frozen=True, slots=True)
class StoredRun:
    id: int
    created_at: str
    doors: int
    opened_doors: int
    host_policy: str
    seed: int
    valid_games: int
    stay_win_rate: float | None
    switch_win_rate: float | None


STORED_RUN_TYPES: tuple[type | tuple[type, ...], ...] = (
    int,
    str,
    int,
    int,
    str,
    int,
    int,
    (float, NoneType),
    (float, NoneType),
)


def parse_stored_run(row: tuple[Any, ...]) -> StoredRun:
    if len(row) != len(STORED_RUN_TYPES) or not all(
        isinstance(value, expected) for value, expected in zip(row, STORED_RUN_TYPES, strict=True)
    ):
        raise ConfigurationError("database contains an invalid run")
    return StoredRun(*row)


def _schema_objects(connection: sqlite3.Connection) -> set[tuple[str, str, str, str]]:
    return set(connection.execute(SELECT_SCHEMA_OBJECTS).fetchall())


def _expected_schema_objects(schema: str) -> set[tuple[str, str, str, str]]:
    reference = sqlite3.connect(":memory:")
    try:
        reference.executescript(schema)
        return _schema_objects(reference)
    finally:
        reference.close()


class RunRepository:
    def __init__(self, path: Path, *, read_only: bool = False) -> None:
        schema = files("monty_hall.persistence").joinpath("schema.sql").read_text("utf-8")
        if read_only:
            uri = f"{path.resolve().as_uri()}?mode=ro"
            self._connection = sqlite3.connect(uri, uri=True)
        else:
            self._connection = sqlite3.connect(path)
        try:
            existing = _schema_objects(self._connection)
            if (read_only or existing) and existing != _expected_schema_objects(schema):
                raise ConfigurationError("database schema does not match the monty-hall schema")
            if not existing:
                self._connection.executescript(schema)
        except BaseException:
            self._connection.close()
            raise

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self._connection.close()

    def save(self, result: SimulationResult) -> int:
        request = result.request
        with self._connection:
            cursor = self._connection.execute(
                INSERT_RUN,
                (
                    request.config.doors,
                    request.config.opened,
                    request.policy.value,
                    request.seed,
                    request.trials,
                    result.valid_games,
                    result.stay_wins,
                    result.switch_wins,
                ),
            )
        run_id = cursor.lastrowid
        if run_id is None:
            raise RuntimeError("insert did not return a row id")
        return run_id

    def recent(self, limit: int = 20) -> list[StoredRun]:
        if not 1 <= limit <= 1000:
            raise ValueError("limit must be between 1 and 1000")
        rows = self._connection.execute(SELECT_RECENT_RUNS, (limit,)).fetchall()
        return [parse_stored_run(row) for row in rows]
