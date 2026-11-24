from random import Random

from hypothesis import given, settings
from hypothesis import strategies as st

from monty_hall.analysis.exact import closed_form, enumerate_game_tree
from monty_hall.analysis.intervals import wilson_interval
from monty_hall.domain.game import play_game
from monty_hall.domain.models import GameConfig, HostPolicy
from monty_hall.simulation.runner import SimulationRequest, run_simulation

policies = st.sampled_from(list(HostPolicy))
configs = st.integers(3, 40).flatmap(
    lambda doors: st.builds(GameConfig, st.just(doors), st.integers(1, doors - 2))
)
small_configs = st.integers(3, 6).flatmap(
    lambda doors: st.builds(GameConfig, st.just(doors), st.integers(1, doors - 2))
)
seeds = st.integers(0, 2**63 - 1)


@settings(derandomize=True, max_examples=200)
@given(configs, policies, seeds)
def test_game_invariants(config: GameConfig, policy: HostPolicy, seed: int) -> None:
    outcome = play_game(config, policy, Random(seed))
    if outcome is None:
        assert policy is HostPolicy.RANDOM
        return
    assert len(outcome.opened) == config.opened
    assert outcome.car not in outcome.opened
    assert outcome.first_pick not in outcome.opened
    assert outcome.switch_pick not in outcome.opened
    assert outcome.switch_pick != outcome.first_pick
    assert not (outcome.stay_wins and outcome.switch_wins)


@settings(derandomize=True, max_examples=30, deadline=None)
@given(small_configs, policies)
def test_closed_form_matches_enumeration(config: GameConfig, policy: HostPolicy) -> None:
    assert closed_form(config, policy) == enumerate_game_tree(config, policy)


@settings(derandomize=True, max_examples=50, deadline=None)
@given(configs, policies, seeds)
def test_runs_are_reproducible(config: GameConfig, policy: HostPolicy, seed: int) -> None:
    request = SimulationRequest(config, policy, 25, seed)
    assert run_simulation(request) == run_simulation(request)


@settings(derandomize=True, max_examples=50, deadline=None)
@given(st.integers(3, 12))
def test_full_reveal_makes_strategies_complementary(doors: int) -> None:
    exact = closed_form(GameConfig(doors, doors - 2), HostPolicy.INFORMED)
    assert exact.stay + exact.switch == 1


@settings(derandomize=True, max_examples=300)
@given(
    st.integers(1, 10_000).flatmap(lambda n: st.tuples(st.integers(0, n), st.just(n))),
    st.floats(0.5, 0.999),
)
def test_wilson_interval_brackets_the_rate(observation: tuple[int, int], confidence: float) -> None:
    successes, trials = observation
    interval = wilson_interval(successes, trials, confidence)
    assert 0.0 <= interval.lower <= successes / trials <= interval.upper <= 1.0
