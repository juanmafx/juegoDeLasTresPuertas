from fractions import Fraction
from typing import Any

import pytest

from monty_hall.lab.model import (
    Host,
    Scenario,
    ScenarioError,
    format_fraction,
    parse_fraction,
    scenario_from_json,
)


@pytest.mark.parametrize(
    "fields",
    [
        {"doors": 2},
        {"doors": 65},
        {"doors": True},
        {"prizes": 0},
        {"doors": 5, "prizes": 4},
        {"pick": 3},
        {"pick": -1},
        {"reveals": -1},
        {"doors": 5, "prizes": 2, "reveals": 3},
        {"prior": (1, 1)},
        {"mixed": Fraction(3, 2)},
        {"doors": 4, "prizes": 2, "prior": (0, 0, 0, 1)},
        {"prior": (1, 1, 1_000_001)},
        {"host": Host.BIASED},
        {"host_weights": (1, 1, 1)},
        {"host": Host.BIASED, "host_weights": (1, 0, 1)},
        {"mixed": Fraction(-1, 2)},
        {"observed": (0,)},
        {"observed": (1, 2)},
        {"observed": (3,)},
        {"doors": 4, "reveals": 2, "observed": (1, 1)},
    ],
)
def test_rejects_invalid_scenarios(fields: dict[str, Any]) -> None:
    with pytest.raises(ScenarioError):
        Scenario(**fields)


def test_observed_is_normalized_to_ascending_order() -> None:
    assert Scenario(doors=6, reveals=2, observed=(5, 1)).observed == (1, 5)


@pytest.mark.parametrize(
    ("text", "value"), [("1/2", Fraction(1, 2)), ("4/8", Fraction(1, 2)), ("3", Fraction(3))]
)
def test_parse_fraction(text: str, value: Fraction) -> None:
    assert parse_fraction(text) == value


@pytest.mark.parametrize("text", ["", "a/b", "1/0", "1.5"])
def test_parse_fraction_rejects_malformed_text(text: str) -> None:
    with pytest.raises(ScenarioError):
        parse_fraction(text)


def test_format_fraction_always_has_a_denominator() -> None:
    assert format_fraction(Fraction(1)) == "1/1"
    assert format_fraction(Fraction(0)) == "0/1"


def test_json_round_trip() -> None:
    scenario = Scenario(
        doors=5,
        prizes=2,
        prior=(1, 2, 3, 4, 5),
        pick=4,
        reveals=2,
        host=Host.BIASED,
        host_weights=(5, 4, 3, 2, 1),
        mixed=Fraction(1, 3),
        observed=(0, 1),
    )
    assert scenario_from_json(scenario.to_json()) == scenario


@pytest.mark.parametrize(
    "data",
    [{"unknown": 1}, {"host": "lazy"}, {"prior": "skewed"}],
)
def test_scenario_from_json_rejects_unknown_input(data: dict[str, Any]) -> None:
    with pytest.raises(ScenarioError):
        scenario_from_json(data)
