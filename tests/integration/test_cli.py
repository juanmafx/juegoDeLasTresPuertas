import json
import sqlite3
from pathlib import Path

import pytest

from monty_hall.cli.main import main


def test_simulate_json_is_reproducible(capsys: pytest.CaptureFixture[str]) -> None:
    arguments = ["simulate", "--trials", "2000", "--seed", "42", "--format", "json"]
    assert main(arguments) == 0
    first = json.loads(capsys.readouterr().out)
    assert main(arguments) == 0
    assert json.loads(capsys.readouterr().out) == first
    assert first["stay"]["wins"] + first["switch"]["wins"] == 2000


def test_simulate_text_output(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["simulate", "--trials", "500", "--seed", "1"]) == 0
    output = capsys.readouterr().out
    assert "seed=1" in output
    assert "switch" in output


def test_simulate_without_seed_reports_generated_seed(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["simulate", "--trials", "10", "--format", "json"]) == 0
    assert json.loads(capsys.readouterr().out)["seed"] >= 0


def test_simulate_handles_zero_valid_games(capsys: pytest.CaptureFixture[str]) -> None:
    seed = next(
        candidate
        for candidate in range(1000)
        if main(
            [
                "simulate",
                "--doors",
                "3",
                "--host",
                "random",
                "--trials",
                "1",
                "--seed",
                str(candidate),
                "--format",
                "json",
            ]
        )
        == 0
        and json.loads(capsys.readouterr().out)["valid_games"] == 0
    )
    assert main(["simulate", "--host", "random", "--trials", "1", "--seed", str(seed)]) == 0
    assert "no valid games" in capsys.readouterr().out


@pytest.mark.parametrize("flags", [[], ["--enumerate"]])
def test_exact(capsys: pytest.CaptureFixture[str], flags: list[str]) -> None:
    assert main(["exact", "--format", "json", *flags]) == 0
    values = json.loads(capsys.readouterr().out)
    assert (values["stay"], values["switch"]) == ("1/3", "2/3")


def test_exact_text(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["exact", "--doors", "5", "--opened", "3"]) == 0
    assert "switch=4/5" in capsys.readouterr().out


def test_simulate_persists_and_history_lists(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    database = tmp_path / "runs.sqlite3"
    assert main(["simulate", "--trials", "100", "--seed", "3", "--db", str(database)]) == 0
    capsys.readouterr()
    assert main(["history", "--db", str(database)]) == 0
    assert json.loads(capsys.readouterr().out.splitlines()[0])["seed"] == 3


def test_history_does_not_create_missing_database(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    database = tmp_path / "missing.sqlite3"
    assert main(["history", "--db", str(database)]) == 2
    assert not database.exists()
    assert "does not exist" in capsys.readouterr().err


def test_history_never_modifies_a_foreign_database(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    database = tmp_path / "foreign.sqlite3"
    connection = sqlite3.connect(database)
    connection.execute("CREATE TABLE unrelated (id INTEGER)")
    connection.commit()
    connection.close()
    before = database.read_bytes()
    assert main(["history", "--db", str(database)]) == 2
    assert database.read_bytes() == before
    assert capsys.readouterr().err.startswith("error:")


@pytest.mark.parametrize(
    "arguments",
    [
        ["exact", "--doors", "2"],
        ["exact", "--doors", "10", "--enumerate"],
        ["simulate", "--trials", "0"],
        ["simulate", "--seed", "-1"],
    ],
)
def test_invalid_input_exits_with_code_two(
    arguments: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(arguments) == 2
    assert capsys.readouterr().err.startswith("error:")


@pytest.mark.parametrize("confidence", ["abc", "0", "1"])
def test_invalid_confidence_is_rejected(confidence: str) -> None:
    with pytest.raises(SystemExit) as error:
        main(["simulate", "--confidence", confidence])
    assert error.value.code == 2
