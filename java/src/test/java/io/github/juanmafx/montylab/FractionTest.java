// Exact rational arithmetic, parsing and formatting.
package io.github.juanmafx.montylab;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.math.BigInteger;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;
import org.junit.jupiter.params.provider.ValueSource;

class FractionTest {
    @ParameterizedTest
    @CsvSource({"1/2,1/2", "2/4,1/2", "0,0/1", "0/7,0/1", "-3/20,-3/20", "3/-20,-3/20", "-6/-4,3/2",
        "5,5/1", "' 7/14 ',1/2", "+3/9,1/3", "-0/5,0/1", "' 1 / 2 ',1/2",
        "9223372036854775807/9223372036854775807,1/1", "-9223372036854775807,-9223372036854775807/1"})
    void parsesAndReducesToLowestTerms(String input, String expected) {
        assertEquals(expected, Fraction.parse(input).toString());
    }

    @ParameterizedTest
    @ValueSource(strings = {"1/0", "", "a/2", "1/b", "1.5", "1//2", "/2", "1/", "1/2/3", "1_0/2", "\uff11/2",
        "1/\u00a02", "1/9223372036854775808", "-9223372036854775808", "9223372036854775808/2"})
    void rejectsMalformedFractions(String input) {
        assertThrows(ScenarioException.class, () -> Fraction.parse(input));
    }

    @Test
    void arithmeticIsExact() {
        Fraction third = Fraction.of(1, 3);
        Fraction sixth = Fraction.of(1, 6);
        assertEquals(Fraction.HALF, third.add(sixth));
        assertEquals(Fraction.of(1, 6), third.subtract(sixth));
        assertEquals(Fraction.of(1, 18), third.multiply(sixth));
        assertEquals(Fraction.of(2), third.divide(sixth));
        assertEquals(Fraction.of(-1, 3), third.negate());
        assertThrows(ArithmeticException.class, () -> third.divide(Fraction.ZERO));
    }

    @Test
    void floorRoundsTowardNegativeInfinity() {
        assertEquals(BigInteger.ONE, Fraction.of(3, 2).floor());
        assertEquals(BigInteger.valueOf(-2), Fraction.of(-3, 2).floor());
        assertEquals(BigInteger.valueOf(-1), Fraction.of(-1).floor());
        assertEquals(BigInteger.ZERO, Fraction.ZERO.floor());
    }

    @Test
    void comparisonAndEqualityFollowValue() {
        assertTrue(Fraction.of(1, 3).compareTo(Fraction.of(1, 2)) < 0);
        assertEquals(Fraction.of(2, 4), Fraction.of(1, 2));
        assertEquals(Fraction.of(2, 4).hashCode(), Fraction.of(1, 2).hashCode());
    }

    @Test
    void handlesNumbersBeyondSixtyFourBits() {
        Fraction big = Fraction.of(new BigInteger("123456789012345678901234567890"), BigInteger.TWO);
        assertEquals("61728394506172839450617283945/1", big.toString());
    }
}
