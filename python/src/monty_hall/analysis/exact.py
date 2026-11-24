from dataclasses import dataclass
from fractions import Fraction
from itertools import combinations, product

from monty_hall.domain.models import ConfigurationError, GameConfig, HostPolicy

MAX_ENUMERATION_DOORS = 9


@dataclass(frozen=True, slots=True)
class WinProbabilities:
    stay: Fraction
    switch: Fraction
    valid_game: Fraction


def closed_form(config: GameConfig, policy: HostPolicy) -> WinProbabilities:
    doors, opened = config.doors, config.opened
    if policy is HostPolicy.INFORMED:
        return WinProbabilities(
            stay=Fraction(1, doors),
            switch=Fraction(doors - 1, doors * (doors - opened - 1)),
            valid_game=Fraction(1),
        )
    conditional = Fraction(1, doors - opened)
    return WinProbabilities(
        stay=conditional,
        switch=conditional,
        valid_game=Fraction(doors - opened, doors),
    )


def enumerate_game_tree(config: GameConfig, policy: HostPolicy) -> WinProbabilities:
    if config.doors > MAX_ENUMERATION_DOORS:
        raise ConfigurationError(f"enumeration supports at most {MAX_ENUMERATION_DOORS} doors")
    doors = range(config.doors)
    root_probability = Fraction(1, config.doors**2)
    valid = stay = switch = Fraction(0)
    for car, first_pick in product(doors, repeat=2):
        other_doors = [door for door in doors if door != first_pick]
        eligible = (
            [door for door in other_doors if door != car]
            if policy is HostPolicy.INFORMED
            else other_doors
        )
        reveals = list(combinations(eligible, config.opened))
        branch_probability = root_probability / len(reveals)
        for reveal in reveals:
            if car in reveal:
                continue
            valid += branch_probability
            if first_pick == car:
                stay += branch_probability
            switch_options = [door for door in other_doors if door not in reveal]
            if car in switch_options:
                switch += branch_probability / len(switch_options)
    return WinProbabilities(stay=stay / valid, switch=switch / valid, valid_game=valid)
