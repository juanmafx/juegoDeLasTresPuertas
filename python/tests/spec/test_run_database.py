import json
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[3]
RECORD = ROOT / "tools" / "record_run.py"
SCHEMA = ROOT / "db" / "schema.sql"
INSERT_RUN = (
    "INSERT INTO lab_runs (implementation, implementation_version, command, doors, prizes, prior,"
    " pick, reveals, host, mixed, seed, trials, output_json) VALUES (:implementation,"
    " :implementation_version, :command, :doors, :prizes, :prior, :pick, :reveals, :host, :mixed,"
    " :seed, :trials, :output_json)"
)


def _lab(*args: str) -> Any:
    completed = subprocess.run(
        [sys.executable, "-m", "monty_hall.lab", *args], capture_output=True, text=True, check=True
    )
    return json.loads(completed.stdout)


def _record(db: Path, implementation: str, *documents: Any) -> subprocess.CompletedProcess[str]:
    files = []
    for index, document in enumerate(documents):
        path = db.parent / f"{implementation}-{index}.json"
        path.write_text(json.dumps(document), encoding="utf-8")
        files.append(str(path))
    return subprocess.run(
        [
            sys.executable,
            "-I",
            str(RECORD),
            "--db",
            str(db),
            "--implementation",
            implementation,
            "--implementation-version",
            "3.0.0",
            *files,
        ],
        capture_output=True,
        text=True,
        check=False,
    )


def test_records_every_command(tmp_path: Path) -> None:
    db = tmp_path / "runs.sqlite3"
    documents = [
        _lab("exact", "--host", "biased", "--host-weights", "1,3,1", "--observed", "2"),
        _lab("simulate", "--host", "random", "--seed", "1", "--trials", "1000"),
        _lab("optimum", "--doors", "10", "--strategy", "switch", "--cost", "1/100"),
    ]
    result = _record(db, "python", *documents)
    assert result.returncode == 0, result.stderr
    with sqlite3.connect(db) as connection:
        exact = connection.execute(
            "SELECT stay_win, switch_win FROM lab_exact_results JOIN lab_runs ON id = run_id"
            " WHERE host = 'biased'"
        ).fetchone()
        counts = connection.execute(
            "SELECT decision, void_games, stay_wins, switch_wins FROM lab_simulation_counts"
        ).fetchone()
        optimum = connection.execute(
            "SELECT optimum_reveals, optimum_value, parabola_shape, fitted_choice_reveals"
            " FROM lab_optimum_results"
        ).fetchone()
        stored = connection.execute("SELECT output_json FROM lab_runs ORDER BY id").fetchall()
    assert exact == ("1/5", "4/5")
    assert counts == (
        documents[1]["counts"]["decision"],
        documents[1]["counts"]["void"],
        documents[1]["strategies"]["stay"]["wins"],
        documents[1]["strategies"]["switch"]["wins"],
    )
    assert optimum == (8, "41/50", "convex", 8)
    assert [json.loads(row[0]) for row in stored] == documents


def test_disagreement_view_flags_different_counts(tmp_path: Path) -> None:
    db = tmp_path / "runs.sqlite3"
    document = _lab("simulate", "--seed", "7", "--trials", "500")
    assert _record(db, "python", document).returncode == 0
    assert _record(db, "c", document).returncode == 0
    with sqlite3.connect(db) as connection:
        assert connection.execute("SELECT * FROM lab_simulation_disagreements").fetchall() == []
    altered = json.loads(json.dumps(document))
    altered["strategies"]["stay"]["wins"] += 1
    assert _record(db, "java", altered).returncode == 0
    with sqlite3.connect(db) as connection:
        rows = connection.execute(
            "SELECT implementations, distinct_counts FROM lab_simulation_disagreements"
        ).fetchall()
    assert rows == [(3, 2)]


@pytest.mark.parametrize(
    ("column", "value"),
    [
        ("implementation", "rust"),
        ("doors", 65),
        ("command", "prng"),
        ("seed", None),
    ],
)
def test_schema_rejects_invalid_runs(column: str, value: Any) -> None:
    row: dict[str, Any] = {
        "implementation": "python",
        "implementation_version": "3.0.0",
        "command": "simulate",
        "doors": 3,
        "prizes": 1,
        "prior": "uniform",
        "pick": 0,
        "reveals": 1,
        "host": "informed",
        "mixed": "1/2",
        "seed": 1,
        "trials": 10,
        "output_json": json.dumps({"command": "simulate"}),
    }
    connection = sqlite3.connect(":memory:")
    connection.executescript(SCHEMA.read_text(encoding="utf-8"))
    connection.execute(INSERT_RUN, row)
    row[column] = value
    with pytest.raises(sqlite3.IntegrityError):
        connection.execute(INSERT_RUN, row)
    connection.close()


def test_rejects_prng_documents(tmp_path: Path) -> None:
    result = _record(
        tmp_path / "runs.sqlite3", "python", _lab("prng", "--seed", "0", "--kind", "words")
    )
    assert result.returncode == 2
    assert result.stderr.startswith("error: expected an exact, simulate or optimum document")
