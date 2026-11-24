# Exact solver: closed forms for unobserved games, full enumeration for observed reveals.
from dataclasses import dataclass
from fractions import Fraction
from itertools import combinations
from math import comb

from monty_hall.lab.model import ENUMERATION_MAX_DOORS, Host, Scenario, ScenarioError, Strategy


@dataclass(frozen=True, slots=True)
class ExactResult:
    prize_at_pick: Fraction
    decision: Fraction
    void: Fraction
    no_offer: Fraction
    observed: Fraction | None
    stay: Fraction | None
    switch: Fraction | None

    def mixed(self, q: Fraction) -> Fraction | None:
        if self.stay is None or self.switch is None:
            return None
        return (1 - q) * self.stay + q * self.switch

    def win(self, strategy: Strategy, q: Fraction) -> Fraction | None:
        if strategy is Strategy.STAY:
            return self.stay
        if strategy is Strategy.SWITCH:
            return self.switch
        return self.mixed(q)


def _require_enumerable(scenario: Scenario) -> None:
    if scenario.doors > ENUMERATION_MAX_DOORS:
        raise ScenarioError(
            f"weighted priors and observed reveals support at most {ENUMERATION_MAX_DOORS} doors"
        )


def prize_set_distribution(
    doors: int, prizes: int, weights: tuple[int, ...]
) -> dict[int, Fraction]:
    layer: dict[int, Fraction] = {0: Fraction(1)}
    total = sum(weights)
    for _ in range(prizes):
        following: dict[int, Fraction] = {}
        for mask, probability in layer.items():
            remaining = total - sum(weights[door] for door in range(doors) if mask >> door & 1)
            for door in range(doors):
                if mask >> door & 1 or weights[door] == 0:
                    continue
                key = mask | 1 << door
                following[key] = following.get(key, Fraction(0)) + probability * Fraction(
                    weights[door], remaining
                )
        layer = following
    return layer


def prize_at_pick(scenario: Scenario) -> Fraction:
    if scenario.prior is None:
        return Fraction(scenario.prizes, scenario.doors)
    _require_enumerable(scenario)
    distribution = prize_set_distribution(scenario.doors, scenario.prizes, scenario.prior)
    return sum(
        (p for mask, p in distribution.items() if mask >> scenario.pick & 1),
        Fraction(0),
    )


def _conditional(numerator: Fraction, denominator: Fraction) -> Fraction | None:
    return None if denominator == 0 else numerator / denominator


def closed_form(scenario: Scenario, pi: Fraction) -> ExactResult:
    n, m, k = scenario.doors, scenario.prizes, scenario.reveals
    remaining = n - 1 - k
    zero = Fraction(0)
    if scenario.host in (Host.INFORMED, Host.BIASED):
        return ExactResult(pi, Fraction(1), zero, zero, None, pi, (m - pi) / remaining)
    if scenario.host is Host.ADVERSARIAL:
        offered = pi != 0
        return ExactResult(
            pi,
            pi,
            zero,
            1 - pi,
            None,
            Fraction(1) if offered else None,
            Fraction(m - 1, remaining) if offered else None,
        )
    hit = Fraction(comb(n - m, k), comb(n - 1, k))
    miss = Fraction(comb(n - 1 - m, k), comb(n - 1, k))
    decision = pi * hit + (1 - pi) * miss
    stay = _conditional(pi * hit, decision)
    switch = _conditional((pi * hit * (m - 1) + (1 - pi) * miss * m) / remaining, decision)
    return ExactResult(pi, decision, 1 - decision, zero, None, stay, switch)


def _ordered_sample_probability(
    chosen: tuple[int, ...], pool_weight: int, weights: tuple[int, ...]
) -> Fraction:
    size = len(chosen)
    layer: dict[int, Fraction] = {0: Fraction(1)}
    for _ in range(size):
        following: dict[int, Fraction] = {}
        for mask, probability in layer.items():
            used = sum(weights[chosen[i]] for i in range(size) if mask >> i & 1)
            for i in range(size):
                if mask >> i & 1:
                    continue
                key = mask | 1 << i
                following[key] = following.get(key, Fraction(0)) + probability * Fraction(
                    weights[chosen[i]], pool_weight - used
                )
        layer = following
    return layer.get((1 << size) - 1, Fraction(1))


def _reveal_probability(
    scenario: Scenario, prizes: frozenset[int], observed: tuple[int, ...]
) -> Fraction:
    n, pick, k = scenario.doors, scenario.pick, scenario.reveals
    if scenario.host is Host.RANDOM:
        if prizes.intersection(observed):
            return Fraction(0)
        return Fraction(1, comb(n - 1, k))
    if scenario.host is Host.ADVERSARIAL and pick not in prizes:
        return Fraction(0)
    valid = [door for door in range(n) if door != pick and door not in prizes]
    if not set(observed) <= set(valid):
        return Fraction(0)
    if scenario.host is Host.BIASED and scenario.host_weights is not None:
        weights = scenario.host_weights
        return _ordered_sample_probability(observed, sum(weights[d] for d in valid), weights)
    return Fraction(1, comb(len(valid), k))


def enumerate_observed(scenario: Scenario, pi: Fraction) -> ExactResult:
    observed = scenario.observed
    if observed is None:
        raise ScenarioError("enumeration requires an observed reveal")
    _require_enumerable(scenario)
    n, pick = scenario.doors, scenario.pick
    remaining = [d for d in range(n) if d != pick and d not in observed]
    distribution = prize_set_distribution(n, scenario.prizes, scenario.prior_weights)
    joint = stay = switch = Fraction(0)
    for mask, probability in distribution.items():
        prizes = frozenset(d for d in range(n) if mask >> d & 1)
        weight = probability * _reveal_probability(scenario, prizes, observed)
        if weight == 0:
            continue
        joint += weight
        if pick in prizes:
            stay += weight
        switch += weight * Fraction(sum(1 for d in remaining if d in prizes), len(remaining))
    unobserved = closed_form(scenario, pi)
    return ExactResult(
        pi,
        unobserved.decision,
        unobserved.void,
        unobserved.no_offer,
        joint,
        _conditional(stay, joint),
        _conditional(switch, joint),
    )


def solve(scenario: Scenario) -> ExactResult:
    pi = prize_at_pick(scenario)
    if scenario.observed is not None:
        return enumerate_observed(scenario, pi)
    return closed_form(scenario, pi)


def all_observations(scenario: Scenario) -> list[tuple[int, ...]]:
    others = [d for d in range(scenario.doors) if d != scenario.pick]
    return list(combinations(others, scenario.reveals))
