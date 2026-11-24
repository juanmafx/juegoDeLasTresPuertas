# Exploration value curve V(K) = P(win) - c*K, its exact optimum and its least-squares parabola.
from dataclasses import dataclass
from fractions import Fraction
from math import floor

from monty_hall.lab.model import Scenario, ScenarioError, Strategy
from monty_hall.lab.solver import solve


@dataclass(frozen=True, slots=True)
class CurvePoint:
    reveals: int
    win: Fraction
    value: Fraction


@dataclass(frozen=True, slots=True)
class Parabola:
    a: Fraction
    b: Fraction
    c: Fraction
    residual_sum_of_squares: Fraction
    vertex_reveals: Fraction | None
    vertex_value: Fraction | None
    fitted_choice: int
    rounded_vertex: int | None

    @property
    def shape(self) -> str:
        if self.a < 0:
            return "concave"
        return "convex" if self.a > 0 else "linear"

    def at(self, k: Fraction) -> Fraction:
        return self.a * k * k + self.b * k + self.c


@dataclass(frozen=True, slots=True)
class OptimumResult:
    strategy: Strategy
    cost: Fraction
    curve: list[CurvePoint]
    best: CurvePoint
    parabola: Parabola | None


def _determinant(m: list[list[Fraction]]) -> Fraction:
    return (
        m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1])
        - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
        + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0])
    )


def fit_parabola(points: list[tuple[int, Fraction]]) -> tuple[Fraction, Fraction, Fraction]:
    s = [sum((Fraction(k) ** power for k, _ in points), Fraction(0)) for power in range(5)]
    t = [sum((v * Fraction(k) ** power for k, v in points), Fraction(0)) for power in range(3)]
    matrix = [[s[4], s[3], s[2]], [s[3], s[2], s[1]], [s[2], s[1], s[0]]]
    rhs = [t[2], t[1], t[0]]
    determinant = _determinant(matrix)
    coefficients = []
    for column in range(3):
        replaced = [
            [rhs[row] if j == column else matrix[row][j] for j in range(3)] for row in range(3)
        ]
        coefficients.append(_determinant(replaced) / determinant)
    return coefficients[0], coefficients[1], coefficients[2]


def _build_parabola(curve: list[CurvePoint]) -> Parabola | None:
    if len(curve) < 3:
        return None
    a, b, c = fit_parabola([(p.reveals, p.value) for p in curve])
    residual = sum(
        ((a * p.reveals**2 + b * p.reveals + c - p.value) ** 2 for p in curve), Fraction(0)
    )
    fitted = [a * p.reveals**2 + b * p.reveals + c for p in curve]
    fitted_choice = curve[fitted.index(max(fitted))].reveals
    if a == 0:
        return Parabola(a, b, c, residual, None, None, fitted_choice, None)
    vertex = -b / (2 * a)
    highest = curve[-1].reveals
    rounded = min(max(floor(vertex + Fraction(1, 2)), 0), highest)
    return Parabola(a, b, c, residual, vertex, c - b * b / (4 * a), fitted_choice, rounded)


def optimum_curve(scenario: Scenario, strategy: Strategy, cost: Fraction) -> OptimumResult:
    if scenario.observed is not None:
        raise ScenarioError("optimum does not accept an observed reveal")
    if cost < 0:
        raise ScenarioError("cost must be a non-negative fraction")
    curve = []
    for reveals in range(scenario.max_reveals + 1):
        win = solve(scenario.with_reveals(reveals)).win(strategy, scenario.mixed)
        if win is None:
            raise ScenarioError("optimum is undefined when the host never offers a decision")
        curve.append(CurvePoint(reveals, win, win - cost * reveals))
    best = curve[0]
    for point in curve[1:]:
        if point.value > best.value:
            best = point
    return OptimumResult(strategy, cost, curve, best, _build_parabola(curve))
