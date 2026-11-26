# Module 3: signalling, reflexivity and latency against closed forms and Monte Carlo.
from fractions import Fraction
from itertools import pairwise
from math import comb

import numpy as np
import pytest
from branching_monty.agents.latency import Timing, timed_joint, timed_likelihood, timed_value
from branching_monty.agents.reflexivity import reflexive_lambda, reflexive_value
from branching_monty.agents.signalling import (
    Policy,
    best_policy,
    evaluate,
    full_disclosure_policy,
    messages,
    monty_policy,
    worst_policy,
)
from branching_monty.agents.two_cpu import run_baseline, run_policy, run_timed
from branching_monty.branches.engine import GameSpec, Hypothesis, exact_value
from monty_hall.lab.model import Scenario
from monty_hall.lab.solver import solve

SHAPES = [(n, k) for n in range(3, 8) for k in range(1, n - 1)]


@pytest.mark.parametrize(("n", "k"), SHAPES)
def test_monty_policy_matches_decision_lab(n: int, k: int) -> None:
    lab = solve(Scenario(doors=n, reveals=k))
    assert evaluate(monty_policy(n, k)).value == pytest.approx(float(max(lab.stay, lab.switch)))


@pytest.mark.parametrize(("n", "k"), SHAPES)
def test_best_goat_only_policy_reaches_matching_bound(n: int, k: int) -> None:
    policy, lp_value = best_policy(n, k)
    expected = min(n, comb(n - 1, k)) / n
    assert lp_value == pytest.approx(expected)
    assert evaluate(policy).value == pytest.approx(expected)


@pytest.mark.parametrize(("n", "k"), SHAPES)
def test_uniform_monty_is_the_least_helpful_goat_only_host(n: int, k: int) -> None:
    policy, lp_value = worst_policy(n, k)
    monty = evaluate(monty_policy(n, k)).value
    assert lp_value == pytest.approx(monty)
    assert evaluate(policy).value == pytest.approx(monty)


def test_player_door_constraint_alone_allows_full_disclosure() -> None:
    for n in range(3, 7):
        assert evaluate(full_disclosure_policy(n, 1), "claim").value == pytest.approx(1.0)
        assert evaluate(full_disclosure_policy(n, 1), "loss").value == pytest.approx(1 / n)


def test_goat_only_policy_may_not_reveal_the_car() -> None:
    msgs = messages(3, 1)
    matrix = np.array([[1.0, 0.0], [1.0, 0.0], [1.0, 0.0]])
    with pytest.raises(ValueError, match="reveals the car"):
        evaluate(Policy(3, msgs, matrix, "goat_only"))


def test_messages_validate_k() -> None:
    with pytest.raises(ValueError, match="k must"):
        messages(4, 3)


@pytest.mark.parametrize(("n", "k"), [(3, 1), (4, 1), (4, 2), (5, 2), (6, 3)])
def test_reflexivity_closed_forms(n: int, k: int) -> None:
    spec = GameSpec(n, k, Fraction(1))
    base = exact_value(spec, k, "claim")
    closed = Fraction(1, n - k)
    for r in (Fraction(0), Fraction(1, 3), Fraction(1, 2), Fraction(1)):
        assert reflexive_value(spec, "claim", r, "adversarial") == (1 - r) * base
        assert reflexive_value(spec, "claim", r, "noise") == (1 - r) * base + r * closed
        assert reflexive_value(spec, "claim", r, "self_fulfilling") == (1 - r) * base + r


def test_reflexivity_monotonicity_depends_on_sign() -> None:
    spec = GameSpec(4, 1, Fraction(1, 2))
    grid = [Fraction(i, 10) for i in range(11)]
    adversarial = [reflexive_value(spec, "claim", r, "adversarial") for r in grid]
    noise = [reflexive_value(spec, "claim", r, "noise") for r in grid]
    fulfilling = [reflexive_value(spec, "claim", r, "self_fulfilling") for r in grid]
    assert all(a > b for a, b in pairwise(adversarial))
    assert all(a > b for a, b in pairwise(noise))
    assert all(a < b for a, b in pairwise(fulfilling))


def test_reflexivity_rejects_invalid_strength() -> None:
    with pytest.raises(ValueError, match="r must"):
        reflexive_value(GameSpec(3, 1, Fraction(1)), "claim", Fraction(2), "noise")


@pytest.mark.parametrize("mode", ["adversarial", "noise", "self_fulfilling"])
def test_reflexive_monte_carlo(mode: str) -> None:
    spec = GameSpec(4, 2, Fraction(2, 3))
    r = Fraction(2, 5)
    result = run_baseline(spec, "claim", 20000, 11, float(r), mode)
    exact = float(reflexive_value(spec, "claim", r, mode))
    assert abs(result.rate - exact) < 4 * np.sqrt(exact * (1 - exact) / result.trials)


@pytest.mark.parametrize("jitter", range(6))
@pytest.mark.parametrize("gap", range(4))
def test_latency_closed_form_three_doors(jitter: int, gap: int) -> None:
    expected = Fraction(2, 3) + Fraction(1, 3) * Fraction(min(gap, jitter + 1), jitter + 1)
    for latency in (0, 3, 50):
        timing = Timing(processing=7, per_choice=gap, latency=latency, jitter=jitter)
        assert timed_value(3, Fraction(1), timing, "claim") == expected


@pytest.mark.parametrize("n", [3, 4, 5])
@pytest.mark.parametrize("q", [Fraction(0), Fraction(1, 2), Fraction(1)])
def test_latency_floor_carries_no_leverage(n: int, q: Fraction) -> None:
    values = {
        timed_value(n, q, Timing(processing=5, per_choice=2, latency=latency, jitter=3), "claim")
        for latency in (0, 1, 10, 1000)
    }
    assert len(values) == 1


@pytest.mark.parametrize("n", [3, 4, 5])
def test_no_timing_gap_recovers_plain_monty(n: int) -> None:
    timing = Timing(processing=5, per_choice=0, latency=4, jitter=2)
    for q in (Fraction(0), Fraction(1, 3), Fraction(1)):
        assert timed_value(n, q, timing, "claim") == exact_value(GameSpec(n, 1, q), 1, "claim")


def test_arrival_before_causal_floor_has_zero_likelihood() -> None:
    timing = Timing(processing=5, per_choice=1, latency=4, jitter=2)
    for car in range(3):
        for knows in (True, False):
            h = Hypothesis(car, knows)
            for arrival in range(0, 9):
                for door in (1, 2):
                    obs = (door, door == car, arrival)
                    assert timed_likelihood(3, h, obs, timing) == 0
    observations, joint = timed_joint(3, Fraction(1, 2), timing)
    assert min(arrival for _, _, arrival in observations) >= 5 + 4
    assert sum(sum(row) for row in joint) == 1


def test_timing_rejects_negative_parameters() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        Timing(processing=1, per_choice=1, latency=-1, jitter=0)


def test_timed_monte_carlo() -> None:
    timing = Timing(processing=10, per_choice=1, latency=3, jitter=2)
    result = run_timed(4, Fraction(3, 4), timing, "claim", 20000, 5)
    exact = float(timed_value(4, Fraction(3, 4), timing, "claim"))
    assert abs(result.rate - exact) < 4 * np.sqrt(exact * (1 - exact) / result.trials)


def test_policy_monte_carlo() -> None:
    best, _ = best_policy(5, 2)
    assert run_policy(best, "claim", 5000, 3).rate == 1.0
    monty = run_policy(monty_policy(4, 1), "claim", 20000, 3)
    exact = evaluate(monty_policy(4, 1)).value
    assert abs(monty.rate - exact) < 4 * np.sqrt(exact * (1 - exact) / monty.trials)


def test_baseline_two_cpu_reproduces_monty() -> None:
    result = run_baseline(GameSpec(3, 1, Fraction(1)), "claim", 30000, 2019)
    assert abs(result.rate - 2 / 3) < 4 * np.sqrt((2 / 9) / result.trials)


def test_reflexive_lambda_cost_curve() -> None:
    spec = GameSpec(3, 1, Fraction(1))
    for r in (Fraction(0), Fraction(1, 4), Fraction(1, 2)):
        lam = reflexive_lambda(spec, "claim", r, "adversarial")
        assert lam == pytest.approx(1 + np.log2(float(1 - r)))
    assert reflexive_lambda(spec, "claim", Fraction(1), "adversarial") == float("-inf")
