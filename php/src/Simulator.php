<?php

// Seeded Monte Carlo simulator whose random stream is fixed by spec/prng.md.

declare(strict_types=1);

namespace MontyHall\Lab;

use MontyHall\Lab\Prng\Xoshiro256StarStar;

final class Simulator
{
    public static function simulate(Scenario $scenario, int $trials, int $seed): SimulationCounts
    {
        if ($trials < 1 || $trials > Scenario::MAX_TRIALS) {
            throw new ScenarioError(sprintf('trials must be between 1 and %d', Scenario::MAX_TRIALS));
        }
        if ($seed < 0) {
            throw new ScenarioError(sprintf('seed must be between 0 and %d', Scenario::MAX_SEED));
        }
        $mixedDenominator = $scenario->mixed->denominator;
        if ($mixedDenominator->isGreaterThan(PHP_INT_MAX)) {
            throw new ScenarioError(sprintf('mixed denominator must be at most %d for simulation', PHP_INT_MAX));
        }
        $qNumerator = $scenario->mixed->numerator->toInt();
        $qDenominator = $mixedDenominator->toInt();
        $rng = new Xoshiro256StarStar($seed);
        $doors = range(0, $scenario->doors - 1);
        $prior = $scenario->priorWeights();
        $pick = $scenario->pick;
        $host = $scenario->host;
        $hostWeights = $scenario->hostWeights;
        $observed = $scenario->observed;
        $randomHost = $host === Host::Random;
        $decision = 0;
        $void = 0;
        $noOffer = 0;
        $observedCount = 0;
        $stay = 0;
        $switch = 0;
        $mixed = 0;
        for ($trial = 0; $trial < $trials; $trial++) {
            $prizes = array_fill_keys($rng->weightedSample($doors, $prior, $scenario->prizes), true);
            $pickIsPrize = isset($prizes[$pick]);
            if ($host === Host::Adversarial && !$pickIsPrize) {
                $noOffer++;
                continue;
            }
            $candidates = [];
            $weights = [];
            foreach ($doors as $door) {
                if ($door === $pick || (!$randomHost && isset($prizes[$door]))) {
                    continue;
                }
                $candidates[] = $door;
                $weights[] = $hostWeights === null ? 1 : $hostWeights[$door];
            }
            $opened = $rng->weightedSample($candidates, $weights, $scenario->reveals);
            $openedSet = array_fill_keys($opened, true);
            if ($randomHost && array_intersect_key($openedSet, $prizes) !== []) {
                $void++;
                continue;
            }
            $decision++;
            $remaining = [];
            foreach ($doors as $door) {
                if ($door !== $pick && !isset($openedSet[$door])) {
                    $remaining[] = $door;
                }
            }
            $target = $remaining[$rng->bounded(count($remaining))];
            $switching = $rng->bounded($qDenominator) < $qNumerator;
            if ($observed !== null) {
                sort($opened);
                if ($opened !== $observed) {
                    continue;
                }
                $observedCount++;
            }
            $switchIsPrize = isset($prizes[$target]);
            $stay += $pickIsPrize ? 1 : 0;
            $switch += $switchIsPrize ? 1 : 0;
            $mixed += ($switching ? $switchIsPrize : $pickIsPrize) ? 1 : 0;
        }
        return new SimulationCounts(
            $trials,
            $seed,
            $decision,
            $void,
            $noOffer,
            $observed === null ? null : $observedCount,
            $stay,
            $switch,
            $mixed,
        );
    }
}
