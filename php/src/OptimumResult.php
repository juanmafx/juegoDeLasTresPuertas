<?php

// Value curve over every feasible K, its exact discrete optimum and its fitted parabola.

declare(strict_types=1);

namespace MontyHall\Lab;

final readonly class OptimumResult
{
    public function __construct(
        public Strategy $strategy,
        public Fraction $cost,
        public array $curve,
        public CurvePoint $best,
        public ?Parabola $parabola,
    ) {
    }

    public function point(int $reveals): CurvePoint
    {
        $point = $this->curve[$reveals];
        assert($point instanceof CurvePoint);
        return $point;
    }
}
