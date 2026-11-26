# Two agents exchanging messages over a clocked channel: CPU A hosts, CPU B infers and decides.
import random
from collections.abc import Callable, Hashable
from dataclasses import dataclass
from fractions import Fraction

import numpy as np

from branching_monty.agents.latency import Timing, emission_time, host_pool, timed_joint
from branching_monty.agents.reflexivity import Mode, closed_doors
from branching_monty.agents.signalling import Policy, observation_joint
from branching_monty.branches.engine import (
    Convention,
    GameSpec,
    Hypothesis,
    allowed_decisions,
    sample_world,
    tree_joint,
)


@dataclass(frozen=True, slots=True)
class MonteCarloResult:
    wins: int
    trials: int

    @property
    def rate(self) -> float:
        return self.wins / self.trials

    @property
    def stderr(self) -> float:
        return float(np.sqrt(self.rate * (1 - self.rate) / self.trials))


def _argmax(column: list[Fraction], options: list[int]) -> int | None:
    if not options:
        return None
    return max(options, key=lambda d: (column[d], -d))


def decision_table(spec: GameSpec, convention: Convention) -> dict[Hashable, int | None]:
    histories, joint = tree_joint(spec, spec.reveals)
    table: dict[Hashable, int | None] = {}
    for i, history in enumerate(histories):
        column = [joint[c][i] for c in range(spec.n_doors)]
        table[history] = _argmax(column, allowed_decisions(spec, history, convention))
    return table


@dataclass
class HostCPU:
    spec: GameSpec
    rng: random.Random

    def play(self) -> tuple[Hypothesis, tuple[tuple[int, bool], ...]]:
        return sample_world(self.spec, self.rng)


@dataclass
class PlayerCPU:
    table: dict[Hashable, int | None]

    def decide(self, observation: Hashable) -> int | None:
        return self.table[observation]


def _feedback(
    car: int, choice: int, closed: list[int], r: float, mode: Mode, rng: random.Random
) -> int:
    if rng.random() >= r:
        return car
    if mode == "adversarial":
        return rng.choice([d for d in closed if d != choice]) if car == choice else car
    if mode == "noise":
        return rng.choice(closed)
    return choice


def run_baseline(
    spec: GameSpec,
    convention: Convention,
    trials: int,
    seed: int,
    r: float = 0.0,
    mode: Mode = "adversarial",
) -> MonteCarloResult:
    rng = random.Random(seed)
    host = HostCPU(spec, rng)
    player = PlayerCPU(decision_table(spec, convention))
    wins = 0
    for _ in range(trials):
        truth, history = host.play()
        choice = player.decide(history)
        if choice is None:
            continue
        revealed = {door for door, shows in history if shows}
        car = truth.car
        if choice not in revealed:
            car = _feedback(car, choice, closed_doors(spec, history), r, mode, rng)
        wins += choice == car
    return MonteCarloResult(wins, trials)


def run_timed(
    n_doors: int, q: Fraction, timing: Timing, convention: Convention, trials: int, seed: int
) -> MonteCarloResult:
    rng = random.Random(seed)
    observations, joint = timed_joint(n_doors, q, timing)
    table: dict[Hashable, int | None] = {}
    for i, obs in enumerate(observations):
        column = [joint[c][i] for c in range(n_doors)]
        options = [] if convention == "loss" and obs[1] else list(range(n_doors))
        table[obs] = _argmax(column, options)
    player = PlayerCPU(table)
    wins = 0
    for _ in range(trials):
        h = Hypothesis(rng.randrange(n_doors), rng.random() < q)
        door = rng.choice(host_pool(n_doors, h))
        sent = emission_time(n_doors, h, timing)
        arrival = sent + timing.latency + rng.randint(0, timing.jitter)
        if arrival < sent + timing.latency:
            raise AssertionError("causality violated")
        choice = player.decide((door, door == h.car, arrival))
        wins += choice == h.car
    return MonteCarloResult(wins, trials)


def run_policy(policy: Policy, convention: Convention, trials: int, seed: int) -> MonteCarloResult:
    rng = random.Random(seed)
    joint, keys = observation_joint(policy)
    table: dict[Hashable, int | None] = {}
    for i, key in enumerate(keys):
        column = [Fraction(float(x)).limit_denominator(10**9) for x in joint[:, i]]
        options = [] if convention == "loss" and key[1] is not None else list(range(policy.n_doors))
        table[key] = _argmax(column, options)
    player = PlayerCPU(table)
    decide: Callable[[Hashable], int | None] = player.decide
    wins = 0
    for _ in range(trials):
        car = rng.randrange(policy.n_doors)
        j = rng.choices(range(len(policy.messages)), weights=policy.matrix[car].tolist())[0]
        message = policy.messages[j]
        wins += decide((message, car if car in message else None)) == car
    return MonteCarloResult(wins, trials)
