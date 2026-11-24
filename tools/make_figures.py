# Generates the SVG charts and the result data under docs/figures/ from monty-lab CLI output.
# Usage: make_figures.py --cli "<command>" [--out DIR] [--check]
import argparse
import json
import shlex
import subprocess
import sys
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from fractions import Fraction
from math import comb
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

DEFAULT_OUT = Path(__file__).resolve().parent.parent / "docs" / "figures"
WIDTH = 760
HEIGHT = 440
LEFT = 72
RIGHT = 196
TOP = 84
BOTTOM = 60
SERIES = ("s1", "s2", "s3", "s4")
STYLE = """
.surface { fill: #fcfcfb; }
.title { fill: #0b0b0b; font: 600 16px sans-serif; }
.subtitle { fill: #52514e; font: 13px sans-serif; }
.label { fill: #52514e; font: 12px sans-serif; }
.value { fill: #0b0b0b; font: 12px sans-serif; }
.tick { fill: #898781; font: 11px sans-serif; }
.grid { stroke: #e1e0d9; stroke-width: 1; }
.axis { stroke: #c3c2b7; stroke-width: 1; }
.ref { stroke: #898781; stroke-width: 1.5; stroke-dasharray: 5 4; fill: none; }
.s1 { stroke: #2a78d6; fill: #2a78d6; } .s2 { stroke: #eb6834; fill: #eb6834; }
.s3 { stroke: #1baf7a; fill: #1baf7a; } .s4 { stroke: #6250d6; fill: #6250d6; }
.q1 { stroke: #9ec5f4; fill: #9ec5f4; } .q2 { stroke: #5598e7; fill: #5598e7; }
.q3 { stroke: #256abf; fill: #256abf; } .q4 { stroke: #0d366b; fill: #0d366b; }
.line { fill: none; stroke-width: 2; stroke-linejoin: round; }
.dashed { fill: none; stroke-width: 2; stroke-dasharray: 6 4; }
.dot { stroke: #fcfcfb; stroke-width: 2; }
@media (prefers-color-scheme: dark) {
  .surface { fill: #1a1a19; } .title, .value { fill: #f0efec; } .subtitle, .label { fill: #c3c2b7; }
  .grid { stroke: #2c2c2a; } .axis { stroke: #383835; } .dot { stroke: #1a1a19; }
  .s1 { stroke: #3987e5; fill: #3987e5; } .s2 { stroke: #d95926; fill: #d95926; }
  .s3 { stroke: #199e70; fill: #199e70; } .s4 { stroke: #9085e9; fill: #9085e9; }
  .q1 { stroke: #2a4f7d; fill: #2a4f7d; } .q2 { stroke: #256abf; fill: #256abf; }
  .q3 { stroke: #5598e7; fill: #5598e7; } .q4 { stroke: #b7d3f6; fill: #b7d3f6; }
}
"""


def frac(text: str) -> Fraction:
    numerator, denominator = text.split("/")
    return Fraction(int(numerator), int(denominator))


def show(value: Fraction) -> str:
    return f"{value.numerator}/{value.denominator}"


def num(value: float) -> str:
    return f"{value:.2f}".rstrip("0").rstrip(".")


class Lab:
    def __init__(self, cli: str, jobs: int) -> None:
        self.command = shlex.split(cli)
        self.jobs = jobs

    def run(self, args: Sequence[str]) -> Any:
        completed = subprocess.run(
            [*self.command, *args], capture_output=True, text=True, check=False
        )
        if completed.returncode != 0:
            raise RuntimeError(f"{' '.join(args)}: exit {completed.returncode} {completed.stderr}")
        return json.loads(completed.stdout)

    def run_all(self, calls: Sequence[Sequence[str]]) -> list[Any]:
        with ThreadPoolExecutor(self.jobs) as pool:
            return list(pool.map(self.run, calls))


@dataclass
class Series:
    name: str
    css: str
    points: list[tuple[float, float]]
    style: str = "line"
    markers: bool = True
    tips: list[str] = field(default_factory=list)


@dataclass
class Frame:
    x_range: tuple[float, float]
    y_range: tuple[float, float]
    left: float = LEFT
    top: float = TOP
    width: float = WIDTH - LEFT - RIGHT
    height: float = HEIGHT - TOP - BOTTOM

    def x(self, value: float) -> float:
        low, high = self.x_range
        return self.left + (value - low) / (high - low) * self.width

    def y(self, value: float) -> float:
        low, high = self.y_range
        return self.top + self.height - (value - low) / (high - low) * self.height


def document(title: str, subtitle: str, body: list[str], height: int = HEIGHT) -> str:
    return "\n".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" '
            f'viewBox="0 0 {WIDTH} {height}" role="img" aria-label="{escape(title)}">',
            f"<title>{escape(title)}</title>",
            f"<style>{STYLE}</style>",
            f'<rect class="surface" width="{WIDTH}" height="{height}"/>',
            f'<text class="title" x="20" y="28">{escape(title)}</text>',
            f'<text class="subtitle" x="20" y="48">{escape(subtitle)}</text>',
            *body,
            "</svg>",
            "",
        ]
    )


def axes(
    frame: Frame,
    x_ticks: Sequence[tuple[float, str]],
    y_ticks: Sequence[tuple[float, str]],
    x_label: str,
    y_label: str,
) -> list[str]:
    parts: list[str] = []
    for value, text in y_ticks:
        y = frame.y(value)
        parts.append(
            f'<line class="grid" x1="{frame.left:.1f}" x2="{frame.left + frame.width:.1f}" '
            f'y1="{y:.1f}" y2="{y:.1f}"/>'
        )
        parts.append(
            f'<text class="tick" x="{frame.left - 8:.1f}" y="{y + 4:.1f}" '
            f'text-anchor="end">{escape(text)}</text>'
        )
    bottom = frame.top + frame.height
    parts.append(
        f'<line class="axis" x1="{frame.left:.1f}" x2="{frame.left + frame.width:.1f}" '
        f'y1="{bottom:.1f}" y2="{bottom:.1f}"/>'
    )
    for value, text in x_ticks:
        x = frame.x(value)
        parts.append(
            f'<text class="tick" x="{x:.1f}" y="{bottom + 18:.1f}" '
            f'text-anchor="middle">{escape(text)}</text>'
        )
    parts.append(
        f'<text class="label" x="{frame.left + frame.width / 2:.1f}" y="{bottom + 40:.1f}" '
        f'text-anchor="middle">{escape(x_label)}</text>'
    )
    parts.append(
        f'<text class="label" x="{frame.left:.1f}" y="{frame.top - 10:.1f}" '
        f'text-anchor="start">{escape(y_label)}</text>'
    )
    return parts


def path(frame: Frame, points: Sequence[tuple[float, float]], step: bool = False) -> str:
    commands: list[str] = []
    previous: tuple[float, float] | None = None
    for x, y in points:
        if previous is None:
            commands.append(f"M{frame.x(x):.1f},{frame.y(y):.1f}")
        elif step:
            commands.append(f"H{frame.x(x):.1f}V{frame.y(y):.1f}")
        else:
            commands.append(f"L{frame.x(x):.1f},{frame.y(y):.1f}")
        previous = (x, y)
    return "".join(commands)


def draw_series(frame: Frame, series: Series) -> list[str]:
    parts = [f"<g><title>{escape(series.name)}</title>"]
    css = "dashed" if series.style == "dashed" else "line"
    step = series.style == "step"
    parts.append(f'<path class="{series.css} {css}" d="{path(frame, series.points, step)}"/>')
    parts.append("</g>")
    if series.markers:
        for index, (x, y) in enumerate(series.points):
            tip = series.tips[index] if index < len(series.tips) else f"{num(x)}, {num(y)}"
            parts.append(
                f'<circle class="{series.css} dot" cx="{frame.x(x):.1f}" cy="{frame.y(y):.1f}" '
                f'r="4.5"><title>{escape(series.name)}: {escape(tip)}</title></circle>'
            )
    return parts


def legend(entries: Sequence[tuple[str, str, str]], x: float, y: float) -> list[str]:
    parts: list[str] = []
    for index, (name, css, style) in enumerate(entries):
        row = y + index * 22
        kind = "dashed" if style == "dashed" else "line"
        parts.append(
            f'<line class="{css} {kind}" x1="{x:.1f}" x2="{x + 22:.1f}" y1="{row:.1f}" '
            f'y2="{row:.1f}"/>'
        )
        parts.append(
            f'<text class="label" x="{x + 30:.1f}" y="{row + 4:.1f}">{escape(name)}</text>'
        )
    return parts


def end_labels(frame: Frame, labelled: Sequence[tuple[str, float]], gap: float = 15) -> list[str]:
    placed: list[tuple[str, float]] = []
    for text, value in sorted(labelled, key=lambda item: -item[1]):
        y = frame.y(value) + 4
        if placed and y - placed[-1][1] < gap:
            y = placed[-1][1] + gap
        placed.append((text, y))
    x = frame.left + frame.width + 10
    return [
        f'<text class="value" x="{x:.1f}" y="{y:.1f}">{escape(text)}</text>' for text, y in placed
    ]


def chart_three_doors(lab: Lab) -> tuple[str, dict[str, Any]]:
    cases = [
        ("Informed host", ["exact"]),
        ("Random host, no prize shown", ["exact", "--host", "random"]),
        (
            "Biased host, door 1 opened",
            ["exact", "--host", "biased", "--host-weights", "1,3,1", "--observed", "1"],
        ),
        (
            "Biased host, door 2 opened",
            ["exact", "--host", "biased", "--host-weights", "1,3,1", "--observed", "2"],
        ),
        ("Adversarial host, switch offered", ["exact", "--host", "adversarial"]),
    ]
    outputs = lab.run_all([args for _, args in cases])
    data = {
        name: {"stay": out["win"]["stay"], "switch": out["win"]["switch"], "args": args}
        for (name, args), out in zip(cases, outputs, strict=True)
    }
    left = 250
    frame = Frame((0, 1), (0, 1), left=left, width=WIDTH - left - 90, top=TOP + 40)
    body = legend([("Stay", "s1", "line"), ("Switch", "s2", "line")], left, TOP + 6)
    for value in (0, 0.25, 0.5, 0.75, 1):
        x = frame.x(value)
        body.append(
            f'<line class="grid" x1="{x:.1f}" x2="{x:.1f}" y1="{TOP + 30}" y2="{HEIGHT - 50}"/>'
        )
        body.append(
            f'<text class="tick" x="{x:.1f}" y="{HEIGHT - 32}" text-anchor="middle">'
            f"{num(value)}</text>"
        )
    body.append(
        f'<text class="label" x="{frame.x(0.5):.1f}" y="{HEIGHT - 12}" text-anchor="middle">'
        "Probability of winning, given the decision is reached</text>"
    )
    row_height = (HEIGHT - 50 - TOP - 40) / len(cases)
    for index, (name, _) in enumerate(cases):
        top = TOP + 40 + index * row_height
        body.append(
            f'<text class="label" x="{left - 12}" y="{top + row_height / 2 + 4:.1f}" '
            f'text-anchor="end">{escape(name)}</text>'
        )
        for offset, strategy, css in ((0, "stay", "s1"), (1, "switch", "s2")):
            win = frac(data[name][strategy])
            y = top + 8 + offset * 16
            width = max(frame.x(float(win)) - left, 1.0)
            body.append(
                f'<rect class="{css}" x="{left}" y="{y:.1f}" width="{width:.1f}" height="14" '
                f'rx="2"><title>{escape(name)}, {strategy}: {show(win)}</title></rect>'
            )
            body.append(
                f'<text class="value" x="{left + width + 6:.1f}" y="{y + 11:.1f}">'
                f"{show(win)}</text>"
            )
    body.append(f'<line class="axis" x1="{left}" x2="{left}" y1="{TOP + 30}" y2="{HEIGHT - 50}"/>')
    svg = document(
        "Three doors, one pick, five hosts",
        "Biased host weights 1,3,1: when the prize is behind the pick it opens door 1 with p = 3/4",
        body,
    )
    return svg, data


def chart_probability_flow(lab: Lab) -> tuple[str, dict[str, Any]]:
    reveals = list(range(9))
    informed = lab.run_all([["exact", "--doors", "10", "--reveals", str(k)] for k in reveals])
    random_host = lab.run_all(
        [["exact", "--doors", "10", "--reveals", str(k), "--host", "random"] for k in reveals]
    )
    pick = [frac(out["win"]["stay"]) for out in informed]
    other = [frac(out["win"]["switch"]) for out in informed]
    fair = [frac(out["win"]["switch"]) for out in random_host]
    data = {
        "doors": 10,
        "reveals": reveals,
        "informed_pick": [show(v) for v in pick],
        "informed_each_closed_other": [show(v) for v in other],
        "random_each_closed_door": [show(v) for v in fair],
    }
    frame = Frame((0, 8), (0, 1))
    series = [
        Series(
            "Informed host: each closed unpicked door",
            "s2",
            list(zip(reveals, map(float, other), strict=True)),
        ),
        Series(
            "Random host: every closed door",
            "s3",
            list(zip(reveals, map(float, fair), strict=True)),
        ),
        Series("Informed host: the pick", "s1", list(zip(reveals, map(float, pick), strict=True))),
    ]
    for item, values in zip(series, (other, fair, pick), strict=True):
        item.tips = [f"K = {k}: {show(v)}" for k, v in zip(reveals, values, strict=True)]
    body = axes(
        frame,
        [(k, str(k)) for k in reveals],
        [(v, num(v)) for v in (0, 0.25, 0.5, 0.75, 1)],
        "Doors opened by the host (K), 10 doors, 1 prize",
        "Probability that the door holds the prize",
    )
    for item in series:
        body += draw_series(frame, item)
    body += end_labels(
        frame,
        [
            (f"Informed, unpicked {show(other[-1])}", float(other[-1])),
            (f"Random, any door {show(fair[-1])}", float(fair[-1])),
            (f"Informed, pick {show(pick[-1])}", float(pick[-1])),
        ],
    )
    svg = document(
        "Where the probability goes",
        "The informed host never opens the pick, so the pick stays at 1/10 and the rest flows "
        "to the unpicked doors",
        body,
    )
    return svg, data


def chart_biased(lab: Lab) -> tuple[str, dict[str, Any]]:
    steps = list(range(1, 20))
    calls = [
        ["exact", "--host", "biased", "--host-weights", f"1,{k},{20 - k}", "--observed", door]
        for door in ("1", "2")
        for k in steps
    ]
    outputs = lab.run_all(calls)
    door1 = [frac(out["win"]["switch"]) for out in outputs[: len(steps)]]
    door2 = [frac(out["win"]["switch"]) for out in outputs[len(steps) :]]
    p_values = [Fraction(k, 20) for k in steps]
    data = {
        "p": [show(p) for p in p_values],
        "switch_given_door1_opened": [show(v) for v in door1],
        "switch_given_door2_opened": [show(v) for v in door2],
        "matches_one_over_one_plus_p": all(
            v == 1 / (1 + p) for v, p in zip(door1, p_values, strict=True)
        ),
        "matches_one_over_two_minus_p": all(
            v == 1 / (2 - p) for v, p in zip(door2, p_values, strict=True)
        ),
    }
    frame = Frame((0, 1), (0.4, 1))
    xs = [float(p) for p in p_values]
    first = Series("Door 1 opened: 1/(1+p)", "s1", list(zip(xs, map(float, door1), strict=True)))
    second = Series("Door 2 opened: 1/(2-p)", "s2", list(zip(xs, map(float, door2), strict=True)))
    first.tips = [f"p = {show(p)}: {show(v)}" for p, v in zip(p_values, door1, strict=True)]
    second.tips = [f"p = {show(p)}: {show(v)}" for p, v in zip(p_values, door2, strict=True)]
    body = axes(
        frame,
        [(v, num(v)) for v in (0, 0.25, 0.5, 0.75, 1)],
        [(v, num(v)) for v in (0.4, 0.5, 0.6, 2 / 3, 0.8, 0.9, 1)],
        "p, the chance the host opens door 1 when it may open either",
        "Probability that switching wins, given which door was opened",
    )
    body.append(f'<path class="ref" d="M{frame.x(0):.1f},{frame.y(2 / 3):.1f}H{frame.x(1):.1f}"/>')
    body += draw_series(frame, first) + draw_series(frame, second)
    body += end_labels(
        frame,
        [
            ("Door 2 opened", float(door2[-1])),
            ("Door 1 opened", float(door1[-1])),
            ("2/3 averaged over doors", 2 / 3),
        ],
    )
    svg = document(
        "A biased host: the opened door carries information",
        "Three doors, pick door 0, host weights 1, 20p, 20(1-p); switching never falls below 1/2",
        body,
    )
    return svg, data


def chart_parabola(lab: Lab) -> tuple[str, dict[str, Any]]:
    args = ["optimum", "--doors", "10", "--strategy", "switch", "--cost", "1/100"]
    out = lab.run(args)
    curve = [(point["reveals"], frac(point["value"])) for point in out["curve"]]
    parabola = out["parabola"]
    a, b, c = frac(parabola["a"]), frac(parabola["b"]), frac(parabola["c"])
    best = out["optimum"]
    vertex = parabola["vertex"]
    frame = Frame((0, 8), (-0.25, 1))
    samples = [i / 10 for i in range(81)]
    fit = Series(
        "Least-squares parabola",
        "s2",
        [(x, float(a) * x * x + float(b) * x + float(c)) for x in samples],
        style="dashed",
        markers=False,
    )
    exact = Series("Exact V(K)", "s1", [(k, float(v)) for k, v in curve])
    exact.tips = [f"K = {k}: V = {show(v)}" for k, v in curve]
    body = axes(
        frame,
        [(k, str(k)) for k in range(9)],
        [(v, num(v)) for v in (-0.25, 0, 0.25, 0.5, 0.75, 1)],
        "Doors opened by the host (K)",
        "Net value V(K) = P(win | switch, K) - K/100",
    )
    body += draw_series(frame, fit) + draw_series(frame, exact)
    vx, vy = float(frac(vertex["reveals"])), float(frac(vertex["value"]))
    kx, ky = float(best["reveals"]), float(frac(best["value"]))
    body.append(
        f'<circle class="s2 dot" cx="{frame.x(vx):.1f}" cy="{frame.y(vy):.1f}" r="6">'
        f"<title>Vertex K = {vertex['reveals']}, a minimum</title></circle>"
    )
    body.append(
        f'<text class="value" x="{frame.x(vx):.1f}" y="{frame.y(vy) + 24:.1f}" '
        f'text-anchor="middle">vertex K = {num(vx)} (a minimum)</text>'
    )
    body.append(
        f'<circle class="s1 dot" cx="{frame.x(kx):.1f}" cy="{frame.y(ky):.1f}" r="7">'
        f"<title>Exact optimum K* = {best['reveals']}</title></circle>"
    )
    body.append(
        f'<text class="value" x="{frame.x(kx) - 10:.1f}" y="{frame.y(ky) - 4:.1f}" '
        f'text-anchor="end">K* = {best["reveals"]}, V = {best["value"]}</text>'
    )
    body += legend(
        [("Exact V(K)", "s1", "line"), ("Fitted parabola", "s2", "dashed")],
        frame.left + frame.width + 14,
        TOP + 10,
    )
    svg = document(
        "The hypothetical optimum parabola against the exact curve",
        "10 doors, informed host, switch, cost 1/100 per reveal: the fit is convex, so its "
        "vertex is a minimum",
        body,
    )
    return svg, {"args": args, "output": out}


def chart_cost_curves(lab: Lab) -> tuple[str, dict[str, Any]]:
    costs = [Fraction(0), Fraction(1, 20), Fraction(1, 10), Fraction(3, 20)]
    outputs = lab.run_all(
        [
            ["optimum", "--doors", "10", "--strategy", "switch", "--cost", show(cost)]
            for cost in costs
        ]
    )
    frame = Frame((0, 8), (-1.25, 1))
    body = axes(
        frame,
        [(k, str(k)) for k in range(9)],
        [(v, num(v)) for v in (-1, -0.5, 0, 0.5, 1)],
        "Doors opened by the host (K), 10 doors, informed host, switch",
        "Net value V(K)",
    )
    labels: list[tuple[str, float]] = []
    data: dict[str, Any] = {}
    for index, (cost, out) in enumerate(zip(costs, outputs, strict=True)):
        points = [(p["reveals"], frac(p["value"])) for p in out["curve"]]
        css = f"q{index + 1}"
        item = Series(f"c = {show(cost)}", css, [(k, float(v)) for k, v in points], markers=False)
        body += draw_series(frame, item)
        best = out["optimum"]
        body.append(
            f'<circle class="{css} dot" cx="{frame.x(best["reveals"]):.1f}" '
            f'cy="{frame.y(float(frac(best["value"]))):.1f}" r="6"><title>c = {show(cost)}: '
            f"K* = {best['reveals']}, V = {best['value']}</title></circle>"
        )
        labels.append((f"c = {show(cost)}, K* = {best['reveals']}", float(points[-1][1])))
        data[show(cost)] = {"optimum": best, "curve": out["curve"]}
    body += end_labels(frame, labels)
    svg = document(
        "Raising the price of a reveal flips the optimum from one corner to the other",
        "Dots mark the exact optimum; the critical cost here is 1/10, where the tie goes to K = 0",
        body,
    )
    return svg, data


def chart_shift(lab: Lab) -> tuple[str, dict[str, Any]]:
    costs = [Fraction(i, 400) for i in range(41)]
    hosts = ["informed", "random", "adversarial"]
    calls = [
        [
            "optimum",
            "--doors",
            "10",
            "--prizes",
            "2",
            "--host",
            host,
            "--strategy",
            "switch",
            "--cost",
            show(c),
        ]
        for host in hosts
        for c in costs
    ]
    outputs = lab.run_all(calls)
    panel_width = (WIDTH - 2 * LEFT) / 3
    body: list[str] = []
    data: dict[str, Any] = {"costs": [show(c) for c in costs]}
    for index, host in enumerate(hosts):
        chunk = outputs[index * len(costs) : (index + 1) * len(costs)]
        best = [out["optimum"]["reveals"] for out in chunk]
        data[host] = best
        frame = Frame(
            (0, 0.1), (0, 7), left=LEFT + index * panel_width, width=panel_width - 40, top=TOP + 20
        )
        frame.height = HEIGHT - TOP - 20 - BOTTOM
        body += axes(
            frame,
            [(v, num(v)) for v in (0, 0.05, 0.1)],
            [(v, str(v)) for v in (0, 7)] if index == 0 else [(v, "") for v in (0, 7)],
            "cost per reveal",
            f"{host} host",
        )
        item = Series(
            host, SERIES[index], [(float(c), k) for c, k in zip(costs, best, strict=True)]
        )
        item.style = "step"
        item.markers = False
        body += draw_series(frame, item)
        flip = next((c for c, k in zip(costs, best, strict=True) if k == 0), None)
        if flip is not None:
            body.append(
                f'<text class="value" x="{frame.x(float(flip)) - 6:.1f}" y="{frame.y(3.5):.1f}" '
                f'text-anchor="end">K* = 0 from c = {show(flip)}</text>'
            )
    svg = document(
        "The best number of reveals as the cost rises, by host",
        "10 doors, 2 prizes, switch: K* is always 0 or 7, and the host sets where it flips",
        body,
    )
    return svg, data


def critical_costs(lab: Lab) -> dict[str, Any]:
    rules: dict[str, Callable[[int, int], Fraction]] = {
        "informed switch": lambda n, m: Fraction(1, n),
        "informed mixed 1/2": lambda n, m: Fraction(1, 2 * n),
        "random switch": lambda n, m: Fraction(m, n * (m + 1)),
        "adversarial switch": lambda n, m: Fraction(m - 1, m * (n - 1)),
    }
    flags = {
        "informed switch": ["--strategy", "switch"],
        "informed mixed 1/2": ["--strategy", "mixed", "--mixed", "1/2"],
        "random switch": ["--host", "random", "--strategy", "switch"],
        "adversarial switch": ["--host", "adversarial", "--strategy", "switch"],
    }
    games = [(n, m) for n in range(4, 17) for m in range(1, min(3, n - 2) + 1)]
    base = [
        (name, n, m, ["optimum", "--doors", str(n), "--prizes", str(m), *flags[name]])
        for name in rules
        for n, m in games
    ]
    zero = lab.run_all([args for *_, args in base])
    checks: list[list[str]] = []
    expected: list[tuple[str, int, int, Fraction, int]] = []
    for (name, n, m, args), out in zip(base, zero, strict=True):
        curve = out["curve"]
        top = len(curve) - 1
        gain = frac(curve[-1]["win"]) - frac(curve[0]["win"])
        critical = gain / top if top > 0 and gain > 0 else Fraction(0)
        expected.append((name, n, m, critical, top))
        if critical > 0:
            checks.append([*args, "--cost", show(critical)])
            checks.append([*args, "--cost", show(critical - Fraction(1, 10**9))])
    outcomes = iter(lab.run_all(checks))
    table: dict[str, list[dict[str, Any]]] = {name: [] for name in rules}
    for name, n, m, critical, top in expected:
        verified = True
        if critical > 0:
            at = next(outcomes)["optimum"]["reveals"]
            below = next(outcomes)["optimum"]["reveals"]
            verified = at == 0 and below == top
        table[name].append(
            {
                "doors": n,
                "prizes": m,
                "critical_cost": show(critical),
                "formula": show(rules[name](n, m)),
                "matches_formula": critical == rules[name](n, m),
                "flips_at_critical_cost": verified,
            }
        )
    return table


def sweep(lab: Lab) -> dict[str, Any]:
    costs = ["0", "1/200", "1/50", "1/20", "1/10"]
    strategies = [["--strategy", "stay"], ["--strategy", "switch"], ["--strategy", "mixed"]]
    calls: list[list[str]] = []
    for n in range(3, 13):
        priors = ["uniform"]
        if n <= 10:
            priors += [",".join(str(n - i) for i in range(n)), ",".join(["1", *["3"] * (n - 1)])]
        for m in range(1, min(3, n - 2) + 1):
            for prior in priors:
                for host in ("informed", "random", "biased", "adversarial"):
                    extra = ["--host", host]
                    if host == "biased":
                        extra += ["--host-weights", ",".join(str(i + 1) for i in range(n))]
                    for strategy in strategies:
                        for cost in costs:
                            calls.append(
                                [
                                    "optimum",
                                    "--doors",
                                    str(n),
                                    "--prizes",
                                    str(m),
                                    "--prior",
                                    prior,
                                    *extra,
                                    *strategy,
                                    "--cost",
                                    cost,
                                ]
                            )
    outputs = lab.run_all(calls)
    summary: dict[str, Any] = {
        "invocations": len(calls),
        "with_parabola": 0,
        "shape": {"concave": 0, "convex": 0, "linear": 0},
        "interior_optimum": 0,
        "rounded_vertex_regret_positive": 0,
        "fitted_choice_regret_positive": 0,
        "fitted_choice_max_regret": "0/1",
        "fitted_choice_failures": [],
        "convex_relative_residual_below_1_percent": 0,
        "convex_relative_residual_max": "0/1",
        "convex_relative_residual_max_case": None,
    }
    worst = Fraction(0)
    worst_regret = Fraction(0)
    for args, out in zip(calls, outputs, strict=True):
        values = [frac(p["value"]) for p in out["curve"]]
        top = len(values) - 1
        if 0 < out["optimum"]["reveals"] < top:
            summary["interior_optimum"] += 1
        parabola = out["parabola"]
        if parabola is None:
            continue
        summary["with_parabola"] += 1
        summary["shape"][parabola["shape"]] += 1
        rounded = parabola["rounded_vertex"]
        if rounded is not None and frac(rounded["regret"]) > 0:
            summary["rounded_vertex_regret_positive"] += 1
        regret = frac(parabola["fitted_choice"]["regret"])
        if regret > 0:
            summary["fitted_choice_regret_positive"] += 1
            worst_regret = max(worst_regret, regret)
            summary["fitted_choice_failures"].append(
                {
                    "args": args[1:],
                    "optimum": out["optimum"]["reveals"],
                    "fitted_choice": parabola["fitted_choice"]["reveals"],
                    "regret": show(regret),
                    "corner_gap": show(abs(values[-1] - values[0])),
                }
            )
        if parabola["shape"] != "convex":
            continue
        mean = sum(values, Fraction(0)) / len(values)
        spread = sum(((v - mean) ** 2 for v in values), Fraction(0))
        relative = frac(parabola["residual_sum_of_squares"]) / spread
        if relative < Fraction(1, 100):
            summary["convex_relative_residual_below_1_percent"] += 1
        if relative > worst:
            worst = relative
            summary["convex_relative_residual_max"] = show(relative)
            summary["convex_relative_residual_max_case"] = args[1:]
    summary["fitted_choice_max_regret"] = show(worst_regret)
    return summary


def pick_prior(doors: int, prizes: int, others: int) -> Fraction:
    missed = Fraction(1)
    for draw in range(prizes):
        rest = (doors - 1 - draw) * others
        missed *= Fraction(rest, 1 + rest)
    return 1 - missed


def random_switch(doors: int, prizes: int, prior: Fraction, reveals: int) -> Fraction:
    total = comb(doors - 1, reveals)
    kept = Fraction(comb(doors - prizes, reveals), total)
    lost = Fraction(comb(doors - 1 - prizes, reveals), total)
    decision = prior * kept + (1 - prior) * lost
    wins = prior * kept * (prizes - 1) + (1 - prior) * lost * prizes
    return wins / ((doors - 1 - reveals) * decision)


def random_host_concavity(lab: Lab) -> dict[str, Any]:
    probe = ["optimum", "--doors", "10", "--prizes", "7", "--host", "random"]
    probe += ["--prior", ",".join(["1", *["8"] * 9]), "--strategy", "switch"]
    curve = lab.run(probe)["curve"]
    agrees = all(
        frac(point["win"]) == random_switch(10, 7, pick_prior(10, 7, 8), point["reveals"])
        for point in curve
    )
    found: list[tuple[int, int, int]] = []
    for doors in range(4, 31):
        for prizes in range(1, doors - 1):
            for others in range(1, 13):
                prior = pick_prior(doors, prizes, others)
                wins = [random_switch(doors, prizes, prior, k) for k in range(doors - prizes)]
                if any(wins[k - 1] + wins[k + 1] < 2 * wins[k] for k in range(1, len(wins) - 1)):
                    found.append((doors, prizes, others))
    doors, prizes, others = 22, 19, 8
    prior = pick_prior(doors, prizes, others)
    wins = [random_switch(doors, prizes, prior, k) for k in range(3)]
    cost = ((wins[1] - wins[0]) + (wins[2] - wins[1])) / 2
    values = [w - cost * k for k, w in enumerate(wins)]
    return {
        "note": "closed form evaluated in exact fractions by this script; N > 10 with an "
        "explicit prior is outside the CLI enumeration limit",
        "closed_form_matches_cli_for": probe[1:],
        "closed_form_matches_cli": agrees,
        "scan": "doors 4..30, every prize count, prior weight 1 on the pick and 1..12 elsewhere",
        "scan_nonconvex_cases": len(found),
        "scan_smallest_doors": min((case[0] for case in found), default=None),
        "example": {
            "doors": doors,
            "prizes": prizes,
            "prior": "1 on the pick, 8 on each other door",
            "prize_at_pick": show(prior),
            "switch_win": [show(w) for w in wins],
            "cost": show(cost),
            "value": [show(v) for v in values],
            "interior_optimum": values[1] > values[0] and values[1] > values[2],
        },
    }


def random_uniform_closed_form(lab: Lab) -> dict[str, Any]:
    games = [(n, m, k) for n in range(3, 12) for m in range(1, n - 1) for k in range(0, n - m)]
    outputs = lab.run_all(
        [
            [
                "exact",
                "--doors",
                str(n),
                "--prizes",
                str(m),
                "--reveals",
                str(k),
                "--host",
                "random",
            ]
            for n, m, k in games
        ]
    )
    mismatches = [
        [n, m, k]
        for (n, m, k), out in zip(games, outputs, strict=True)
        if frac(out["outcomes"]["decision"]) != Fraction(comb(n - m, k), comb(n, k))
        or frac(out["win"]["stay"]) != Fraction(m, n - k)
        or frac(out["win"]["switch"]) != Fraction(m, n - k)
    ]
    return {
        "formulas": "decision = C(N-M,K)/C(N,K), stay = switch = M/(N-K)",
        "games": len(games),
        "mismatches": mismatches,
    }


def build(lab: Lab) -> dict[str, str]:
    files: dict[str, str] = {}
    results: dict[str, Any] = {}
    charts = [
        ("three-doors", chart_three_doors),
        ("probability-flow", chart_probability_flow),
        ("biased-host", chart_biased),
        ("optimum-parabola", chart_parabola),
        ("cost-curves", chart_cost_curves),
        ("optimum-shift", chart_shift),
    ]
    for name, make in charts:
        svg, data = make(lab)
        files[f"{name}.svg"] = svg
        results[name] = data
    results["critical_costs"] = critical_costs(lab)
    results["sweep"] = sweep(lab)
    results["random_host_concavity"] = random_host_concavity(lab)
    results["random_uniform_closed_form"] = random_uniform_closed_form(lab)
    files["results.json"] = json.dumps(results, indent=2, sort_keys=True) + "\n"
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate docs/figures from monty-lab output.")
    parser.add_argument("--cli", required=True, help="command that runs a monty-lab CLI")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--jobs", type=int, default=8)
    parser.add_argument("--check", action="store_true", help="fail if the files are not current")
    options = parser.parse_args()
    files = build(Lab(options.cli, options.jobs))
    stale = [
        name
        for name, content in files.items()
        if not (options.out / name).is_file()
        or (options.out / name).read_text(encoding="utf-8") != content
    ]
    if options.check:
        for name in stale:
            print(f"stale: {name}", file=sys.stderr)
        print(f"{len(files) - len(stale)} of {len(files)} files current")
        return 1 if stale else 0
    options.out.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        (options.out / name).write_text(content, encoding="utf-8")
    print(f"wrote {len(files)} files to {options.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
