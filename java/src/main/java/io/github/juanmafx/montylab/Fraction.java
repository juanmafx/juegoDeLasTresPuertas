// Exact rational number in lowest terms with a positive denominator, backed by BigInteger.
package io.github.juanmafx.montylab;

import java.math.BigInteger;
import java.util.Objects;

public final class Fraction implements Comparable<Fraction> {
    public static final Fraction ZERO = new Fraction(BigInteger.ZERO, BigInteger.ONE);
    public static final Fraction ONE = new Fraction(BigInteger.ONE, BigInteger.ONE);
    public static final Fraction HALF = new Fraction(BigInteger.ONE, BigInteger.TWO);
    private static final BigInteger MAX_PART = BigInteger.valueOf(Long.MAX_VALUE);

    private final BigInteger numerator;
    private final BigInteger denominator;

    private Fraction(BigInteger numerator, BigInteger denominator) {
        this.numerator = numerator;
        this.denominator = denominator;
    }

    public static Fraction of(BigInteger numerator, BigInteger denominator) {
        if (denominator.signum() == 0) {
            throw new ArithmeticException("zero denominator");
        }
        if (denominator.signum() < 0) {
            numerator = numerator.negate();
            denominator = denominator.negate();
        }
        BigInteger divisor = numerator.gcd(denominator);
        if (!divisor.equals(BigInteger.ONE) && divisor.signum() != 0) {
            numerator = numerator.divide(divisor);
            denominator = denominator.divide(divisor);
        }
        if (numerator.signum() == 0) {
            denominator = BigInteger.ONE;
        }
        return new Fraction(numerator, denominator);
    }

    public static Fraction of(long numerator, long denominator) {
        return of(BigInteger.valueOf(numerator), BigInteger.valueOf(denominator));
    }

    public static Fraction of(long value) {
        return new Fraction(BigInteger.valueOf(value), BigInteger.ONE);
    }

    public static Fraction of(BigInteger value) {
        return new Fraction(value, BigInteger.ONE);
    }

    public static Fraction parse(String text) {
        String[] parts = text.split("/", -1);
        if (parts.length > 2) {
            throw new ScenarioException("invalid fraction '" + text + "'");
        }
        try {
            BigInteger numerator = Integers.parse(parts[0]);
            BigInteger denominator = parts.length == 2 ? Integers.parse(parts[1]) : BigInteger.ONE;
            if (denominator.signum() == 0 || numerator.abs().compareTo(MAX_PART) > 0
                    || denominator.abs().compareTo(MAX_PART) > 0) {
                throw new ScenarioException("invalid fraction '" + text + "'");
            }
            return of(numerator, denominator);
        } catch (NumberFormatException error) {
            throw new ScenarioException("invalid fraction '" + text + "'");
        }
    }

    public BigInteger numerator() {
        return numerator;
    }

    public BigInteger denominator() {
        return denominator;
    }

    public Fraction add(Fraction other) {
        return of(numerator.multiply(other.denominator).add(other.numerator.multiply(denominator)),
                denominator.multiply(other.denominator));
    }

    public Fraction subtract(Fraction other) {
        return add(other.negate());
    }

    public Fraction multiply(Fraction other) {
        return of(numerator.multiply(other.numerator), denominator.multiply(other.denominator));
    }

    public Fraction multiply(long factor) {
        return multiply(of(factor));
    }

    public Fraction divide(Fraction other) {
        if (other.numerator.signum() == 0) {
            throw new ArithmeticException("division by zero");
        }
        return of(numerator.multiply(other.denominator), denominator.multiply(other.numerator));
    }

    public Fraction negate() {
        return new Fraction(numerator.negate(), denominator);
    }

    public int signum() {
        return numerator.signum();
    }

    public boolean isZero() {
        return numerator.signum() == 0;
    }

    public BigInteger floor() {
        BigInteger[] parts = numerator.divideAndRemainder(denominator);
        return parts[1].signum() < 0 ? parts[0].subtract(BigInteger.ONE) : parts[0];
    }

    @Override
    public int compareTo(Fraction other) {
        return numerator.multiply(other.denominator).compareTo(other.numerator.multiply(denominator));
    }

    @Override
    public boolean equals(Object other) {
        return other instanceof Fraction fraction
                && numerator.equals(fraction.numerator)
                && denominator.equals(fraction.denominator);
    }

    @Override
    public int hashCode() {
        return Objects.hash(numerator, denominator);
    }

    @Override
    public String toString() {
        return numerator + "/" + denominator;
    }
}
