from dataclasses import dataclass
from math import sqrt
from statistics import NormalDist

Z95 = 1.959963984540054


@dataclass(frozen=True, slots=True)
class ConfidenceInterval:
    lower: float
    upper: float

    def contains(self, value: float) -> bool:
        return self.lower <= value <= self.upper


def wilson_interval(successes: int, trials: int, confidence: float = 0.95) -> ConfidenceInterval:
    if trials <= 0:
        raise ValueError("trials must be positive")
    if not 0 <= successes <= trials:
        raise ValueError("successes must be between 0 and trials")
    if not 0 < confidence < 1:
        raise ValueError("confidence must be strictly between 0 and 1")
    z = Z95 if confidence == 0.95 else NormalDist().inv_cdf((1 + confidence) / 2)
    z_squared = z * z
    rate = successes / trials
    denominator = 1 + z_squared / trials
    center = (rate + z_squared / (2 * trials)) / denominator
    margin = z * sqrt(rate * (1 - rate) / trials + z_squared / (4 * trials**2)) / denominator
    lower = 0.0 if successes == 0 else max(0.0, center - margin)
    upper = 1.0 if successes == trials else min(1.0, center + margin)
    return ConfidenceInterval(lower, upper)


def z_score(successes: int, trials: int, expected: float) -> float:
    if trials <= 0:
        raise ValueError("trials must be positive")
    if not 0 < expected < 1:
        raise ValueError("expected must be strictly between 0 and 1")
    standard_error = sqrt(expected * (1 - expected) / trials)
    return (successes / trials - expected) / standard_error
