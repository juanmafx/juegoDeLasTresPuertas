# Latency as a causal constraint: arrival times prune host branches that could not produce them.
from dataclasses import dataclass
from fractions import Fraction

import numpy as np

from branching_monty.branches.engine import Convention, GameSpec, Hypothesis, prior
from branching_monty.core.leverage import Leverage, leverage

TimedObservation = tuple[int, bool, int]


@dataclass(frozen=True, slots=True)
class Timing:
    processing: int
    per_choice: int
    latency: int
    jitter: int

    def __post_init__(self) -> None:
        if min(self.processing, self.per_choice, self.latency, self.jitter) < 0:
            raise ValueError("timing parameters must be non-negative")


def host_pool(n_doors: int, h: Hypothesis) -> list[int]:
    doors = list(range(1, n_doors))
    return [d for d in doors if d != h.car] if h.host_knows else doors


def emission_time(n_doors: int, h: Hypothesis, timing: Timing) -> int:
    return timing.processing + timing.per_choice * (len(host_pool(n_doors, h)) - 1)


def timed_likelihood(
    n_doors: int, h: Hypothesis, obs: TimedObservation, timing: Timing
) -> Fraction:
    door, shows_car, arrival = obs
    pool = host_pool(n_doors, h)
    if door not in pool or shows_car != (door == h.car):
        return Fraction(0)
    delay = arrival - emission_time(n_doors, h, timing)
    if not timing.latency <= delay <= timing.latency + timing.jitter:
        return Fraction(0)
    return Fraction(1, len(pool)) * Fraction(1, timing.jitter + 1)


def timed_joint(
    n_doors: int, q: Fraction, timing: Timing
) -> tuple[list[TimedObservation], list[list[Fraction]]]:
    weights = prior(GameSpec(n_doors, 1, q))
    emissions = {emission_time(n_doors, h, timing) for h in weights}
    arrivals = sorted({e + timing.latency + j for e in emissions for j in range(timing.jitter + 1)})
    observations: list[TimedObservation] = [
        (door, shows, arrival)
        for door in range(1, n_doors)
        for shows in (False, True)
        for arrival in arrivals
    ]
    joint = [[Fraction(0)] * len(observations) for _ in range(n_doors)]
    for column, obs in enumerate(observations):
        for h, w in weights.items():
            joint[h.car][column] += w * timed_likelihood(n_doors, h, obs, timing)
    keep = [i for i in range(len(observations)) if any(joint[c][i] for c in range(n_doors))]
    return [observations[i] for i in keep], [[row[i] for i in keep] for row in joint]


def timed_value(n_doors: int, q: Fraction, timing: Timing, convention: Convention) -> Fraction:
    observations, joint = timed_joint(n_doors, q, timing)
    total = Fraction(0)
    for column, (_, shows, _) in enumerate(observations):
        if convention == "loss" and shows:
            continue
        total += max(joint[c][column] for c in range(n_doors))
    return total


def timed_leverage(n_doors: int, q: Fraction, timing: Timing, convention: Convention) -> Leverage:
    observations, joint = timed_joint(n_doors, q, timing)
    probs = np.array([[float(x) for x in row] for row in joint])
    mask = np.ones((len(observations), n_doors), dtype=bool)
    if convention == "loss":
        for row, (_, shows, _) in enumerate(observations):
            if shows:
                mask[row] = False
    return leverage(probs, mask)
