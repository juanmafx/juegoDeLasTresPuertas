# Bayesian tier: classical one-query comparators for the same marked-door black boxes.
from fractions import Fraction


def monty_partial_host(q: Fraction) -> Fraction:
    return (1 + q) / (2 + q)


def mark_likelihood(n: int, q: Fraction, target: int, mark: int) -> Fraction:
    return q if mark == target else (1 - q) / (n - 1)


def bit_query_value(n: int, q: Fraction) -> Fraction:
    best = Fraction(0)
    for queried in range(n):
        total = Fraction(0)
        for answer in (True, False):
            column = []
            for target in range(n):
                hit = mark_likelihood(n, q, target, queried)
                column.append(Fraction(1, n) * (hit if answer else 1 - hit))
            total += max(column)
        best = max(best, total)
    return best


def mark_reveal_value(n: int, q: Fraction) -> Fraction:
    total = Fraction(0)
    for mark in range(n):
        total += max(Fraction(1, n) * mark_likelihood(n, q, t, mark) for t in range(n))
    return total
