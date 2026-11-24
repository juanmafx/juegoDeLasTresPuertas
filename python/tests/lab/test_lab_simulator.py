from fractions import Fraction

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from monty_hall.lab.model import Host, Scenario, ScenarioError
from monty_hall.lab.simulator import simulate

scenarios = st.integers(3, 12).flatmap(
    lambda n: st.integers(1, n - 2).flatmap(
        lambda m: st.builds(
            Scenario,
            doors=st.just(n),
            prizes=st.just(m),
            pick=st.integers(0, n - 1),
            reveals=st.integers(0, n - m - 1),
            host=st.sampled_from([Host.INFORMED, Host.RANDOM, Host.ADVERSARIAL]),
            mixed=st.fractions(0, 1, max_denominator=9),
        )
    )
)


@settings(derandomize=True, max_examples=100, deadline=None)
@given(scenarios, st.integers(0, 2**63 - 1))
def test_counts_are_consistent_and_reproducible(scenario: Scenario, seed: int) -> None:
    counts = simulate(scenario, 50, seed)
    assert counts == simulate(scenario, 50, seed)
    assert counts.decision + counts.void + counts.no_offer == 50
    for wins in (counts.stay_wins, counts.switch_wins, counts.mixed_wins):
        assert 0 <= wins <= counts.sample_size
    if scenario.host is not Host.RANDOM:
        assert counts.void == 0
    if scenario.host is not Host.ADVERSARIAL:
        assert counts.no_offer == 0
    if scenario.mixed == 0:
        assert counts.mixed_wins == counts.stay_wins
    if scenario.mixed == 1:
        assert counts.mixed_wins == counts.switch_wins


def test_adversarial_single_prize_switch_never_wins() -> None:
    counts = simulate(Scenario(doors=5, host=Host.ADVERSARIAL, reveals=2), 2000, 3)
    assert counts.switch_wins == 0
    assert counts.stay_wins == counts.decision


def test_observed_counts_only_matching_reveals() -> None:
    counts = simulate(Scenario(observed=(1,)), 1000, 5)
    assert counts.observed is not None
    assert 0 < counts.observed < counts.decision


def test_zero_weight_doors_never_hold_prizes() -> None:
    counts = simulate(Scenario(doors=4, prior=(0, 1, 1, 1)), 500, 1)
    assert counts.stay_wins == 0


def test_large_game_runs() -> None:
    counts = simulate(Scenario(doors=64, reveals=62, mixed=Fraction(1)), 200, 9)
    assert counts.decision == 200


@pytest.mark.parametrize(("trials", "seed"), [(0, 1), (1, -1), (1, 2**63), (True, 1)])
def test_rejects_invalid_requests(trials: int, seed: int) -> None:
    with pytest.raises(ScenarioError):
        simulate(Scenario(), trials, seed)
