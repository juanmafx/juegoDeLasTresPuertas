import json
import os
import subprocess
import sys

import pytest

from monty_hall.lab.cli import main


def _run(arguments: list[str], capsys: pytest.CaptureFixture[str]) -> dict[str, object]:
    assert main(arguments) == 0
    output: dict[str, object] = json.loads(capsys.readouterr().out)
    return output


def test_exact_defaults_to_the_classic_game(capsys: pytest.CaptureFixture[str]) -> None:
    output = _run(["exact"], capsys)
    assert output["win"] == {"stay": "1/3", "switch": "2/3", "mixed": "1/2"}


def test_biased_observed(capsys: pytest.CaptureFixture[str]) -> None:
    arguments = ["exact", "--host", "biased", "--host-weights", "1,3,1", "--observed", "2"]
    output = _run(arguments, capsys)
    assert output["win"] == {"stay": "1/5", "switch": "4/5", "mixed": "1/2"}
    assert output["outcomes"] == {
        "decision": "1/1",
        "void": "0/1",
        "no_offer": "0/1",
        "observed": "5/12",
    }


def test_simulate_is_reproducible(capsys: pytest.CaptureFixture[str]) -> None:
    arguments = ["simulate", "--seed", "7", "--trials", "500", "--host", "random"]
    assert _run(arguments, capsys) == _run(arguments, capsys)


def test_simulate_empty_sample_reports_null_rates(capsys: pytest.CaptureFixture[str]) -> None:
    arguments = ["simulate", "--seed", "1", "--trials", "50", "--doors", "4"]
    arguments += ["--prior", "0,1,1,1", "--host", "adversarial"]
    output = _run(arguments, capsys)
    assert output["sample_size"] == 0
    assert output["strategies"] == {
        name: {"wins": 0, "rate": None, "wilson95": None} for name in ("stay", "switch", "mixed")
    }


def test_optimum_echoes_null_reveals(capsys: pytest.CaptureFixture[str]) -> None:
    output = _run(["optimum", "--doors", "5", "--strategy", "switch", "--cost", "1/20"], capsys)
    scenario = output["scenario"]
    assert isinstance(scenario, dict)
    assert scenario["reveals"] is None
    assert output["optimum"] == {"reveals": 3, "value": "13/20"}


@pytest.mark.parametrize(
    ("kind", "extra", "values"),
    [
        ("splitmix", [], ["16294208416658607535"]),
        ("words", [], ["11091344671253066420"]),
        ("shuffle", ["--size", "1"], [0]),
        ("weighted", ["--weights", "0,1"], [1]),
    ],
)
def test_prng(
    kind: str, extra: list[str], values: list[object], capsys: pytest.CaptureFixture[str]
) -> None:
    output = _run(["prng", "--seed", "0", "--kind", kind, *extra], capsys)
    assert output["values"] == values


@pytest.mark.parametrize(
    "arguments",
    [
        ["exact", "--doors", "2"],
        ["exact", "--prior", "1,x,1"],
        ["exact", "--mixed", "2/1"],
        ["simulate", "--seed", "-1"],
        ["optimum", "--strategy", "stay", "--cost", "-1"],
        ["prng", "--seed", "0", "--kind", "bounded"],
        ["prng", "--seed", "0", "--kind", "weighted", "--weights", "0,0"],
        ["prng", "--seed", "0", "--kind", "shuffle"],
        ["prng", "--seed", "0", "--kind", "words", "--count", "0"],
        ["prng", "--seed", str(2**63), "--kind", "words"],
    ],
)
def test_invalid_input_exits_with_code_two(
    arguments: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(arguments) == 2
    captured = capsys.readouterr()
    assert captured.err.startswith("error:")
    assert captured.out == ""


def test_module_entry_point_and_closed_pipe() -> None:
    read_end, write_end = os.pipe()
    os.close(read_end)
    completed = subprocess.run(
        [sys.executable, "-m", "monty_hall.lab", "exact"],
        stdout=write_end,
        stderr=subprocess.PIPE,
        check=False,
        text=True,
    )
    os.close(write_end)
    assert completed.returncode == 141
    assert completed.stderr == ""
