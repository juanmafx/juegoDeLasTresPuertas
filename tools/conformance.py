# Runs one language's monty-lab CLI against spec/: exact, bit-identical and statistical checks.
import argparse
import json
import os
import shlex
import subprocess
import sys
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from fractions import Fraction
from math import comb, sqrt
from pathlib import Path
from typing import Any

SPEC = Path(__file__).resolve().parents[1] / "spec"
Z95 = 1.959963984540054
HARD_Z = 5.0
MISS_RATE = 0.05
MISS_BUDGET_TAIL = 0.001
FLOAT_TOLERANCE = 1e-9

INVALID_INVOCATIONS = [
    ["exact", "--doors", "2"],
    ["exact", "--doors", "65"],
    ["exact", "--doors", "5", "--prizes", "4"],
    ["exact", "--doors", "5", "--prizes", "2", "--reveals", "3"],
    ["exact", "--pick", "3"],
    ["exact", "--observed", "0"],
    ["exact", "--observed", "1,2"],
    ["exact", "--host", "biased"],
    ["exact", "--host-weights", "1,1,1"],
    ["exact", "--host", "biased", "--host-weights", "1,0,1"],
    ["exact", "--prior", "1,1"],
    ["exact", "--doors", "4", "--prizes", "2", "--prior", "0,0,0,1"],
    ["exact", "--mixed", "3/2"],
    ["exact", "--mixed", "1/0"],
    ["exact", "--doors", "11", "--prior", "1,1,1,1,1,1,1,1,1,1,1"],
    ["simulate", "--seed", "-1"],
    ["simulate", "--seed", "1", "--trials", "0"],
    ["optimum", "--strategy", "switch", "--cost", "-1/2"],
    [
        "optimum",
        "--strategy",
        "stay",
        "--doors",
        "4",
        "--prior",
        "0,1,1,1",
        "--host",
        "adversarial",
    ],
    ["prng", "--seed", "1", "--kind", "bounded", "--bound", "0"],
]


@dataclass
class Section:
    name: str
    passed: int = 0
    failures: list[str] = field(default_factory=list)

    def check(self, ok: bool, message: str) -> None:
        if ok:
            self.passed += 1
        else:
            self.failures.append(message)


@dataclass(frozen=True)
class Invocation:
    code: int
    stdout: str
    stderr: str

    def json(self) -> Any:
        return json.loads(self.stdout)


def run_cli(command: list[str], arguments: list[str]) -> Invocation:
    completed = subprocess.run(
        [*command, *arguments], capture_output=True, text=True, check=False, timeout=600
    )
    return Invocation(completed.returncode, completed.stdout, completed.stderr)


def scenario_arguments(scenario: dict[str, Any], *, with_reveals: bool = True) -> list[str]:
    arguments = [
        "--doors",
        str(scenario["doors"]),
        "--prizes",
        str(scenario["prizes"]),
        "--pick",
        str(scenario["pick"]),
        "--host",
        scenario["host"],
        "--mixed",
        scenario["mixed"],
    ]
    if scenario["prior"] != "uniform":
        arguments += ["--prior", ",".join(map(str, scenario["prior"]))]
    if scenario["host_weights"] is not None:
        arguments += ["--host-weights", ",".join(map(str, scenario["host_weights"]))]
    if with_reveals:
        arguments += ["--reveals", str(scenario["reveals"])]
        if scenario["observed"] is not None:
            arguments += ["--observed", ",".join(map(str, scenario["observed"]))]
    return arguments


def prng_arguments(vector: dict[str, Any]) -> list[str]:
    arguments = ["prng", "--seed", str(vector["seed"]), "--kind", vector["kind"]]
    if vector["kind"] == "shuffle":
        return [*arguments, "--size", str(vector["size"])]
    arguments += ["--count", str(vector["count"])]
    if vector["kind"] == "bounded":
        arguments += ["--bound", str(vector["bound"])]
    if vector["kind"] == "weighted":
        arguments += ["--weights", ",".join(map(str, vector["weights"]))]
    return arguments


def wilson(successes: int, trials: int) -> tuple[float, float]:
    rate = successes / trials
    z2 = Z95 * Z95
    denominator = 1 + z2 / trials
    center = (rate + z2 / (2 * trials)) / denominator
    margin = Z95 * sqrt(rate * (1 - rate) / trials + z2 / (4 * trials * trials)) / denominator
    lower = 0.0 if successes == 0 else max(0.0, center - margin)
    upper = 1.0 if successes == trials else min(1.0, center + margin)
    return lower, upper


def miss_budget(checks: int) -> int:
    for allowed in range(checks + 1):
        tail = sum(
            comb(checks, k) * MISS_RATE**k * (1 - MISS_RATE) ** (checks - k)
            for k in range(allowed + 1, checks + 1)
        )
        if tail < MISS_BUDGET_TAIL:
            return allowed
    return checks


def as_fraction(text: str) -> Fraction:
    numerator, denominator = text.split("/")
    return Fraction(int(numerator), int(denominator))


def parallel(jobs: int, tasks: list[Callable[[], None]]) -> None:
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        for future in [pool.submit(task) for task in tasks]:
            future.result()


def check_prng(
    command: list[str], vectors: list[dict[str, Any]], section: Section, jobs: int
) -> None:
    def task(vector: dict[str, Any]) -> Callable[[], None]:
        def run() -> None:
            result = run_cli(command, prng_arguments(vector))
            if result.code != 0:
                section.check(False, f"{vector['id']}: exit {result.code} {result.stderr.strip()}")
                return
            got = [str(value) for value in result.json().get("values", [])]
            want = [str(value) for value in vector["values"]]
            section.check(got == want, f"{vector['id']}: values differ")

        return run

    parallel(jobs, [task(vector) for vector in vectors])


def check_exact(
    command: list[str], scenarios: list[dict[str, Any]], section: Section, jobs: int
) -> None:
    def task(entry: dict[str, Any]) -> Callable[[], None]:
        def run() -> None:
            result = run_cli(command, ["exact", *scenario_arguments(entry["scenario"])])
            if result.code != 0:
                section.check(False, f"{entry['id']}: exit {result.code} {result.stderr.strip()}")
                return
            output = result.json()
            expected = entry["expected"]["exact"]
            for key in ("prize_at_pick", "outcomes", "win"):
                section.check(
                    output.get(key) == expected[key],
                    f"{entry['id']}: {key} {output.get(key)} != {expected[key]}",
                )

        return run

    parallel(jobs, [task(entry) for entry in scenarios])


def check_optimum(
    command: list[str], scenarios: list[dict[str, Any]], section: Section, jobs: int
) -> None:
    def task(entry: dict[str, Any]) -> Callable[[], None]:
        def run() -> None:
            arguments = [
                "optimum",
                *scenario_arguments(entry["scenario"], with_reveals=False),
                "--strategy",
                entry["optimum"]["strategy"],
                "--cost",
                entry["optimum"]["cost"],
            ]
            result = run_cli(command, arguments)
            if result.code != 0:
                section.check(False, f"{entry['id']}: exit {result.code} {result.stderr.strip()}")
                return
            output = result.json()
            expected = entry["expected"]["optimum"]
            for key in ("curve", "optimum", "parabola"):
                section.check(
                    output.get(key) == expected[key], f"{entry['id']}: optimum {key} differs"
                )

        return run

    parallel(jobs, [task(entry) for entry in scenarios if "optimum" in entry])


@dataclass
class Interval:
    label: str
    wins: int
    sample: int
    exact: Fraction


def check_simulation(
    command: list[str],
    scenarios: list[dict[str, Any]],
    reference: dict[str, dict[str, Any]],
    identical: Section,
    statistical: Section,
    jobs: int,
) -> dict[str, Any]:
    intervals: list[Interval] = []

    def task(entry: dict[str, Any]) -> Callable[[], None]:
        def run() -> None:
            run_spec = entry["simulation"]
            arguments = [
                "simulate",
                *scenario_arguments(entry["scenario"]),
                "--seed",
                str(run_spec["seed"]),
                "--trials",
                str(run_spec["trials"]),
            ]
            result = run_cli(command, arguments)
            if result.code != 0:
                identical.check(False, f"{entry['id']}: exit {result.code} {result.stderr.strip()}")
                return
            output = result.json()
            golden = reference[entry["id"]]
            wins = {
                name: output["strategies"][name]["wins"] for name in ("stay", "switch", "mixed")
            }
            identical.check(
                output["counts"] == golden["counts"]
                and output["sample_size"] == golden["sample_size"]
                and wins == golden["wins"],
                f"{entry['id']}: counts {output['counts']} wins {wins} differ from reference",
            )
            sample = output["sample_size"]
            for name, summary in output["strategies"].items():
                if sample == 0:
                    statistical.check(
                        summary["rate"] is None and summary["wilson95"] is None,
                        f"{entry['id']}: {name} must report null rate for an empty sample",
                    )
                    continue
                lower, upper = wilson(summary["wins"], sample)
                reported = summary["wilson95"]
                statistical.check(
                    abs(summary["rate"] - summary["wins"] / sample) <= FLOAT_TOLERANCE
                    and abs(reported[0] - lower) <= FLOAT_TOLERANCE
                    and abs(reported[1] - upper) <= FLOAT_TOLERANCE,
                    f"{entry['id']}: {name} reported rate or interval is wrong",
                )
                exact = entry["expected"]["exact"]["win"][name]
                if exact is not None:
                    intervals.append(
                        Interval(
                            f"{entry['id']}:{name}", summary["wins"], sample, as_fraction(exact)
                        )
                    )
            decision = as_fraction(entry["expected"]["exact"]["outcomes"]["decision"])
            intervals.append(
                Interval(
                    f"{entry['id']}:decision",
                    output["counts"]["decision"],
                    run_spec["trials"],
                    decision,
                )
            )

        return run

    parallel(jobs, [task(entry) for entry in scenarios if "simulation" in entry])
    misses = []
    for interval in sorted(intervals, key=lambda i: i.label):
        p = float(interval.exact)
        if interval.exact in (0, 1):
            statistical.check(
                interval.wins == (0 if interval.exact == 0 else interval.sample),
                f"{interval.label}: exact {interval.exact} but {interval.wins}/{interval.sample}",
            )
            continue
        z = (interval.wins / interval.sample - p) / sqrt(p * (1 - p) / interval.sample)
        statistical.check(abs(z) < HARD_Z, f"{interval.label}: |z| = {abs(z):.2f} >= {HARD_Z}")
        lower, upper = wilson(interval.wins, interval.sample)
        if not lower <= p <= upper:
            misses.append(f"{interval.label} z={z:+.2f}")
    budget = miss_budget(len(intervals))
    statistical.check(
        len(misses) <= budget,
        f"{len(misses)} of {len(intervals)} exact values fell outside their Wilson 95% interval, "
        f"more than the allowed {budget}",
    )
    return {"interval_checks": len(intervals), "outside_95": misses, "allowed_outside": budget}


def check_errors(command: list[str], section: Section, jobs: int) -> None:
    def task(arguments: list[str]) -> Callable[[], None]:
        def run() -> None:
            result = run_cli(command, arguments)
            section.check(
                result.code == 2 and "error" in result.stderr and result.stdout == "",
                f"{' '.join(arguments)}: expected exit 2 and an error, got {result.code}",
            )

        return run

    parallel(jobs, [task(arguments) for arguments in INVALID_INVOCATIONS])


def main() -> int:
    parser = argparse.ArgumentParser(description="Check a monty-lab CLI against spec/.")
    parser.add_argument(
        "--cli", required=True, help="command that runs the CLI, e.g. 'java -jar x.jar'"
    )
    parser.add_argument("--spec", type=Path, default=SPEC)
    parser.add_argument("--jobs", type=int, default=os.cpu_count() or 1)
    parser.add_argument("--report", type=Path, help="write a JSON report to this file")
    args = parser.parse_args()
    command = shlex.split(args.cli)
    scenarios = json.loads((args.spec / "scenarios.json").read_text("utf-8"))["scenarios"]
    vectors = json.loads((args.spec / "prng-vectors.json").read_text("utf-8"))["vectors"]
    runs = json.loads((args.spec / "simulation-reference.json").read_text("utf-8"))["runs"]
    reference = {run["id"]: run for run in runs}
    sections = {
        name: Section(name)
        for name in (
            "prng",
            "exact",
            "optimum",
            "simulation_identical",
            "simulation_statistical",
            "errors",
        )
    }
    check_prng(command, vectors, sections["prng"], args.jobs)
    check_exact(command, scenarios, sections["exact"], args.jobs)
    check_optimum(command, scenarios, sections["optimum"], args.jobs)
    statistics = check_simulation(
        command,
        scenarios,
        reference,
        sections["simulation_identical"],
        sections["simulation_statistical"],
        args.jobs,
    )
    check_errors(command, sections["errors"], args.jobs)
    failed = 0
    for section in sections.values():
        status = "PASS" if not section.failures else "FAIL"
        print(f"{status} {section.name}: {section.passed} passed, {len(section.failures)} failed")
        for failure in section.failures:
            print(f"  - {failure}")
        failed += len(section.failures)
    outside = statistics["outside_95"]
    print(
        f"INFO {len(outside)} of {statistics['interval_checks']} Wilson 95% intervals "
        f"exclude the exact value (allowed {statistics['allowed_outside']})"
        + (": " + "; ".join(outside) if outside else "")
    )
    if args.report is not None:
        report = {
            "cli": args.cli,
            "sections": {
                name: {"passed": s.passed, "failures": s.failures} for name, s in sections.items()
            },
            "statistics": statistics,
        }
        args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
