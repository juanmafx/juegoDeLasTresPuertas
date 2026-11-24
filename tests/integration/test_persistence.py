import sqlite3
from pathlib import Path

import pytest

from monty_hall.domain.models import GameConfig, HostPolicy
from monty_hall.persistence.repository import RunRepository
from monty_hall.simulation.runner import SimulationRequest, SimulationResult, run_simulation

ROOT = Path(__file__).resolve().parents[2]


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
