# Branch engine: each branch is a full hypothesis; observations prune it by Bayes' rule.
import random
from dataclasses import dataclass, field
from fractions import Fraction
from functools import cache
from typing import Any, Literal

import numpy as np

from branching_monty.core.leverage import Leverage, entropy, leverage

Observation = tuple[int, bool]
History = tuple[Observation, ...]
Convention = Literal["claim", "loss"]


@dataclass(frozen=True, slots=True)
class GameSpec:
    n_doors: int
    reveals: int
    q: Fraction

    def __post_init__(self) -> None:
        if self.n_doors < 3:
            raise ValueError("n_doors must be at least 3")
        if not 0 <= self.reveals <= self.n_doors - 2:
            raise ValueError("reveals must lie between 0 and n_doors - 2")
        if not 0 <= self.q <= 1:
            raise ValueError("q must lie in [0, 1]")


@dataclass(frozen=True, slots=True, order=True)
class Hypothesis:
    car: int
    host_knows: bool


@dataclass(frozen=True, slots=True)
class StepLog:
    step: int
    observation: Observation | None
    live_branches: int
    posterior_entropy: float
    min_entropy: float
    ensemble_lambda: float
    ensemble_info: float


@dataclass
class BranchRecord:
    hypothesis: Hypothesis
    weights: list[Fraction] = field(default_factory=list)


def prior(spec: GameSpec) -> dict[Hypothesis, Fraction]:
    share = Fraction(1, spec.n_doors)
    return {
        Hypothesis(car, knows): share * (spec.q if knows else 1 - spec.q)
        for car in range(spec.n_doors)
        for knows in (True, False)
    }


def unopened(spec: GameSpec, history: History) -> list[int]:
    opened = {door for door, _ in history}
    return [door for door in range(1, spec.n_doors) if door not in opened]


def likelihood(spec: GameSpec, h: Hypothesis, history: History, obs: Observation) -> Fraction:
    door, shows_car = obs
    candidates = unopened(spec, history)
    if door not in candidates or shows_car != (door == h.car):
        return Fraction(0)
    if not h.host_knows:
        return Fraction(1, len(candidates))
    goats = [d for d in candidates if d != h.car]
    return Fraction(0) if shows_car else Fraction(1, len(goats))


def observations(spec: GameSpec, history: History) -> list[Observation]:
    return [(door, shows) for door in unopened(spec, history) for shows in (False, True)]


def allowed_decisions(spec: GameSpec, history: History, convention: Convention) -> list[int]:
    cars = [door for door, shows in history if shows]
    if convention == "loss" and cars:
        return []
    return [0, *unopened(spec, history), *cars]


def tree_joint(spec: GameSpec, steps: int) -> tuple[list[History], list[list[Fraction]]]:
    layer: list[tuple[History, dict[Hypothesis, Fraction]]] = [((), prior(spec))]
    for _ in range(steps):
        following = []
        for history, weights in layer:
            for obs in observations(spec, history):
                updated = {h: w * likelihood(spec, h, history, obs) for h, w in weights.items()}
                if any(updated.values()):
                    following.append(((*history, obs), updated))
        layer = following
    histories = [history for history, _ in layer]
    joint = [[Fraction(0)] * len(layer) for _ in range(spec.n_doors)]
    for column, (_, weights) in enumerate(layer):
        for h, w in weights.items():
            joint[h.car][column] += w
    return histories, joint


def exact_value(spec: GameSpec, steps: int, convention: Convention) -> Fraction:
    histories, joint = tree_joint(spec, steps)
    total = Fraction(0)
    for column, history in enumerate(histories):
        options = [joint[d][column] for d in allowed_decisions(spec, history, convention)]
        total += max(options, default=Fraction(0))
    return total


@cache
def ensemble_leverage(spec: GameSpec, steps: int, convention: Convention) -> Leverage:
    histories, joint = tree_joint(spec, steps)
    probs = np.array([[float(x) for x in row] for row in joint])
    mask = np.zeros((len(histories), spec.n_doors), dtype=bool)
    for column, history in enumerate(histories):
        mask[column, allowed_decisions(spec, history, convention)] = True
    return leverage(probs, mask)


class BranchEngine:
    def __init__(self, spec: GameSpec, convention: Convention = "claim") -> None:
        self.spec = spec
        self.convention = convention
        self.history: History = ()
        self.weights = prior(spec)
        self.warehouse = {h: BranchRecord(h) for h in sorted(self.weights)}
        self.log: list[StepLog] = []
        self._ensemble = [ensemble_leverage(spec, k, convention) for k in range(spec.reveals + 1)]
        self._record(None)

    @property
    def evidence(self) -> Fraction:
        return sum(self.weights.values(), Fraction(0))

    def posterior(self) -> dict[Hypothesis, Fraction]:
        evidence = self.evidence
        return {h: w / evidence for h, w in self.weights.items()}

    def posterior_car(self) -> list[Fraction]:
        marginal = [Fraction(0)] * self.spec.n_doors
        for h, p in self.posterior().items():
            marginal[h.car] += p
        return marginal

    def observe(self, obs: Observation) -> StepLog:
        if len(self.history) >= self.spec.reveals:
            raise ValueError("no reveals left")
        updated = {
            h: w * likelihood(self.spec, h, self.history, obs) for h, w in self.weights.items()
        }
        if not any(updated.values()):
            raise ValueError(f"observation {obs} is impossible under every live branch")
        self.weights = updated
        self.history = (*self.history, obs)
        return self._record(obs)

    def best_decision(self) -> tuple[int | None, Fraction]:
        marginal = self.posterior_car()
        options = allowed_decisions(self.spec, self.history, self.convention)
        if not options:
            return None, Fraction(0)
        door = max(options, key=lambda d: (marginal[d], -d))
        return door, marginal[door]

    def _record(self, obs: Observation | None) -> StepLog:
        posterior = self.posterior()
        for h, record in self.warehouse.items():
            record.weights.append(posterior[h])
        marginal = np.array([float(p) for p in self.posterior_car()])
        ensemble = self._ensemble[len(self.history)]
        entry = StepLog(
            step=len(self.history),
            observation=obs,
            live_branches=sum(1 for w in self.weights.values() if w > 0),
            posterior_entropy=entropy(marginal),
            min_entropy=float(-np.log2(marginal.max())),
            ensemble_lambda=ensemble.lam,
            ensemble_info=ensemble.info,
        )
        self.log.append(entry)
        return entry

    def to_json(self) -> dict[str, Any]:
        return {
            "spec": {
                "n_doors": self.spec.n_doors,
                "reveals": self.spec.reveals,
                "q": str(self.spec.q),
                "convention": self.convention,
            },
            "history": [list(obs) for obs in self.history],
            "branches": [
                {
                    "car": record.hypothesis.car,
                    "host_knows": record.hypothesis.host_knows,
                    "weights": [str(w) for w in record.weights],
                }
                for record in self.warehouse.values()
            ],
            "log": [
                {
                    "step": entry.step,
                    "observation": list(entry.observation) if entry.observation else None,
                    "live_branches": entry.live_branches,
                    "posterior_entropy": entry.posterior_entropy,
                    "min_entropy": entry.min_entropy,
                    "ensemble_lambda": entry.ensemble_lambda,
                    "ensemble_info": entry.ensemble_info,
                }
                for entry in self.log
            ],
        }


def sample_world(spec: GameSpec, rng: random.Random) -> tuple[Hypothesis, History]:
    car = rng.randrange(spec.n_doors)
    knows = rng.random() < spec.q
    h = Hypothesis(car, knows)
    history: History = ()
    for _ in range(spec.reveals):
        candidates = unopened(spec, history)
        pool = [d for d in candidates if d != car] if knows else candidates
        door = rng.choice(pool)
        history = (*history, (door, door == car))
    return h, history
