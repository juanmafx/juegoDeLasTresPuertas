# Runs randomized exact, simulate and optimum invocations through several monty-lab CLIs and
# requires identical exit codes and identical JSON values, floats compared exactly.
import argparse
import json
import random
import shlex
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from typing import Any

Outcome = tuple[int, Any]


def scenario_args(rng: random.Random, command: str) -> list[str]:
    small = command == "exact" or rng.random() < 0.6
    doors = rng.randint(3, 10 if small else 64)
    prizes = rng.randint(1, min(doors - 2, 3))
    pick = rng.randrange(doors)
    host = rng.choice(["informed", "random", "biased", "adversarial"])
    args = [command, "--doors", str(doors), "--prizes", str(prizes), "--pick", str(pick)]
    args += ["--host", host, "--mixed", f"{rng.randint(0, 7)}/7"]
    if doors <= 10 and rng.random() < 0.4:
        weights = [rng.randint(0, 9) for _ in range(doors)]
        for door in [pick, *rng.sample(range(doors), prizes)]:
            weights[door] = max(weights[door], 1)
        args += ["--prior", ",".join(map(str, weights))]
    if host == "biased":
        args += ["--host-weights", ",".join(str(rng.randint(1, 9)) for _ in range(doors))]
    if command == "optimum":
        strategy = rng.choice(["stay", "switch", "mixed"])
        cost = f"{rng.randint(0, 5)}/{rng.randint(1, 60)}"
        return [*args, "--strategy", strategy, "--cost", cost]
    reveals = rng.randint(0, doors - prizes - 1)
    args += ["--reveals", str(reveals)]
    if doors <= 10 and rng.random() < 0.5:
        others = [door for door in range(doors) if door != pick]
        args += ["--observed", ",".join(map(str, sorted(rng.sample(others, reveals))))]
    if command == "simulate":
        args += ["--seed", str(rng.randrange(2**63)), "--trials", str(rng.randint(1, 3000))]
    return args


def invocation(rng: random.Random) -> list[str]:
    args = scenario_args(rng, rng.choice(["exact", "simulate", "optimum"]))
    if rng.random() < 0.05:
        position = args.index("--doors") + 1
        args[position] = rng.choice(["2", "65", "x"])
    return args


def run(cli: str, args: list[str]) -> Outcome:
    completed = subprocess.run(
        [*shlex.split(cli), *args], capture_output=True, text=True, check=False
    )
    if completed.returncode != 0:
        return completed.returncode, completed.stdout
    return 0, json.loads(completed.stdout)


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare monty-lab CLIs against each other.")
    parser.add_argument("--cli", action="append", required=True, help="name=command, repeatable")
    parser.add_argument("--count", type=int, default=300)
    parser.add_argument("--seed", type=int, default=20261124)
    parser.add_argument("--jobs", type=int, default=8)
    options = parser.parse_args()
    clis = dict(entry.split("=", 1) for entry in options.cli)
    if len(clis) < 2:
        parser.error("at least two --cli entries are needed")
    rng = random.Random(options.seed)
    cases = [invocation(rng) for _ in range(options.count)]

    def compare(args: list[str]) -> tuple[list[str], dict[str, Outcome]]:
        return args, {name: run(cli, args) for name, cli in clis.items()}

    with ThreadPoolExecutor(options.jobs) as pool:
        results = list(pool.map(compare, cases))
    exit_codes: dict[int, int] = {}
    mismatches = 0
    for args, outcomes in results:
        reference = next(iter(outcomes.values()))
        exit_codes[reference[0]] = exit_codes.get(reference[0], 0) + 1
        differing = [name for name, outcome in outcomes.items() if outcome != reference]
        if differing:
            mismatches += 1
            print(f"MISMATCH {','.join(differing)}: {shlex.join(args)}")
    summary = {
        "clis": list(clis),
        "invocations": options.count,
        "exit_codes": {str(code): total for code, total in sorted(exit_codes.items())},
        "mismatches": mismatches,
    }
    print(json.dumps(summary))
    return 1 if mismatches else 0


if __name__ == "__main__":
    sys.exit(main())
