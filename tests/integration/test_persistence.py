import sqlite3
from pathlib import Path
from typing import Any

import pytest

from monty_hall.domain.models import ConfigurationError, GameConfig, HostPolicy
from monty_hall.persistence.repository import RunRepository, parse_stored_run
from monty_hall.simulation.runner import SimulationRequest, SimulationResult, run_simulation

ROOT = Path(__file__).resolve().parents[2]


def _execute(path: Path, statement: str) -> None:
    connection = sqlite3.connect(path)
    connection.execute(statement)
    connection.commit()
    connection.close()


@pytest.mark.parametrize("read_only", [True, False])
@pytest.mark.parametrize(
    "statement",
    [
        "CREATE VIEW simulation_run_rates AS SELECT 1 AS id",
        "CREATE VIEW simulation_run_rates AS WITH RECURSIVE r(x) AS "
        "(SELECT 1 UNION ALL SELECT x + 1 FROM r) SELECT x AS id FROM r",
        "CREATE TABLE simulation_runs (id INTEGER PRIMARY KEY)",
        "CREATE TABLE SIMULATION_RUNS (id INTEGER PRIMARY KEY)",
    ],
)
def test_rejects_tampered_schema(tmp_path: Path, statement: str, read_only: bool) -> None:
    path = tmp_path / "tampered.sqlite3"
    _execute(path, statement)
    before = path.read_bytes()
    with pytest.raises(ConfigurationError, match="schema"):
        RunRepository(path, read_only=read_only)
    assert path.read_bytes() == before


def test_rejects_added_trigger(tmp_path: Path) -> None:
    path = tmp_path / "runs.sqlite3"
    RunRepository(path).__exit__(None, None, None)
    _execute(
        path,
        "CREATE TRIGGER wipe AFTER INSERT ON simulation_runs "
        "BEGIN DELETE FROM simulation_runs; END",
    )
    with pytest.raises(ConfigurationError, match="schema"):
        RunRepository(path)


def test_reopening_a_valid_database_keeps_its_runs(tmp_path: Path) -> None:
    path = tmp_path / "runs.sqlite3"
    with RunRepository(path) as repository:
        run_id = repository.save(_result())
    with RunRepository(path) as repository:
        repository.save(_result(8))
    with RunRepository(path, read_only=True) as repository:
        assert run_id in [run.id for run in repository.recent()]


def test_schema_is_added_next_to_unrelated_tables(tmp_path: Path) -> None:
    path = tmp_path / "shared.sqlite3"
    _execute(path, "CREATE TABLE unrelated (id INTEGER)")
    with RunRepository(path) as repository:
        assert repository.save(_result()) == 1


@pytest.mark.parametrize(
    "row",
    [
        (1, b"\x00", 3, 1, "informed", 1, 1, 0.5, 0.5),
        (1, "now", 3, 1, "informed", 1, 1, 0.5),
        (1, "now", "3", 1, "informed", 1, 1, 0.5, 0.5),
    ],
)
def test_parse_stored_run_rejects_invalid_rows(row: tuple[Any, ...]) -> None:
    with pytest.raises(ConfigurationError, match="invalid run"):
        parse_stored_run(row)


def test_parse_stored_run_accepts_null_rates() -> None:
    run = parse_stored_run((1, "now", 3, 1, "random", 1, 0, None, None))
    assert run.stay_win_rate is None


def _result(seed: int = 7) -> SimulationResult:
    return run_simulation(SimulationRequest(GameConfig(), HostPolicy.INFORMED, 200, seed))


def test_packaged_schema_matches_published_schema() -> None:
    published = (ROOT / "db" / "schema.sql").read_text("utf-8")
    packaged = (ROOT / "src" / "monty_hall" / "persistence" / "schema.sql").read_text("utf-8")
    assert packaged == published


def test_round_trip(tmp_path: Path) -> None:
    result = _result()
    with RunRepository(tmp_path / "runs.sqlite3") as repository:
        run_id = repository.save(result)
        stored = repository.recent()
    assert [run.id for run in stored] == [run_id]
    assert stored[0].valid_games == 200
    assert stored[0].switch_win_rate == result.switch_rate


def test_recent_returns_newest_first_and_honors_limit(tmp_path: Path) -> None:
    with RunRepository(tmp_path / "runs.sqlite3") as repository:
        ids = [repository.save(_result(seed)) for seed in range(3)]
        stored = repository.recent(limit=2)
    assert [run.id for run in stored] == [ids[2], ids[1]]


@pytest.mark.parametrize("limit", [0, 1001])
def test_recent_rejects_invalid_limit(tmp_path: Path, limit: int) -> None:
    with (
        RunRepository(tmp_path / "runs.sqlite3") as repository,
        pytest.raises(ValueError, match="limit"),
    ):
        repository.recent(limit)


@pytest.mark.parametrize(
    "values",
    [
        (2, 1, "informed", 1, 10, 10, 1, 1),
        (3, 1, "unknown", 1, 10, 10, 1, 1),
        (3, 1, "informed", 1, 10, 9, 1, 1),
        (3, 1, "random", 1, 10, 5, 3, 3),
        (3, 1, "informed", -1, 10, 10, 1, 1),
    ],
)
def test_schema_constraints_reject_inconsistent_rows(
    tmp_path: Path, values: tuple[object, ...]
) -> None:
    path = tmp_path / "runs.sqlite3"
    RunRepository(path).__exit__(None, None, None)
    connection = sqlite3.connect(path)
    with pytest.raises(sqlite3.IntegrityError):
        connection.execute(
            "INSERT INTO simulation_runs (doors, opened_doors, host_policy, seed, "
            "requested_trials, valid_games, stay_wins, switch_wins) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            values,
        )
    connection.close()
