// Exact solver: closed forms for unobserved games, full enumeration for weighted priors and observed reveals.
package io.github.juanmafx.montylab;

import java.math.BigInteger;
import java.util.HashMap;
import java.util.Map;

public final class Solver {
    private Solver() {
    }

    public static ExactResult solve(Scenario scenario) {
        Fraction pi = prizeAtPick(scenario);
        if (scenario.observed() != null) {
            return enumerateObserved(scenario, pi);
        }
        return closedForm(scenario, pi);
    }

    static BigInteger binomial(int n, int k) {
        if (k < 0 || k > n) {
            return BigInteger.ZERO;
        }
        BigInteger result = BigInteger.ONE;
        for (int i = 0; i < k; i++) {
            result = result.multiply(BigInteger.valueOf(n - i)).divide(BigInteger.valueOf(i + 1L));
        }
        return result;
    }

    private static void requireEnumerable(Scenario scenario) {
        if (scenario.doors() > Scenario.ENUMERATION_MAX_DOORS) {
            throw new ScenarioException("weighted priors and observed reveals support at most "
                    + Scenario.ENUMERATION_MAX_DOORS + " doors");
        }
    }

    static Map<Integer, Fraction> prizeSetDistribution(int doors, int prizes, long[] weights) {
        Map<Integer, Fraction> layer = new HashMap<>();
        layer.put(0, Fraction.ONE);
        long total = 0;
        for (long weight : weights) {
            total += weight;
        }
        for (int draw = 0; draw < prizes; draw++) {
            Map<Integer, Fraction> following = new HashMap<>();
            for (Map.Entry<Integer, Fraction> entry : layer.entrySet()) {
                int mask = entry.getKey();
                long remaining = total;
                for (int door = 0; door < doors; door++) {
                    if ((mask >> door & 1) != 0) {
                        remaining -= weights[door];
                    }
                }
                for (int door = 0; door < doors; door++) {
                    if ((mask >> door & 1) != 0 || weights[door] == 0) {
                        continue;
                    }
                    Fraction step = entry.getValue().multiply(Fraction.of(weights[door], remaining));
                    following.merge(mask | 1 << door, step, Fraction::add);
                }
            }
            layer = following;
        }
        return layer;
    }

    public static Fraction prizeAtPick(Scenario scenario) {
        long[] prior = scenario.prior();
        if (prior == null) {
            return Fraction.of(scenario.prizes(), scenario.doors());
        }
        requireEnumerable(scenario);
        Fraction sum = Fraction.ZERO;
        for (Map.Entry<Integer, Fraction> entry
                : prizeSetDistribution(scenario.doors(), scenario.prizes(), prior).entrySet()) {
            if ((entry.getKey() >> scenario.pick() & 1) != 0) {
                sum = sum.add(entry.getValue());
            }
        }
        return sum;
    }

    private static Fraction conditional(Fraction numerator, Fraction denominator) {
        return denominator.isZero() ? null : numerator.divide(denominator);
    }

    public static ExactResult closedForm(Scenario scenario, Fraction pi) {
        int n = scenario.doors();
        int m = scenario.prizes();
        int k = scenario.reveals();
        Fraction remaining = Fraction.of(n - 1L - k);
        Fraction prizes = Fraction.of(m);
        Fraction zero = Fraction.ZERO;
        switch (scenario.host()) {
            case INFORMED:
            case BIASED:
                return new ExactResult(pi, Fraction.ONE, zero, zero, null, pi,
                        prizes.subtract(pi).divide(remaining));
            case ADVERSARIAL: {
                boolean offered = !pi.isZero();
                return new ExactResult(pi, pi, zero, Fraction.ONE.subtract(pi), null,
                        offered ? Fraction.ONE : null,
                        offered ? Fraction.of(m - 1L, n - 1L - k) : null);
            }
            default: {
                BigInteger total = binomial(n - 1, k);
                Fraction hit = Fraction.of(binomial(n - m, k), total);
                Fraction miss = Fraction.of(binomial(n - 1 - m, k), total);
                Fraction notPi = Fraction.ONE.subtract(pi);
                Fraction decision = pi.multiply(hit).add(notPi.multiply(miss));
                Fraction stay = conditional(pi.multiply(hit), decision);
                Fraction switchNumerator = pi.multiply(hit).multiply(m - 1L)
                        .add(notPi.multiply(miss).multiply(m))
                        .divide(remaining);
                Fraction switched = conditional(switchNumerator, decision);
                return new ExactResult(pi, decision, Fraction.ONE.subtract(decision), zero, null, stay, switched);
            }
        }
    }

    static Fraction orderedSampleProbability(int[] chosen, long poolWeight, long[] weights) {
        int size = chosen.length;
        Map<Integer, Fraction> layer = new HashMap<>();
        layer.put(0, Fraction.ONE);
        for (int draw = 0; draw < size; draw++) {
            Map<Integer, Fraction> following = new HashMap<>();
            for (Map.Entry<Integer, Fraction> entry : layer.entrySet()) {
                int mask = entry.getKey();
                long used = 0;
                for (int i = 0; i < size; i++) {
                    if ((mask >> i & 1) != 0) {
                        used += weights[chosen[i]];
                    }
                }
                for (int i = 0; i < size; i++) {
                    if ((mask >> i & 1) != 0) {
                        continue;
                    }
                    Fraction step = entry.getValue().multiply(Fraction.of(weights[chosen[i]], poolWeight - used));
                    following.merge(mask | 1 << i, step, Fraction::add);
                }
            }
            layer = following;
        }
        return layer.getOrDefault((1 << size) - 1, Fraction.ONE);
    }

    private static Fraction revealProbability(Scenario scenario, int prizeMask, int[] observed) {
        int n = scenario.doors();
        int pick = scenario.pick();
        int k = scenario.reveals();
        if (scenario.host() == Host.RANDOM) {
            for (int door : observed) {
                if ((prizeMask >> door & 1) != 0) {
                    return Fraction.ZERO;
                }
            }
            return Fraction.of(BigInteger.ONE, binomial(n - 1, k));
        }
        if (scenario.host() == Host.ADVERSARIAL && (prizeMask >> pick & 1) == 0) {
            return Fraction.ZERO;
        }
        int validCount = 0;
        long[] hostWeights = scenario.hostWeights();
        long poolWeight = 0;
        for (int door = 0; door < n; door++) {
            if (door != pick && (prizeMask >> door & 1) == 0) {
                validCount++;
                if (hostWeights != null) {
                    poolWeight += hostWeights[door];
                }
            }
        }
        for (int door : observed) {
            if (door == pick || (prizeMask >> door & 1) != 0) {
                return Fraction.ZERO;
            }
        }
        if (scenario.host() == Host.BIASED && hostWeights != null) {
            return orderedSampleProbability(observed, poolWeight, hostWeights);
        }
        return Fraction.of(BigInteger.ONE, binomial(validCount, k));
    }

    public static ExactResult enumerateObserved(Scenario scenario, Fraction pi) {
        int[] observed = scenario.observed();
        if (observed == null) {
            throw new ScenarioException("enumeration requires an observed reveal");
        }
        requireEnumerable(scenario);
        int n = scenario.doors();
        int pick = scenario.pick();
        int observedMask = 0;
        for (int door : observed) {
            observedMask |= 1 << door;
        }
        int remainingCount = 0;
        for (int door = 0; door < n; door++) {
            if (door != pick && (observedMask >> door & 1) == 0) {
                remainingCount++;
            }
        }
        Fraction joint = Fraction.ZERO;
        Fraction stay = Fraction.ZERO;
        Fraction switched = Fraction.ZERO;
        Map<Integer, Fraction> distribution = prizeSetDistribution(n, scenario.prizes(), scenario.priorWeights());
        for (Map.Entry<Integer, Fraction> entry : distribution.entrySet()) {
            int mask = entry.getKey();
            Fraction weight = entry.getValue().multiply(revealProbability(scenario, mask, observed));
            if (weight.isZero()) {
                continue;
            }
            joint = joint.add(weight);
            if ((mask >> pick & 1) != 0) {
                stay = stay.add(weight);
            }
            int closedPrizes = 0;
            for (int door = 0; door < n; door++) {
                if (door != pick && (observedMask >> door & 1) == 0 && (mask >> door & 1) != 0) {
                    closedPrizes++;
                }
            }
            switched = switched.add(weight.multiply(Fraction.of(closedPrizes, remainingCount)));
        }
        ExactResult unobserved = closedForm(scenario, pi);
        return new ExactResult(pi, unobserved.decision(), unobserved.voided(), unobserved.noOffer(), joint,
                conditional(stay, joint), conditional(switched, joint));
    }
}
