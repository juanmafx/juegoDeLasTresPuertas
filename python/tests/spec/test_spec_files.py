import json
import re
import subprocess
import sys
from fractions import Fraction
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from monty_hall.lab.cli import exact_report, optimum_report, simulate_report
from monty_hall.lab.model import Strategy, parse_fraction, scenario_from_json

ROOT = Path(__file__).resolve().parents[3]
SPEC = ROOT / "spec"
FRACTION = re.compile(r"-?\d+/\d+")
SCENARIOS: list[dict[str, Any]] = json.loads((SPEC / "scenarios.json").read_text("utf-8"))[
    "scenarios"
]


def _validator(name: str) -> Any:
    schemas = [
        json.loads((SPEC / f).read_text("utf-8"))
        for f in ("scenario.schema.json", "cli-output.schema.json")
    ]
    for schema in schemas:
        Draft202012Validator.check_schema(schema)
    registry: Registry[Any] = Registry().with_resources(
        [(schema["$id"], Resource.from_contents(schema)) for schema in schemas]
    )
    target = next(s for s in schemas if s["$id"].endswith(name))
    return Draft202012Validator(target, registry=registry)


def test_scenario_file_matches_schema() -> None:
    document = json.loads((SPEC / "scenarios.json").read_text("utf-8"))
    errors = [error.message for error in _validator("scenario.schema.json").iter_errors(document)]
    assert errors == []


def test_scenario_coverage() -> None:
    assert len(SCENARIOS) >= 40
    assert {e["scenario"]["host"] for e in SCENARIOS} == {
        "informed",
        "random",
        "biased",
        "adversarial",
    }
    assert {e["optimum"]["strategy"] for e in SCENARIOS if "optimum" in e} == {
        "stay",
        "switch",
        "mixed",
    }
    doors = {e["scenario"]["doors"] for e in SCENARIOS}
    assert {3, 64} <= doors
    assert any(e["scenario"]["reveals"] == 0 for e in SCENARIOS)
    assert any(e["scenario"]["prizes"] == e["scenario"]["doors"] - 2 for e in SCENARIOS)
    assert any(e["scenario"]["prior"] != "uniform" for e in SCENARIOS)
    assert any(e["scenario"]["observed"] is not None for e in SCENARIOS)


@pytest.mark.parametrize("entry", SCENARIOS, ids=lambda e: e["id"])
def test_reference_matches_independent_enumerator(entry: dict[str, Any]) -> None:
    scenario = scenario_from_json(entry["scenario"])
    expected = entry["expected"]
    exact = exact_report(scenario)
    assert {k: exact[k] for k in ("prize_at_pick", "outcomes", "win")} == expected["exact"]
    if "optimum" in entry:
        strategy = Strategy(entry["optimum"]["strategy"])
        report = optimum_report(scenario, strategy, parse_fraction(entry["optimum"]["cost"]))
        assert {k: report[k] for k in ("curve", "optimum", "parabola")} == expected["optimum"]


@pytest.mark.parametrize(
    ("identifier", "stay", "switch"),
    [
        ("classic-informed", "1/3", "2/3"),
        ("classic-random", "1/2", "1/2"),
        ("classic-adversarial", "1/1", "0/1"),
        ("biased-p3-4-lower-opened", "3/7", "4/7"),
        ("biased-p3-4-upper-opened", "1/5", "4/5"),
    ],
)
def test_textbook_anchors(identifier: str, stay: str, switch: str) -> None:
    entry = next(e for e in SCENARIOS if e["id"] == identifier)
    win = entry["expected"]["exact"]["win"]
    assert (win["stay"], win["switch"]) == (stay, switch)


def _strings(node: Any) -> list[str]:
    if isinstance(node, str):
        return [node]
    if isinstance(node, dict):
        return [text for value in node.values() for text in _strings(value)]
    if isinstance(node, list):
        return [text for value in node for text in _strings(value)]
    return []


def test_expected_fractions_are_reduced() -> None:
    fractions = [t for e in SCENARIOS for t in _strings(e["expected"]) if FRACTION.fullmatch(t)]
    assert len(fractions) > 500
    for text in fractions:
        numerator, denominator = text.split("/")
        value = Fraction(int(numerator), int(denominator))
        assert f"{value.numerator}/{value.denominator}" == text


def test_cli_outputs_match_output_schema() -> None:
    validator = _validator("cli-output.schema.json")
    for entry in SCENARIOS:
        scenario = scenario_from_json(entry["scenario"])
        assert list(validator.iter_errors(exact_report(scenario))) == []
        if "simulation" in entry:
            report = simulate_report(scenario, 200, entry["simulation"]["seed"])
            assert list(validator.iter_errors(report)) == []
        if "optimum" in entry:
            strategy = Strategy(entry["optimum"]["strategy"])
            report = optimum_report(scenario, strategy, parse_fraction(entry["optimum"]["cost"]))
            assert list(validator.iter_errors(report)) == []


def test_enumerator_check_passes() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-I",
            str(ROOT / "tools" / "enumerate.py"),
            str(SPEC / "scenarios.json"),
            "--check",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_generated_spec_data_is_current() -> None:
    completed = subprocess.run(
        [sys.executable, str(ROOT / "python" / "tools" / "write_spec_data.py"), "--check"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
