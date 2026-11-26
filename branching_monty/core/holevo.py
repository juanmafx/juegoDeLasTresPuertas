# Holevo information and optimal state discrimination (square-root measurement and SDP).
from collections.abc import Sequence
from typing import Literal

import cvxpy as cp
import numpy as np
from numpy.typing import NDArray

ComplexMatrix = NDArray[np.complex128]


def as_density(state: NDArray[np.complex128]) -> ComplexMatrix:
    state = np.asarray(state, dtype=np.complex128)
    if state.ndim == 1:
        return np.outer(state, state.conj())
    return state


def von_neumann_entropy(rho: ComplexMatrix) -> float:
    eigenvalues = np.linalg.eigvalsh(rho)
    eigenvalues = eigenvalues[eigenvalues > 1e-12]
    return float(-(eigenvalues * np.log2(eigenvalues)).sum())


def holevo_chi(states: Sequence[NDArray[np.complex128]], priors: Sequence[float]) -> float:
    rhos = [as_density(s) for s in states]
    average = sum(p * r for p, r in zip(priors, rhos, strict=True))
    conditional = sum(p * von_neumann_entropy(r) for p, r in zip(priors, rhos, strict=True))
    return von_neumann_entropy(np.asarray(average)) - float(conditional)


def _srm(rhos: list[ComplexMatrix], priors: Sequence[float]) -> float:
    average = sum(p * r for p, r in zip(priors, rhos, strict=True))
    eigenvalues, vectors = np.linalg.eigh(np.asarray(average))
    inverse_root = np.array(
        [1 / np.sqrt(e) if e > 1e-12 else 0.0 for e in eigenvalues], dtype=np.complex128
    )
    root = vectors @ np.diag(inverse_root) @ vectors.conj().T
    success = 0.0
    for p, r in zip(priors, rhos, strict=True):
        effect = root @ (p * r) @ root
        success += p * float(np.real(np.trace(effect @ r)))
    return success


def _sdp(rhos: list[ComplexMatrix], priors: Sequence[float]) -> float:
    d = rhos[0].shape[0]
    effects = [cp.Variable((d, d), hermitian=True) for _ in rhos]
    constraints = [e >> 0 for e in effects]
    constraints.append(sum(effects) == np.eye(d))
    objective = sum(
        p * cp.real(cp.trace(e @ r)) for p, e, r in zip(priors, effects, rhos, strict=True)
    )
    problem = cp.Problem(cp.Maximize(objective), constraints)
    problem.solve(solver=cp.CLARABEL)
    return float(problem.value)


def guess_probability(
    states: Sequence[NDArray[np.complex128]],
    priors: Sequence[float],
    method: Literal["sdp", "srm"] = "sdp",
) -> float:
    rhos = [as_density(s) for s in states]
    return _sdp(rhos, priors) if method == "sdp" else _srm(rhos, priors)
