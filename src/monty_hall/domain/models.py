from dataclasses import dataclass
from enum import StrEnum

MIN_DOORS = 3
MAX_DOORS = 1024


class ConfigurationError(ValueError):
    pass


class HostPolicy(StrEnum):
    INFORMED = "informed"
    RANDOM = "random"


def require_integer(name: str, value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigurationError(f"{name} must be an integer")
    return value


@dataclass(frozen=True, slots=True)
class GameConfig:
    doors: int = 3
    opened: int = 1

    def __post_init__(self) -> None:
        doors = require_integer("doors", self.doors)
        opened = require_integer("opened", self.opened)
        if not MIN_DOORS <= doors <= MAX_DOORS:
            raise ConfigurationError(f"doors must be between {MIN_DOORS} and {MAX_DOORS}")
        if not 1 <= opened <= doors - 2:
            raise ConfigurationError("opened must be between 1 and doors - 2")


@dataclass(frozen=True, slots=True)
class GameOutcome:
    car: int
    first_pick: int
    opened: frozenset[int]
    switch_pick: int

    @property
    def stay_wins(self) -> bool:
        return self.first_pick == self.car

    @property
    def switch_wins(self) -> bool:
        return self.switch_pick == self.car
