# Committed host signalling policies over k-door reveals: value, information, best and worst design.
from dataclasses import dataclass
from itertools import combinations
from typing import Literal

import numpy as np
from numpy.typing import NDArray
from scipy.optimize import linprog

from branching_monty.core.leverage import Leverage, leverage

Message = tuple[int, ...]
Constraint = Literal["goat_only", "player_door"]
Convention = Literal["claim", "loss"]


@dataclass(frozen=True)
class Policy:
    n_doors: int
    messages: tuple[Message, ...]
    matrix: NDArray[np.float64]
    constraint: Constraint


def messages(n_doors: int, k: int) -> tuple[Message, ...]:
    if not 1 <= k <= n_doors - 2:
        raise ValueError("k must lie between 1 and n_doors - 2")
    return tuple(combinations(range(1, n_doors), k))


def allowed(car: int, message: Message, constraint: Constraint) -> bool:
    return constraint == "player_door" or car not in message


def _check(policy: Policy) -> None:
    for car in range(policy.n_doors):
        for j, message in enumerate(policy.messages):
            if policy.matrix[car, j] > 1e-12 and not allowed(car, message, policy.constraint):
                raise ValueError(f"policy reveals the car at door {car} under {policy.constraint}")
    if not np.allclose(policy.matrix.sum(axis=1), 1):
        raise ValueError("each policy row must sum to 1")


def monty_policy(n_doors: int, k: int) -> Policy:
    msgs = messages(n_doors, k)
    matrix = np.zeros((n_doors, len(msgs)))
    for car in range(n_doors):
        usable = [j for j, m in enumerate(msgs) if car not in m]
        matrix[car, usable] = 1 / len(usable)
    return Policy(n_doors, msgs, matrix, "goat_only")


def observation_joint(
    policy: Policy, prior: NDArray[np.float64] | None = None
) -> tuple[NDArray[np.float64], list[tuple[Message, int | None]]]:
    _check(policy)
    n = policy.n_doors
    prior = np.full(n, 1 / n) if prior is None else prior
    columns: dict[tuple[Message, int | None], NDArray[np.float64]] = {}
    for j, message in enumerate(policy.messages):
        for car in range(n):
            weight = prior[car] * policy.matrix[car, j]
            if weight <= 0:
                continue
            key = (message, car if car in message else None)
            columns.setdefault(key, np.zeros(n))[car] += weight
    keys = list(columns)
    return np.column_stack([columns[k] for k in keys]), keys


def evaluate(
    policy: Policy, convention: Convention = "claim", prior: NDArray[np.float64] | None = None
) -> Leverage:
    joint, keys = observation_joint(policy, prior)
    mask = np.ones((len(keys), policy.n_doors), dtype=bool)
    if convention == "loss":
        for row, (_, revealed) in enumerate(keys):
            if revealed is not None:
                mask[row] = False
    return leverage(joint, mask)


def best_policy(
    n_doors: int, k: int, prior: NDArray[np.float64] | None = None
) -> tuple[Policy, float]:
    msgs = messages(n_doors, k)
    prior = np.full(n_doors, 1 / n_doors) if prior is None else prior
    pairs = [(c, j) for c in range(n_doors) for j, m in enumerate(msgs) if c not in m]
    cost = np.array([-prior[c] for c, _ in pairs])
    rows = []
    for car in range(n_doors):
        rows.append([1.0 if c == car else 0.0 for c, _ in pairs])
    for j in range(len(msgs)):
        rows.append([1.0 if jj == j else 0.0 for _, jj in pairs])
    result = linprog(
        cost, A_ub=np.array(rows), b_ub=np.ones(len(rows)), bounds=(0, 1), method="highs"
    )
    if not result.success:
        raise RuntimeError(result.message)
    matrix = np.zeros((n_doors, len(msgs)))
    for (car, j), x in zip(pairs, result.x, strict=True):
        if x > 0.5:
            matrix[car, j] = 1.0
    for car in range(n_doors):
        if matrix[car].sum() == 0:
            matrix[car, next(j for j, m in enumerate(msgs) if car not in m)] = 1.0
    return Policy(n_doors, msgs, matrix, "goat_only"), float(-result.fun)


def worst_policy(
    n_doors: int, k: int, prior: NDArray[np.float64] | None = None
) -> tuple[Policy, float]:
    msgs = messages(n_doors, k)
    prior = np.full(n_doors, 1 / n_doors) if prior is None else prior
    pairs = [(c, j) for c in range(n_doors) for j, m in enumerate(msgs) if c not in m]
    n_pi, n_t = len(pairs), len(msgs)
    cost = np.concatenate([np.zeros(n_pi), np.ones(n_t)])
    a_ub, b_ub = [], []
    for i, (car, j) in enumerate(pairs):
        row = np.zeros(n_pi + n_t)
        row[i] = prior[car]
        row[n_pi + j] = -1.0
        a_ub.append(row)
        b_ub.append(0.0)
    a_eq, b_eq = [], []
    for car in range(n_doors):
        row = np.zeros(n_pi + n_t)
        for i, (c, _) in enumerate(pairs):
            if c == car:
                row[i] = 1.0
        a_eq.append(row)
        b_eq.append(1.0)
    result = linprog(
        cost,
        A_ub=np.array(a_ub),
        b_ub=np.array(b_ub),
        A_eq=np.array(a_eq),
        b_eq=np.array(b_eq),
        bounds=(0, None),
        method="highs",
    )
    if not result.success:
        raise RuntimeError(result.message)
    matrix = np.zeros((n_doors, len(msgs)))
    for (car, j), x in zip(pairs, result.x[:n_pi], strict=True):
        matrix[car, j] = max(x, 0.0)
    matrix /= matrix.sum(axis=1, keepdims=True)
    return Policy(n_doors, msgs, matrix, "goat_only"), float(result.fun)


def full_disclosure_policy(n_doors: int, k: int) -> Policy:
    msgs = messages(n_doors, k)
    matrix = np.zeros((n_doors, len(msgs)))
    matrix[0, 0] = 1.0
    for car in range(1, n_doors):
        matrix[car, next(j for j, m in enumerate(msgs) if car in m)] = 1.0
    return Policy(n_doors, msgs, matrix, "player_door")
