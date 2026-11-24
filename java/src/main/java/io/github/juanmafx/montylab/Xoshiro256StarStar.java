// xoshiro256** generator with Lemire bounded draws, weighted choice and shuffle from spec/prng.md.
package io.github.juanmafx.montylab;

import java.util.ArrayList;
import java.util.List;

public final class Xoshiro256StarStar {
    private final long[] s = new long[4];

    public Xoshiro256StarStar(long seed) {
        SplitMix64 expander = new SplitMix64(seed);
        for (int i = 0; i < 4; i++) {
            s[i] = expander.next();
        }
    }

    public long nextU64() {
        long result = Long.rotateLeft(s[1] * 5, 7) * 9;
        long t = s[1] << 17;
        s[2] ^= s[0];
        s[3] ^= s[1];
        s[1] ^= s[2];
        s[0] ^= s[3];
        s[2] ^= t;
        s[3] = Long.rotateLeft(s[3], 45);
        return result;
    }

    static long unsignedMultiplyHigh(long x, long y) {
        return Math.multiplyHigh(x, y) + ((x >> 63) & y) + ((y >> 63) & x);
    }

    public long bounded(long bound) {
        if (bound == 0) {
            throw new IllegalArgumentException("bound must be between 1 and 2^64 - 1");
        }
        long x = nextU64();
        long low = x * bound;
        if (Long.compareUnsigned(low, bound) < 0) {
            long threshold = Long.remainderUnsigned(-bound, bound);
            while (Long.compareUnsigned(low, threshold) < 0) {
                x = nextU64();
                low = x * bound;
            }
        }
        return unsignedMultiplyHigh(x, bound);
    }

    public int weightedIndex(long[] weights) {
        return weightedIndex(weights, weights.length);
    }

    private int weightedIndex(long[] weights, int length) {
        long total = 0;
        for (int i = 0; i < length; i++) {
            if (weights[i] < 0) {
                throw new IllegalArgumentException("weights must be non-negative with a positive total");
            }
            total = Math.addExact(total, weights[i]);
        }
        if (total <= 0) {
            throw new IllegalArgumentException("weights must be non-negative with a positive total");
        }
        long draw = bounded(total);
        long cumulative = 0;
        for (int i = 0; i < length; i++) {
            cumulative += weights[i];
            if (draw < cumulative) {
                return i;
            }
        }
        throw new IllegalStateException("unreachable");
    }

    public void shuffle(int[] items) {
        for (int i = items.length - 1; i > 0; i--) {
            int j = (int) bounded(i + 1L);
            int swap = items[i];
            items[i] = items[j];
            items[j] = swap;
        }
    }

    public List<Integer> weightedSample(int[] items, long[] weights, int count) {
        int[] pool = items.clone();
        long[] poolWeights = weights.clone();
        int size = pool.length;
        List<Integer> chosen = new ArrayList<>(count);
        for (int draw = 0; draw < count; draw++) {
            int index = weightedIndex(poolWeights, size);
            chosen.add(pool[index]);
            System.arraycopy(pool, index + 1, pool, index, size - index - 1);
            System.arraycopy(poolWeights, index + 1, poolWeights, index, size - index - 1);
            size--;
        }
        return chosen;
    }
}
