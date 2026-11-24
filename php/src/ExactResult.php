<?php

// Exact outcome probabilities and decision-conditional win probabilities of one scenario.

declare(strict_types=1);

namespace MontyHall\Lab;

final readonly class ExactResult
{
    public function __construct(
        public Fraction $prizeAtPick,
        public Fraction $decision,
        public Fraction $void,
        public Fraction $noOffer,
        public ?Fraction $observed,
        public ?Fraction $stay,
        public ?Fraction $switch,
    ) {
    }

    public function mixed(Fraction $q): ?Fraction
    {
        if ($this->stay === null || $this->switch === null) {
            return null;
        }
        return Fraction::one()->minus($q)->times($this->stay)->plus($q->times($this->switch));
    }

    public function win(Strategy $strategy, Fraction $q): ?Fraction
    {
        return match ($strategy) {
            Strategy::Stay => $this->stay,
            Strategy::Switch => $this->switch,
            Strategy::Mixed => $this->mixed($q),
        };
    }
}
