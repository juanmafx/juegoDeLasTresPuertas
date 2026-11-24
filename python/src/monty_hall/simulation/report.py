from typing import Any

from monty_hall.analysis.exact import closed_form
from monty_hall.analysis.intervals import wilson_interval, z_score
from monty_hall.simulation.runner import SimulationResult


def _strategy_summary(wins: int, games: int, expected: float, confidence: float) -> dict[str, Any]:
    if games == 0:
        return {"wins": 0, "rate": None, "expected": expected, "interval": None, "z_score": None}
    interval = wilson_interval(wins, games, confidence)
    return {
        "wins": wins,
        "rate": wins / games,
        "expected": expected,
        "interval": [interval.lower, interval.upper],
        "z_score": z_score(wins, games, expected),
    }


def build_report(result: SimulationResult, confidence: float = 0.95) -> dict[str, Any]:
    request = result.request
    exact = closed_form(request.config, request.policy)
    return {
        "doors": request.config.doors,
        "opened": request.config.opened,
        "host": request.policy.value,
        "seed": request.seed,
        "trials": request.trials,
        "valid_games": result.valid_games,
        "confidence": confidence,
        "stay": _strategy_summary(
            result.stay_wins, result.valid_games, float(exact.stay), confidence
        ),
        "switch": _strategy_summary(
            result.switch_wins, result.valid_games, float(exact.switch), confidence
        ),
    }
