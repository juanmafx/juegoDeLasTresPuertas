# Regenerates spec/prng-vectors.json and spec/simulation-reference.json from this reference package.
import argparse
import json
import sys
from pathlib import Path
from typing import Any

from monty_hall.lab.cli import build_parser, prng_report, simulate_report
from monty_hall.lab.model import scenario_from_json

SPEC = Path(__file__).resolve().parents[2] / "spec"
SEEDS = [0, 1, 42, 20190925, 2**63 - 1]
BOUNDS = [1, 2, 3, 6, 10, 64, 1_000_003, 2**62 + 1, 2**63 - 1]
WEIGHTS = [[1, 1, 1], [1, 3, 1], [0, 5, 0, 2], [1_000_000, 1, 0, 7], [7]]
SIZES = [1, 2, 3, 10, 64]


def _prng(arguments: list[str]) -> dict[str, Any]:
    report = prng_report(build_parser().parse_args(["prng", *arguments]))
    report.pop("command")
    return report


def prng_vectors() -> dict[str, Any]:
    vectors = []
    for seed in SEEDS:
        base = ["--seed", str(seed)]
        vectors.append(_prng([*base, "--kind", "splitmix", "--count", "4"]))
        vectors.append(_prng([*base, "--kind", "words", "--count", "8"]))
        for bound in BOUNDS:
            vectors.append(
                _prng([*base, "--kind", "bounded", "--bound", str(bound), "--count", "8"])
            )
        for weights in WEIGHTS:
            joined = ",".join(map(str, weights))
            vectors.append(
                _prng([*base, "--kind", "weighted", "--weights", joined, "--count", "12"])
            )
        for size in SIZES:
            vectors.append(_prng([*base, "--kind", "shuffle", "--size", str(size)]))
    for index, vector in enumerate(vectors):
        vector["count"] = len(vector["values"])
        vector["id"] = f"v{index:03d}-{vector['kind']}-seed-{vector['seed']}"
    return {"version": 1, "vectors": vectors}


def simulation_reference() -> dict[str, Any]:
    scenarios = json.loads((SPEC / "scenarios.json").read_text("utf-8"))["scenarios"]
    runs = []
    for entry in scenarios:
        if "simulation" not in entry:
            continue
        seed, trials = entry["simulation"]["seed"], entry["simulation"]["trials"]
        report = simulate_report(scenario_from_json(entry["scenario"]), trials, seed)
        runs.append(
            {
                "id": entry["id"],
                "seed": seed,
                "trials": trials,
                "counts": report["counts"],
                "sample_size": report["sample_size"],
                "wins": {name: s["wins"] for name, s in report["strategies"].items()},
            }
        )
    return {"version": 1, "runs": runs}


def render(document: dict[str, Any]) -> str:
    return json.dumps(document, indent=2) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    outputs = {
        SPEC / "prng-vectors.json": render(prng_vectors()),
        SPEC / "simulation-reference.json": render(simulation_reference()),
    }
    stale = [
        path.name
        for path, text in outputs.items()
        if not path.is_file() or path.read_text("utf-8") != text
    ]
    if args.check:
        print("stale: " + ", ".join(stale) if stale else "spec data is current")
        return 1 if stale else 0
    for path, text in outputs.items():
        path.write_text(text, encoding="utf-8")
    print(f"wrote {len(outputs)} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
