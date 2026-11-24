<?php

// Exact least-squares quadratic fit of the value curve: the hypothetical optimum parabola.

declare(strict_types=1);

namespace MontyHall\Lab;

final readonly class Parabola
{
    public function __construct(
        public Fraction $a,
        public Fraction $b,
        public Fraction $c,
        public Fraction $residualSumOfSquares,
        public ?Fraction $vertexReveals,
        public ?Fraction $vertexValue,
        public int $fittedChoice,
        public ?int $roundedVertex,
    ) {
    }

    public function shape(): string
    {
        return match ($this->a->sign()) {
            -1 => 'concave',
            1 => 'convex',
            default => 'linear',
        };
    }

    public function at(Fraction $k): Fraction
    {
        return $this->a->times($k)->times($k)->plus($this->b->times($k))->plus($this->c);
    }
}
