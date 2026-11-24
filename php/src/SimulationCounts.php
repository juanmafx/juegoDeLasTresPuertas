<?php

// Integer tallies of one deterministic simulation run.

declare(strict_types=1);

namespace MontyHall\Lab;

final readonly class SimulationCounts
{
    public function __construct(
        public int $trials,
        public int $seed,
        public int $decision,
        public int $void,
        public int $noOffer,
        public ?int $observed,
        public int $stayWins,
        public int $switchWins,
        public int $mixedWins,
    ) {
    }

    public function sampleSize(): int
    {
        return $this->observed ?? $this->decision;
    }
}
