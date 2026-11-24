// monty-lab command-line contract from spec/cli.md: exact, simulate, optimum and prng.
package io.github.juanmafx.montylab;

import java.io.PrintStream;
import java.math.BigInteger;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.regex.Pattern;

public final class Cli {
    public static final int EXIT_OK = 0;
    public static final int EXIT_USAGE = 2;
    public static final int EXIT_BROKEN_PIPE = 141;
    static final long MAX_PRNG_COUNT = 100_000L;
    static final long MAX_SHUFFLE_SIZE = 10_000L;

    private static final Pattern NEGATIVE_NUMBER = Pattern.compile("^-\\d+$|^-\\d*\\.\\d+$");
    private static final List<String> SCENARIO_FLAGS =
            List.of("doors", "prizes", "prior", "pick", "host", "host-weights", "mixed");
    private static final Map<String, List<String>> COMMAND_FLAGS = new LinkedHashMap<>();

    static {
        COMMAND_FLAGS.put("exact", concat(SCENARIO_FLAGS, List.of("reveals", "observed")));
        COMMAND_FLAGS.put("simulate", concat(SCENARIO_FLAGS, List.of("reveals", "observed", "trials", "seed")));
        COMMAND_FLAGS.put("optimum", concat(SCENARIO_FLAGS, List.of("strategy", "cost")));
        COMMAND_FLAGS.put("prng", List.of("seed", "kind", "count", "bound", "weights", "size"));
    }

    private Cli() {
    }

    private static List<String> concat(List<String> first, List<String> second) {
        List<String> all = new ArrayList<>(first);
        all.addAll(second);
        return List.copyOf(all);
    }

    public static void main(String[] args) {
        PrintStream out = new PrintStream(new java.io.FileOutputStream(java.io.FileDescriptor.out), false,
                StandardCharsets.UTF_8);
        PrintStream err = new PrintStream(new java.io.FileOutputStream(java.io.FileDescriptor.err), true,
                StandardCharsets.UTF_8);
        System.exit(run(args, out, err));
    }

    public static int run(String[] args, PrintStream out, PrintStream err) {
        if (args.length > 0 && (args[0].equals("-h") || args[0].equals("--help"))) {
            out.print(usage());
            out.flush();
            return out.checkError() ? EXIT_BROKEN_PIPE : EXIT_OK;
        }
        if (args.length > 0 && args[0].equals("--version")) {
            out.println("monty-lab " + version());
            out.flush();
            return out.checkError() ? EXIT_BROKEN_PIPE : EXIT_OK;
        }
        Object report;
        try {
            if (args.length == 0) {
                throw new ScenarioException("the following arguments are required: command");
            }
            String command = args[0];
            List<String> allowed = COMMAND_FLAGS.get(command);
            if (allowed == null) {
                throw new ScenarioException("argument command: invalid choice '" + command
                        + "' (choose from exact, simulate, optimum, prng)");
            }
            Map<String, String> flags = parseFlags(command, allowed, args);
            if (flags == null) {
                out.print(usage());
                out.flush();
                return out.checkError() ? EXIT_BROKEN_PIPE : EXIT_OK;
            }
            report = execute(command, flags);
        } catch (IllegalArgumentException | ArithmeticException error) {
            err.println("error: " + error.getMessage());
            return EXIT_USAGE;
        }
        out.println(Json.write(report));
        out.flush();
        return out.checkError() ? EXIT_BROKEN_PIPE : EXIT_OK;
    }

    static String version() {
        String version = Cli.class.getPackage().getImplementationVersion();
        return version == null ? "dev" : version;
    }

    static String usage() {
        return String.join("\n",
                "usage: monty-lab [-h] [--version] {exact,simulate,optimum,prng} ...",
                "",
                "Generalized Monty Hall decision lab (cross-language contract).",
                "",
                "  exact     [scenario flags] [--reveals K] [--observed D,...]",
                "  simulate  [scenario flags] [--reveals K] [--observed D,...] --seed S [--trials T]",
                "  optimum   [scenario flags] --strategy stay|switch|mixed [--cost C]",
                "  prng      --seed S --kind splitmix|words|bounded|weighted|shuffle",
                "            [--count C] [--bound B] [--weights W] [--size Z]",
                "",
                "scenario flags: --doors N --prizes M --prior uniform|W,... --pick D",
                "                --host informed|random|biased|adversarial --host-weights W,... --mixed Q",
                "");
    }

    private static Map<String, String> parseFlags(String command, List<String> allowed, String[] args) {
        Map<String, String> flags = new HashMap<>();
        for (int i = 1; i < args.length; i++) {
            String token = args[i];
            if (token.equals("-h") || token.equals("--help")) {
                return null;
            }
            if (!token.startsWith("--") || token.length() == 2) {
                throw new ScenarioException("unrecognized arguments: " + token);
            }
            String name = token.substring(2);
            String value = null;
            int equals = name.indexOf('=');
            if (equals >= 0) {
                value = name.substring(equals + 1);
                name = name.substring(0, equals);
            }
            name = resolve(command, allowed, name, token);
            if (value == null) {
                if (i + 1 >= args.length || (args[i + 1].startsWith("-")
                        && !NEGATIVE_NUMBER.matcher(args[i + 1]).matches())) {
                    throw new ScenarioException("argument --" + name + ": expected one argument");
                }
                value = args[++i];
            }
            flags.put(name, value);
        }
        return flags;
    }

    private static String resolve(String command, List<String> allowed, String name, String token) {
        if (allowed.contains(name)) {
            return name;
        }
        List<String> matches = new ArrayList<>();
        for (String candidate : allowed) {
            if (candidate.startsWith(name)) {
                matches.add(candidate);
            }
        }
        if (matches.size() == 1 && !name.isEmpty()) {
            return matches.get(0);
        }
        if (matches.size() > 1) {
            throw new ScenarioException("ambiguous option: " + token + " could match --"
                    + String.join(", --", matches));
        }
        throw new ScenarioException("unrecognized arguments for " + command + ": " + token);
    }

    private static String required(Map<String, String> flags, String name) {
        String value = flags.get(name);
        if (value == null) {
            throw new ScenarioException("the following arguments are required: --" + name);
        }
        return value;
    }

    private static Object execute(String command, Map<String, String> flags) {
        switch (command) {
            case "prng":
                return prngReport(flags);
            case "exact":
                return exactReport(scenario(flags, true));
            case "simulate": {
                String seedText = required(flags, "seed");
                long trials = Integers.parseLong("trials", flags.getOrDefault("trials", "100000"));
                long seed = Integers.parseLong("seed", seedText);
                return simulateReport(scenario(flags, true), trials, seed);
            }
            default: {
                Strategy strategy = Strategy.parse(required(flags, "strategy"));
                Scenario scenario = scenario(flags, false);
                return optimumReport(scenario, strategy, Fraction.parse(flags.getOrDefault("cost", "0")));
            }
        }
    }

    static Scenario scenario(Map<String, String> flags, boolean withReveals) {
        Scenario.Builder builder = Scenario.builder()
                .doors(Integers.parseLong("doors", flags.getOrDefault("doors", "3")))
                .prizes(Integers.parseLong("prizes", flags.getOrDefault("prizes", "1")))
                .pick(Integers.parseLong("pick", flags.getOrDefault("pick", "0")))
                .host(Host.parse(flags.getOrDefault("host", "informed")));
        String prior = flags.getOrDefault("prior", "uniform");
        if (!prior.equals("uniform")) {
            builder.prior(Integers.parseList(prior));
        }
        if (flags.containsKey("host-weights")) {
            builder.hostWeights(Integers.parseList(flags.get("host-weights")));
        }
        builder.mixed(Fraction.parse(flags.getOrDefault("mixed", "1/2")));
        if (withReveals) {
            builder.reveals(Integers.parseLong("reveals", flags.getOrDefault("reveals", "1")));
            if (flags.containsKey("observed")) {
                builder.observed(Integers.parseList(flags.get("observed")));
            }
        } else {
            builder.reveals(0);
        }
        return builder.build();
    }

    private static String fraction(Fraction value) {
        return value == null ? null : value.toString();
    }

    static Map<String, Object> exactReport(Scenario scenario) {
        ExactResult result = Solver.solve(scenario);
        Map<String, Object> outcomes = new LinkedHashMap<>();
        outcomes.put("decision", fraction(result.decision()));
        outcomes.put("void", fraction(result.voided()));
        outcomes.put("no_offer", fraction(result.noOffer()));
        outcomes.put("observed", fraction(result.observed()));
        Map<String, Object> win = new LinkedHashMap<>();
        win.put("stay", fraction(result.stay()));
        win.put("switch", fraction(result.switched()));
        win.put("mixed", fraction(result.mixed(scenario.mixed())));
        Map<String, Object> report = new LinkedHashMap<>();
        report.put("command", "exact");
        report.put("scenario", scenario.toJson());
        report.put("prize_at_pick", fraction(result.prizeAtPick()));
        report.put("outcomes", outcomes);
        report.put("win", win);
        return report;
    }

    private static Map<String, Object> strategySummary(long wins, long sample) {
        Map<String, Object> summary = new LinkedHashMap<>();
        summary.put("wins", wins);
        if (sample == 0) {
            summary.put("rate", null);
            summary.put("wilson95", null);
            return summary;
        }
        double[] interval = Wilson.interval(wins, sample);
        summary.put("rate", (double) wins / (double) sample);
        summary.put("wilson95", List.of(interval[0], interval[1]));
        return summary;
    }

    static Map<String, Object> simulateReport(Scenario scenario, long trials, long seed) {
        Simulator.Counts counts = Simulator.simulate(scenario, trials, seed);
        long sample = counts.sampleSize();
        Map<String, Object> countsJson = new LinkedHashMap<>();
        countsJson.put("decision", counts.decision());
        countsJson.put("void", counts.voided());
        countsJson.put("no_offer", counts.noOffer());
        countsJson.put("observed", counts.observed());
        Map<String, Object> strategies = new LinkedHashMap<>();
        strategies.put("stay", strategySummary(counts.stayWins(), sample));
        strategies.put("switch", strategySummary(counts.switchWins(), sample));
        strategies.put("mixed", strategySummary(counts.mixedWins(), sample));
        Map<String, Object> report = new LinkedHashMap<>();
        report.put("command", "simulate");
        report.put("scenario", scenario.toJson());
        report.put("seed", seed);
        report.put("trials", trials);
        report.put("counts", countsJson);
        report.put("sample_size", sample);
        report.put("strategies", strategies);
        return report;
    }

    private static Map<String, Object> choice(Optimum.Result result, int reveals) {
        Fraction value = result.curve().get(reveals).value();
        Map<String, Object> json = new LinkedHashMap<>();
        json.put("reveals", reveals);
        json.put("value", value.toString());
        json.put("regret", result.best().value().subtract(value).toString());
        return json;
    }

    static Map<String, Object> optimumReport(Scenario scenario, Strategy strategy, Fraction cost) {
        Optimum.Result result = Optimum.curve(scenario, strategy, cost);
        Map<String, Object> echoed = scenario.toJson();
        echoed.put("reveals", null);
        Map<String, Object> parabola = null;
        Optimum.Parabola fit = result.parabola();
        if (fit != null) {
            parabola = new LinkedHashMap<>();
            parabola.put("a", fit.a().toString());
            parabola.put("b", fit.b().toString());
            parabola.put("c", fit.c().toString());
            parabola.put("shape", fit.shape());
            parabola.put("residual_sum_of_squares", fit.residualSumOfSquares().toString());
            parabola.put("vertex", null);
            parabola.put("vertex_offset", null);
            parabola.put("vertex_value_gap", null);
            parabola.put("rounded_vertex", null);
            parabola.put("fitted_choice", choice(result, fit.fittedChoice()));
            if (fit.vertexReveals() != null && fit.vertexValue() != null) {
                Map<String, Object> vertex = new LinkedHashMap<>();
                vertex.put("reveals", fit.vertexReveals().toString());
                vertex.put("value", fit.vertexValue().toString());
                parabola.put("vertex", vertex);
                parabola.put("vertex_offset",
                        fit.vertexReveals().subtract(Fraction.of(result.best().reveals())).toString());
                parabola.put("vertex_value_gap", fit.vertexValue().subtract(result.best().value()).toString());
            }
            if (fit.roundedVertex() != null) {
                parabola.put("rounded_vertex", choice(result, fit.roundedVertex()));
            }
        }
        List<Object> curve = new ArrayList<>();
        for (Optimum.CurvePoint point : result.curve()) {
            Map<String, Object> json = new LinkedHashMap<>();
            json.put("reveals", point.reveals());
            json.put("win", point.win().toString());
            json.put("value", point.value().toString());
            curve.add(json);
        }
        Map<String, Object> best = new LinkedHashMap<>();
        best.put("reveals", result.best().reveals());
        best.put("value", result.best().value().toString());
        Map<String, Object> report = new LinkedHashMap<>();
        report.put("command", "optimum");
        report.put("scenario", echoed);
        report.put("strategy", strategy.label());
        report.put("cost", cost.toString());
        report.put("curve", curve);
        report.put("optimum", best);
        report.put("parabola", parabola);
        return report;
    }

    static Map<String, Object> prngReport(Map<String, String> flags) {
        long seed = Integers.parseLong("seed", required(flags, "seed"));
        String kind = required(flags, "kind");
        if (!List.of("splitmix", "words", "bounded", "weighted", "shuffle").contains(kind)) {
            throw new ScenarioException("argument --kind: invalid choice '" + kind
                    + "' (choose from splitmix, words, bounded, weighted, shuffle)");
        }
        long count = Integers.parseLong("count", flags.getOrDefault("count", "1"));
        if (seed < 0) {
            throw new ScenarioException("seed must be between 0 and " + Scenario.MAX_SEED);
        }
        if (count < 1 || count > MAX_PRNG_COUNT) {
            throw new ScenarioException("count must be between 1 and " + MAX_PRNG_COUNT);
        }
        Xoshiro256StarStar rng = new Xoshiro256StarStar(seed);
        Map<String, Object> report = new LinkedHashMap<>();
        report.put("command", "prng");
        report.put("seed", seed);
        report.put("kind", kind);
        List<Object> values = new ArrayList<>();
        switch (kind) {
            case "splitmix": {
                SplitMix64 expander = new SplitMix64(seed);
                for (long i = 0; i < count; i++) {
                    values.add(Long.toUnsignedString(expander.next()));
                }
                break;
            }
            case "words":
                for (long i = 0; i < count; i++) {
                    values.add(Long.toUnsignedString(rng.nextU64()));
                }
                break;
            case "bounded": {
                long bound = flags.containsKey("bound") ? Integers.parseLong("bound", flags.get("bound")) : 0;
                if (bound < 1) {
                    throw new ScenarioException("bound must be between 1 and " + Scenario.MAX_SEED);
                }
                report.put("bound", bound);
                for (long i = 0; i < count; i++) {
                    values.add(rng.bounded(bound));
                }
                break;
            }
            case "weighted": {
                List<BigInteger> parsed = Integers.parseList(flags.getOrDefault("weights", ""));
                BigInteger total = BigInteger.ZERO;
                boolean negative = false;
                for (BigInteger weight : parsed) {
                    negative |= weight.signum() < 0;
                    total = total.add(weight);
                }
                if (parsed.isEmpty() || negative || total.signum() <= 0) {
                    throw new ScenarioException("weights must be non-negative integers with a positive total");
                }
                if (total.compareTo(BigInteger.valueOf(Scenario.MAX_SEED)) > 0) {
                    throw new ScenarioException("weights must sum to at most " + Scenario.MAX_SEED);
                }
                long[] weights = new long[parsed.size()];
                List<Object> echoed = new ArrayList<>();
                for (int i = 0; i < weights.length; i++) {
                    weights[i] = parsed.get(i).longValueExact();
                    echoed.add(weights[i]);
                }
                report.put("weights", echoed);
                for (long i = 0; i < count; i++) {
                    values.add(rng.weightedIndex(weights));
                }
                break;
            }
            default: {
                long size = flags.containsKey("size") ? Integers.parseLong("size", flags.get("size")) : 0;
                if (size < 1 || size > MAX_SHUFFLE_SIZE) {
                    throw new ScenarioException("size must be between 1 and " + MAX_SHUFFLE_SIZE);
                }
                report.put("size", size);
                int[] items = new int[(int) size];
                for (int i = 0; i < items.length; i++) {
                    items[i] = i;
                }
                rng.shuffle(items);
                for (int item : items) {
                    values.add(item);
                }
            }
        }
        report.put("values", values);
        return report;
    }
}
