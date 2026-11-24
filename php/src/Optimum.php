<?php

// Exploration value curve V(K) = P(win) - c*K, its exact optimum and its least-squares parabola.

declare(strict_types=1);

namespace MontyHall\Lab;

final class Optimum
{
    public static function curve(Scenario $scenario, Strategy $strategy, Fraction $cost): OptimumResult
    {
        if ($scenario->observed !== null) {
            throw new ScenarioError('optimum does not accept an observed reveal');
        }
        if ($cost->sign() < 0) {
            throw new ScenarioError('cost must be a non-negative fraction');
        }
        $curve = [];
        for ($reveals = 0; $reveals <= $scenario->maxReveals(); $reveals++) {
            $win = Solver::solve($scenario->withReveals($reveals))->win($strategy, $scenario->mixed);
            if ($win === null) {
                throw new ScenarioError('optimum is undefined when the host never offers a decision');
            }
            $curve[] = new CurvePoint($reveals, $win, $win->minus($cost->times(Fraction::of($reveals))));
        }
        $best = $curve[0];
        foreach ($curve as $point) {
            if ($point->value->compareTo($best->value) > 0) {
                $best = $point;
            }
        }
        return new OptimumResult($strategy, $cost, $curve, $best, self::buildParabola($curve));
    }

    public static function fitParabola(array $points): array
    {
        $s = array_fill(0, 5, Fraction::zero());
        $t = array_fill(0, 3, Fraction::zero());
        foreach ($points as [$k, $value]) {
            $power = Fraction::one();
            for ($exponent = 0; $exponent < 5; $exponent++) {
                $s[$exponent] = $s[$exponent]->plus($power);
                if ($exponent < 3) {
                    $t[$exponent] = $t[$exponent]->plus($value->times($power));
                }
                $power = $power->times(Fraction::of($k));
            }
        }
        $matrix = [[$s[4], $s[3], $s[2]], [$s[3], $s[2], $s[1]], [$s[2], $s[1], $s[0]]];
        $rhs = [$t[2], $t[1], $t[0]];
        $determinant = self::determinant($matrix);
        $coefficients = [];
        for ($column = 0; $column < 3; $column++) {
            $replaced = $matrix;
            for ($row = 0; $row < 3; $row++) {
                $replaced[$row][$column] = $rhs[$row];
            }
            $coefficients[] = self::determinant($replaced)->dividedBy($determinant);
        }
        return $coefficients;
    }

    private static function buildParabola(array $curve): ?Parabola
    {
        if (count($curve) < 3) {
            return null;
        }
        $points = [];
        foreach ($curve as $point) {
            $points[] = [$point->reveals, $point->value];
        }
        [$a, $b, $c] = self::fitParabola($points);
        $residual = Fraction::zero();
        $fittedChoice = 0;
        $highestFit = null;
        foreach ($curve as $point) {
            $k = Fraction::of($point->reveals);
            $fitted = $a->times($k)->times($k)->plus($b->times($k))->plus($c);
            $error = $fitted->minus($point->value);
            $residual = $residual->plus($error->times($error));
            if ($highestFit === null || $fitted->compareTo($highestFit) > 0) {
                $highestFit = $fitted;
                $fittedChoice = $point->reveals;
            }
        }
        if ($a->isZero()) {
            return new Parabola($a, $b, $c, $residual, null, null, $fittedChoice, null);
        }
        $two = Fraction::of(2);
        $vertex = $b->negated()->dividedBy($two->times($a));
        $vertexValue = $c->minus($b->times($b)->dividedBy(Fraction::of(4)->times($a)));
        $highest = $curve[count($curve) - 1]->reveals;
        $rounded = $vertex->plus(Fraction::of(1, 2))->floor();
        $roundedVertex = $rounded->isNegative() ? 0 : ($rounded->isGreaterThan($highest) ? $highest : $rounded->toInt());
        return new Parabola($a, $b, $c, $residual, $vertex, $vertexValue, $fittedChoice, $roundedVertex);
    }

    private static function determinant(array $m): Fraction
    {
        return $m[0][0]->times($m[1][1]->times($m[2][2])->minus($m[1][2]->times($m[2][1])))
            ->minus($m[0][1]->times($m[1][0]->times($m[2][2])->minus($m[1][2]->times($m[2][0]))))
            ->plus($m[0][2]->times($m[1][0]->times($m[2][1])->minus($m[1][1]->times($m[2][0]))));
    }
}
