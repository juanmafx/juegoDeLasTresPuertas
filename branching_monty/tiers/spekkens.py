# Spekkens epistemically restricted tier on the d x d phase space Z_d x Z_d, for odd prime d.
from dataclasses import dataclass
from functools import cache
from itertools import product

import numpy as np
from numpy.typing import NDArray

from branching_monty.core.wigner import phase_point_operators, wigner

Point = tuple[int, int]
Distribution = NDArray[np.float64]


class NotRepresentable(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class AffineSymplectic:
    matrix: tuple[tuple[int, int], tuple[int, int]]
    shift: Point
    d: int

    def __call__(self, v: Point) -> Point:
        (a, b), (c, e) = self.matrix
        x, p = v
        return ((a * x + b * p + self.shift[0]) % self.d, (c * x + e * p + self.shift[1]) % self.d)

    def act(self, dist: Distribution) -> Distribution:
        image = np.zeros_like(dist)
        for x, p in product(range(self.d), repeat=2):
            image[self((x, p))] += dist[x, p]
        return image


@cache
def symplectic_group(d: int) -> tuple[tuple[tuple[int, int], tuple[int, int]], ...]:
    return tuple(
        ((a, b), (c, e)) for a, b, c, e in product(range(d), repeat=4) if (a * e - b * c) % d == 1
    )


@cache
def lines(d: int) -> tuple[frozenset[Point], ...]:
    directions = [(0, 1), *[(1, m) for m in range(d)]]
    found: set[frozenset[Point]] = set()
    for dx, dp in directions:
        for x0, p0 in product(range(d), repeat=2):
            found.add(frozenset(((x0 + t * dx) % d, (p0 + t * dp) % d) for t in range(d)))
    return tuple(sorted(found, key=sorted))


def line_state(line: frozenset[Point], d: int) -> Distribution:
    dist = np.zeros((d, d))
    for point in line:
        dist[point] = 1 / d
    return dist


def is_line_state(dist: Distribution, d: int, tol: float = 1e-12) -> bool:
    return any(np.allclose(dist, line_state(line, d), atol=tol) for line in lines(d))


def momentum_eigenstate(p0: int, d: int) -> Distribution:
    return line_state(frozenset((x, p0) for x in range(d)), d)


def represent(unitary: NDArray[np.complex128], d: int, tol: float = 1e-9) -> AffineSymplectic:
    operators = phase_point_operators(d)
    flat = {(x, p): operators[x, p] for x, p in product(range(d), repeat=2)}

    def image(v: Point) -> Point:
        moved = unitary @ flat[v] @ unitary.conj().T
        for w, op in flat.items():
            if np.allclose(moved, op, atol=tol):
                return w
        raise NotRepresentable("gate does not map phase-point operators to phase-point operators")

    shift = image((0, 0))
    e1, e2 = image((1, 0)), image((0, 1))
    column1 = ((e1[0] - shift[0]) % d, (e1[1] - shift[1]) % d)
    column2 = ((e2[0] - shift[0]) % d, (e2[1] - shift[1]) % d)
    matrix = ((column1[0], column2[0]), (column1[1], column2[1]))
    if (matrix[0][0] * matrix[1][1] - matrix[0][1] * matrix[1][0]) % d != 1:
        raise NotRepresentable("induced phase-space map is not symplectic")
    candidate = AffineSymplectic(matrix, shift, d)
    for v in flat:
        if image(v) != candidate(v):
            raise NotRepresentable("induced phase-space map is not affine")
    return candidate


def is_clifford(unitary: NDArray[np.complex128], d: int) -> bool:
    try:
        represent(unitary, d)
    except NotRepresentable:
        return False
    return True


def evolve(initial: Distribution, maps: list[AffineSymplectic]) -> list[Distribution]:
    states = [initial]
    for step in maps:
        states.append(step.act(states[-1]))
    return states


def measure_position(dist: Distribution) -> NDArray[np.float64]:
    return np.asarray(dist.sum(axis=1), dtype=np.float64)


def collapse_position(dist: Distribution, outcome: int) -> Distribution:
    d = dist.shape[0]
    if dist[outcome].sum() <= 0:
        raise ValueError("outcome has zero probability")
    return momentum_free_line(outcome, d)


def momentum_free_line(x0: int, d: int) -> Distribution:
    return line_state(frozenset((x0, p) for p in range(d)), d)


def quantum_wigner_states(states: list[NDArray[np.complex128]], d: int) -> list[Distribution]:
    return [wigner(np.outer(s, s.conj()), d) for s in states]
