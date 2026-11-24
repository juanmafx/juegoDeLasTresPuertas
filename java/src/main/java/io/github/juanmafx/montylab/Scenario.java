// Validated game scenario shared by the exact solver, the simulator and the optimum curve.
package io.github.juanmafx.montylab;

import java.math.BigInteger;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public final class Scenario {
    public static final int MIN_DOORS = 3;
    public static final int MAX_DOORS = 64;
    public static final long MAX_WEIGHT = 1_000_000L;
    public static final int ENUMERATION_MAX_DOORS = 10;
    public static final long MAX_TRIALS = 100_000_000L;
    public static final long MAX_SEED = Long.MAX_VALUE;

    private final int doors;
    private final int prizes;
    private final long[] prior;
    private final int pick;
    private final int reveals;
    private final Host host;
    private final long[] hostWeights;
    private final Fraction mixed;
    private final int[] observed;

    private Scenario(int doors, int prizes, long[] prior, int pick, int reveals, Host host,
            long[] hostWeights, Fraction mixed, int[] observed) {
        this.doors = doors;
        this.prizes = prizes;
        this.prior = prior;
        this.pick = pick;
        this.reveals = reveals;
        this.host = host;
        this.hostWeights = hostWeights;
        this.mixed = mixed;
        this.observed = observed;
    }

    public static Builder builder() {
        return new Builder();
    }

    public int doors() {
        return doors;
    }

    public int prizes() {
        return prizes;
    }

    public long[] prior() {
        return prior == null ? null : prior.clone();
    }

    public int pick() {
        return pick;
    }

    public int reveals() {
        return reveals;
    }

    public Host host() {
        return host;
    }

    public long[] hostWeights() {
        return hostWeights == null ? null : hostWeights.clone();
    }

    public Fraction mixed() {
        return mixed;
    }

    public int[] observed() {
        return observed == null ? null : observed.clone();
    }

    public int maxReveals() {
        return doors - prizes - 1;
    }

    public long[] priorWeights() {
        if (prior != null) {
            return prior.clone();
        }
        long[] uniform = new long[doors];
        Arrays.fill(uniform, 1L);
        return uniform;
    }

    public Scenario withReveals(int newReveals) {
        if (newReveals < 0 || newReveals > maxReveals()) {
            throw new ScenarioException("reveals must be between 0 and doors - prizes - 1");
        }
        return new Scenario(doors, prizes, prior, pick, newReveals, host, hostWeights, mixed, null);
    }

    public Map<String, Object> toJson() {
        Map<String, Object> json = new LinkedHashMap<>();
        json.put("doors", doors);
        json.put("prizes", prizes);
        json.put("prior", prior == null ? "uniform" : longList(prior));
        json.put("pick", pick);
        json.put("reveals", reveals);
        json.put("host", host.label());
        json.put("host_weights", hostWeights == null ? null : longList(hostWeights));
        json.put("mixed", mixed.toString());
        json.put("observed", observed == null ? null : intList(observed));
        return json;
    }

    private static List<Long> longList(long[] values) {
        List<Long> list = new ArrayList<>();
        for (long value : values) {
            list.add(value);
        }
        return list;
    }

    private static List<Integer> intList(int[] values) {
        List<Integer> list = new ArrayList<>();
        for (int value : values) {
            list.add(value);
        }
        return list;
    }

    public static final class Builder {
        private long doors = 3;
        private long prizes = 1;
        private List<BigInteger> prior;
        private long pick;
        private long reveals = 1;
        private Host host = Host.INFORMED;
        private List<BigInteger> hostWeights;
        private Fraction mixed = Fraction.HALF;
        private List<BigInteger> observed;

        private Builder() {
        }

        public Builder doors(long value) {
            doors = value;
            return this;
        }

        public Builder prizes(long value) {
            prizes = value;
            return this;
        }

        public Builder prior(List<BigInteger> value) {
            prior = value;
            return this;
        }

        public Builder prior(long... value) {
            prior = bigList(value);
            return this;
        }

        public Builder pick(long value) {
            pick = value;
            return this;
        }

        public Builder reveals(long value) {
            reveals = value;
            return this;
        }

        public Builder host(Host value) {
            host = value;
            return this;
        }

        public Builder hostWeights(List<BigInteger> value) {
            hostWeights = value;
            return this;
        }

        public Builder hostWeights(long... value) {
            hostWeights = bigList(value);
            return this;
        }

        public Builder mixed(Fraction value) {
            mixed = value;
            return this;
        }

        public Builder observed(List<BigInteger> value) {
            observed = value;
            return this;
        }

        public Builder observed(long... value) {
            observed = bigList(value);
            return this;
        }

        private static List<BigInteger> bigList(long[] values) {
            if (values == null) {
                return null;
            }
            List<BigInteger> list = new ArrayList<>();
            for (long value : values) {
                list.add(BigInteger.valueOf(value));
            }
            return list;
        }

        public Scenario build() {
            if (doors < MIN_DOORS || doors > MAX_DOORS) {
                throw new ScenarioException("doors must be between " + MIN_DOORS + " and " + MAX_DOORS);
            }
            int n = (int) doors;
            if (prizes < 1 || prizes > n - 2) {
                throw new ScenarioException("prizes must be between 1 and doors - 2");
            }
            int m = (int) prizes;
            if (pick < 0 || pick >= n) {
                throw new ScenarioException("pick must be a door index between 0 and doors - 1");
            }
            if (reveals < 0 || reveals > n - m - 1) {
                throw new ScenarioException("reveals must be between 0 and doors - prizes - 1");
            }
            if (host == null) {
                throw new ScenarioException("host must be informed, random, biased or adversarial");
            }
            long[] priorWeights = null;
            if (prior != null) {
                priorWeights = weights("prior", prior, n, 0);
                int positive = 0;
                for (long weight : priorWeights) {
                    if (weight > 0) {
                        positive++;
                    }
                }
                if (positive < m) {
                    throw new ScenarioException("prior must give positive weight to at least prizes doors");
                }
            }
            if ((host == Host.BIASED) != (hostWeights != null)) {
                throw new ScenarioException("host weights are required for, and only for, the biased host");
            }
            long[] hostWeightValues = hostWeights == null ? null : weights("host weights", hostWeights, n, 1);
            if (mixed == null || mixed.signum() < 0 || mixed.compareTo(Fraction.ONE) > 0) {
                throw new ScenarioException("mixed must be a fraction between 0 and 1");
            }
            int[] observedDoors = null;
            if (observed != null) {
                observedDoors = new int[observed.size()];
                boolean valid = observed.size() == reveals;
                boolean[] seen = new boolean[n];
                for (int i = 0; valid && i < observed.size(); i++) {
                    BigInteger door = observed.get(i);
                    if (door.signum() < 0 || door.compareTo(BigInteger.valueOf(n)) >= 0) {
                        valid = false;
                        break;
                    }
                    int index = door.intValueExact();
                    if (seen[index] || index == pick) {
                        valid = false;
                        break;
                    }
                    seen[index] = true;
                    observedDoors[i] = index;
                }
                if (!valid) {
                    throw new ScenarioException("observed must list reveals distinct doors other than the pick");
                }
                Arrays.sort(observedDoors);
            }
            return new Scenario(n, m, priorWeights, (int) pick, (int) reveals, host, hostWeightValues, mixed,
                    observedDoors);
        }

        private static long[] weights(String name, List<BigInteger> values, int doors, long minimum) {
            if (values.size() != doors) {
                throw new ScenarioException(name + " must list exactly one weight per door");
            }
            long[] result = new long[doors];
            for (int i = 0; i < doors; i++) {
                BigInteger weight = values.get(i);
                if (weight.compareTo(BigInteger.valueOf(minimum)) < 0
                        || weight.compareTo(BigInteger.valueOf(MAX_WEIGHT)) > 0) {
                    throw new ScenarioException(name + " entries must be between " + minimum + " and " + MAX_WEIGHT);
                }
                result[i] = weight.longValueExact();
            }
            return result;
        }
    }
}
