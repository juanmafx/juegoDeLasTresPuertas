// Simulator counts against spec/simulation-reference.json, stream invariants and the Wilson interval.
package io.github.juanmafx.montylab;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Stream;
import org.junit.jupiter.api.DynamicTest;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.TestFactory;

class SimulatorTest {
    @TestFactory
    Stream<DynamicTest> countsAreBitIdenticalToTheReference() {
        Map<String, Map<String, Object>> reference = new HashMap<>();
        for (Map<String, Object> run : SpecData.list(SpecData.read("simulation-reference.json"), "runs")) {
            reference.put((String) run.get("id"), run);
        }
        List<Map<String, Object>> scenarios = SpecData.list(SpecData.read("scenarios.json"), "scenarios");
        return scenarios.stream().filter(entry -> entry.containsKey("simulation"))
                .map(entry -> DynamicTest.dynamicTest((String) entry.get("id"), () -> {
                    Map<String, Object> run = SpecData.map(entry.get("simulation"));
                    Scenario scenario = SpecData.scenario(SpecData.map(entry.get("scenario")));
                    Simulator.Counts counts = Simulator.simulate(scenario, SpecData.number(run.get("trials")),
                            SpecData.number(run.get("seed")));
                    Map<String, Object> golden = reference.get(entry.get("id"));
                    Map<String, Object> expectedCounts = SpecData.map(golden.get("counts"));
                    Map<String, Object> wins = SpecData.map(golden.get("wins"));
                    assertEquals(SpecData.number(expectedCounts.get("decision")), counts.decision());
                    assertEquals(SpecData.number(expectedCounts.get("void")), counts.voided());
                    assertEquals(SpecData.number(expectedCounts.get("no_offer")), counts.noOffer());
                    Object observed = expectedCounts.get("observed");
                    assertEquals(observed == null ? null : SpecData.number(observed), counts.observed());
                    assertEquals(SpecData.number(golden.get("sample_size")), counts.sampleSize());
                    assertEquals(SpecData.number(wins.get("stay")), counts.stayWins());
                    assertEquals(SpecData.number(wins.get("switch")), counts.switchWins());
                    assertEquals(SpecData.number(wins.get("mixed")), counts.mixedWins());
                }));
    }

    @Test
    void cliContractExampleForRandomHost() {
        Simulator.Counts counts = Simulator.simulate(Scenario.builder().host(Host.RANDOM).build(), 1000, 1);
        assertEquals(675, counts.decision());
        assertEquals(325, counts.voided());
        assertEquals(343, counts.stayWins());
        assertEquals(332, counts.switchWins());
        assertEquals(346, counts.mixedWins());
    }

    @Test
    void observationFiltersWithoutChangingTheStream() {
        Simulator.Counts all = Simulator.simulate(Scenario.builder().doors(4).build(), 5000, 3);
        long total = 0;
        for (int door = 1; door < 4; door++) {
            Simulator.Counts filtered = Simulator.simulate(Scenario.builder().doors(4).observed(door).build(), 5000, 3);
            assertEquals(all.decision(), filtered.decision());
            total += filtered.observed();
        }
        assertEquals(all.decision(), total);
    }

    @Test
    void sameSeedIsDeterministic() {
        Scenario scenario = Scenario.builder().doors(7).prizes(2).reveals(3).host(Host.RANDOM).mixed(Fraction.of(2, 7))
                .build();
        assertEquals(Simulator.simulate(scenario, 2000, 42), Simulator.simulate(scenario, 2000, 42));
    }

    @Test
    void extremeMixedValuesMatchPureStrategies() {
        Simulator.Counts never = Simulator.simulate(Scenario.builder().mixed(Fraction.ZERO).build(), 3000, 8);
        Simulator.Counts always = Simulator.simulate(Scenario.builder().mixed(Fraction.ONE).build(), 3000, 8);
        assertEquals(never.stayWins(), never.mixedWins());
        assertEquals(always.switchWins(), always.mixedWins());
    }

    @Test
    void rejectsInvalidTrialsAndSeed() {
        Scenario scenario = Scenario.builder().build();
        assertThrows(ScenarioException.class, () -> Simulator.simulate(scenario, 0, 1));
        assertThrows(ScenarioException.class, () -> Simulator.simulate(scenario, Scenario.MAX_TRIALS + 1, 1));
        assertThrows(ScenarioException.class, () -> Simulator.simulate(scenario, 10, -1));
    }

    @Test
    void adversarialHostWithZeroPriorPickNeverOffers() {
        Simulator.Counts counts = Simulator.simulate(Scenario.builder().doors(4).prior(0, 1, 1, 1)
                .host(Host.ADVERSARIAL).build(), 100, 1);
        assertEquals(100, counts.noOffer());
        assertEquals(0, counts.sampleSize());
    }

    @Test
    void wilsonIntervalEdgesAndKnownValue() {
        double[] none = Wilson.interval(0, 10);
        double[] all = Wilson.interval(10, 10);
        assertEquals(0.0, none[0]);
        assertEquals(1.0, all[1]);
        double[] example = Wilson.interval(343, 675);
        assertEquals(0.4705, example[0], 1e-4);
        assertEquals(0.5457, example[1], 1e-4);
        assertTrue(example[0] < 343.0 / 675 && 343.0 / 675 < example[1]);
        assertThrows(IllegalArgumentException.class, () -> Wilson.interval(1, 0));
        assertThrows(IllegalArgumentException.class, () -> Wilson.interval(5, 4));
    }

    @Test
    void emptySampleReportsNullRates() {
        Map<String, Object> report = Cli.simulateReport(Scenario.builder().doors(4).prior(0, 1, 1, 1)
                .host(Host.ADVERSARIAL).build(), 50, 1);
        Map<String, Object> stay = SpecData.map(SpecData.map(report.get("strategies")).get("stay"));
        assertNull(stay.get("rate"));
        assertNull(stay.get("wilson95"));
    }
}
