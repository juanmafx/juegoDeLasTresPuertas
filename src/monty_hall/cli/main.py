import argparse
import json
import secrets
import sqlite3
import sys
from collections.abc import Sequence
from dataclasses import asdict
from pathlib import Path
from typing import Any

from monty_hall import __version__
from monty_hall.analysis.exact import closed_form, enumerate_game_tree
from monty_hall.domain.models import ConfigurationError, GameConfig, HostPolicy
from monty_hall.persistence.repository import RunRepository
from monty_hall.simulation.report import build_report
from monty_hall.simulation.runner import MAX_SEED, SimulationRequest, run_simulation


def _confidence(raw: str) -> float:
    try:
        value = float(raw)
    except ValueError as error:
        raise argparse.ArgumentTypeError("confidence must be a number") from error
    if not 0 < value < 1:
        raise argparse.ArgumentTypeError("confidence must be strictly between 0 and 1")
    return value


def _add_game_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--doors", type=int, default=3)
    parser.add_argument("--opened", type=int, default=1)
    parser.add_argument(
        "--host",
        type=HostPolicy,
        choices=list(HostPolicy),
        default=HostPolicy.INFORMED,
    )
    parser.add_argument("--format", choices=["text", "json"], default="text")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="monty-hall",
        description="Exact and seeded Monte Carlo analysis of the generalized Monty Hall problem.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)

    simulate = commands.add_parser("simulate", help="run a seeded Monte Carlo simulation")
    _add_game_arguments(simulate)
    simulate.add_argument("--trials", type=int, default=100_000)
    simulate.add_argument("--seed", type=int)
    simulate.add_argument("--confidence", type=_confidence, default=0.95)
    simulate.add_argument("--db", type=Path, help="optional SQLite file for storing the run")

    exact = commands.add_parser("exact", help="compute exact win probabilities")
    _add_game_arguments(exact)
    exact.add_argument(
        "--enumerate",
        action="store_true",
        help="walk the full game tree instead of using the closed form",
    )

    history = commands.add_parser("history", help="list runs stored in a SQLite file")
    history.add_argument("--db", type=Path, required=True)
    history.add_argument("--limit", type=int, default=20)
    return parser


def _format_strategy(name: str, summary: dict[str, Any], confidence: float) -> str:
    if summary["rate"] is None:
        return f"{name:<7} no valid games (exact {summary['expected']:.6f})"
    lower, upper = summary["interval"]
    return (
        f"{name:<7} wins={summary['wins']} rate={summary['rate']:.6f} "
        f"exact={summary['expected']:.6f} "
        f"{confidence:.0%} CI=[{lower:.6f}, {upper:.6f}] z={summary['z_score']:+.3f}"
    )


def _simulate(args: argparse.Namespace) -> int:
    seed = args.seed if args.seed is not None else secrets.randbelow(MAX_SEED + 1)
    request = SimulationRequest(GameConfig(args.doors, args.opened), args.host, args.trials, seed)
    result = run_simulation(request)
    report = build_report(result, args.confidence)
    if args.db is not None:
        with RunRepository(args.db) as repository:
            report["run_id"] = repository.save(result)
    if args.format == "json":
        print(json.dumps(report, indent=2))
        return 0
    print(
        f"doors={report['doors']} opened={report['opened']} host={report['host']} "
        f"seed={report['seed']} trials={report['trials']} valid_games={report['valid_games']}"
    )
    print(_format_strategy("stay", report["stay"], args.confidence))
    print(_format_strategy("switch", report["switch"], args.confidence))
    return 0


def _exact(args: argparse.Namespace) -> int:
    config = GameConfig(args.doors, args.opened)
    solver = enumerate_game_tree if args.enumerate else closed_form
    probabilities = solver(config, args.host)
    values = {
        "doors": config.doors,
        "opened": config.opened,
        "host": args.host.value,
        "method": "enumeration" if args.enumerate else "closed_form",
        "stay": str(probabilities.stay),
        "switch": str(probabilities.switch),
        "valid_game": str(probabilities.valid_game),
    }
    if args.format == "json":
        print(json.dumps(values, indent=2))
    else:
        print(" ".join(f"{key}={value}" for key, value in values.items()))
    return 0


def _history(args: argparse.Namespace) -> int:
    if not args.db.is_file():
        raise ConfigurationError("database file does not exist")
    with RunRepository(args.db, read_only=True) as repository:
        for run in repository.recent(args.limit):
            print(json.dumps(asdict(run)))
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    handlers = {"simulate": _simulate, "exact": _exact, "history": _history}
    try:
        return handlers[args.command](args)
    except (ValueError, sqlite3.Error, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


def entry_point() -> None:
    raise SystemExit(main())
