import sys
from fractions import Fraction
from typing import Any

import pytest

from monty_hall.lab.model import (
    Host,
    Scenario,
    ScenarioError,
    format_fraction,
    parse_fraction,
    parse_integer,
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
    ("text", "value"),
    [
        ("1/2", Fraction(1, 2)),
        ("4/8", Fraction(1, 2)),
        ("3", Fraction(3)),
        ("-1/-2", Fraction(1, 2)),
        ("-0/5", Fraction(0)),
        (" +1 / 2 ", Fraction(1, 2)),
        ("9223372036854775807/9223372036854775807", Fraction(1)),
        ("1/" + "0" * 50 + "2", Fraction(1, 2)),
    ],
)
def test_parse_fraction(text: str, value: Fraction) -> None:
    assert parse_fraction(text) == value


@pytest.mark.parametrize(
    "text",
    [
        "",
        "a/b",
        "1/0",
        "1.5",
        "1/2/3",
        "1_0/2",
        "\uff11/2",
        "1/\u00a02",
        "1/9223372036854775808",
        "-9223372036854775808",
        "1/1" + "0" * 5000,
    ],
)
def test_parse_fraction_rejects_malformed_text(text: str) -> None:
    with pytest.raises(ScenarioError):
        parse_fraction(text)


@pytest.mark.parametrize(("text", "value"), [("04", 4), (" +4\t", 4), ("-0", 0), ("\f-12 ", -12)])
def test_parse_integer(text: str, value: int) -> None:
    assert parse_integer(text) == value


@pytest.mark.parametrize("text", ["", "+", "1_0", "\u0664", "\uff14", "4\u2003", "0x10", "1e3"])
def test_parse_integer_rejects_anything_but_ascii_decimal(text: str) -> None:
    with pytest.raises(ScenarioError):
        parse_integer(text)


def test_format_fraction_always_has_a_denominator() -> None:
    assert format_fraction(Fraction(1)) == "1/1"
    assert format_fraction(Fraction(0)) == "0/1"


def test_format_fraction_is_not_limited_by_the_integer_string_limit() -> None:
    limit = sys.get_int_max_str_digits()
    text = format_fraction(Fraction(10**6000 + 1, 3))
    assert len(text) == 6003
    assert text.startswith("1" + "0" * 5999)
    assert text.endswith("1/3")
    assert sys.get_int_max_str_digits() == limit


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
