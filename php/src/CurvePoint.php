<?php

// One point (K, P(win), V(K)) of the exploration value curve.

declare(strict_types=1);

namespace MontyHall\Lab;

final readonly class CurvePoint
{
    public function __construct(public int $reveals, public Fraction $win, public Fraction $value)
    {
    }
}
