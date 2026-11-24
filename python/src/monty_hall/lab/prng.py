# Cross-language deterministic generator: SplitMix64 seeding, xoshiro256**, Lemire bounded draws.
from collections.abc import Sequence
from typing import TypeVar

MASK64 = (1 << 64) - 1
GOLDEN_GAMMA = 0x9E3779B97F4A7C15

T = TypeVar("T")


def _rotl(value: int, shift: int) -> int:
    return ((value << shift) | (value >> (64 - shift))) & MASK64


class SplitMix64:
    def __init__(self, seed: int) -> None:
        if not 0 <= seed <= MASK64:
            raise ValueError("seed must be an unsigned 64-bit integer")
        self._state = seed

    def next(self) -> int:
        self._state = (self._state + GOLDEN_GAMMA) & MASK64
        z = self._state
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & MASK64
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & MASK64
        return z ^ (z >> 31)


class Xoshiro256StarStar:
    def __init__(self, seed: int) -> None:
        expander = SplitMix64(seed)
        self._s = [expander.next() for _ in range(4)]

    def next_u64(self) -> int:
        s = self._s
        result = (_rotl((s[1] * 5) & MASK64, 7) * 9) & MASK64
        t = (s[1] << 17) & MASK64
        s[2] ^= s[0]
        s[3] ^= s[1]
        s[1] ^= s[2]
        s[0] ^= s[3]
        s[2] ^= t
        s[3] = _rotl(s[3], 45)
        return result

    def bounded(self, bound: int) -> int:
        if not 1 <= bound <= MASK64:
            raise ValueError("bound must be between 1 and 2^64 - 1")
        product = self.next_u64() * bound
        low = product & MASK64
        if low < bound:
            threshold = ((1 << 64) - bound) % bound
            while low < threshold:
                product = self.next_u64() * bound
                low = product & MASK64
        return product >> 64

    def weighted_index(self, weights: Sequence[int]) -> int:
        total = sum(weights)
        if total <= 0 or any(weight < 0 for weight in weights):
            raise ValueError("weights must be non-negative with a positive total")
        draw = self.bounded(total)
        cumulative = 0
        for index, weight in enumerate(weights):
            cumulative += weight
            if draw < cumulative:
                return index
        raise AssertionError("unreachable")

    def shuffle(self, items: list[T]) -> None:
        for index in range(len(items) - 1, 0, -1):
            other = self.bounded(index + 1)
            items[index], items[other] = items[other], items[index]

    def weighted_sample(
        self, items: Sequence[int], weights: Sequence[int], count: int
    ) -> list[int]:
        pool = list(items)
        pool_weights = list(weights)
        chosen: list[int] = []
        for _ in range(count):
            index = self.weighted_index(pool_weights)
            chosen.append(pool.pop(index))
            pool_weights.pop(index)
        return chosen
