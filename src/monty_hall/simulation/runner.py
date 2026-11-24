from dataclasses import dataclass
from random import Random

from monty_hall.domain.game import play_game
from monty_hall.domain.models import ConfigurationError, GameConfig, HostPolicy, require_integer

MAX_TRIALS = 100_000_000
MAX_SEED = 2**63 - 1


@dataclass(frozen=True, slots=True)
class SimulationRequest:
    config: GameConfig
    policy: HostPolicy
    trials: int
    seed: int

    def __post_init__(self) -> None:
        trials = require_integer("trials", self.trials)
        seed = require_integer("seed", self.seed)
        if not 1 <= trials <= MAX_TRIALS:
            raise ConfigurationError(f"trials must be between 1 and {MAX_TRIALS}")
        if not 0 <= seed <= MAX_SEED:
            raise ConfigurationError(f"seed must be between 0 and {MAX_SEED}")


@dataclass(frozen=True, slots=True)
class SimulationResult:
    request: SimulationRequest
    valid_games: int
    stay_wins: int
    switch_wins: int

    @property
    def stay_rate(self) -> float | None:
        return self.stay_wins / self.valid_games if self.valid_games else None

    @property
    def switch_rate(self) -> float | None:
        return self.switch_wins / self.valid_games if self.valid_games else None


def run_simulation(request: SimulationRequest) -> SimulationResult:
    rng = Random(request.seed)
    valid_games = stay_wins = switch_wins = 0
    for _ in range(request.trials):
        outcome = play_game(request.config, request.policy, rng)
        if outcome is None:
            continue
        valid_games += 1
        stay_wins += outcome.stay_wins
        switch_wins += outcome.switch_wins
    return SimulationResult(request, valid_games, stay_wins, switch_wins)
