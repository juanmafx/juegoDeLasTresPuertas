# Scenario model shared by the exact solver, the simulator and the optimum curve.
import re
import sys
from dataclasses import dataclass, replace
from enum import StrEnum
from fractions import Fraction
from typing import Any

MIN_DOORS = 3
MAX_DOORS = 64
MAX_WEIGHT = 1_000_000
ENUMERATION_MAX_DOORS = 10
MAX_TRIALS = 100_000_000
MAX_SEED = 2**63 - 1
MAX_FRACTION_PART = 2**63 - 1
_INTEGER = re.compile(r"[ \t\n\v\f\r]*([+-]?)([0-9]+)[ \t\n\v\f\r]*", re.ASCII)
_MAX_INTEGER_DIGITS = 40


class ScenarioError(ValueError):
    pass


class Host(StrEnum):
    INFORMED = "informed"
    RANDOM = "random"
    BIASED = "biased"
    ADVERSARIAL = "adversarial"


class Strategy(StrEnum):
    STAY = "stay"
    SWITCH = "switch"
    MIXED = "mixed"


def parse_integer(text: str) -> int:
    match = _INTEGER.fullmatch(text)
    if match is None:
        raise ScenarioError(f"invalid integer {text!r}")
    digits = match.group(2).lstrip("0") or "0"
    if len(digits) > _MAX_INTEGER_DIGITS:
        raise ScenarioError(f"integer out of range {text!r}")
    value = int(digits)
    return -value if match.group(1) == "-" else value


def parse_fraction(text: str) -> Fraction:
    parts = text.split("/")
    if len(parts) > 2:
        raise ScenarioError(f"invalid fraction {text!r}")
    numerator = parse_integer(parts[0])
    denominator = parse_integer(parts[1]) if len(parts) == 2 else 1
    if denominator == 0 or max(abs(numerator), abs(denominator)) > MAX_FRACTION_PART:
        raise ScenarioError(f"invalid fraction {text!r}")
    return Fraction(numerator, denominator)


def format_fraction(value: Fraction) -> str:
    limit = sys.get_int_max_str_digits()
    sys.set_int_max_str_digits(0)
    try:
        return f"{value.numerator}/{value.denominator}"
    finally:
        sys.set_int_max_str_digits(limit)


def _integer(name: str, value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ScenarioError(f"{name} must be an integer")
    return value


def _weights(name: str, value: object, doors: int, minimum: int) -> tuple[int, ...]:
    if not isinstance(value, tuple) or len(value) != doors:
        raise ScenarioError(f"{name} must list exactly one weight per door")
    for weight in value:
        if not minimum <= _integer(name, weight) <= MAX_WEIGHT:
            raise ScenarioError(f"{name} entries must be between {minimum} and {MAX_WEIGHT}")
    return value


@dataclass(frozen=True, slots=True)
class Scenario:
    doors: int = 3
    prizes: int = 1
    prior: tuple[int, ...] | None = None
    pick: int = 0
    reveals: int = 1
    host: Host = Host.INFORMED
    host_weights: tuple[int, ...] | None = None
    mixed: Fraction = Fraction(1, 2)
    observed: tuple[int, ...] | None = None

    def __post_init__(self) -> None:
        doors = _integer("doors", self.doors)
        if not MIN_DOORS <= doors <= MAX_DOORS:
            raise ScenarioError(f"doors must be between {MIN_DOORS} and {MAX_DOORS}")
        if not 1 <= _integer("prizes", self.prizes) <= doors - 2:
            raise ScenarioError("prizes must be between 1 and doors - 2")
        if not 0 <= _integer("pick", self.pick) < doors:
            raise ScenarioError("pick must be a door index between 0 and doors - 1")
        if not 0 <= _integer("reveals", self.reveals) <= self.max_reveals:
            raise ScenarioError("reveals must be between 0 and doors - prizes - 1")
        if not isinstance(self.host, Host):
            raise ScenarioError("host must be informed, random, biased or adversarial")
        if self.prior is not None:
            prior = _weights("prior", self.prior, doors, 0)
            if sum(1 for weight in prior if weight > 0) < self.prizes:
                raise ScenarioError("prior must give positive weight to at least prizes doors")
        if (self.host is Host.BIASED) != (self.host_weights is not None):
            raise ScenarioError("host weights are required for, and only for, the biased host")
        if self.host_weights is not None:
            _weights("host weights", self.host_weights, doors, 1)
        if not isinstance(self.mixed, Fraction) or not 0 <= self.mixed <= 1:
            raise ScenarioError("mixed must be a fraction between 0 and 1")
        if self.observed is not None:
            observed = self.observed
            if (
                len(observed) != self.reveals
                or len(set(observed)) != len(observed)
                or any(not 0 <= _integer("observed", door) < doors for door in observed)
                or self.pick in observed
            ):
                raise ScenarioError("observed must list reveals distinct doors other than the pick")
            if list(observed) != sorted(observed):
                object.__setattr__(self, "observed", tuple(sorted(observed)))

    @property
    def max_reveals(self) -> int:
        return self.doors - self.prizes - 1

    @property
    def prior_weights(self) -> tuple[int, ...]:
        return self.prior if self.prior is not None else (1,) * self.doors

    @property
    def needs_enumeration(self) -> bool:
        return self.prior is not None or self.observed is not None

    def with_reveals(self, reveals: int) -> "Scenario":
        return replace(self, reveals=reveals, observed=None)

    def to_json(self) -> dict[str, Any]:
        return {
            "doors": self.doors,
            "prizes": self.prizes,
            "prior": "uniform" if self.prior is None else list(self.prior),
            "pick": self.pick,
            "reveals": self.reveals,
            "host": self.host.value,
            "host_weights": None if self.host_weights is None else list(self.host_weights),
            "mixed": format_fraction(self.mixed),
            "observed": None if self.observed is None else list(self.observed),
        }


def scenario_from_json(data: dict[str, Any]) -> Scenario:
    known = {
        "doors",
        "prizes",
        "prior",
        "pick",
        "reveals",
        "host",
        "host_weights",
        "mixed",
        "observed",
    }
    unknown = set(data) - known
    if unknown:
        raise ScenarioError(f"unknown scenario fields: {sorted(unknown)}")
    prior = data.get("prior", "uniform")
    host_weights = data.get("host_weights")
    observed = data.get("observed")
    try:
        host = Host(data.get("host", "informed"))
    except ValueError as error:
        raise ScenarioError("host must be informed, random, biased or adversarial") from error
    if prior != "uniform" and not isinstance(prior, list):
        raise ScenarioError("prior must be 'uniform' or a list of integer weights")
    return Scenario(
        doors=data.get("doors", 3),
        prizes=data.get("prizes", 1),
        prior=None if prior == "uniform" else tuple(prior),
        pick=data.get("pick", 0),
        reveals=data.get("reveals", 1),
        host=host,
        host_weights=None if host_weights is None else tuple(host_weights),
        mixed=parse_fraction(str(data.get("mixed", "1/2"))),
        observed=None if observed is None else tuple(observed),
    )
