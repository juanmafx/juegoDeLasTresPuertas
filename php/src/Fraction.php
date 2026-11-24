<?php

// Exact rational number in lowest terms on arbitrary-precision integers.

declare(strict_types=1);

namespace MontyHall\Lab;

use Brick\Math\BigInteger;
use Brick\Math\Exception\MathException;

final readonly class Fraction
{
    public BigInteger $numerator;
    public BigInteger $denominator;

    private function __construct(BigInteger $numerator, BigInteger $denominator)
    {
        $this->numerator = $numerator;
        $this->denominator = $denominator;
    }

    public static function of(BigInteger|int $numerator, BigInteger|int $denominator = 1): self
    {
        $numerator = BigInteger::of($numerator);
        $denominator = BigInteger::of($denominator);
        if ($denominator->isZero()) {
            throw new ScenarioError('fraction denominator must not be zero');
        }
        if ($denominator->isNegative()) {
            $numerator = $numerator->negated();
            $denominator = $denominator->negated();
        }
        $divisor = $numerator->gcd($denominator);
        if (!$divisor->isEqualTo(1)) {
            $numerator = $numerator->quotient($divisor);
            $denominator = $denominator->quotient($divisor);
        }
        return new self($numerator, $denominator);
    }

    public static function zero(): self
    {
        return new self(BigInteger::zero(), BigInteger::one());
    }

    public static function one(): self
    {
        return new self(BigInteger::one(), BigInteger::one());
    }

    public static function parse(string $text): self
    {
        $parts = explode('/', trim($text));
        if (count($parts) > 2) {
            throw new ScenarioError(sprintf('invalid fraction %s', json_encode($text)));
        }
        try {
            $numerator = self::integer($parts[0]);
            $denominator = count($parts) === 2 ? self::integer($parts[1]) : BigInteger::one();
        } catch (MathException) {
            throw new ScenarioError(sprintf('invalid fraction %s', json_encode($text)));
        }
        if ($denominator->isZero()) {
            throw new ScenarioError(sprintf('invalid fraction %s', json_encode($text)));
        }
        return self::of($numerator, $denominator);
    }

    public function plus(self $other): self
    {
        if ($this->denominator->isEqualTo($other->denominator)) {
            return self::of($this->numerator->plus($other->numerator), $this->denominator);
        }
        return self::of(
            $this->numerator->multipliedBy($other->denominator)->plus($other->numerator->multipliedBy($this->denominator)),
            $this->denominator->multipliedBy($other->denominator),
        );
    }

    public function minus(self $other): self
    {
        return $this->plus($other->negated());
    }

    public function times(self $other): self
    {
        return self::of(
            $this->numerator->multipliedBy($other->numerator),
            $this->denominator->multipliedBy($other->denominator),
        );
    }

    public function dividedBy(self $other): self
    {
        if ($other->isZero()) {
            throw new ScenarioError('division by zero');
        }
        return self::of(
            $this->numerator->multipliedBy($other->denominator),
            $this->denominator->multipliedBy($other->numerator),
        );
    }

    public function negated(): self
    {
        return new self($this->numerator->negated(), $this->denominator);
    }

    public function compareTo(self $other): int
    {
        return $this->numerator->multipliedBy($other->denominator)
            ->compareTo($other->numerator->multipliedBy($this->denominator));
    }

    public function isZero(): bool
    {
        return $this->numerator->isZero();
    }

    public function sign(): int
    {
        return $this->numerator->getSign();
    }

    public function floor(): BigInteger
    {
        $quotient = $this->numerator->quotient($this->denominator);
        if ($this->numerator->isNegative() && !$quotient->multipliedBy($this->denominator)->isEqualTo($this->numerator)) {
            return $quotient->minus(1);
        }
        return $quotient;
    }

    public function equals(self $other): bool
    {
        return $this->numerator->isEqualTo($other->numerator) && $this->denominator->isEqualTo($other->denominator);
    }

    public function toString(): string
    {
        return $this->numerator->toString() . '/' . $this->denominator->toString();
    }

    private static function integer(string $text): BigInteger
    {
        $text = trim($text);
        if (preg_match('/^[+-]?[0-9]+$/', $text) !== 1) {
            throw new ScenarioError(sprintf('invalid integer %s', json_encode($text)));
        }
        return BigInteger::of(ltrim($text, '+'));
    }
}
