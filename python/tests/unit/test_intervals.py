from math import sqrt

import pytest

from monty_hall.analysis.intervals import wilson_interval, z_score


def test_wilson_matches_reference_value() -> None:
    interval = wilson_interval(50, 100, 0.95)
    assert interval.lower == pytest.approx(0.40383, abs=1e-4)
    assert interval.upper == pytest.approx(0.59617, abs=1e-4)


@pytest.mark.parametrize(("successes", "trials"), [(1, 3), (343, 675), (332, 675), (5034, 10000)])
def test_wilson_95_uses_the_spec_z_constant_bit_for_bit(successes: int, trials: int) -> None:
    z = 1.959963984540054
    z_squared = z * z
    rate = successes / trials
    denominator = 1 + z_squared / trials
    center = (rate + z_squared / (2 * trials)) / denominator
    margin = z * sqrt(rate * (1 - rate) / trials + z_squared / (4 * trials**2)) / denominator
    interval = wilson_interval(successes, trials, 0.95)
    assert (interval.lower, interval.upper) == (center - margin, center + margin)


def test_wilson_extremes_reach_bounds() -> None:
    assert wilson_interval(0, 10).lower == 0.0
    assert wilson_interval(10, 10).upper == 1.0


@pytest.mark.parametrize(
    ("successes", "trials", "confidence"),
    [(1, 0, 0.95), (-1, 5, 0.95), (6, 5, 0.95), (1, 5, 0.0), (1, 5, 1.0)],
)
def test_wilson_rejects_invalid_input(successes: int, trials: int, confidence: float) -> None:
    with pytest.raises(ValueError, match="must be"):
        wilson_interval(successes, trials, confidence)


def test_z_score_value() -> None:
    assert z_score(60, 100, 0.5) == pytest.approx(2.0)


@pytest.mark.parametrize(("trials", "expected"), [(0, 0.5), (10, 0.0), (10, 1.0)])
def test_z_score_rejects_invalid_input(trials: int, expected: float) -> None:
    with pytest.raises(ValueError, match="must be"):
        z_score(1, trials, expected)
