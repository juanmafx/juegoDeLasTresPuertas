<?php

// Exact rational number in lowest terms on arbitrary-precision integers.

declare(strict_types=1);

namespace MontyHall\Lab;

use Brick\Math\BigInteger;

final readonly class Fraction
{
    public const string ASCII_SPACE = " \t\n\x0B\f\r";

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
        $parts = explode('/', $text);
        if (count($parts) > 2) {
            throw new ScenarioError(sprintf('invalid fraction %s', json_encode($text)));
        }
        $numerator = self::integer($parts[0]);
        $denominator = count($parts) === 2 ? self::integer($parts[1]) : BigInteger::one();
        if ($denominator->isZero() || $numerator->abs()->isGreaterThan(PHP_INT_MAX)
            || $denominator->abs()->isGreaterThan(PHP_INT_MAX)) {
            throw new ScenarioError(sprintf('invalid fraction %s', json_encode($text)));
        }
        return self::of($numerator, $denominator);
    }

    public function plus(self $other): self
    {
        if ($this->numerator->isZero()) {
            return $other;
        }
        if ($other->numerator->isZero()) {
            return $this;
        }
        $divisor = $this->denominator->gcd($other->denominator);
        if ($divisor->isEqualTo(1)) {
            return new self(
                $this->numerator->multipliedBy($other->denominator)->plus($other->numerator->multipliedBy($this->denominator)),
                $this->denominator->multipliedBy($other->denominator),
            );
        }
        $otherScale = self::exactQuotient($other->denominator, $divisor);
        $thisScale = self::exactQuotient($this->denominator, $divisor);
        $sum = $this->numerator->multipliedBy($otherScale)->plus($other->numerator->multipliedBy($thisScale));
        if ($sum->isZero()) {
            return self::zero();
        }
        $common = $sum->gcd($divisor);
        return new self(
            self::exactQuotient($sum, $common),
            $thisScale->multipliedBy(self::exactQuotient($other->denominator, $common)),
        );
    }

    public function minus(self $other): self
    {
        return $this->plus($other->negated());
    }

    public function times(self $other): self
    {
        if ($this->numerator->isZero() || $other->numerator->isZero()) {
            return self::zero();
        }
        $first = $this->numerator->gcd($other->denominator);
        $second = $other->numerator->gcd($this->denominator);
        return new self(
            self::exactQuotient($this->numerator, $first)->multipliedBy(self::exactQuotient($other->numerator, $second)),
            self::exactQuotient($this->denominator, $second)->multipliedBy(self::exactQuotient($other->denominator, $first)),
        );
    }

    public function dividedBy(self $other): self
    {
        if ($other->isZero()) {
            throw new ScenarioError('division by zero');
        }
        $inverse = $other->numerator->isNegative()
            ? new self($other->denominator->negated(), $other->numerator->negated())
            : new self($other->denominator, $other->numerator);
        return $this->times($inverse);
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

    private static function exactQuotient(BigInteger $value, BigInteger $divisor): BigInteger
    {
        return $divisor->isEqualTo(1) ? $value : $value->quotient($divisor);
    }

    public static function integer(string $text): BigInteger
    {
        $trimmed = trim($text, self::ASCII_SPACE);
        if (preg_match('/^[+-]?[0-9]+$/D', $trimmed) !== 1) {
            throw new ScenarioError(sprintf('invalid integer %s', json_encode($text)));
        }
        $digits = ltrim(ltrim($trimmed, '+-'), '0');
        if (strlen($digits) > 40) {
            throw new ScenarioError(sprintf('integer out of range %s', json_encode($text)));
        }
        $value = BigInteger::of($digits === '' ? '0' : $digits);
        return str_starts_with($trimmed, '-') ? $value->negated() : $value;
    }
}
