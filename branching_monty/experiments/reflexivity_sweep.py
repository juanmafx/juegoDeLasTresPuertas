# Lambda as a function of reflexive feedback strength r for each feedback mode.
import argparse
from fractions import Fraction
from pathlib import Path

from branching_monty.agents.reflexivity import reflexive_lambda, reflexive_value
from branching_monty.agents.two_cpu import run_baseline
from branching_monty.branches.engine import GameSpec
from branching_monty.experiments.output import emit


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--doors", type=int, default=3)
    parser.add_argument("--reveals", type=int, default=1)
    parser.add_argument("--q", type=Fraction, default=Fraction(1))
    parser.add_argument("--convention", choices=["claim", "loss"], default="claim")
    parser.add_argument("--steps", type=int, default=10)
    parser.add_argument("--trials", type=int, default=20000)
    parser.add_argument("--seed", type=int, default=20191001)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)

    spec = GameSpec(args.doors, args.reveals, args.q)
    rows = []
    for mode in ("adversarial", "noise", "self_fulfilling"):
        for i in range(args.steps + 1):
            r = Fraction(i, args.steps)
            value = reflexive_value(spec, args.convention, r, mode)
            mc = run_baseline(spec, args.convention, args.trials, args.seed, float(r), mode)
            lam = reflexive_lambda(spec, args.convention, r, mode) if value > 0 else None
            rows.append(
                {
                    "mode": mode,
                    "r": str(r),
                    "value": str(value),
                    "lambda": lam,
                    "mc_rate": mc.rate,
                    "mc_stderr": mc.stderr,
                }
            )
    emit(
        {
            "experiment": "reflexivity_sweep",
            "black_box": "player's final choice moves the car with probability r after it is made",
            "spec": {"doors": args.doors, "reveals": args.reveals, "q": str(args.q)},
            "convention": args.convention,
            "seed": args.seed,
            "trials": args.trials,
            "rows": rows,
        },
        args.out,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
