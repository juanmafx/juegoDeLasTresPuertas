# Car-by-action joint distribution for the partially informed host. The player holds door 0.
from dataclasses import dataclass
from typing import Literal

import numpy as np
from numpy.typing import NDArray

Action = tuple[int, bool]
Convention = Literal["claim", "loss"]


@dataclass(frozen=True)
class HostJoint:
    probs: NDArray[np.float64]
    actions: tuple[Action, ...]

    @property
    def n_doors(self) -> int:
        return int(self.probs.shape[0])


def host_joint(q: float, n_doors: int) -> HostJoint:
    if not 0 <= q <= 1:
        raise ValueError("q must lie in [0, 1]")
    if n_doors < 3:
        raise ValueError("n_doors must be at least 3")
    actions = tuple((door, shows_car) for door in range(1, n_doors) for shows_car in (False, True))
    index = {action: i for i, action in enumerate(actions)}
    probs = np.zeros((n_doors, len(actions)))
    others = n_doors - 1
    for car in range(n_doors):
        goat_doors = [door for door in range(1, n_doors) if door != car]
        for door in range(1, n_doors):
            informed = 1 / len(goat_doors) if door in goat_doors else 0.0
            likelihood = q * informed + (1 - q) / others
            probs[car, index[(door, door == car)]] += likelihood / n_doors
    keep = probs.sum(axis=0) > 0
    return HostJoint(probs[:, keep], tuple(a for a, k in zip(actions, keep, strict=True) if k))


def decision_mask(joint: HostJoint, convention: Convention) -> NDArray[np.bool_]:
    mask = np.ones((len(joint.actions), joint.n_doors), dtype=bool)
    if convention == "loss":
        for row, (_, shows_car) in enumerate(joint.actions):
            if shows_car:
                mask[row] = False
    return mask


def success_given_goat(joint: HostJoint) -> float:
    goat = [i for i, (_, shows_car) in enumerate(joint.actions) if not shows_car]
    sub = joint.probs[:, goat]
    return float(sub.max(axis=0).sum() / sub.sum())
