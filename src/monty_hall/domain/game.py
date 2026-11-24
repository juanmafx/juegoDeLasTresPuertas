from random import Random

from monty_hall.domain.models import GameConfig, GameOutcome, HostPolicy


def play_game(config: GameConfig, policy: HostPolicy, rng: Random) -> GameOutcome | None:
    car = rng.randrange(config.doors)
    first_pick = rng.randrange(config.doors)
    other_doors = [door for door in range(config.doors) if door != first_pick]
    eligible = (
        [door for door in other_doors if door != car]
        if policy is HostPolicy.INFORMED
        else other_doors
    )
    opened = frozenset(rng.sample(eligible, config.opened))
    if car in opened:
        return None
    switch_options = [door for door in other_doors if door not in opened]
    return GameOutcome(car, first_pick, opened, rng.choice(switch_options))
