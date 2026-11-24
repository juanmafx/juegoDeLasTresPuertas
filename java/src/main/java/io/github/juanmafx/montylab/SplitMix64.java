// SplitMix64 seed expander from spec/prng.md; the seed is an unsigned 64-bit value.
package io.github.juanmafx.montylab;

public final class SplitMix64 {
    private static final long GOLDEN_GAMMA = 0x9E3779B97F4A7C15L;

    private long state;

    public SplitMix64(long seed) {
        state = seed;
    }

    public long next() {
        state += GOLDEN_GAMMA;
        long z = state;
        z = (z ^ (z >>> 30)) * 0xBF58476D1CE4E5B9L;
        z = (z ^ (z >>> 27)) * 0x94D049BB133111EBL;
        return z ^ (z >>> 31);
    }
}
