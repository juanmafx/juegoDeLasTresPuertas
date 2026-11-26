# Partially informed oracle: quantum one-query success against the classical black boxes, over q.
import argparse
from fractions import Fraction
from pathlib import Path

import numpy as np

from branching_monty.experiments.output import emit
from branching_monty.tiers.bayesian import bit_query_value, mark_reveal_value, monty_partial_host
from branching_monty.tiers.quantum import best_phases, partial_oracle_grover, partial_oracle_optimum


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--steps", type=int, default=40)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)

    phi, theta = best_phases(3)
    rows = []
    for i in range(args.steps + 1):
        q = Fraction(i, args.steps)
        qf = float(q)
        rows.append(
            {
                "q": qf,
                "monty_host": float(monty_partial_host(q)),
                "classical_bit_query": float(bit_query_value(3, q)),
                "classical_mark_reveal": float(mark_reveal_value(3, q)),
                "quantum_exact_phases": partial_oracle_grover(phi, theta, 3, qf),
                "quantum_pi_phases": partial_oracle_grover(np.pi, np.pi, 3, qf),
                "quantum_sdp_exact_phase": partial_oracle_optimum(phi, 3, qf),
                "quantum_sdp_pi_phase": partial_oracle_optimum(np.pi, 3, qf),
            }
        )
    emit(
        {
            "experiment": "partial_oracle",
            "black_boxes": {
                "monty_host": "host opens one door, informed w.p. q; conditional on a goat",
                "classical_bit_query": "one query 'is door x marked?' to a mark correct w.p. q",
                "classical_mark_reveal": "one call returning the marked door, correct w.p. q",
                "quantum": "one phase-oracle call on the mark, correct w.p. q (mixed channel)",
            },
            "crossing_q": (np.sqrt(5) - 1) / 2,
            "rows": rows,
        },
        args.out,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
