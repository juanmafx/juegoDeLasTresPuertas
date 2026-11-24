// The generator against every golden vector in spec/prng-vectors.json, plus its edge cases.
package io.github.juanmafx.montylab;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.math.BigInteger;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Map;
import java.util.stream.Stream;
import org.junit.jupiter.api.DynamicTest;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.TestFactory;

class PrngTest {
    private static final BigInteger TWO_64 = BigInteger.ONE.shiftLeft(64);

    @TestFactory
    Stream<DynamicTest> goldenVectors() {
        List<Map<String, Object>> vectors = SpecData.list(SpecData.read("prng-vectors.json"), "vectors");
        assertEquals(105, vectors.size());
        return vectors.stream().map(vector -> DynamicTest.dynamicTest((String) vector.get("id"),
                () -> assertEquals(stringify((List<?>) vector.get("values")), generate(vector))));
    }

    private static List<String> stringify(List<?> values) {
        List<String> result = new ArrayList<>();
        for (Object value : values) {
            result.add(value.toString());
        }
        return result;
    }

    private static List<String> generate(Map<String, Object> vector) {
        long seed = SpecData.number(vector.get("seed"));
        String kind = (String) vector.get("kind");
        int count = (int) SpecData.number(vector.get("count"));
        Xoshiro256StarStar rng = new Xoshiro256StarStar(seed);
        List<String> values = new ArrayList<>();
        switch (kind) {
            case "splitmix" -> {
                SplitMix64 expander = new SplitMix64(seed);
                for (int i = 0; i < count; i++) {
                    values.add(Long.toUnsignedString(expander.next()));
                }
            }
            case "words" -> {
                for (int i = 0; i < count; i++) {
                    values.add(Long.toUnsignedString(rng.nextU64()));
                }
            }
            case "bounded" -> {
                long bound = SpecData.number(vector.get("bound"));
                for (int i = 0; i < count; i++) {
                    values.add(Long.toString(rng.bounded(bound)));
                }
            }
            case "weighted" -> {
                List<BigInteger> parsed = SpecData.bigList(vector.get("weights"));
                long[] weights = parsed.stream().mapToLong(BigInteger::longValueExact).toArray();
                for (int i = 0; i < count; i++) {
                    values.add(Integer.toString(rng.weightedIndex(weights)));
                }
            }
            default -> {
                int[] items = new int[(int) SpecData.number(vector.get("size"))];
                Arrays.setAll(items, i -> i);
                rng.shuffle(items);
                for (int item : items) {
                    values.add(Integer.toString(item));
                }
            }
        }
        return values;
    }

    @Test
    void splitMixFirstOutputForSeedZeroMatchesSpec() {
        assertEquals("16294208416658607535", Long.toUnsignedString(new SplitMix64(0).next()));
    }

    @Test
    void unsignedMultiplyHighMatchesBigIntegerProduct() {
        long[] samples = {0L, 1L, 2L, -1L, Long.MIN_VALUE, Long.MAX_VALUE, 0x9E3779B97F4A7C15L, 12345L};
        for (long x : samples) {
            for (long y : samples) {
                BigInteger product = new BigInteger(Long.toUnsignedString(x)).multiply(new BigInteger(Long.toUnsignedString(y)));
                assertEquals(product.divide(TWO_64).longValue(), Xoshiro256StarStar.unsignedMultiplyHigh(x, y));
            }
        }
    }

    @Test
    void boundedMatchesBigIntegerReferenceForLargeAndUnsignedBounds() {
        long[] bounds = {1L, 3L, 7L, 1L << 40, Long.MAX_VALUE, -1L, Long.MIN_VALUE + 1};
        for (long bound : bounds) {
            Xoshiro256StarStar rng = new Xoshiro256StarStar(99);
            Xoshiro256StarStar words = new Xoshiro256StarStar(99);
            BigInteger n = new BigInteger(Long.toUnsignedString(bound));
            for (int i = 0; i < 200; i++) {
                BigInteger product = new BigInteger(Long.toUnsignedString(words.nextU64())).multiply(n);
                BigInteger low = product.mod(TWO_64);
                if (low.compareTo(n) < 0) {
                    BigInteger threshold = TWO_64.subtract(n).mod(n);
                    while (low.compareTo(threshold) < 0) {
                        product = new BigInteger(Long.toUnsignedString(words.nextU64())).multiply(n);
                        low = product.mod(TWO_64);
                    }
                }
                assertEquals(Long.toUnsignedString(product.shiftRight(64).longValue()),
                        Long.toUnsignedString(rng.bounded(bound)));
            }
        }
    }

    @Test
    void boundedRejectsZero() {
        assertThrows(IllegalArgumentException.class, () -> new Xoshiro256StarStar(1).bounded(0));
    }

    @Test
    void weightedIndexNeverReturnsZeroWeightEntries() {
        Xoshiro256StarStar rng = new Xoshiro256StarStar(7);
        for (int i = 0; i < 1000; i++) {
            int index = rng.weightedIndex(new long[] {0, 3, 0, 1, 0});
            assertTrue(index == 1 || index == 3);
        }
    }

    @Test
    void weightedIndexWithUnitWeightsEqualsBounded() {
        Xoshiro256StarStar weighted = new Xoshiro256StarStar(11);
        Xoshiro256StarStar bounded = new Xoshiro256StarStar(11);
        for (int i = 0; i < 500; i++) {
            assertEquals(bounded.bounded(6), weighted.weightedIndex(new long[] {1, 1, 1, 1, 1, 1}));
        }
    }

    @Test
    void weightedIndexRejectsInvalidWeights() {
        Xoshiro256StarStar rng = new Xoshiro256StarStar(1);
        assertThrows(IllegalArgumentException.class, () -> rng.weightedIndex(new long[] {0, 0}));
        assertThrows(IllegalArgumentException.class, () -> rng.weightedIndex(new long[] {2, -1}));
    }

    @Test
    void weightedSampleDrawsDistinctItemsAndZeroCountConsumesNothing() {
        Xoshiro256StarStar rng = new Xoshiro256StarStar(5);
        Xoshiro256StarStar untouched = new Xoshiro256StarStar(5);
        assertEquals(List.of(), rng.weightedSample(new int[] {4, 5, 6}, new long[] {1, 1, 1}, 0));
        assertEquals(untouched.nextU64(), rng.nextU64());
        List<Integer> sample = rng.weightedSample(new int[] {10, 11, 12, 13}, new long[] {1, 2, 3, 4}, 4);
        int[] sorted = sample.stream().mapToInt(Integer::intValue).sorted().toArray();
        assertArrayEquals(new int[] {10, 11, 12, 13}, sorted);
    }
}
