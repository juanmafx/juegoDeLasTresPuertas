# Five doors: one-query quantum search against the Spekkens tier; does the gap track mana.
import argparse
from fractions import Fraction
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

from branching_monty.core.grover import oracle, uniform_state
from branching_monty.core.holevo import guess_probability
from branching_monty.experiments.output import emit
from branching_monty.tiers.bayesian import bit_query_value
from branching_monty.tiers.quantum import chirp_success, post_oracle_mana, success_grid
from branching_monty.tiers.spekkens import is_clifford


def sweep(d: int, points: int) -> list[dict[str, float | bool]]:
    rows = []
    thetas = np.linspace(0, 2 * np.pi, 361)
    for phi in np.linspace(0, 2 * np.pi, points):
        states = [oracle(phi, d, t) @ uniform_state(d) for t in range(d)]
        rows.append(
            {
                "phi": float(phi),
                "mana": post_oracle_mana(phi, d),
                "sdp_optimum": guess_probability(states, [1 / d] * d),
                "grover_best_theta": float(success_grid(d, np.array([phi]), thetas).max()),
                "oracle_is_clifford": is_clifford(oracle(phi, d, 0), d),
            }
        )
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--points", type=int, default=91)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)

    summary = {}
    for d in (3, 5):
        rows = sweep(d, args.points)
        clifford_best = max(
            (float(r["sdp_optimum"]) for r in rows if r["oracle_is_clifford"]), default=0.0
        )
        spekkens_indicator = max(clifford_best, float(bit_query_value(d, Fraction(1))))
        quantum_best = max(float(r["sdp_optimum"]) for r in rows)
        gaps = [float(r["sdp_optimum"]) - spekkens_indicator for r in rows]
        rho, _ = spearmanr([r["mana"] for r in rows], gaps)
        summary[str(d)] = {
            "quantum_best": quantum_best,
            "spekkens_best_indicator_box": spekkens_indicator,
            "spekkens_best_chirp_box": min(chirp_success(d, t)[1] for t in range(d)),
            "strict_gap": quantum_best - spekkens_indicator,
            "spearman_mana_gap": float(rho),
            "rows": rows,
        }
    emit(
        {
            "experiment": "five_doors",
            "black_boxes": {
                "indicator": "one call to diag(exp(i phi [x = t])); Spekkens may use it only "
                "if Clifford, otherwise it falls back to one classical bit query",
                "chirp": "one call to diag(omega^((x - t)^2)), Clifford for every odd prime d",
            },
            "summary": summary,
        },
        args.out,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
