# Gross discrete Wigner function and mana for odd prime dimension d.
from functools import cache

import numpy as np
from numpy.typing import NDArray


def _require_odd_prime(d: int) -> None:
    if d < 3 or d % 2 == 0 or any(d % k == 0 for k in range(3, int(d**0.5) + 1, 2)):
        raise ValueError(f"d must be an odd prime, got {d}")


def _weyl(a1: int, a2: int, d: int) -> NDArray[np.complex128]:
    omega = np.exp(2j * np.pi / d)
    shift = np.roll(np.eye(d, dtype=np.complex128), 1, axis=0)
    clock = np.diag(omega ** np.arange(d))
    half = pow(2, -1, d)
    phase = omega ** (-(a1 * a2 * half) % d)
    return phase * np.linalg.matrix_power(clock, a1) @ np.linalg.matrix_power(shift, a2)


@cache
def phase_point_operators(d: int) -> NDArray[np.complex128]:
    _require_odd_prime(d)
    origin = sum(_weyl(a1, a2, d) for a1 in range(d) for a2 in range(d)) / d
    operators = np.empty((d, d, d, d), dtype=np.complex128)
    for x in range(d):
        for p in range(d):
            translation = _weyl(p, x, d)
            operators[x, p] = translation @ origin @ translation.conj().T
    return operators


def wigner(rho: NDArray[np.complex128], d: int) -> NDArray[np.float64]:
    operators = phase_point_operators(d)
    values = np.einsum("xpij,ji->xp", operators, rho) / d
    return np.asarray(values.real, dtype=np.float64)


def mana(rho: NDArray[np.complex128], d: int) -> float:
    return float(np.log2(np.abs(wigner(rho, d)).sum()))
