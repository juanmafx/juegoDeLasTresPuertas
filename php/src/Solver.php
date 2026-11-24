<?php

// Exact solver: closed forms for unobserved games, full enumeration for weighted priors and observed reveals.

declare(strict_types=1);

namespace MontyHall\Lab;

use Brick\Math\BigInteger;

final class Solver
{
    public static function solve(Scenario $scenario): ExactResult
    {
        $pi = self::prizeAtPick($scenario);
        if ($scenario->observed !== null) {
            return self::enumerateObserved($scenario, $pi);
        }
        return self::closedForm($scenario, $pi);
    }

    public static function prizeAtPick(Scenario $scenario): Fraction
    {
        if ($scenario->prior === null) {
            return Fraction::of($scenario->prizes, $scenario->doors);
        }
        self::requireEnumerable($scenario);
        $total = Fraction::zero();
        foreach (self::prizeSetDistribution($scenario->doors, $scenario->prizes, $scenario->prior) as $mask => $probability) {
            if (($mask >> $scenario->pick & 1) === 1) {
                $total = $total->plus($probability);
            }
        }
        return $total;
    }

    public static function prizeSetDistribution(int $doors, int $prizes, array $weights): array
    {
        $layer = [0 => Fraction::one()];
        $total = array_sum($weights);
        for ($draw = 0; $draw < $prizes; $draw++) {
            $following = [];
            foreach ($layer as $mask => $probability) {
                $remaining = $total;
                for ($door = 0; $door < $doors; $door++) {
                    if (($mask >> $door & 1) === 1) {
                        $remaining -= $weights[$door];
                    }
                }
                for ($door = 0; $door < $doors; $door++) {
                    if (($mask >> $door & 1) === 1 || $weights[$door] === 0) {
                        continue;
                    }
                    $key = $mask | 1 << $door;
                    $term = $probability->times(Fraction::of($weights[$door], $remaining));
                    $following[$key] = isset($following[$key]) ? $following[$key]->plus($term) : $term;
                }
            }
            $layer = $following;
        }
        return $layer;
    }

    public static function closedForm(Scenario $scenario, Fraction $pi): ExactResult
    {
        $n = $scenario->doors;
        $m = $scenario->prizes;
        $k = $scenario->reveals;
        $remaining = Fraction::of($n - 1 - $k);
        $zero = Fraction::zero();
        $one = Fraction::one();
        $prizes = Fraction::of($m);
        if ($scenario->host === Host::Informed || $scenario->host === Host::Biased) {
            return new ExactResult($pi, $one, $zero, $zero, null, $pi, $prizes->minus($pi)->dividedBy($remaining));
        }
        if ($scenario->host === Host::Adversarial) {
            $offered = !$pi->isZero();
            return new ExactResult(
                $pi,
                $pi,
                $zero,
                $one->minus($pi),
                null,
                $offered ? $one : null,
                $offered ? Fraction::of($m - 1)->dividedBy($remaining) : null,
            );
        }
        $hit = Fraction::of(self::binomial($n - $m, $k), self::binomial($n - 1, $k));
        $miss = Fraction::of(self::binomial($n - 1 - $m, $k), self::binomial($n - 1, $k));
        $stayJoint = $pi->times($hit);
        $missJoint = $one->minus($pi)->times($miss);
        $decision = $stayJoint->plus($missJoint);
        $switchJoint = $stayJoint->times(Fraction::of($m - 1))->plus($missJoint->times($prizes))->dividedBy($remaining);
        return new ExactResult(
            $pi,
            $decision,
            $one->minus($decision),
            $zero,
            null,
            self::conditional($stayJoint, $decision),
            self::conditional($switchJoint, $decision),
        );
    }

    public static function enumerateObserved(Scenario $scenario, Fraction $pi): ExactResult
    {
        $observed = $scenario->observed;
        if ($observed === null) {
            throw new ScenarioError('enumeration requires an observed reveal');
        }
        self::requireEnumerable($scenario);
        $n = $scenario->doors;
        $pick = $scenario->pick;
        $remaining = [];
        for ($door = 0; $door < $n; $door++) {
            if ($door !== $pick && !in_array($door, $observed, true)) {
                $remaining[] = $door;
            }
        }
        $joint = Fraction::zero();
        $stay = Fraction::zero();
        $switch = Fraction::zero();
        foreach (self::prizeSetDistribution($n, $scenario->prizes, $scenario->priorWeights()) as $mask => $probability) {
            $weight = $probability->times(self::revealProbability($scenario, $mask, $observed));
            if ($weight->isZero()) {
                continue;
            }
            $joint = $joint->plus($weight);
            if (($mask >> $pick & 1) === 1) {
                $stay = $stay->plus($weight);
            }
            $closedPrizes = 0;
            foreach ($remaining as $door) {
                $closedPrizes += $mask >> $door & 1;
            }
            $switch = $switch->plus($weight->times(Fraction::of($closedPrizes, count($remaining))));
        }
        $unobserved = self::closedForm($scenario, $pi);
        return new ExactResult(
            $pi,
            $unobserved->decision,
            $unobserved->void,
            $unobserved->noOffer,
            $joint,
            self::conditional($stay, $joint),
            self::conditional($switch, $joint),
        );
    }

    public static function binomial(int $n, int $k): BigInteger
    {
        if ($k < 0 || $k > $n) {
            return BigInteger::zero();
        }
        $k = min($k, $n - $k);
        $result = BigInteger::one();
        for ($i = 1; $i <= $k; $i++) {
            $result = $result->multipliedBy($n - $k + $i)->quotient($i);
        }
        return $result;
    }

    private static function revealProbability(Scenario $scenario, int $prizeMask, array $observed): Fraction
    {
        $pick = $scenario->pick;
        $k = $scenario->reveals;
        if ($scenario->host === Host::Random) {
            foreach ($observed as $door) {
                if (($prizeMask >> $door & 1) === 1) {
                    return Fraction::zero();
                }
            }
            return Fraction::of(1, self::binomial($scenario->doors - 1, $k));
        }
        if ($scenario->host === Host::Adversarial && ($prizeMask >> $pick & 1) === 0) {
            return Fraction::zero();
        }
        $valid = [];
        for ($door = 0; $door < $scenario->doors; $door++) {
            if ($door !== $pick && ($prizeMask >> $door & 1) === 0) {
                $valid[] = $door;
            }
        }
        foreach ($observed as $door) {
            if (!in_array($door, $valid, true)) {
                return Fraction::zero();
            }
        }
        if ($scenario->host === Host::Biased && $scenario->hostWeights !== null) {
            $weights = $scenario->hostWeights;
            $poolWeight = 0;
            foreach ($valid as $door) {
                $poolWeight += $weights[$door];
            }
            return self::orderedSampleProbability($observed, $poolWeight, $weights);
        }
        return Fraction::of(1, self::binomial(count($valid), $k));
    }

    private static function orderedSampleProbability(array $chosen, int $poolWeight, array $weights): Fraction
    {
        $size = count($chosen);
        $layer = [0 => Fraction::one()];
        for ($step = 0; $step < $size; $step++) {
            $following = [];
            foreach ($layer as $mask => $probability) {
                $used = 0;
                for ($i = 0; $i < $size; $i++) {
                    if (($mask >> $i & 1) === 1) {
                        $used += $weights[$chosen[$i]];
                    }
                }
                for ($i = 0; $i < $size; $i++) {
                    if (($mask >> $i & 1) === 1) {
                        continue;
                    }
                    $key = $mask | 1 << $i;
                    $term = $probability->times(Fraction::of($weights[$chosen[$i]], $poolWeight - $used));
                    $following[$key] = isset($following[$key]) ? $following[$key]->plus($term) : $term;
                }
            }
            $layer = $following;
        }
        return $layer[(1 << $size) - 1] ?? Fraction::one();
    }

    private static function conditional(Fraction $numerator, Fraction $denominator): ?Fraction
    {
        return $denominator->isZero() ? null : $numerator->dividedBy($denominator);
    }

    private static function requireEnumerable(Scenario $scenario): void
    {
        if ($scenario->doors > Scenario::ENUMERATION_MAX_DOORS) {
            throw new ScenarioError(sprintf(
                'weighted priors and observed reveals support at most %d doors',
                Scenario::ENUMERATION_MAX_DOORS,
            ));
        }
    }
}
