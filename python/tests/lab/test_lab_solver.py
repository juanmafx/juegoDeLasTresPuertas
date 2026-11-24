from dataclasses import replace
from fractions import Fraction

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from monty_hall.lab.model import ENUMERATION_MAX_DOORS, Host, Scenario, ScenarioError
from monty_hall.lab.solver import all_observations, prize_set_distribution, solve


def test_classic_informed_anchor() -> None:
    result = solve(Scenario())
    assert (result.stay, result.switch) == (Fraction(1, 3), Fraction(2, 3))


def test_random_host_anchor_is_conditional_on_no_prize_revealed() -> None:
    result = solve(Scenario(host=Host.RANDOM))
    assert (result.stay, result.switch, result.void) == (
        Fraction(1, 2),
        Fraction(1, 2),
        Fraction(1, 3),
    )


def test_adversarial_anchor() -> None:
    result = solve(Scenario(host=Host.ADVERSARIAL))
    assert (result.switch, result.no_offer) == (Fraction(0), Fraction(2, 3))


@pytest.mark.parametrize("p", [Fraction(1, 4), Fraction(1, 2), Fraction(3, 4), Fraction(9, 10)])
def test_biased_anchor_is_door_dependent(p: Fraction) -> None:
    weights = (1, p.numerator, p.denominator - p.numerator)
    lower = solve(Scenario(host=Host.BIASED, host_weights=weights, observed=(1,)))
    upper = solve(Scenario(host=Host.BIASED, host_weights=weights, observed=(2,)))
    assert lower.switch == 1 / (1 + p)
    assert upper.switch == 1 / (2 - p)


def test_mixed_interpolates() -> None:
    assert solve(Scenario()).mixed(Fraction(1, 3)) == Fraction(4, 9)


def test_zero_prior_at_pick_leaves_adversarial_undefined() -> None:
    result = solve(Scenario(doors=4, prior=(0, 1, 1, 1), host=Host.ADVERSARIAL))
    assert result.decision == 0
    assert (result.stay, result.switch, result.mixed(Fraction(1, 2))) == (None, None, None)


def test_enumeration_limit() -> None:
    with pytest.raises(ScenarioError, match="at most"):
        solve(Scenario(doors=ENUMERATION_MAX_DOORS + 1, prior=(1,) * (ENUMERATION_MAX_DOORS + 1)))


def test_prize_set_distribution_sums_to_one() -> None:
    distribution = prize_set_distribution(6, 3, (1, 2, 0, 4, 5, 6))
    assert sum(distribution.values()) == 1
    assert all(not mask >> 2 & 1 for mask in distribution)


small = st.integers(3, 6).flatmap(
    lambda n: st.integers(1, n - 2).flatmap(
        lambda m: st.builds(
            Scenario,
            doors=st.just(n),
            prizes=st.just(m),
            prior=st.one_of(
                st.none(),
                st.lists(st.integers(1, 5), min_size=n, max_size=n).map(tuple),
            ),
            pick=st.integers(0, n - 1),
            reveals=st.integers(0, n - m - 1),
            host=st.sampled_from([Host.INFORMED, Host.RANDOM, Host.ADVERSARIAL]),
        )
    )
)


@settings(derandomize=True, max_examples=80, deadline=None)
@given(small)
def test_observations_average_back_to_the_unconditional_result(scenario: Scenario) -> None:
    unconditional = solve(scenario)
    joint = stay = switch = Fraction(0)
    for observed in all_observations(scenario):
        result = solve(replace(scenario, observed=observed))
        assert result.observed is not None
        joint += result.observed
        if result.observed:
            assert result.stay is not None
            assert result.switch is not None
            stay += result.observed * result.stay
            switch += result.observed * result.switch
    assert joint == unconditional.decision
    if joint:
        assert stay / joint == unconditional.stay
        assert switch / joint == unconditional.switch


@settings(derandomize=True, max_examples=80, deadline=None)
@given(small)
def test_probabilities_are_valid(scenario: Scenario) -> None:
    result = solve(scenario)
    assert result.decision + result.void + result.no_offer == 1
    for value in (result.prize_at_pick, result.stay, result.switch):
        assert value is None or 0 <= value <= 1


@settings(derandomize=True, max_examples=60, deadline=None)
@given(st.integers(3, 64).flatmap(lambda n: st.tuples(st.just(n), st.integers(0, n - 2))))
def test_informed_switch_beats_stay_with_one_prize(game: tuple[int, int]) -> None:
    doors, reveals = game
    result = solve(Scenario(doors=doors, reveals=reveals))
    assert result.switch is not None
    assert result.stay is not None
    assert result.switch >= result.stay
    assert (result.switch > result.stay) == (reveals > 0)
