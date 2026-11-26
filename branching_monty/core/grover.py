# One-query generalized Grover search: oracle phase phi, diffusion phase theta.
import numpy as np
from numpy.typing import NDArray

ComplexVector = NDArray[np.complex128]
ComplexMatrix = NDArray[np.complex128]


def uniform_state(n: int) -> ComplexVector:
    return np.full(n, 1 / np.sqrt(n), dtype=np.complex128)


def oracle(phi: float, n: int, target: int) -> ComplexMatrix:
    diagonal = np.ones(n, dtype=np.complex128)
    diagonal[target] = np.exp(1j * phi)
    return np.diag(diagonal)


def diffusion(theta: float, n: int) -> ComplexMatrix:
    s = uniform_state(n)
    return np.eye(n, dtype=np.complex128) + (np.exp(1j * theta) - 1) * np.outer(s, s.conj())


def grover_states(
    phi: float, theta: float, n: int, target: int
) -> tuple[ComplexVector, ComplexVector, ComplexVector]:
    initial = uniform_state(n)
    marked = oracle(phi, n, target) @ initial
    final = diffusion(theta, n) @ marked
    return initial, marked, final


def grover_success(phi: float, theta: float, n: int, target: int) -> float:
    final = grover_states(phi, theta, n, target)[2]
    return float(abs(final[target]) ** 2)


def density(vector: ComplexVector) -> ComplexMatrix:
    return np.outer(vector, vector.conj())
