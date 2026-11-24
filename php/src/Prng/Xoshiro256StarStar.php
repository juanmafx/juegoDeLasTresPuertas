<?php

// xoshiro256** generator with Lemire bounded draws, weighted choice, sampling and shuffle from spec/prng.md.

declare(strict_types=1);

namespace MontyHall\Lab\Prng;

use InvalidArgumentException;
use LogicException;

final class Xoshiro256StarStar
{
    private int $s0;
    private int $s1;
    private int $s2;
    private int $s3;

    public function __construct(int $seed)
    {
        $expander = new SplitMix64($seed);
        $this->s0 = $expander->next();
        $this->s1 = $expander->next();
        $this->s2 = $expander->next();
        $this->s3 = $expander->next();
    }

    public function nextU64(): int
    {
        $result = Uint64::multiply(Uint64::rotateLeft(Uint64::multiply($this->s1, 5), 7), 9);
        $t = $this->s1 << 17;
        $this->s2 ^= $this->s0;
        $this->s3 ^= $this->s1;
        $this->s1 ^= $this->s2;
        $this->s0 ^= $this->s3;
        $this->s2 ^= $t;
        $this->s3 = Uint64::rotateLeft($this->s3, 45);
        return $result;
    }

    public function bounded(int $bound): int
    {
        if ($bound < 1) {
            throw new InvalidArgumentException('bound must be between 1 and 2^63 - 1');
        }
        [$high, $low] = Uint64::multiplyFull($this->nextU64(), $bound);
        if (Uint64::lessThan($low, $bound)) {
            $threshold = Uint64::twoPow64Mod($bound);
            while (Uint64::lessThan($low, $threshold)) {
                [$high, $low] = Uint64::multiplyFull($this->nextU64(), $bound);
            }
        }
        return $high;
    }

    public function weightedIndex(array $weights): int
    {
        $total = 0;
        foreach ($weights as $weight) {
            if ($weight < 0) {
                throw new InvalidArgumentException('weights must be non-negative with a positive total');
            }
            $total += $weight;
        }
        if ($total <= 0) {
            throw new InvalidArgumentException('weights must be non-negative with a positive total');
        }
        $draw = $this->bounded($total);
        $cumulative = 0;
        foreach ($weights as $index => $weight) {
            $cumulative += $weight;
            if ($draw < $cumulative) {
                return $index;
            }
        }
        throw new LogicException('unreachable');
    }

    public function weightedSample(array $items, array $weights, int $count): array
    {
        $pool = array_values($items);
        $poolWeights = array_values($weights);
        $chosen = [];
        for ($draw = 0; $draw < $count; $draw++) {
            $index = $this->weightedIndex($poolWeights);
            $chosen[] = $pool[$index];
            array_splice($pool, $index, 1);
            array_splice($poolWeights, $index, 1);
        }
        return $chosen;
    }

    public function shuffle(array $items): array
    {
        $items = array_values($items);
        for ($index = count($items) - 1; $index > 0; $index--) {
            $other = $this->bounded($index + 1);
            [$items[$index], $items[$other]] = [$items[$other], $items[$index]];
        }
        return $items;
    }
}
