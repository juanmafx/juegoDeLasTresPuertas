from fractions import Fraction

import pytest

from monty_hall.analysis.exact import closed_form, enumerate_game_tree
from monty_hall.domain.models import ConfigurationError, GameConfig, HostPolicy


def test_classic_informed_host() -> None:
    result = enumerate_game_tree(GameConfig(), HostPolicy.INFORMED)
    assert (result.stay, result.switch, result.valid_game) == (
        Fraction(1, 3),
        Fraction(2, 3),
        Fraction(1),
    )


def test_classic_random_host_removes_the_advantage() -> None:
    result = enumerate_game_tree(GameConfig(), HostPolicy.RANDOM)
    assert (result.stay, result.switch, result.valid_game) == (
        Fraction(1, 2),
        Fraction(1, 2),
        Fraction(2, 3),
    )


def test_partial_reveal_leaves_switch_below_certainty() -> None:
    result = closed_form(GameConfig(5, 1), HostPolicy.INFORMED)
    assert result.switch == Fraction(4, 15)


def test_enumeration_rejects_large_games() -> None:
    with pytest.raises(ConfigurationError):
        enumerate_game_tree(GameConfig(10, 1), HostPolicy.INFORMED)
