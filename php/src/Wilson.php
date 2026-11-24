<?php

// Wilson score interval for a binomial proportion, reported as floating point by the simulate command.

declare(strict_types=1);

namespace MontyHall\Lab;

use InvalidArgumentException;

final class Wilson
{
    public const float Z95 = 1.959963984540054;

    public static function interval(int $successes, int $trials, float $z = self::Z95): array
    {
        if ($trials <= 0) {
            throw new InvalidArgumentException('trials must be positive');
        }
        if ($successes < 0 || $successes > $trials) {
            throw new InvalidArgumentException('successes must be between 0 and trials');
        }
        $zSquared = $z * $z;
        $rate = (float) $successes / $trials;
        $denominator = 1 + $zSquared / $trials;
        $center = ($rate + $zSquared / (2 * $trials)) / $denominator;
        $margin = $z * sqrt($rate * (1 - $rate) / $trials + $zSquared / (4 * $trials ** 2)) / $denominator;
        $lower = $successes === 0 ? 0.0 : max(0.0, $center - $margin);
        $upper = $successes === $trials ? 1.0 : min(1.0, $center + $margin);
        return [$lower, $upper];
    }
}
