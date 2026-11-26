# Three-door phase grid: success over oracle and diffusion phases, post-oracle mana, residual.
import argparse
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

from branching_monty.core.grover import oracle
from branching_monty.experiments.output import emit
from branching_monty.tiers.quantum import post_oracle_mana, success_grid
from branching_monty.tiers.spekkens import is_clifford

SPEKKENS_BEST = 1.0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--points", type=int, default=721)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)

    axis = np.linspace(0, 2 * np.pi, args.points)
    grid = success_grid(3, axis, axis)
    manas = np.array([post_oracle_mana(phi, 3) for phi in axis])
    best = grid.max(axis=1)
    residual = best - SPEKKENS_BEST
    order = np.argsort(manas, kind="stable")
    sorted_residual = residual[order]
    rho, _ = spearmanr(manas, residual)
    step = (args.points - 1) // 3 if (args.points - 1) % 3 == 0 else None
    stabilizer = []
    if step:
        for i in range(0, args.points - 1, step):
            for j in range(0, args.points - 1, step):
                stabilizer.append(
                    {"phi": float(axis[i]), "theta": float(axis[j]), "success": float(grid[i, j])}
                )
    peaks = [
        {"phi": float(axis[i]), "theta": float(axis[j])}
        for i, j in zip(*np.where(grid > 1 - 1e-12), strict=True)
    ]
    emit(
        {
            "experiment": "phase_grid",
            "black_box": (
                "one call to O_t = diag(exp(i phi [x = t])) on a qutrit; uniform preparation; "
                "diffusion with phase theta; computational measurement"
            ),
            "points": args.points,
            "max_success": float(grid.max()),
            "peaks": peaks,
            "stabilizer_points": stabilizer,
            "clifford_oracle_phases": [
                float(phi) for phi in axis if is_clifford(oracle(phi, 3, 0), 3)
            ],
            "spekkens_best": SPEKKENS_BEST,
            "max_mana": float(manas.max()),
            "phi_at_max_mana": float(axis[int(np.argmax(manas))]),
            "residual_nonincreasing_in_mana": bool(np.all(np.diff(sorted_residual) <= 1e-12)),
            "residual_nondecreasing_in_mana": bool(np.all(np.diff(sorted_residual) >= -1e-12)),
            "spearman_mana_residual": float(rho),
            "per_phi": [
                {"phi": float(p), "mana": float(m), "best_success": float(b)}
                for p, m, b in zip(axis[::4], manas[::4], best[::4], strict=True)
            ],
        },
        args.out,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
