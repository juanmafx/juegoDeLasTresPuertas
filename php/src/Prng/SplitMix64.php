<?php

// SplitMix64 seed expander, as fixed by spec/prng.md.

declare(strict_types=1);

namespace MontyHall\Lab\Prng;

final class SplitMix64
{
    private int $state;

    public function __construct(int $seed)
    {
        $this->state = $seed;
    }

    public function next(): int
    {
        $this->state = Uint64::add($this->state, Uint64::fromHalves(0x9E3779B9, 0x7F4A7C15));
        $z = $this->state;
        $z = Uint64::multiply($z ^ Uint64::shiftRight($z, 30), Uint64::fromHalves(0xBF58476D, 0x1CE4E5B9));
        $z = Uint64::multiply($z ^ Uint64::shiftRight($z, 27), Uint64::fromHalves(0x94D049BB, 0x133111EB));
        return $z ^ Uint64::shiftRight($z, 31);
    }
}
