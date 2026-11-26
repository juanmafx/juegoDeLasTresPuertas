# Leverage metric: Bayes value V, Lambda = log2(N V), information spent I, efficiency.
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]


@dataclass(frozen=True)
class Leverage:
    value: float
    lam: float
    info: float
    efficiency: float


def entropy(p: FloatArray) -> float:
    p = np.asarray(p, dtype=np.float64).ravel()
    p = p[p > 1e-15]
    return float(-(p * np.log2(p)).sum())


def mutual_information(joint: FloatArray) -> float:
    return entropy(joint.sum(axis=1)) + entropy(joint.sum(axis=0)) - entropy(joint)


def conditional_min_entropy(joint: FloatArray) -> float:
    return float(-np.log2(joint.max(axis=0).sum()))


def bayes_value(joint: FloatArray, allowed: NDArray[np.bool_] | None = None) -> float:
    if allowed is None:
        return float(joint.max(axis=0).sum())
    masked = np.where(allowed.T, joint, 0.0)
    return float(masked.max(axis=0).sum())


def leverage(joint: FloatArray, allowed: NDArray[np.bool_] | None = None) -> Leverage:
    n = joint.shape[0]
    value = bayes_value(joint, allowed)
    lam = float(np.log2(n * value)) if value > 0 else float("-inf")
    info = mutual_information(joint)
    return Leverage(value, lam, info, efficiency(lam, info))


def efficiency(lam: float, info: float) -> float:
    if info > 1e-12:
        return lam / info
    return 0.0 if abs(lam) < 1e-12 else float("inf")
