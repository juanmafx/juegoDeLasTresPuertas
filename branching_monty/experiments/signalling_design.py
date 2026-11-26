# Uniform Monty versus the best and worst committed goat-only host, across N doors and k reveals.
import argparse
from pathlib import Path

from branching_monty.agents.signalling import (
    best_policy,
    evaluate,
    full_disclosure_policy,
    monty_policy,
    worst_policy,
)
from branching_monty.agents.two_cpu import run_policy
from branching_monty.experiments.output import emit


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-doors", type=int, default=7)
    parser.add_argument("--trials", type=int, default=20000)
    parser.add_argument("--seed", type=int, default=20191001)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)

    rows = []
    for n in range(3, args.max_doors + 1):
        for k in range(1, n - 1):
            best, best_lp = best_policy(n, k)
            worst, worst_lp = worst_policy(n, k)
            candidates = [
                ("monty_uniform", monty_policy(n, k)),
                ("best_goat_only", best),
                ("worst_goat_only", worst),
                ("full_disclosure_player_door_only", full_disclosure_policy(n, k)),
            ]
            for name, policy in candidates:
                result = evaluate(policy, "claim")
                mc = run_policy(policy, "claim", args.trials, args.seed)
                rows.append(
                    {
                        "doors": n,
                        "reveals": k,
                        "policy": name,
                        "value": result.value,
                        "lambda": result.lam,
                        "info": result.info,
                        "efficiency": result.efficiency,
                        "mc_rate": mc.rate,
                        "mc_stderr": mc.stderr,
                    }
                )
            rows[-3]["lp_value"] = best_lp
            rows[-2]["lp_value"] = worst_lp
    emit(
        {
            "experiment": "signalling_design",
            "black_box": "host knows the car; one committed message = the set of k opened doors",
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
