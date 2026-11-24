<?php

// Validated scenario shared by the exact solver, the simulator and the optimum curve.

declare(strict_types=1);

namespace MontyHall\Lab;

final readonly class Scenario
{
    public const int MIN_DOORS = 3;
    public const int MAX_DOORS = 64;
    public const int MAX_WEIGHT = 1_000_000;
    public const int ENUMERATION_MAX_DOORS = 10;
    public const int MAX_TRIALS = 100_000_000;
    public const int MAX_SEED = PHP_INT_MAX;

    public ?array $observed;
    public Fraction $mixed;

    public function __construct(
        public int $doors = 3,
        public int $prizes = 1,
        public ?array $prior = null,
        public int $pick = 0,
        public int $reveals = 1,
        public Host $host = Host::Informed,
        public ?array $hostWeights = null,
        ?Fraction $mixed = null,
        ?array $observed = null,
    ) {
        $this->mixed = $mixed ?? Fraction::of(1, 2);
        if ($doors < self::MIN_DOORS || $doors > self::MAX_DOORS) {
            throw new ScenarioError(sprintf('doors must be between %d and %d', self::MIN_DOORS, self::MAX_DOORS));
        }
        if ($prizes < 1 || $prizes > $doors - 2) {
            throw new ScenarioError('prizes must be between 1 and doors - 2');
        }
        if ($pick < 0 || $pick >= $doors) {
            throw new ScenarioError('pick must be a door index between 0 and doors - 1');
        }
        if ($reveals < 0 || $reveals > $this->maxReveals()) {
            throw new ScenarioError('reveals must be between 0 and doors - prizes - 1');
        }
        if ($prior !== null) {
            self::checkWeights('prior', $prior, $doors, 0);
            if (count(array_filter($prior, static fn (int $weight): bool => $weight > 0)) < $prizes) {
                throw new ScenarioError('prior must give positive weight to at least prizes doors');
            }
        }
        if (($host === Host::Biased) !== ($hostWeights !== null)) {
            throw new ScenarioError('host weights are required for, and only for, the biased host');
        }
        if ($hostWeights !== null) {
            self::checkWeights('host weights', $hostWeights, $doors, 1);
        }
        if ($this->mixed->sign() < 0 || $this->mixed->compareTo(Fraction::one()) > 0) {
            throw new ScenarioError('mixed must be a fraction between 0 and 1');
        }
        if ($observed !== null) {
            $valid = count($observed) === $reveals && array_is_list($observed);
            foreach ($observed as $door) {
                if (!is_int($door) || $door < 0 || $door >= $doors || $door === $pick) {
                    $valid = false;
                }
            }
            if (!$valid || count(array_unique($observed)) !== count($observed)) {
                throw new ScenarioError('observed must list reveals distinct doors other than the pick');
            }
            sort($observed);
        }
        $this->observed = $observed;
    }

    public function maxReveals(): int
    {
        return $this->doors - $this->prizes - 1;
    }

    public function priorWeights(): array
    {
        return $this->prior ?? array_fill(0, $this->doors, 1);
    }

    public function withReveals(int $reveals): self
    {
        return new self(
            $this->doors,
            $this->prizes,
            $this->prior,
            $this->pick,
            $reveals,
            $this->host,
            $this->hostWeights,
            $this->mixed,
            null,
        );
    }

    public function toJson(): array
    {
        return [
            'doors' => $this->doors,
            'prizes' => $this->prizes,
            'prior' => $this->prior ?? 'uniform',
            'pick' => $this->pick,
            'reveals' => $this->reveals,
            'host' => $this->host->value,
            'host_weights' => $this->hostWeights,
            'mixed' => $this->mixed->toString(),
            'observed' => $this->observed,
        ];
    }

    private static function checkWeights(string $name, array $weights, int $doors, int $minimum): void
    {
        if (!array_is_list($weights) || count($weights) !== $doors) {
            throw new ScenarioError(sprintf('%s must list exactly one weight per door', $name));
        }
        foreach ($weights as $weight) {
            if (!is_int($weight) || $weight < $minimum || $weight > self::MAX_WEIGHT) {
                throw new ScenarioError(sprintf('%s entries must be between %d and %d', $name, $minimum, self::MAX_WEIGHT));
            }
        }
    }
}
