from typing import Any

import pytest

from monty_hall.domain.models import (
    MAX_DOORS,
    ConfigurationError,
    GameConfig,
    GameOutcome,
    HostPolicy,
)
from monty_hall.simulation.runner import MAX_SEED, MAX_TRIALS, SimulationRequest


@pytest.mark.parametrize(
    ("doors", "opened"),
    [(2, 1), (3, 0), (3, 2), (5, 4), (MAX_DOORS + 1, 1), (True, 1), (3, True), (3.0, 1)],
)
def test_rejects_invalid_configurations(doors: Any, opened: Any) -> None:
    with pytest.raises(ConfigurationError):
        GameConfig(doors, opened)


@pytest.mark.parametrize(("doors", "opened"), [(3, 1), (4, 2), (MAX_DOORS, MAX_DOORS - 2)])
def test_accepts_boundary_configurations(doors: int, opened: int) -> None:
    assert GameConfig(doors, opened).doors == doors


@pytest.mark.parametrize(
    ("trials", "seed"),
    [(0, 1), (MAX_TRIALS + 1, 1), (1, -1), (1, MAX_SEED + 1), (True, 1), (1, False)],
)
def test_rejects_invalid_requests(trials: int, seed: int) -> None:
    with pytest.raises(ConfigurationError):
        SimulationRequest(GameConfig(), HostPolicy.INFORMED, trials, seed)


def test_outcome_win_flags() -> None:
    outcome = GameOutcome(car=1, first_pick=0, opened=frozenset({2}), switch_pick=1)
    assert outcome.switch_wins
    assert not outcome.stay_wins
