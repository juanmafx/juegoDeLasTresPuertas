// Seeded Monte Carlo simulator whose random stream is fixed by spec/prng.md.
package io.github.juanmafx.montylab;

import java.math.BigInteger;
import java.util.Arrays;
import java.util.List;

public final class Simulator {
    private static final BigInteger MAX_UNSIGNED = BigInteger.ONE.shiftLeft(64).subtract(BigInteger.ONE);

    private Simulator() {
    }

    public record Counts(long trials, long seed, long decision, long voided, long noOffer, Long observed,
            long stayWins, long switchWins, long mixedWins) {

        public long sampleSize() {
            return observed == null ? decision : observed;
        }
    }

    public static Counts simulate(Scenario scenario, long trials, long seed) {
        if (trials < 1 || trials > Scenario.MAX_TRIALS) {
            throw new ScenarioException("trials must be between 1 and " + Scenario.MAX_TRIALS);
        }
        if (seed < 0) {
            throw new ScenarioException("seed must be between 0 and " + Scenario.MAX_SEED);
        }
        Xoshiro256StarStar rng = new Xoshiro256StarStar(seed);
        int n = scenario.doors();
        int[] doors = new int[n];
        for (int door = 0; door < n; door++) {
            doors[door] = door;
        }
        long[] prior = scenario.priorWeights();
        int pick = scenario.pick();
        Host host = scenario.host();
        long[] hostWeights = scenario.hostWeights();
        int[] observedDoors = scenario.observed();
        long observedMask = 0;
        if (observedDoors != null) {
            for (int door : observedDoors) {
                observedMask |= 1L << door;
            }
        }
        BigInteger qNumerator = scenario.mixed().numerator();
        BigInteger qDenominator = scenario.mixed().denominator();
        boolean denominatorFits = qDenominator.compareTo(MAX_UNSIGNED) <= 0;
        long qNum = qNumerator.longValue();
        long qDen = qDenominator.longValue();
        int[] candidates = new int[n];
        long[] candidateWeights = new long[n];
        int[] remaining = new int[n];
        long decision = 0;
        long voided = 0;
        long noOffer = 0;
        long observedCount = 0;
        long stay = 0;
        long switched = 0;
        long mixed = 0;
        for (long trial = 0; trial < trials; trial++) {
            long prizeMask = 0;
            for (int door : rng.weightedSample(doors, prior, scenario.prizes())) {
                prizeMask |= 1L << door;
            }
            boolean pickIsPrize = (prizeMask >>> pick & 1L) != 0;
            if (host == Host.ADVERSARIAL && !pickIsPrize) {
                noOffer++;
                continue;
            }
            int candidateCount = 0;
            for (int door = 0; door < n; door++) {
                if (door == pick || (host != Host.RANDOM && (prizeMask >>> door & 1L) != 0)) {
                    continue;
                }
                candidates[candidateCount] = door;
                candidateWeights[candidateCount] = hostWeights == null ? 1L : hostWeights[door];
                candidateCount++;
            }
            int[] pool = Arrays.copyOf(candidates, candidateCount);
            long[] poolWeights = Arrays.copyOf(candidateWeights, candidateCount);
            List<Integer> opened = rng.weightedSample(pool, poolWeights, scenario.reveals());
            long openedMask = 0;
            for (int door : opened) {
                openedMask |= 1L << door;
            }
            if (host == Host.RANDOM && (openedMask & prizeMask) != 0) {
                voided++;
                continue;
            }
            decision++;
            int remainingCount = 0;
            for (int door = 0; door < n; door++) {
                if (door != pick && (openedMask >>> door & 1L) == 0) {
                    remaining[remainingCount++] = door;
                }
            }
            int target = remaining[(int) rng.bounded(remainingCount)];
            if (!denominatorFits) {
                throw new ScenarioException("mixed denominator must be at most 2^64 - 1");
            }
            boolean switching = Long.compareUnsigned(rng.bounded(qDen), qNum) < 0;
            if (observedDoors != null) {
                if (openedMask != observedMask) {
                    continue;
                }
                observedCount++;
            }
            boolean switchWin = (prizeMask >>> target & 1L) != 0;
            if (pickIsPrize) {
                stay++;
            }
            if (switchWin) {
                switched++;
            }
            if (switching ? switchWin : pickIsPrize) {
                mixed++;
            }
        }
        return new Counts(trials, seed, decision, voided, noOffer, observedDoors == null ? null : observedCount,
                stay, switched, mixed);
    }
}
