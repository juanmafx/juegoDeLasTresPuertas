# Lambda from causal pruning of arrival times, swept over jitter, processing gap and latency floor.
import argparse
from fractions import Fraction
from pathlib import Path

from branching_monty.agents.latency import Timing, timed_leverage, timed_value
from branching_monty.agents.two_cpu import run_timed
from branching_monty.experiments.output import emit


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--doors", type=int, default=3)
    parser.add_argument("--q", type=Fraction, default=Fraction(1))
    parser.add_argument("--processing", type=int, default=10)
    parser.add_argument("--max-jitter", type=int, default=8)
    parser.add_argument("--max-gap", type=int, default=4)
    parser.add_argument("--latencies", type=int, nargs="+", default=[0, 5, 50])
    parser.add_argument("--trials", type=int, default=20000)
    parser.add_argument("--seed", type=int, default=20191001)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)

    rows = []
    for latency in args.latencies:
        for gap in range(args.max_gap + 1):
            for jitter in range(args.max_jitter + 1):
                timing = Timing(args.processing, gap, latency, jitter)
                value = timed_value(args.doors, args.q, timing, "claim")
                result = timed_leverage(args.doors, args.q, timing, "claim")
                mc = run_timed(args.doors, args.q, timing, "claim", args.trials, args.seed)
                rows.append(
                    {
                        "latency": latency,
                        "gap": gap,
                        "jitter": jitter,
                        "value": str(value),
                        "lambda": result.lam,
                        "info": result.info,
                        "efficiency": result.efficiency,
                        "mc_rate": mc.rate,
                        "mc_stderr": mc.stderr,
                    }
                )
    emit(
        {
            "experiment": "latency_sweep",
            "black_box": (
                "host message plus its arrival time; emission time = processing + gap * "
                "(host choices - 1); delay uniform on [latency, latency + jitter]"
            ),
            "spec": {"doors": args.doors, "q": str(args.q)},
            "convention": "claim",
            "seed": args.seed,
            "trials": args.trials,
            "rows": rows,
        },
        args.out,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
