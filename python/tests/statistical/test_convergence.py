from collections import Counter
from random import Random

import pytest

from monty_hall.analysis.exact import closed_form
from monty_hall.analysis.intervals import z_score
from monty_hall.domain.game import play_game
from monty_hall.domain.models import GameConfig, HostPolicy
from monty_hall.simulation.runner import SimulationRequest, run_simulation

Z_LIMIT = 4.5
CHI_SQUARE_DF2_P001 = 13.816
SEED = 20_190_925


@pytest.mark.parametrize("policy", list(HostPolicy))
@pytest.mark.parametrize(("doors", "opened"), [(3, 1), (4, 1), (4, 2), (6, 3), (10, 8)])
def test_simulation_converges_to_exact(doors: int, opened: int, policy: HostPolicy) -> None:
    config = GameConfig(doors, opened)
    result = run_simulation(SimulationRequest(config, policy, 40_000, SEED))
    exact = closed_form(config, policy)
    assert abs(z_score(result.stay_wins, result.valid_games, float(exact.stay))) < Z_LIMIT
    assert abs(z_score(result.switch_wins, result.valid_games, float(exact.switch))) < Z_LIMIT
    if exact.valid_game == 1:
        assert result.valid_games == 40_000
    else:
        assert abs(z_score(result.valid_games, 40_000, float(exact.valid_game))) < Z_LIMIT


def test_car_placement_is_uniform() -> None:
    rng = Random(SEED)
    games = 30_000
    counts: Counter[int] = Counter()
    for _ in range(games):
        outcome = play_game(GameConfig(), HostPolicy.INFORMED, rng)
        assert outcome is not None
        counts[outcome.car] += 1
    expected = games / 3
    statistic = sum((counts[door] - expected) ** 2 / expected for door in range(3))
    assert statistic < CHI_SQUARE_DF2_P001


def test_host_is_unbiased_when_first_pick_holds_the_car() -> None:
    rng = Random(SEED)
    reveals: Counter[int] = Counter()
    while sum(reveals.values()) < 10_000:
        outcome = play_game(GameConfig(), HostPolicy.INFORMED, rng)
        assert outcome is not None
        if outcome.car == 0 and outcome.first_pick == 0:
            reveals[next(iter(outcome.opened))] += 1
    assert set(reveals) == {1, 2}
    assert abs(z_score(reveals[1], 10_000, 0.5)) < Z_LIMIT
