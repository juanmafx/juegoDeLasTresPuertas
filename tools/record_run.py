# Records monty-lab exact, simulate and optimum JSON documents from any implementation in SQLite.
# Usage: record_run.py --db FILE --implementation NAME --implementation-version V [FILE ...]
import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

SCHEMA = Path(__file__).resolve().parent.parent / "db" / "schema.sql"
IMPLEMENTATIONS = ("python", "java", "php", "c")


def encoded(value: Any) -> str | None:
    if value is None:
        return None
    return json.dumps(value, separators=(",", ":"))


def record(connection: sqlite3.Connection, name: str, version: str, document: Any) -> int:
    if not isinstance(document, dict) or document.get("command") not in (
        "exact",
        "simulate",
        "optimum",
    ):
        raise ValueError("expected an exact, simulate or optimum document")
    command = document["command"]
    scenario = document["scenario"]
    prior = scenario["prior"]
    cursor = connection.execute(
        "INSERT INTO lab_runs (implementation, implementation_version, command, doors, prizes,"
        " prior, pick, reveals, host, host_weights, mixed, observed, seed, trials, strategy,"
        " cost, output_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            name,
            version,
            command,
            scenario["doors"],
            scenario["prizes"],
            prior if prior == "uniform" else encoded(prior),
            scenario["pick"],
            scenario["reveals"],
            scenario["host"],
            encoded(scenario["host_weights"]),
            scenario["mixed"],
            encoded(scenario["observed"]),
            document.get("seed"),
            document.get("trials"),
            document.get("strategy"),
            document.get("cost"),
            json.dumps(document, sort_keys=True),
        ),
    )
    run_id = cursor.lastrowid
    if run_id is None:
        raise ValueError("insert did not return a row id")
    if command == "exact":
        outcomes, win = document["outcomes"], document["win"]
        connection.execute(
            "INSERT INTO lab_exact_results VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                run_id,
                document["prize_at_pick"],
                outcomes["decision"],
                outcomes["void"],
                outcomes["no_offer"],
                outcomes["observed"],
                win["stay"],
                win["switch"],
                win["mixed"],
            ),
        )
    elif command == "simulate":
        counts, strategies = document["counts"], document["strategies"]
        connection.execute(
            "INSERT INTO lab_simulation_counts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                run_id,
                counts["decision"],
                counts["void"],
                counts["no_offer"],
                counts["observed"],
                document["sample_size"],
                strategies["stay"]["wins"],
                strategies["switch"]["wins"],
                strategies["mixed"]["wins"],
            ),
        )
    else:
        parabola = document["parabola"] or {}
        vertex = parabola.get("vertex") or {}
        rounded = parabola.get("rounded_vertex") or {}
        fitted = parabola.get("fitted_choice") or {}
        connection.execute(
            "INSERT INTO lab_optimum_results VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                run_id,
                document["optimum"]["reveals"],
                document["optimum"]["value"],
                parabola.get("shape"),
                vertex.get("reveals"),
                rounded.get("regret"),
                fitted.get("reveals"),
                fitted.get("regret"),
            ),
        )
    return run_id


def main() -> int:
    parser = argparse.ArgumentParser(description="Record monty-lab output in SQLite.")
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--implementation", choices=IMPLEMENTATIONS, required=True)
    parser.add_argument("--implementation-version", required=True)
    parser.add_argument("files", nargs="*", type=Path, help="JSON files; standard input if none")
    options = parser.parse_args()
    texts = [path.read_text(encoding="utf-8") for path in options.files] or [sys.stdin.read()]
    connection = sqlite3.connect(options.db)
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript(SCHEMA.read_text(encoding="utf-8"))
        with connection:
            ids = [
                record(
                    connection,
                    options.implementation,
                    options.implementation_version,
                    json.loads(text),
                )
                for text in texts
            ]
    except (ValueError, KeyError, TypeError, sqlite3.Error) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    finally:
        connection.close()
    print(json.dumps({"recorded": ids}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
