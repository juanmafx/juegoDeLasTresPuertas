# Command-line contract shared by every language implementation, defined in spec/cli.md.
import argparse
import json
import os
import sys
from collections.abc import Sequence
from fractions import Fraction
from typing import Any

from monty_hall import __version__
from monty_hall.analysis.intervals import wilson_interval
from monty_hall.lab.model import (
    MAX_SEED,
    Host,
    Scenario,
    ScenarioError,
    Strategy,
    format_fraction,
    parse_fraction,
)
from monty_hall.lab.optimum import OptimumResult, optimum_curve
from monty_hall.lab.prng import SplitMix64, Xoshiro256StarStar
from monty_hall.lab.simulator import simulate
from monty_hall.lab.solver import solve

EXIT_USAGE = 2
EXIT_BROKEN_PIPE = 141
MAX_PRNG_COUNT = 100_000
MAX_SHUFFLE_SIZE = 10_000


def _fraction(value: Fraction | None) -> str | None:
    return None if value is None else format_fraction(value)


def _integer_list(text: str) -> tuple[int, ...]:
    if text.strip() == "":
        return ()
    try:
        return tuple(int(part) for part in text.split(","))
    except ValueError as error:
        raise ScenarioError(f"invalid integer list {text!r}") from error


def _add_scenario_arguments(parser: argparse.ArgumentParser, *, reveals: bool) -> None:
    parser.add_argument("--doors", type=int, default=3)
    parser.add_argument("--prizes", type=int, default=1)
    parser.add_argument("--prior", default="uniform")
    parser.add_argument("--pick", type=int, default=0)
    parser.add_argument("--host", choices=[h.value for h in Host], default=Host.INFORMED.value)
    parser.add_argument("--host-weights")
    parser.add_argument("--mixed", default="1/2")
    if reveals:
        parser.add_argument("--reveals", type=int, default=1)
        parser.add_argument("--observed")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="monty-lab",
        description="Generalized Monty Hall decision lab (cross-language contract).",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)
    exact = commands.add_parser("exact", help="exact win probabilities as fractions")
    _add_scenario_arguments(exact, reveals=True)
    sim = commands.add_parser("simulate", help="deterministic Monte Carlo simulation")
    _add_scenario_arguments(sim, reveals=True)
    sim.add_argument("--trials", type=int, default=100_000)
    sim.add_argument("--seed", type=int, required=True)
    optimum = commands.add_parser("optimum", help="value of exploration over all reveal counts")
    _add_scenario_arguments(optimum, reveals=False)
    optimum.add_argument("--strategy", choices=[s.value for s in Strategy], required=True)
    optimum.add_argument("--cost", default="0")
    prng = commands.add_parser("prng", help="raw generator output for conformance vectors")
    prng.add_argument("--seed", type=int, required=True)
    prng.add_argument(
        "--kind", choices=["splitmix", "words", "bounded", "weighted", "shuffle"], required=True
    )
    prng.add_argument("--count", type=int, default=1)
    prng.add_argument("--bound", type=int)
    prng.add_argument("--weights")
    prng.add_argument("--size", type=int)
    return parser


def scenario_from_args(args: argparse.Namespace) -> Scenario:
    prior = None if args.prior == "uniform" else _integer_list(args.prior)
    host_weights = None if args.host_weights is None else _integer_list(args.host_weights)
    observed = getattr(args, "observed", None)
    return Scenario(
        doors=args.doors,
        prizes=args.prizes,
        prior=prior,
        pick=args.pick,
        reveals=getattr(args, "reveals", 0),
        host=Host(args.host),
        host_weights=host_weights,
        mixed=parse_fraction(args.mixed),
        observed=None if observed is None else _integer_list(observed),
    )


def exact_report(scenario: Scenario) -> dict[str, Any]:
    result = solve(scenario)
    return {
        "command": "exact",
        "scenario": scenario.to_json(),
        "prize_at_pick": _fraction(result.prize_at_pick),
        "outcomes": {
            "decision": _fraction(result.decision),
            "void": _fraction(result.void),
            "no_offer": _fraction(result.no_offer),
            "observed": _fraction(result.observed),
        },
        "win": {
            "stay": _fraction(result.stay),
            "switch": _fraction(result.switch),
            "mixed": _fraction(result.mixed(scenario.mixed)),
        },
    }


def _strategy_summary(wins: int, sample: int) -> dict[str, Any]:
    if sample == 0:
        return {"wins": wins, "rate": None, "wilson95": None}
    interval = wilson_interval(wins, sample, 0.95)
    return {"wins": wins, "rate": wins / sample, "wilson95": [interval.lower, interval.upper]}


def simulate_report(scenario: Scenario, trials: int, seed: int) -> dict[str, Any]:
    counts = simulate(scenario, trials, seed)
    sample = counts.sample_size
    return {
        "command": "simulate",
        "scenario": scenario.to_json(),
        "seed": seed,
        "trials": trials,
        "counts": {
            "decision": counts.decision,
            "void": counts.void,
            "no_offer": counts.no_offer,
            "observed": counts.observed,
        },
        "sample_size": sample,
        "strategies": {
            "stay": _strategy_summary(counts.stay_wins, sample),
            "switch": _strategy_summary(counts.switch_wins, sample),
            "mixed": _strategy_summary(counts.mixed_wins, sample),
        },
    }


def _choice(result: OptimumResult, reveals: int) -> dict[str, Any]:
    value = result.curve[reveals].value
    return {
        "reveals": reveals,
        "value": format_fraction(value),
        "regret": format_fraction(result.best.value - value),
    }


def optimum_report(scenario: Scenario, strategy: Strategy, cost: Fraction) -> dict[str, Any]:
    result = optimum_curve(scenario, strategy, cost)
    echoed = scenario.to_json()
    echoed["reveals"] = None
    parabola: dict[str, Any] | None = None
    fit = result.parabola
    if fit is not None:
        parabola = {
            "a": format_fraction(fit.a),
            "b": format_fraction(fit.b),
            "c": format_fraction(fit.c),
            "shape": fit.shape,
            "residual_sum_of_squares": format_fraction(fit.residual_sum_of_squares),
            "vertex": None,
            "vertex_offset": None,
            "vertex_value_gap": None,
            "rounded_vertex": None,
            "fitted_choice": _choice(result, fit.fitted_choice),
        }
        if fit.vertex_reveals is not None and fit.vertex_value is not None:
            parabola["vertex"] = {
                "reveals": format_fraction(fit.vertex_reveals),
                "value": format_fraction(fit.vertex_value),
            }
            parabola["vertex_offset"] = format_fraction(fit.vertex_reveals - result.best.reveals)
            parabola["vertex_value_gap"] = format_fraction(fit.vertex_value - result.best.value)
        if fit.rounded_vertex is not None:
            parabola["rounded_vertex"] = _choice(result, fit.rounded_vertex)
    return {
        "command": "optimum",
        "scenario": echoed,
        "strategy": strategy.value,
        "cost": format_fraction(cost),
        "curve": [
            {
                "reveals": p.reveals,
                "win": format_fraction(p.win),
                "value": format_fraction(p.value),
            }
            for p in result.curve
        ],
        "optimum": {"reveals": result.best.reveals, "value": format_fraction(result.best.value)},
        "parabola": parabola,
    }


def prng_report(args: argparse.Namespace) -> dict[str, Any]:
    if not 0 <= args.seed <= MAX_SEED:
        raise ScenarioError(f"seed must be between 0 and {MAX_SEED}")
    if not 1 <= args.count <= MAX_PRNG_COUNT:
        raise ScenarioError(f"count must be between 1 and {MAX_PRNG_COUNT}")
    rng = Xoshiro256StarStar(args.seed)
    report: dict[str, Any] = {"command": "prng", "seed": args.seed, "kind": args.kind}
    values: list[Any]
    if args.kind == "splitmix":
        expander = SplitMix64(args.seed)
        values = [str(expander.next()) for _ in range(args.count)]
    elif args.kind == "words":
        values = [str(rng.next_u64()) for _ in range(args.count)]
    elif args.kind == "bounded":
        if args.bound is None or not 1 <= args.bound <= MAX_SEED:
            raise ScenarioError(f"bound must be between 1 and {MAX_SEED}")
        report["bound"] = args.bound
        values = [rng.bounded(args.bound) for _ in range(args.count)]
    elif args.kind == "weighted":
        weights = list(_integer_list(args.weights or ""))
        if not weights or any(w < 0 for w in weights) or sum(weights) <= 0:
            raise ScenarioError("weights must be non-negative integers with a positive total")
        if sum(weights) > MAX_SEED:
            raise ScenarioError(f"weights must sum to at most {MAX_SEED}")
        report["weights"] = weights
        values = [rng.weighted_index(weights) for _ in range(args.count)]
    else:
        if args.size is None or not 1 <= args.size <= MAX_SHUFFLE_SIZE:
            raise ScenarioError(f"size must be between 1 and {MAX_SHUFFLE_SIZE}")
        report["size"] = args.size
        values = list(range(args.size))
        rng.shuffle(values)
    report["values"] = values
    return report


def run(args: argparse.Namespace) -> dict[str, Any]:
    if args.command == "prng":
        return prng_report(args)
    scenario = scenario_from_args(args)
    if args.command == "exact":
        return exact_report(scenario)
    if args.command == "simulate":
        return simulate_report(scenario, args.trials, args.seed)
    return optimum_report(scenario, Strategy(args.strategy), parse_fraction(args.cost))


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = run(args)
        print(json.dumps(report, indent=2))
        sys.stdout.flush()
        return 0
    except BrokenPipeError:
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, sys.stdout.fileno())
        os.close(devnull)
        return EXIT_BROKEN_PIPE
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        return EXIT_USAGE


def entry_point() -> None:
    raise SystemExit(main())
