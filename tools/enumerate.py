# Independent brute-force oracle for spec/scenarios.json; shares no code with any implementation.
import argparse
import json
import sys
from fractions import Fraction
from math import comb, floor
from pathlib import Path
from typing import Any

BRUTE_FORCE_LEAF_LIMIT = 400_000


class Game:
    def __init__(self, scenario: dict[str, Any]) -> None:
        self.n: int = scenario["doors"]
        self.m: int = scenario["prizes"]
        self.pick: int = scenario["pick"]
        self.k: int = scenario["reveals"]
        self.host: str = scenario["host"]
        prior = scenario["prior"]
        self.uniform = prior == "uniform"
        self.prior: list[int] = [1] * self.n if self.uniform else list(prior)
        self.host_weights: list[int] | None = scenario["host_weights"]
        q_num, q_den = scenario["mixed"].split("/")
        self.q = Fraction(int(q_num), int(q_den))
        observed = scenario["observed"]
        self.observed: frozenset[int] | None = None if observed is None else frozenset(observed)


def _falling(n: int, k: int) -> int:
    product = 1
    for i in range(k):
        product *= n - i
    return product


def leaf_estimate(game: Game) -> int:
    return _falling(game.n, game.m) * _falling(game.n - 1, game.k) * max(1, game.n - 1 - game.k)


def _draws(
    pool: list[int], weights: dict[int, int], count: int
) -> list[tuple[tuple[int, ...], Fraction]]:
    if count == 0:
        return [((), Fraction(1))]
    total = sum(weights[d] for d in pool)
    sequences: list[tuple[tuple[int, ...], Fraction]] = []
    for door in pool:
        if weights[door] == 0:
            continue
        first = Fraction(weights[door], total)
        rest = [d for d in pool if d != door]
        for tail, probability in _draws(rest, weights, count - 1):
            sequences.append(((door, *tail), first * probability))
    return sequences


def brute_force(game: Game) -> dict[str, Fraction]:
    doors = list(range(game.n))
    prior = dict(enumerate(game.prior))
    tally = {
        "prize_at_pick": Fraction(0),
        "decision": Fraction(0),
        "void": Fraction(0),
        "no_offer": Fraction(0),
        "observed": Fraction(0),
        "stay": Fraction(0),
        "switch": Fraction(0),
        "mixed": Fraction(0),
    }
    for placement, p_place in _draws(doors, prior, game.m):
        prizes = set(placement)
        pick_wins = game.pick in prizes
        if pick_wins:
            tally["prize_at_pick"] += p_place
        if game.host == "adversarial" and not pick_wins:
            tally["no_offer"] += p_place
            continue
        if game.host == "random":
            pool = [d for d in doors if d != game.pick]
        else:
            pool = [d for d in doors if d != game.pick and d not in prizes]
        if game.host == "biased" and game.host_weights is not None:
            host_weights = dict(enumerate(game.host_weights))
        else:
            host_weights = dict.fromkeys(doors, 1)
        for opened_sequence, p_open in _draws(pool, host_weights, game.k):
            p_branch = p_place * p_open
            opened = set(opened_sequence)
            if game.host == "random" and opened & prizes:
                tally["void"] += p_branch
                continue
            tally["decision"] += p_branch
            if game.observed is not None and frozenset(opened) != game.observed:
                continue
            tally["observed"] += p_branch
            closed = [d for d in doors if d != game.pick and d not in opened]
            for target in closed:
                p_leaf = p_branch / len(closed)
                stay_win = Fraction(1 if pick_wins else 0)
                switch_win = Fraction(1 if target in prizes else 0)
                tally["stay"] += p_leaf * stay_win
                tally["switch"] += p_leaf * switch_win
                tally["mixed"] += p_leaf * ((1 - game.q) * stay_win + game.q * switch_win)
    return tally


def class_enumeration(game: Game) -> dict[str, Fraction]:
    if not game.uniform or game.observed is not None:
        raise ValueError("class enumeration needs a uniform prior and no observation")
    n, m, k = game.n, game.m, game.k
    closed = n - 1 - k
    tally = dict.fromkeys(
        ["prize_at_pick", "decision", "void", "no_offer", "observed", "stay", "switch", "mixed"],
        Fraction(0),
    )
    for pick_has_prize in (1, 0):
        p_class = Fraction(m, n) if pick_has_prize else Fraction(n - m, n)
        tally["prize_at_pick"] += p_class * pick_has_prize
        elsewhere = m - pick_has_prize
        if game.host == "adversarial" and not pick_has_prize:
            tally["no_offer"] += p_class
            continue
        if game.host == "random":
            outcomes = [
                (
                    revealed,
                    Fraction(
                        comb(elsewhere, revealed) * comb(n - 1 - elsewhere, k - revealed),
                        comb(n - 1, k),
                    ),
                )
                for revealed in range(min(elsewhere, k) + 1)
            ]
        else:
            outcomes = [(0, Fraction(1))]
        for revealed, p_reveal in outcomes:
            p_branch = p_class * p_reveal
            if revealed:
                tally["void"] += p_branch
                continue
            tally["decision"] += p_branch
            tally["observed"] += p_branch
            stay_win = Fraction(pick_has_prize)
            switch_win = Fraction(elsewhere, closed)
            tally["stay"] += p_branch * stay_win
            tally["switch"] += p_branch * switch_win
            tally["mixed"] += p_branch * ((1 - game.q) * stay_win + game.q * switch_win)
    return tally


def solve(scenario: dict[str, Any]) -> tuple[str, dict[str, Fraction]]:
    game = Game(scenario)
    if leaf_estimate(game) <= BRUTE_FORCE_LEAF_LIMIT:
        return "brute_force", brute_force(game)
    return "class_enumeration", class_enumeration(game)


def text(value: Fraction | None) -> str | None:
    return None if value is None else f"{value.numerator}/{value.denominator}"


def ratio(numerator: Fraction, denominator: Fraction) -> Fraction | None:
    return None if denominator == 0 else numerator / denominator


def exact_expectation(scenario: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    method, t = solve(scenario)
    condition = t["observed"] if scenario["observed"] is not None else t["decision"]
    return method, {
        "prize_at_pick": text(t["prize_at_pick"]),
        "outcomes": {
            "decision": text(t["decision"]),
            "void": text(t["void"]),
            "no_offer": text(t["no_offer"]),
            "observed": text(t["observed"]) if scenario["observed"] is not None else None,
        },
        "win": {
            "stay": text(ratio(t["stay"], condition)),
            "switch": text(ratio(t["switch"], condition)),
            "mixed": text(ratio(t["mixed"], condition)),
        },
    }


def gaussian_solve(matrix: list[list[Fraction]], rhs: list[Fraction]) -> list[Fraction]:
    size = len(rhs)
    rows = [[*matrix[i], rhs[i]] for i in range(size)]
    for column in range(size):
        pivot = next(r for r in range(column, size) if rows[r][column] != 0)
        rows[column], rows[pivot] = rows[pivot], rows[column]
        for r in range(size):
            if r != column and rows[r][column] != 0:
                factor = rows[r][column] / rows[column][column]
                rows[r] = [a - factor * b for a, b in zip(rows[r], rows[column], strict=True)]
    return [rows[i][size] / rows[i][i] for i in range(size)]


def optimum_expectation(
    scenario: dict[str, Any], strategy: str, cost: Fraction
) -> tuple[list[str], dict[str, Any]]:
    methods = []
    curve = []
    for reveals in range(scenario["doors"] - scenario["prizes"]):
        method, t = solve(dict(scenario, reveals=reveals, observed=None))
        methods.append(method)
        win = ratio(t[strategy], t["decision"])
        if win is None:
            raise ValueError("optimum undefined without a decision")
        curve.append((reveals, win, win - cost * reveals))
    best = curve[0]
    for candidate in curve[1:]:
        if candidate[2] > best[2]:
            best = candidate
    parabola: dict[str, Any] | None = None
    if len(curve) >= 3:
        xs = [Fraction(r) for r, _, _ in curve]
        ys = [v for _, _, v in curve]
        design = [[x * x, x, Fraction(1)] for x in xs]
        normal = [
            [sum((row[i] * row[j] for row in design), Fraction(0)) for j in range(3)]
            for i in range(3)
        ]
        moment = [
            sum((row[i] * y for row, y in zip(design, ys, strict=True)), Fraction(0))
            for i in range(3)
        ]
        a, b, c = gaussian_solve(normal, moment)
        fitted = [a * x * x + b * x + c for x in xs]
        residual = sum(((f - y) ** 2 for f, y in zip(fitted, ys, strict=True)), Fraction(0))
        top = max(fitted)
        fitted_choice = next(i for i, f in enumerate(fitted) if f == top)

        def choice(reveals: int) -> dict[str, Any]:
            return {
                "reveals": reveals,
                "value": text(curve[reveals][2]),
                "regret": text(best[2] - curve[reveals][2]),
            }

        shape = "concave" if a < 0 else "convex" if a > 0 else "linear"
        parabola = {
            "a": text(a),
            "b": text(b),
            "c": text(c),
            "shape": shape,
            "residual_sum_of_squares": text(residual),
            "vertex": None,
            "vertex_offset": None,
            "vertex_value_gap": None,
            "rounded_vertex": None,
            "fitted_choice": choice(fitted_choice),
        }
        if a != 0:
            vertex = -b / (2 * a)
            vertex_value = a * vertex * vertex + b * vertex + c
            parabola["vertex"] = {"reveals": text(vertex), "value": text(vertex_value)}
            parabola["vertex_offset"] = text(vertex - best[0])
            parabola["vertex_value_gap"] = text(vertex_value - best[2])
            rounded = min(max(floor(vertex + Fraction(1, 2)), 0), curve[-1][0])
            parabola["rounded_vertex"] = choice(rounded)
    return methods, {
        "curve": [{"reveals": r, "win": text(w), "value": text(v)} for r, w, v in curve],
        "optimum": {"reveals": best[0], "value": text(best[2])},
        "parabola": parabola,
    }


def expectations(entry: dict[str, Any]) -> dict[str, Any]:
    scenario = entry["scenario"]
    method, exact = exact_expectation(scenario)
    result: dict[str, Any] = {"exact_method": method, "exact": exact}
    if "optimum" in entry:
        strategy = entry["optimum"]["strategy"]
        num, den = entry["optimum"]["cost"].split("/")
        methods, optimum = optimum_expectation(scenario, strategy, Fraction(int(num), int(den)))
        result["optimum_methods"] = sorted(set(methods))
        result["optimum"] = optimum
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenarios", type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write", action="store_true")
    args = parser.parse_args()
    document = json.loads(args.scenarios.read_text("utf-8"))
    mismatches = []
    for entry in document["scenarios"]:
        computed = expectations(entry)
        if args.write:
            entry["expected"] = computed
        elif entry.get("expected") != computed:
            mismatches.append(entry["id"])
    if args.write:
        args.scenarios.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
        print(f"wrote expectations for {len(document['scenarios'])} scenarios")
        return 0
    for identifier in mismatches:
        print(f"MISMATCH {identifier}")
    print(f"checked {len(document['scenarios'])} scenarios, {len(mismatches)} mismatches")
    return 1 if mismatches else 0


if __name__ == "__main__":
    sys.exit(main())
