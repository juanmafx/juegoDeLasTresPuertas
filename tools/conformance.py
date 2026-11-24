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
from math import comb, floor, sqrt
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

REJECTED_SYNTAX = [
    ["exact", "--doors", "1_0"],
    ["exact", "--door", "4"],
    ["exact", "--doors", "\uff14"],
    ["exact", "--doors", "\u00a04"],
    ["exact", "--doors", "4\u2003"],
    ["exact", "--prior", "1,2,3,"],
    ["exact", "--prior", " uniform"],
    ["exact", "--host", "Random"],
    ["exact", "--prior", "-h"],
    ["exact", "--doors", "--help"],
    ["exact", "--mixed", "0.5"],
    ["exact", "--mixed", "1/2/3"],
    ["exact", "--mixed", "1/9223372036854775808"],
    ["exact", "--mixed", "-9223372036854775808/-9223372036854775808"],
    ["exact", "--mixed", "1/1" + "0" * 5000],
    ["optimum", "--strategy", "switch", "--cost", "9223372036854775808"],
    ["simulate", "--se", "1"],
    ["simulate", "--seed", "1", "--trials", "1_000"],
    ["simulate", "--seed", "1", "--trials", "5", "--mixed", "1/18446744073709551615"],
    ["prng", "--seed", "1", "--kind", "weighted", "--weights", "9223372036854775807,1"],
]

ACCEPTED_SYNTAX: list[tuple[list[str], dict[str, Any]]] = [
    (["exact", "--doors", " +04 "], {"doors": 4}),
    (["exact", "--doors=5", "--doors", "4"], {"doors": 4}),
    (["exact", "--mixed", "-1/-2"], {"mixed": "1/2"}),
    (["exact", "--mixed", "-0/5"], {"mixed": "0/1"}),
    (["exact", "--mixed", "9223372036854775807/9223372036854775807"], {"mixed": "1/1"}),
    (["exact", "--prior", "\t1, 2 ,3\f"], {"prior": [1, 2, 3]}),
    (["exact", "--reveals", "0", "--observed", ""], {"observed": []}),
    (["optimum", "--strategy", "switch", "--cost", "-0/1"], {"reveals": None}),
]

HELP_SYNTAX = [
    ["exact", "-h"],
    ["optimum", "--help"],
    ["exact", "--doors", "1_0", "--bogus", "5", "-h"],
]

LARGE_PRIOR = [999001, 999017, 999023, 999037, 999049, 999059, 999067, 999079]
LARGE_COST = "1/9223372036854775783"


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


def check_syntax(command: list[str], section: Section, jobs: int) -> None:
    def rejected(arguments: list[str]) -> Callable[[], None]:
        def run() -> None:
            result = run_cli(command, arguments)
            section.check(
                result.code == 2 and result.stdout == "",
                f"{arguments!r:.120}: expected exit 2 and no output, got {result.code}",
            )

        return run

    def accepted(arguments: list[str], echoed: dict[str, Any]) -> Callable[[], None]:
        def run() -> None:
            result = run_cli(command, arguments)
            if result.code != 0:
                section.check(False, f"{arguments!r:.120}: exit {result.code}")
                return
            scenario = result.json()["scenario"]
            for key, value in echoed.items():
                section.check(scenario.get(key) == value, f"{arguments!r}: {key} is not {value!r}")

        return run

    def helped(arguments: list[str]) -> Callable[[], None]:
        def run() -> None:
            result = run_cli(command, arguments)
            section.check(
                result.code == 0 and result.stdout.strip() != "",
                f"{arguments!r}: expected usage text and exit 0, got {result.code}",
            )

        return run

    tasks = [rejected(arguments) for arguments in REJECTED_SYNTAX]
    tasks += [accepted(arguments, echoed) for arguments, echoed in ACCEPTED_SYNTAX]
    tasks += [helped(arguments) for arguments in HELP_SYNTAX]
    parallel(jobs, tasks)


def weighted_prize_at_pick(weights: list[int], prizes: int, pick: int) -> Fraction:
    layer = {0: Fraction(1)}
    total = sum(weights)
    for _ in range(prizes):
        following: dict[int, Fraction] = {}
        for mask, probability in layer.items():
            remaining = total - sum(w for door, w in enumerate(weights) if mask >> door & 1)
            for door, weight in enumerate(weights):
                if mask >> door & 1 or weight == 0:
                    continue
                key = mask | 1 << door
                following[key] = following.get(key, Fraction(0)) + probability * Fraction(
                    weight, remaining
                )
        layer = following
    return sum((p for mask, p in layer.items() if mask >> pick & 1), Fraction(0))


def random_host_switch(doors: int, prizes: int, reveals: int, pi: Fraction) -> Fraction:
    unpicked = comb(doors - 1, reveals)
    hit = Fraction(comb(doors - prizes, reveals), unpicked)
    miss = Fraction(comb(doors - 1 - prizes, reveals), unpicked)
    decision = pi * hit + (1 - pi) * miss
    numerator = pi * hit * (prizes - 1) + (1 - pi) * miss * prizes
    return numerator / ((doors - 1 - reveals) * decision)


def fraction_text(value: Fraction) -> str:
    return f"{value.numerator}/{value.denominator}"


def expected_parabola(values: list[Fraction]) -> dict[str, Any]:
    ks = list(range(len(values)))
    s = [sum(Fraction(k**p) for k in ks) for p in range(5)]
    t = [sum(v * k**p for k, v in zip(ks, values, strict=True)) for p in range(3)]
    rows = [[s[4], s[3], s[2], t[2]], [s[3], s[2], s[1], t[1]], [s[2], s[1], s[0], t[0]]]
    for column in range(3):
        pivot = next(r for r in range(column, 3) if rows[r][column] != 0)
        rows[column], rows[pivot] = rows[pivot], rows[column]
        for r in range(3):
            if r != column and rows[r][column] != 0:
                factor = rows[r][column] / rows[column][column]
                rows[r] = [x - factor * y for x, y in zip(rows[r], rows[column], strict=True)]
    a, b, c = (rows[i][3] / rows[i][i] for i in range(3))
    fitted = [a * k * k + b * k + c for k in ks]
    best = max(ks, key=lambda k: (values[k], -k))
    choice = max(ks, key=lambda k: (fitted[k], -k))
    vertex = -b / (2 * a)
    vertex_value = c - b * b / (4 * a)
    rounded = min(max(floor(vertex + Fraction(1, 2)), 0), ks[-1])
    return {
        "a": fraction_text(a),
        "b": fraction_text(b),
        "c": fraction_text(c),
        "shape": "concave" if a < 0 else "convex" if a > 0 else "linear",
        "residual_sum_of_squares": fraction_text(
            sum((f - v) ** 2 for f, v in zip(fitted, values, strict=True))
        ),
        "vertex": {"reveals": fraction_text(vertex), "value": fraction_text(vertex_value)},
        "vertex_offset": fraction_text(vertex - best),
        "vertex_value_gap": fraction_text(vertex_value - values[best]),
        "rounded_vertex": {
            "reveals": rounded,
            "value": fraction_text(values[rounded]),
            "regret": fraction_text(values[best] - values[rounded]),
        },
        "fitted_choice": {
            "reveals": choice,
            "value": fraction_text(values[choice]),
            "regret": fraction_text(values[best] - values[choice]),
        },
    }


def check_large_values(command: list[str], section: Section) -> None:
    doors, prizes = len(LARGE_PRIOR), 3
    pi = weighted_prize_at_pick(LARGE_PRIOR, prizes, 0)
    cost = Fraction(LARGE_COST)
    wins = [random_host_switch(doors, prizes, k, pi) for k in range(doors - prizes)]
    values = [w - cost * k for k, w in enumerate(wins)]
    prior = ",".join(map(str, LARGE_PRIOR))
    scenario = [
        "--doors",
        str(doors),
        "--prizes",
        str(prizes),
        "--prior",
        prior,
        "--host",
        "random",
    ]
    result = run_cli(command, ["optimum", *scenario, "--strategy", "switch", "--cost", LARGE_COST])
    if result.code != 0:
        section.check(False, f"large optimum: exit {result.code} {result.stderr.strip()}")
        return
    output = result.json()
    curve = [
        {"reveals": k, "win": fraction_text(w), "value": fraction_text(v)}
        for k, (w, v) in enumerate(zip(wins, values, strict=True))
    ]
    section.check(output["curve"] == curve, "large optimum: curve differs")
    parabola = expected_parabola(values)
    for key, value in parabola.items():
        section.check(
            output["parabola"].get(key) == value, f"large optimum: parabola {key} differs"
        )
    widest = as_fraction(parabola["residual_sum_of_squares"]).denominator.bit_length()
    section.check(
        widest > 4096, f"large optimum: expected values wider than 4096 bits, got {widest}"
    )
    result = run_cli(command, ["exact", *scenario, "--reveals", "2"])
    if result.code != 0:
        section.check(False, f"large exact: exit {result.code} {result.stderr.strip()}")
        return
    output = result.json()
    section.check(
        output["prize_at_pick"] == fraction_text(pi), "large exact: prize_at_pick differs"
    )
    section.check(output["win"]["switch"] == fraction_text(wins[2]), "large exact: switch differs")


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
    sys.set_int_max_str_digits(0)
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
            "syntax",
            "large_values",
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
    check_syntax(command, sections["syntax"], args.jobs)
    check_large_values(command, sections["large_values"])
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
