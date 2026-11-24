from fractions import Fraction

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from monty_hall.lab.model import Host, Scenario, ScenarioError, Strategy
from monty_hall.lab.optimum import fit_parabola, optimum_curve


def test_value_subtracts_cost_per_reveal() -> None:
    result = optimum_curve(Scenario(doors=5), Strategy.SWITCH, Fraction(1, 20))
    assert [p.value for p in result.curve] == [
        p.win - Fraction(p.reveals, 20) for p in result.curve
    ]
    assert result.best.reveals == 3


def test_two_point_curve_has_no_parabola() -> None:
    assert optimum_curve(Scenario(), Strategy.SWITCH, Fraction(0)).parabola is None


def test_constant_win_gives_a_linear_fit_without_vertex() -> None:
    fit = optimum_curve(Scenario(doors=6), Strategy.STAY, Fraction(1, 50)).parabola
    assert fit is not None
    assert fit.shape == "linear"
    assert fit.a == 0
    assert fit.b == Fraction(-1, 50)
    assert fit.vertex_reveals is None


def test_ties_resolve_to_fewest_reveals() -> None:
    assert optimum_curve(Scenario(doors=6), Strategy.STAY, Fraction(0)).best.reveals == 0


def test_fit_recovers_an_exact_parabola() -> None:
    points = [(k, Fraction(-3) * k * k + Fraction(7, 2) * k + 1) for k in range(6)]
    assert fit_parabola(points) == (Fraction(-3), Fraction(7, 2), Fraction(1))


def test_rejects_observed_and_negative_cost() -> None:
    with pytest.raises(ScenarioError, match="observed"):
        optimum_curve(Scenario(observed=(1,)), Strategy.SWITCH, Fraction(0))
    with pytest.raises(ScenarioError, match="cost"):
        optimum_curve(Scenario(), Strategy.SWITCH, Fraction(-1))


def test_undefined_when_no_decision_is_ever_offered() -> None:
    scenario = Scenario(doors=4, prior=(0, 1, 1, 1), host=Host.ADVERSARIAL)
    with pytest.raises(ScenarioError, match="undefined"):
        optimum_curve(scenario, Strategy.STAY, Fraction(0))


games = st.integers(4, 24).flatmap(
    lambda n: st.tuples(
        st.just(n),
        st.integers(1, n - 3),
        st.sampled_from(list(Host)),
        st.sampled_from(list(Strategy)),
        st.fractions(0, 1, max_denominator=200),
        st.fractions(0, 1, max_denominator=20),
    )
)


@settings(derandomize=True, max_examples=60, deadline=None)
@given(games)
def test_uniform_prior_optimum_is_a_corner(
    game: tuple[int, int, Host, Strategy, Fraction, Fraction],
) -> None:
    doors, prizes, host, strategy, cost, q = game
    weights = tuple(range(1, doors + 1)) if host is Host.BIASED else None
    scenario = Scenario(doors=doors, prizes=prizes, host=host, host_weights=weights, mixed=q)
    result = optimum_curve(scenario, strategy, cost)
    assert result.best.reveals in (0, scenario.max_reveals)
    assert result.parabola is not None
    assert result.parabola.shape in ("convex", "linear")


@settings(derandomize=True, max_examples=40, deadline=None)
@given(games, st.sampled_from([(1, 0, 0), (0, 1, 0), (0, 0, 1)]))
def test_fit_minimizes_squared_error(
    game: tuple[int, int, Host, Strategy, Fraction, Fraction],
    direction: tuple[int, int, int],
) -> None:
    doors, prizes, host, strategy, cost, q = game
    weights = tuple(range(1, doors + 1)) if host is Host.BIASED else None
    scenario = Scenario(doors=doors, prizes=prizes, host=host, host_weights=weights, mixed=q)
    result = optimum_curve(scenario, strategy, cost)
    assert result.parabola is not None
    a, b, c = result.parabola.a, result.parabola.b, result.parabola.c
    step = Fraction(1, 1000)

    def error(da: Fraction, db: Fraction, dc: Fraction) -> Fraction:
        return sum(
            (
                ((a + da) * p.reveals**2 + (b + db) * p.reveals + c + dc - p.value) ** 2
                for p in result.curve
            ),
            Fraction(0),
        )

    da, db, dc = (step * d for d in direction)
    assert error(da, db, dc) > result.parabola.residual_sum_of_squares
    assert error(-da, -db, -dc) > result.parabola.residual_sum_of_squares
