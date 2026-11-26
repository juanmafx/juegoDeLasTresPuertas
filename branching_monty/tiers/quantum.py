# Quantum tier: one-query search, partial oracles, dephasing and optimal one-query discrimination.
import numpy as np
from numpy.typing import NDArray
from scipy.optimize import brentq

from branching_monty.core.grover import density, diffusion, oracle, uniform_state
from branching_monty.core.holevo import guess_probability
from branching_monty.core.wigner import mana

FloatArray = NDArray[np.float64]
ComplexMatrix = NDArray[np.complex128]


def success_grid(n: int, phis: FloatArray, thetas: FloatArray) -> FloatArray:
    phi, theta = np.meshgrid(phis, thetas, indexing="ij")
    overlap = (n - 1 + np.exp(1j * phi)) / n
    amplitude = (np.exp(1j * phi) + (np.exp(1j * theta) - 1) * overlap) / np.sqrt(n)
    return np.asarray(np.abs(amplitude) ** 2, dtype=np.float64)


def post_oracle_mana(phi: float, d: int) -> float:
    return mana(density(oracle(phi, d, 0) @ uniform_state(d)), d)


def best_one_query_closed_form(n: int) -> float:
    return 1.0 if n == 3 else (3 * n - 4) ** 2 / n**3


def oracle_mixture(phi: float, n: int, target: int, q: float) -> ComplexMatrix:
    s = uniform_state(n)
    rho = np.zeros((n, n), dtype=np.complex128)
    for mark in range(n):
        weight = q if mark == target else (1 - q) / (n - 1)
        rho += weight * density(oracle(phi, n, mark) @ s)
    return rho


def partial_oracle_grover(phi: float, theta: float, n: int, q: float) -> float:
    dif = diffusion(theta, n)
    joint = np.zeros((n, n))
    for target in range(n):
        final = dif @ oracle_mixture(phi, n, target, q) @ dif.conj().T
        joint[target] = np.real(np.diag(final)) / n
    return float(joint.max(axis=0).sum())


def partial_oracle_optimum(phi: float, n: int, q: float) -> float:
    states = [oracle_mixture(phi, n, t, q) for t in range(n)]
    return guess_probability(states, [1 / n] * n)


def dephase(rho: ComplexMatrix, gamma: float) -> ComplexMatrix:
    return (1 - gamma) * rho + gamma * np.diag(np.diag(rho))


def dephased_success(phi: float, theta: float, n: int, gamma: float) -> float:
    marked = density(oracle(phi, n, 0) @ uniform_state(n))
    dif = diffusion(theta, n)
    final = dif @ dephase(marked, gamma) @ dif.conj().T
    return float(np.real(final[0, 0]))


def best_phases(n: int) -> tuple[float, float]:
    return (4 * np.pi / 3, 4 * np.pi / 3) if n == 3 else (np.pi, np.pi)


def gamma_star_closed_form(n: int, threshold: float) -> float:
    best = best_one_query_closed_form(n)
    return (best - threshold) / (best - 1 / n)


def gamma_star_numeric(n: int, threshold: float) -> float:
    phi, theta = best_phases(n)
    return float(brentq(lambda g: dephased_success(phi, theta, n, g) - threshold, 0.0, 1.0))


def chirp_oracle(n: int, target: int) -> ComplexMatrix:
    omega = np.exp(2j * np.pi / n)
    x = np.arange(n)
    return np.diag(omega ** (((x - target) ** 2) % n))


def fourier(n: int) -> ComplexMatrix:
    omega = np.exp(2j * np.pi / n)
    j, k = np.meshgrid(np.arange(n), np.arange(n), indexing="ij")
    return np.asarray(omega ** (j * k) / np.sqrt(n), dtype=np.complex128)


def chirp_protocol(n: int) -> list[ComplexMatrix]:
    omega = np.exp(2j * np.pi / n)
    x = np.arange(n)
    unchirp = np.diag(omega ** (-(x**2) % n))
    return [unchirp, fourier(n).conj().T]


def chirp_success(n: int, target: int) -> tuple[int, float]:
    state = chirp_oracle(n, target) @ uniform_state(n)
    for gate in chirp_protocol(n):
        state = gate @ state
    probs = np.abs(state) ** 2
    outcome = int(np.argmax(probs))
    return outcome, float(probs[outcome])
