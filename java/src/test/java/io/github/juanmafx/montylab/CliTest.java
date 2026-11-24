// Command-line contract: flags, validation, exit codes and JSON output shape.
package io.github.juanmafx.montylab;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.ByteArrayOutputStream;
import java.io.OutputStream;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Map;
import java.util.stream.Stream;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.Arguments;
import org.junit.jupiter.params.provider.MethodSource;

class CliTest {
    private record Outcome(int code, String stdout, String stderr) {
        Map<String, Object> json() {
            return SpecData.map(SpecData.parse(stdout));
        }
    }

    private static Outcome invoke(String... args) {
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        ByteArrayOutputStream err = new ByteArrayOutputStream();
        int code = Cli.run(args, new PrintStream(out, true, StandardCharsets.UTF_8),
                new PrintStream(err, true, StandardCharsets.UTF_8));
        return new Outcome(code, out.toString(StandardCharsets.UTF_8), err.toString(StandardCharsets.UTF_8));
    }

    static Stream<Arguments> invalidInvocations() {
        return Stream.of(
                List.of("exact", "--doors", "2"),
                List.of("exact", "--doors", "65"),
                List.of("exact", "--doors", "5", "--prizes", "4"),
                List.of("exact", "--doors", "5", "--prizes", "2", "--reveals", "3"),
                List.of("exact", "--pick", "3"),
                List.of("exact", "--observed", "0"),
                List.of("exact", "--observed", "1,2"),
                List.of("exact", "--host", "biased"),
                List.of("exact", "--host-weights", "1,1,1"),
                List.of("exact", "--host", "biased", "--host-weights", "1,0,1"),
                List.of("exact", "--prior", "1,1"),
                List.of("exact", "--doors", "4", "--prizes", "2", "--prior", "0,0,0,1"),
                List.of("exact", "--mixed", "3/2"),
                List.of("exact", "--mixed", "1/0"),
                List.of("exact", "--doors", "11", "--prior", "1,1,1,1,1,1,1,1,1,1,1"),
                List.of("exact", "--doors", "11", "--observed", "1"),
                List.of("exact", "--doors", "x"),
                List.of("exact", "--doors"),
                List.of("exact", "--host", "sneaky"),
                List.of("exact", "--prior", "1,,1"),
                List.of("exact", "--prior", "1,1,1000001"),
                List.of("exact", "--seed", "1"),
                List.of("exact", "stray"),
                List.of("simulate"),
                List.of("simulate", "--seed", "-1"),
                List.of("simulate", "--seed", "9223372036854775808"),
                List.of("simulate", "--seed", "1", "--trials", "0"),
                List.of("simulate", "--seed", "1", "--trials", "100000001"),
                List.of("simulate", "--seed", "1", "--mixed", "1/18446744073709551616"),
                List.of("optimum"),
                List.of("optimum", "--strategy", "switch", "--cost", "-1/2"),
                List.of("optimum", "--strategy", "switch", "--reveals", "1"),
                List.of("optimum", "--strategy", "stay", "--doors", "4", "--prior", "0,1,1,1", "--host", "adversarial"),
                List.of("prng", "--seed", "1", "--kind", "bounded", "--bound", "0"),
                List.of("prng", "--seed", "1", "--kind", "bounded"),
                List.of("prng", "--seed", "1", "--kind", "words", "--count", "0"),
                List.of("prng", "--seed", "1", "--kind", "weighted", "--weights", "0,0"),
                List.of("prng", "--seed", "1", "--kind", "weighted", "--weights", "9223372036854775807,1"),
                List.of("prng", "--seed", "1", "--kind", "shuffle", "--size", "10001"),
                List.of("prng", "--seed", "1", "--kind", "dice"),
                List.of("teleport"),
                List.of()).map(arguments -> Arguments.of(arguments));
    }

    @ParameterizedTest
    @MethodSource("invalidInvocations")
    void invalidInputExitsTwoWithAnErrorAndNoOutput(List<String> arguments) {
        Outcome outcome = invoke(arguments.toArray(String[]::new));
        assertEquals(Cli.EXIT_USAGE, outcome.code(), outcome.stderr());
        assertEquals("", outcome.stdout());
        assertTrue(outcome.stderr().startsWith("error: "), outcome.stderr());
    }

    @Test
    void exactDefaultsMatchTheContractExample() {
        Map<String, Object> json = invoke("exact").json();
        assertEquals("exact", json.get("command"));
        assertEquals("1/3", json.get("prize_at_pick"));
        assertEquals(Map.of("stay", "1/3", "switch", "2/3", "mixed", "1/2"), json.get("win"));
        Map<String, Object> scenario = SpecData.map(json.get("scenario"));
        assertEquals("uniform", scenario.get("prior"));
        assertNull(scenario.get("host_weights"));
        assertNull(scenario.get("observed"));
    }

    @Test
    void scenarioEchoIsNormalized() {
        Map<String, Object> json = invoke("exact", "--doors", "6", "--reveals", "2", "--observed", "5,2",
                "--mixed", "4/8", "--pick", "1").json();
        Map<String, Object> scenario = SpecData.map(json.get("scenario"));
        assertEquals("1/2", scenario.get("mixed"));
        assertEquals(List.of(2, 5), SpecData.bigList(scenario.get("observed")).stream().map(Number::intValue).toList());
    }

    @Test
    void equalsSyntaxAndUniquePrefixesAreAccepted() {
        Outcome outcome = invoke("exact", "--doors=4", "--rev", "2");
        assertEquals(0, outcome.code(), outcome.stderr());
        Map<String, Object> scenario = SpecData.map(outcome.json().get("scenario"));
        assertEquals(4, SpecData.number(scenario.get("doors")));
        assertEquals(2, SpecData.number(scenario.get("reveals")));
    }

    @Test
    void ambiguousPrefixIsRejected() {
        Outcome outcome = invoke("exact", "--p", "1");
        assertEquals(Cli.EXIT_USAGE, outcome.code());
        assertTrue(outcome.stderr().contains("ambiguous"));
    }

    @Test
    void emptyObservedIsAllowedWithZeroReveals() {
        Outcome outcome = invoke("exact", "--reveals", "0", "--observed", "");
        assertEquals(0, outcome.code(), outcome.stderr());
        Map<String, Object> outcomes = SpecData.map(outcome.json().get("outcomes"));
        assertEquals("1/1", outcomes.get("observed"));
    }

    @Test
    void simulateOutputHasCountsRatesAndIntervals() {
        Map<String, Object> json = invoke("simulate", "--host", "random", "--seed", "1", "--trials", "1000").json();
        assertEquals(675, SpecData.number(json.get("sample_size")));
        Map<String, Object> stay = SpecData.map(SpecData.map(json.get("strategies")).get("stay"));
        assertEquals(343, SpecData.number(stay.get("wins")));
        assertEquals(343.0 / 675, (Double) stay.get("rate"), 1e-12);
        assertEquals(2, ((List<?>) stay.get("wilson95")).size());
    }

    @Test
    void optimumEchoesNullRevealsAndReportsTheParabola() {
        Map<String, Object> json = invoke("optimum", "--doors", "5", "--strategy", "switch", "--cost", "1/20").json();
        assertNull(SpecData.map(json.get("scenario")).get("reveals"));
        assertEquals("1/20", json.get("cost"));
        Map<String, Object> parabola = SpecData.map(json.get("parabola"));
        assertEquals("-59/25", parabola.get("vertex_offset"));
        assertEquals("-889/1875", parabola.get("vertex_value_gap"));
        Map<String, Object> rounded = SpecData.map(parabola.get("rounded_vertex"));
        assertEquals("13/30", rounded.get("regret"));
        Map<String, Object> fitted = SpecData.map(parabola.get("fitted_choice"));
        assertEquals("0/1", fitted.get("regret"));
    }

    @Test
    void optimumWithTwoFeasibleRevealsHasNoParabola() {
        Map<String, Object> json = invoke("optimum", "--strategy", "switch").json();
        assertNull(json.get("parabola"));
        assertEquals("0/1", json.get("cost"));
    }

    @Test
    void prngEchoesTheExtraFlag() {
        Map<String, Object> bounded = invoke("prng", "--seed", "0", "--kind", "bounded", "--bound", "6", "--count", "3").json();
        assertEquals(6, SpecData.number(bounded.get("bound")));
        assertEquals(3, ((List<?>) bounded.get("values")).size());
        Map<String, Object> words = invoke("prng", "--seed", "0", "--kind", "words").json();
        assertEquals(List.of("11091344671253066420"), words.get("values"));
        Map<String, Object> shuffle = invoke("prng", "--seed", "0", "--kind", "shuffle", "--size", "5").json();
        assertEquals(5, SpecData.number(shuffle.get("size")));
    }

    @Test
    void helpAndVersionExitZero() {
        Outcome help = invoke("--help");
        assertEquals(0, help.code());
        assertTrue(help.stdout().startsWith("usage: monty-lab"));
        assertEquals(0, invoke("exact", "-h").code());
        Outcome version = invoke("--version");
        assertEquals(0, version.code());
        assertTrue(version.stdout().startsWith("monty-lab "));
    }

    @Test
    void closedOutputReportsBrokenPipe() {
        PrintStream closed = new PrintStream(new OutputStream() {
            @Override
            public void write(int value) throws java.io.IOException {
                throw new java.io.IOException("closed");
            }
        }, false, StandardCharsets.UTF_8);
        int code = Cli.run(new String[] {"exact"}, closed, new PrintStream(new ByteArrayOutputStream(), true,
                StandardCharsets.UTF_8));
        assertEquals(Cli.EXIT_BROKEN_PIPE, code);
    }
}
