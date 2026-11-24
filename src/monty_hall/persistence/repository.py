import sqlite3
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from types import TracebackType
from typing import Self

from monty_hall.simulation.runner import SimulationResult

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


class RunRepository:
    def __init__(self, path: Path, *, read_only: bool = False) -> None:
        if read_only:
            uri = f"{path.resolve().as_uri()}?mode=ro"
            self._connection = sqlite3.connect(uri, uri=True)
            return
        self._connection = sqlite3.connect(path)
        schema = files("monty_hall.persistence").joinpath("schema.sql").read_text("utf-8")
        self._connection.executescript(schema)

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
        return [StoredRun(*row) for row in rows]
