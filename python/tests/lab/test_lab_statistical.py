from fractions import Fraction

import pytest

from monty_hall.analysis.intervals import z_score
from monty_hall.lab.model import Host, Scenario
from monty_hall.lab.simulator import simulate
from monty_hall.lab.solver import solve

Z_LIMIT = 4.5
SEED = 20_190_925
TRIALS = 40_000

CASES = [
    Scenario(),
    Scenario(host=Host.RANDOM),
    Scenario(doors=5, prizes=2, reveals=2),
    Scenario(doors=6, prizes=2, reveals=3, host=Host.RANDOM, mixed=Fraction(1, 3)),
    Scenario(doors=6, prizes=2, reveals=1, host=Host.ADVERSARIAL),
    Scenario(host=Host.BIASED, host_weights=(1, 3, 1), observed=(1,)),
    Scenario(host=Host.BIASED, host_weights=(1, 3, 1), observed=(2,)),
    Scenario(doors=5, prizes=2, prior=(5, 1, 1, 1, 1), reveals=2, host=Host.RANDOM),
    Scenario(doors=8, prizes=2, prior=(1, 1, 2, 2, 3, 3, 4, 4), pick=7, reveals=3),
]


@pytest.mark.parametrize("scenario", CASES, ids=lambda s: f"{s.host}-{s.doors}-{s.reveals}")
def test_simulation_converges_to_exact(scenario: Scenario) -> None:
    exact = solve(scenario)
    counts = simulate(scenario, TRIALS, SEED)
    sample = counts.sample_size
    for wins, expected in (
        (counts.stay_wins, exact.stay),
        (counts.switch_wins, exact.switch),
        (counts.mixed_wins, exact.mixed(scenario.mixed)),
    ):
        assert expected is not None
        if expected in (0, 1):
            assert wins == expected * sample
        else:
            assert abs(z_score(wins, sample, float(expected))) < Z_LIMIT
    if exact.decision not in (0, 1):
        assert abs(z_score(counts.decision, TRIALS, float(exact.decision))) < Z_LIMIT
