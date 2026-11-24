// Exact solver and optimum curve against every expectation in spec/scenarios.json, plus closed-form anchors.
package io.github.juanmafx.montylab;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;

import java.util.List;
import java.util.Map;
import java.util.stream.Stream;
import org.junit.jupiter.api.DynamicTest;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.TestFactory;

class SolverTest {
    private static List<Map<String, Object>> scenarios() {
        return SpecData.list(SpecData.read("scenarios.json"), "scenarios");
    }

    @TestFactory
    Stream<DynamicTest> exactMatchesEveryScenario() {
        List<Map<String, Object>> entries = scenarios();
        assertEquals(49, entries.size());
        return entries.stream().map(entry -> DynamicTest.dynamicTest((String) entry.get("id"), () -> {
            Scenario scenario = SpecData.scenario(SpecData.map(entry.get("scenario")));
            Map<String, Object> report = Cli.exactReport(scenario);
            Map<String, Object> expected = SpecData.map(SpecData.map(entry.get("expected")).get("exact"));
            assertEquals(expected.get("prize_at_pick"), report.get("prize_at_pick"));
            assertEquals(expected.get("outcomes"), report.get("outcomes"));
            assertEquals(expected.get("win"), report.get("win"));
        }));
    }

    @TestFactory
    Stream<DynamicTest> optimumMatchesEveryScenarioWithAnOptimumBlock() {
        return scenarios().stream().filter(entry -> entry.containsKey("optimum"))
                .map(entry -> DynamicTest.dynamicTest((String) entry.get("id"), () -> {
                    Map<String, Object> request = SpecData.map(entry.get("optimum"));
                    Scenario scenario = SpecData.scenario(SpecData.map(entry.get("scenario")));
                    Scenario base = Scenario.builder().doors(scenario.doors()).prizes(scenario.prizes())
                            .prior(scenario.prior()).pick(scenario.pick()).reveals(0).host(scenario.host())
                            .hostWeights(scenario.hostWeights()).mixed(scenario.mixed()).build();
                    Map<String, Object> report = Cli.optimumReport(base,
                            Strategy.parse((String) request.get("strategy")),
                            Fraction.parse((String) request.get("cost")));
                    Map<String, Object> expected = SpecData.map(SpecData.map(entry.get("expected")).get("optimum"));
                    Object roundTrip = SpecData.parse(Json.write(report));
                    for (String key : List.of("curve", "optimum", "parabola")) {
                        assertEquals(expected.get(key), SpecData.map(roundTrip).get(key), key);
                    }
                }));
    }

    @Test
    void classicInformedHost() {
        ExactResult result = Solver.solve(Scenario.builder().build());
        assertEquals(Fraction.of(1, 3), result.stay());
        assertEquals(Fraction.of(2, 3), result.switched());
        assertEquals(Fraction.HALF, result.mixed(Fraction.HALF));
    }

    @Test
    void randomHostGivesNoAdvantageConditionalOnNoVoid() {
        ExactResult result = Solver.solve(Scenario.builder().host(Host.RANDOM).build());
        assertEquals(Fraction.of(2, 3), result.decision());
        assertEquals(Fraction.of(1, 3), result.voided());
        assertEquals(Fraction.HALF, result.stay());
        assertEquals(Fraction.HALF, result.switched());
    }

    @Test
    void adversarialHostMakesSwitchingAlwaysLose() {
        ExactResult result = Solver.solve(Scenario.builder().host(Host.ADVERSARIAL).build());
        assertEquals(Fraction.of(1, 3), result.decision());
        assertEquals(Fraction.of(2, 3), result.noOffer());
        assertEquals(Fraction.ONE, result.stay());
        assertEquals(Fraction.ZERO, result.switched());
    }

    @Test
    void adversarialHostWithZeroPriorPickHasNoDecision() {
        ExactResult result = Solver.solve(Scenario.builder().doors(4).prior(0, 1, 1, 1)
                .host(Host.ADVERSARIAL).build());
        assertEquals(Fraction.ZERO, result.decision());
        assertNull(result.stay());
        assertNull(result.switched());
        assertNull(result.mixed(Fraction.HALF));
    }

    @Test
    void biasedHostObservationShiftsTheOdds() {
        Scenario scenario = Scenario.builder().host(Host.BIASED).hostWeights(1, 3, 1).observed(2).build();
        ExactResult result = Solver.solve(scenario);
        assertEquals(Fraction.of(1, 5), result.stay());
        assertEquals(Fraction.of(4, 5), result.switched());
        assertEquals(Fraction.of(5, 12), result.observed());
    }

    @Test
    void sixtyFourDoorsUseArbitraryPrecision() {
        ExactResult result = Solver.solve(Scenario.builder().doors(64).prizes(3).reveals(30).host(Host.RANDOM).build());
        assertEquals(Fraction.ONE, result.decision().add(result.voided()));
    }

    @Test
    void enumerationIsLimitedToTenDoors() {
        assertThrows(ScenarioException.class,
                () -> Solver.solve(Scenario.builder().doors(11).prior(1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1).build()));
        assertThrows(ScenarioException.class,
                () -> Solver.solve(Scenario.builder().doors(11).reveals(1).observed(3).build()));
    }

    @Test
    void parabolaExampleFromCliContract() {
        Optimum.Result result = Optimum.curve(Scenario.builder().doors(5).reveals(0).build(), Strategy.SWITCH,
                Fraction.of(1, 20));
        Optimum.Parabola fit = result.parabola();
        assertEquals(3, result.best().reveals());
        assertEquals("13/20", result.best().value().toString());
        assertEquals("1/12", fit.a().toString());
        assertEquals("-8/75", fit.b().toString());
        assertEquals("21/100", fit.c().toString());
        assertEquals("convex", fit.shape());
        assertEquals("16/25", fit.vertexReveals().toString());
        assertEquals("1319/7500", fit.vertexValue().toString());
        assertEquals("1/500", fit.residualSumOfSquares().toString());
        assertEquals(1, fit.roundedVertex());
        assertEquals(3, fit.fittedChoice());
    }

    @Test
    void exactQuadraticIsRecoveredWithZeroResidual() {
        int[] ks = {0, 1, 2, 3, 4};
        Fraction[] values = new Fraction[ks.length];
        for (int i = 0; i < ks.length; i++) {
            Fraction k = Fraction.of(ks[i]);
            values[i] = Fraction.of(-1, 2).multiply(k).multiply(k).add(Fraction.of(3).multiply(k)).add(Fraction.of(1, 7));
        }
        Fraction[] fit = Optimum.fitParabola(ks, values);
        assertEquals(Fraction.of(-1, 2), fit[0]);
        assertEquals(Fraction.of(3), fit[1]);
        assertEquals(Fraction.of(1, 7), fit[2]);
    }

    @Test
    void optimumRejectsNegativeCostAndUndefinedDecisions() {
        assertThrows(ScenarioException.class,
                () -> Optimum.curve(Scenario.builder().reveals(0).build(), Strategy.STAY, Fraction.of(-1, 2)));
        assertThrows(ScenarioException.class, () -> Optimum.curve(Scenario.builder().doors(4).prior(0, 1, 1, 1)
                .host(Host.ADVERSARIAL).reveals(0).build(), Strategy.STAY, Fraction.ZERO));
        assertThrows(ScenarioException.class, () -> Optimum.curve(Scenario.builder().observed(1).build(),
                Strategy.STAY, Fraction.ZERO));
    }

    @Test
    void optimumTiesGoToTheSmallestReveals() {
        Optimum.Result result = Optimum.curve(Scenario.builder().doors(5).reveals(0).build(), Strategy.STAY,
                Fraction.ZERO);
        assertEquals(0, result.best().reveals());
        assertEquals("linear", result.parabola().shape());
        assertNull(result.parabola().vertexReveals());
        assertNull(result.parabola().roundedVertex());
    }
}
