# Reflexivity: the player's committed choice feeds back into where the car ends up, with strength r.
from fractions import Fraction
from typing import Literal

import numpy as np

from branching_monty.branches.engine import (
    Convention,
    GameSpec,
    allowed_decisions,
    tree_joint,
    unopened,
)

Mode = Literal["adversarial", "noise", "self_fulfilling"]


def closed_doors(spec: GameSpec, history: tuple[tuple[int, bool], ...]) -> list[int]:
    return [0, *unopened(spec, history)]


def win_after_feedback(
    posterior_of_choice: Fraction, revealed_car: bool, n_closed: int, r: Fraction, mode: Mode
) -> Fraction:
    if revealed_car:
        return Fraction(1)
    base = (1 - r) * posterior_of_choice
    if mode == "adversarial":
        return base
    if mode == "noise":
        return base + r / n_closed
    return base + r


def reflexive_value(spec: GameSpec, convention: Convention, r: Fraction, mode: Mode) -> Fraction:
    if not 0 <= r <= 1:
        raise ValueError("r must lie in [0, 1]")
    histories, joint = tree_joint(spec, spec.reveals)
    total = Fraction(0)
    for column, history in enumerate(histories):
        weight = sum((joint[c][column] for c in range(spec.n_doors)), Fraction(0))
        options = allowed_decisions(spec, history, convention)
        if not options:
            continue
        cars = {door for door, shows in history if shows}
        n_closed = len(closed_doors(spec, history))
        best = max(
            win_after_feedback(joint[d][column] / weight, d in cars, n_closed, r, mode)
            for d in options
        )
        total += weight * best
    return total


def reflexive_lambda(spec: GameSpec, convention: Convention, r: Fraction, mode: Mode) -> float:
    value = reflexive_value(spec, convention, r, mode)
    return float(np.log2(float(spec.n_doors * value))) if value > 0 else float("-inf")
