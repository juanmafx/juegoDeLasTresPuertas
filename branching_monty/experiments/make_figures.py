# Generates the report figures (PNG) from reports/data and the core library.
import argparse
import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap

from branching_monty.core.grover import oracle, uniform_state
from branching_monty.core.holevo import holevo_chi
from branching_monty.core.host import decision_mask, host_joint
from branching_monty.core.leverage import leverage
from branching_monty.tiers.quantum import post_oracle_mana, success_grid

SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
BLUES = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
MARKERS = ["o", "s", "^", "D"]
STYLES = ["-", "--", "-.", ":"]


def style() -> None:
    plt.rcParams.update(
        {
            "figure.facecolor": SURFACE,
            "axes.facecolor": SURFACE,
            "axes.edgecolor": AXIS,
            "axes.labelcolor": INK_2,
            "axes.titlecolor": INK,
            "axes.titlesize": 11,
            "axes.labelsize": 9,
            "axes.grid": True,
            "grid.color": GRID,
            "grid.linewidth": 0.6,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "xtick.color": MUTED,
            "ytick.color": MUTED,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "legend.frameon": False,
            "legend.fontsize": 8,
            "lines.linewidth": 2,
            "font.family": "sans-serif",
            "savefig.dpi": 160,
            "savefig.bbox": "tight",
        }
    )


def load(data: Path, name: str) -> dict[str, Any]:
    return json.loads((data / f"{name}.json").read_text())


def label_end(ax: plt.Axes, x: float, y: float, text: str, dy: float = 0.0) -> None:
    ax.annotate(
        text,
        (x, y),
        xytext=(4, dy),
        textcoords="offset points",
        fontsize=8,
        color=INK_2,
        va="center",
    )


def lambda_vs_info(data: Path, out: Path) -> None:
    fig, axes = plt.subplots(2, 3, figsize=(12, 7))
    ax = axes[0, 0]
    qs = np.linspace(0, 1, 41)
    for i, convention in enumerate(("claim", "loss")):
        points = [
            leverage(host_joint(q, 3).probs, decision_mask(host_joint(q, 3), convention))
            for q in qs
        ]
        ax.plot(
            [p.info for p in points],
            [p.lam for p in points],
            STYLES[i],
            color=SERIES[i],
            label=f"revealed car = {convention}",
        )
    ax.annotate(
        "q = 1 (fully informed)",
        (2 / 3, 1.0),
        xytext=(6, -14),
        textcoords="offset points",
        fontsize=8,
        color=INK_2,
    )
    ax.annotate(
        "q = 0",
        (np.log2(3) - 2 / 3, 0.0),
        xytext=(-30, 8),
        textcoords="offset points",
        fontsize=8,
        color=INK_2,
    )
    ax.set_title("Partially informed host, N = 3")
    ax.legend(loc="lower left")

    ax = axes[0, 1]
    rows = load(data, "signalling_design")["rows"]
    names = [
        ("monty_uniform", "uniform Monty"),
        ("best_goat_only", "best goat-only code"),
        ("worst_goat_only", "worst goat-only (LP)"),
    ]
    for i, (key, label) in enumerate(names):
        sel = [r for r in rows if r["policy"] == key]
        ax.scatter(
            [r["info"] for r in sel],
            [r["lambda"] for r in sel],
            s=36 if i else 46,
            marker=MARKERS[i],
            color=SERIES[i],
            edgecolor=SURFACE,
            linewidth=1.2,
            label=label,
            zorder=3 - i,
        )
    ax.set_title("Committed host codes, N = 3..7, k = 1..N-2")
    ax.legend(loc="upper left")

    ax = axes[0, 2]
    rows = [r for r in load(data, "latency_sweep")["rows"] if r["latency"] == 0]
    for i, gap in enumerate((1, 2, 4)):
        sel = sorted((r for r in rows if r["gap"] == gap), key=lambda r: r["jitter"])
        ax.plot(
            [r["info"] for r in sel],
            [r["lambda"] for r in sel],
            STYLES[i],
            marker=MARKERS[i],
            markersize=5,
            color=SERIES[i],
            label=f"timing gap = {gap}",
        )
    base = next(r for r in rows if r["gap"] == 0)
    ax.scatter([base["info"]], [base["lambda"]], color=INK_2, s=40, zorder=4)
    label_end(ax, base["info"], base["lambda"], "no gap (plain Monty)", dy=8)
    ax.set_title("Timing side channel, N = 3 (jitter 0..8)")
    ax.legend(loc="upper left")

    ax = axes[1, 0]
    rows = load(data, "reflexivity_sweep")["rows"]
    for i, (mode, label) in enumerate(
        (("adversarial", "adversarial"), ("noise", "noise"), ("self_fulfilling", "self-fulfilling"))
    ):
        sel = [r for r in rows if r["mode"] == mode and r["lambda"] is not None]
        ax.plot(
            [eval_fraction(r["r"]) for r in sel],
            [r["lambda"] for r in sel],
            STYLES[i],
            marker=MARKERS[i],
            markersize=4,
            color=SERIES[i],
            label=label,
        )
    ax.set_title("Reflexive feedback, N = 3 (I(C;O) fixed at 2/3 bit)")
    ax.set_xlabel("feedback strength r")
    ax.set_ylabel("Lambda (bits)")
    ax.legend(loc="lower left")

    ax = axes[1, 1]
    phis = np.linspace(0, 2 * np.pi, 181)
    thetas = np.linspace(0, 2 * np.pi, 361)
    best = success_grid(3, phis, thetas).max(axis=1)
    chis = [
        holevo_chi([oracle(p, 3, t) @ uniform_state(3) for t in range(3)], [1 / 3] * 3)
        for p in phis
    ]
    ax.plot(
        chis,
        np.log2(3 * best),
        "o",
        markersize=3,
        color=SERIES[0],
        label="one oracle call, best diffusion",
    )
    for phi, text in ((np.pi, "phi = pi"), (2 * np.pi / 3, "phi = 2pi/3")):
        i = int(np.argmin(np.abs(phis - phi)))
        ax.scatter([chis[i]], [np.log2(3 * best[i])], color=INK, s=30, zorder=4)
        label_end(ax, chis[i], np.log2(3 * best[i]), text, dy=-8)
    ax.set_title("Quantum oracle phase family, N = 3")
    ax.set_xlabel("Holevo chi (bits)")
    ax.legend(loc="upper left")

    for a in (axes[0, 0], axes[0, 1], axes[0, 2], axes[1, 1]):
        if not a.get_xlabel():
            a.set_xlabel("information spent I (bits)")
        a.set_ylabel("Lambda = log2(N V) (bits)")
    axes[1, 2].axis("off")
    axes[1, 2].text(
        0,
        0.6,
        "Lambda = log2(N V) is the leverage of the\nBayes-optimal decision; "
        "I is I(C;O)\nclassically and the Holevo chi quantumly.\n\n"
        "Every panel states its own black box.",
        color=INK_2,
        fontsize=9,
    )
    fig.suptitle("Leverage against information spent, per policy family", color=INK)
    fig.tight_layout()
    fig.savefig(out / "lambda_vs_info.png")
    plt.close(fig)


def eval_fraction(text: str) -> float:
    num, _, den = text.partition("/")
    return float(num) / float(den) if den else float(num)


def p_of_q(data: Path, out: Path) -> None:
    doc = load(data, "partial_oracle")
    rows = doc["rows"]
    q = [r["q"] for r in rows]
    fig, ax = plt.subplots(figsize=(7.5, 4.8))
    series = [
        ("monty_host", "Monty host (1+q)/(2+q), goat shown"),
        ("quantum_exact_phases", "quantum one call = classical mark reveal"),
        ("quantum_pi_phases", "quantum one call, pi phases"),
        ("classical_bit_query", "classical one bit query"),
    ]
    for i, (key, label) in enumerate(series):
        ax.plot(q, [r[key] for r in rows], STYLES[i], color=SERIES[i], label=label)
    cross = doc["crossing_q"]
    ax.axvline(cross, color=MUTED, linewidth=1, linestyle=":")
    ax.annotate(
        f"crossing q = (sqrt5 - 1)/2 = {cross:.3f}",
        (cross, 0.32),
        xytext=(6, 0),
        textcoords="offset points",
        fontsize=8,
        color=INK_2,
    )
    ax.set_xlabel("probability q that the informed agent marks the car")
    ax.set_ylabel("probability of finding the car")
    ax.set_title("Partially informed agent, three doors: classical against quantum")
    ax.legend(loc="upper left")
    fig.savefig(out / "p_of_q.png")
    plt.close(fig)


def phase_heatmap(data: Path, out: Path, points: int) -> None:
    axis = np.linspace(0, 2 * np.pi, points)
    grid = success_grid(3, axis, axis)
    manas = np.array([post_oracle_mana(p, 3) for p in axis])
    fig, ax = plt.subplots(figsize=(7.5, 6))
    cmap = LinearSegmentedColormap.from_list("blue_seq", BLUES)
    mesh = ax.pcolormesh(
        axis, axis, grid.T, cmap=cmap, vmin=0, vmax=1, shading="auto", rasterized=True
    )
    bar = fig.colorbar(mesh, ax=ax, fraction=0.046, pad=0.04)
    bar.set_label("one-query success probability", color=INK_2, fontsize=9)
    bar.outline.set_edgecolor(AXIS)
    mana_field = np.tile(manas[:, None], (1, points)).T
    ax.contour(
        axis,
        axis,
        mana_field,
        levels=[0.25, 0.5],
        colors=INK_2,
        linewidths=[0.8, 1.2],
        linestyles=[":", "--"],
    )
    stab = load(data, "phase_grid")["stabilizer_points"]
    ax.scatter(
        [s["phi"] for s in stab],
        [s["theta"] for s in stab],
        s=60,
        facecolor=SURFACE,
        edgecolor=INK,
        linewidth=1.5,
        zorder=4,
        label="stabilizer (Clifford) points",
    )
    for phi, text in ((2 * np.pi / 3, "success 1"), (4 * np.pi / 3, "success 1")):
        ax.annotate(
            text, (phi, phi), xytext=(8, 8), textcoords="offset points", fontsize=8, color=INK
        )
    ticks = [0, 2 * np.pi / 3, np.pi, 4 * np.pi / 3, 2 * np.pi]
    labels = ["0", "2pi/3", "pi", "4pi/3", "2pi"]
    ax.set_xticks(ticks, labels)
    ax.set_yticks(ticks, labels)
    ax.grid(False)
    ax.set_xlabel("oracle phase phi")
    ax.set_ylabel("diffusion phase theta")
    ax.set_title(
        "Three doors, one query: success over the phase torus\n"
        "dotted: mana 0.25 bit, dashed: mana 0.5 bit (mana depends on phi only)"
    )
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12))
    fig.savefig(out / "phase_heatmap.png")
    plt.close(fig)


def gamma_curve(data: Path, out: Path) -> None:
    curves = load(data, "decoherence")["curves"]
    fig, ax = plt.subplots(figsize=(7.5, 4.8))
    for i, c in enumerate(curves):
        ax.plot(c["gamma"], c["success"], STYLES[i], color=SERIES[i], label=f"N = {c['doors']}")
        g = c["gamma_star_two_thirds"]["closed_form"]
        ax.scatter([g], [2 / 3], color=SERIES[i], s=50, edgecolor=SURFACE, linewidth=1.5, zorder=4)
        exact = {3: "1/2", 4: "4/9", 5: "113/288"}.get(c["doors"], f"{g:.4f}")
        ax.annotate(
            f"N = {c['doors']}: gamma* = {exact}",
            (g, 2 / 3),
            xytext=(0.62, 0.86 - 0.06 * i),
            textcoords="data",
            fontsize=8,
            color=INK_2,
            arrowprops={"arrowstyle": "-", "color": MUTED, "linewidth": 0.6},
        )
    ax.axhline(2 / 3, color=MUTED, linewidth=1, linestyle=":")
    ax.annotate(
        "classical Monty 2/3",
        (0.0, 2 / 3),
        xytext=(2, -11),
        textcoords="offset points",
        fontsize=8,
        color=MUTED,
    )
    ax.set_xlabel("dephasing strength gamma between oracle and diffusion")
    ax.set_ylabel("one-query success probability")
    ax.set_title("Decoherence as constraint erosion: success = (1 - gamma) P1 + gamma / N")
    ax.legend(loc="upper right")
    fig.savefig(out / "gamma_star.png")
    plt.close(fig)


def five_doors(data: Path, out: Path) -> None:
    summary = load(data, "five_doors")["summary"]["5"]
    rows = summary["rows"]
    phi = [r["phi"] for r in rows]
    fig, (top, bottom) = plt.subplots(
        2, 1, figsize=(7.5, 6.5), sharex=True, gridspec_kw={"height_ratios": [3, 2]}
    )
    top.plot(
        phi,
        [r["sdp_optimum"] for r in rows],
        STYLES[0],
        color=SERIES[0],
        label="quantum, indicator box (SDP optimum)",
    )
    top.axhline(
        summary["spekkens_best_indicator_box"],
        color=SERIES[1],
        linestyle=STYLES[1],
        label="Spekkens, indicator box (falls back to one bit query, 2/5)",
    )
    top.axhline(
        summary["spekkens_best_chirp_box"],
        color=SERIES[2],
        linestyle=STYLES[2],
        label="Spekkens, chirp box (exact)",
    )
    top.set_ylabel("one-query success")
    top.set_title("Five doors: quantum against Spekkens, same call budget")
    top.legend(loc="lower center", fontsize=7)
    bottom.plot(phi, [r["mana"] for r in rows], STYLES[0], color=INK_2)
    for k in (1, 2):
        x = 2 * np.pi * k / 5
        i = int(np.argmin(np.abs(np.array(phi) - x)))
        bottom.scatter([x], [rows[i]["mana"]], color=INK, s=24, zorder=4)
        top.scatter([x], [rows[i]["sdp_optimum"]], color=INK, s=24, zorder=4)
        top.annotate(
            f"{rows[i]['sdp_optimum']:.3f}",
            (x, rows[i]["sdp_optimum"]),
            xytext=(6, -10),
            textcoords="offset points",
            fontsize=8,
            color=INK_2,
        )
    bottom.annotate(
        "equal mana at 2pi/5 and 4pi/5,\nvery different success",
        (2 * np.pi / 5, rows[0]["mana"]),
        xytext=(0, 4),
        textcoords="offset points",
        fontsize=8,
        color=INK_2,
    )
    bottom.set_ylabel("post-oracle mana (bits)")
    bottom.set_xlabel("oracle phase phi")
    ticks = [0, 2 * np.pi / 5, 4 * np.pi / 5, np.pi, 6 * np.pi / 5, 8 * np.pi / 5, 2 * np.pi]
    bottom.set_xticks(ticks, ["0", "2pi/5", "4pi/5", "pi", "6pi/5", "8pi/5", "2pi"])
    fig.tight_layout()
    fig.savefig(out / "five_doors.png")
    plt.close(fig)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    root = Path(__file__).resolve().parent.parent / "reports"
    parser.add_argument("--data", type=Path, default=root / "data")
    parser.add_argument("--out", type=Path, default=root / "figures")
    parser.add_argument("--grid-points", type=int, default=721)
    args = parser.parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)
    style()
    lambda_vs_info(args.data, args.out)
    p_of_q(args.data, args.out)
    phase_heatmap(args.data, args.out, args.grid_points)
    gamma_curve(args.data, args.out)
    five_doors(args.data, args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
