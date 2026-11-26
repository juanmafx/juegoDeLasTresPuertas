# Dephasing between oracle and diffusion as constraint erosion; gamma* closed form and numeric.
import argparse
from pathlib import Path

import numpy as np

from branching_monty.experiments.output import emit
from branching_monty.tiers.quantum import (
    best_one_query_closed_form,
    best_phases,
    dephased_success,
    gamma_star_closed_form,
    gamma_star_numeric,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--doors", type=int, nargs="+", default=[3, 4, 5])
    parser.add_argument("--steps", type=int, default=50)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)

    curves = []
    for n in args.doors:
        phi, theta = best_phases(n)
        gammas = np.linspace(0, 1, args.steps + 1)
        curves.append(
            {
                "doors": n,
                "phases": [phi, theta],
                "best_one_query": best_one_query_closed_form(n),
                "gamma": gammas.tolist(),
                "success": [dephased_success(phi, theta, n, g) for g in gammas],
                "gamma_star_two_thirds": {
                    "closed_form": gamma_star_closed_form(n, 2 / 3),
                    "numeric": gamma_star_numeric(n, 2 / 3),
                },
                "gamma_star_classical_one_query": {
                    "threshold": 2 / n,
                    "closed_form": gamma_star_closed_form(n, 2 / n),
                    "numeric": gamma_star_numeric(n, 2 / n),
                },
            }
        )
    emit(
        {
            "experiment": "decoherence",
            "black_box": "one oracle call; rho -> (1 - gamma) rho + gamma diag(rho); diffusion",
            "closed_form": "gamma* = (P1 - T)/(P1 - 1/N); P1 = 1 (N = 3), (3N - 4)^2/N^3 (N >= 4)",
            "curves": curves,
        },
        args.out,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
