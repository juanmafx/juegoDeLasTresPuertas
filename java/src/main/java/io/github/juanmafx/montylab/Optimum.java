// Exploration value curve V(K) = P(win) - c*K, its exact optimum and its least-squares parabola.
package io.github.juanmafx.montylab;

import java.math.BigInteger;
import java.util.ArrayList;
import java.util.List;

public final class Optimum {
    private Optimum() {
    }

    public record CurvePoint(int reveals, Fraction win, Fraction value) {
    }

    public record Parabola(Fraction a, Fraction b, Fraction c, Fraction residualSumOfSquares,
            Fraction vertexReveals, Fraction vertexValue, int fittedChoice, Integer roundedVertex) {

        public String shape() {
            if (a.signum() < 0) {
                return "concave";
            }
            return a.signum() > 0 ? "convex" : "linear";
        }

        public Fraction at(Fraction k) {
            return a.multiply(k).multiply(k).add(b.multiply(k)).add(c);
        }
    }

    public record Result(Strategy strategy, Fraction cost, List<CurvePoint> curve, CurvePoint best,
            Parabola parabola) {
    }

    private static Fraction determinant(Fraction[][] m) {
        return m[0][0].multiply(m[1][1].multiply(m[2][2]).subtract(m[1][2].multiply(m[2][1])))
                .subtract(m[0][1].multiply(m[1][0].multiply(m[2][2]).subtract(m[1][2].multiply(m[2][0]))))
                .add(m[0][2].multiply(m[1][0].multiply(m[2][1]).subtract(m[1][1].multiply(m[2][0]))));
    }

    public static Fraction[] fitParabola(int[] ks, Fraction[] values) {
        Fraction[] s = new Fraction[5];
        Fraction[] t = new Fraction[3];
        for (int power = 0; power < 5; power++) {
            s[power] = Fraction.ZERO;
        }
        for (int power = 0; power < 3; power++) {
            t[power] = Fraction.ZERO;
        }
        for (int i = 0; i < ks.length; i++) {
            Fraction k = Fraction.of(ks[i]);
            Fraction kp = Fraction.ONE;
            for (int power = 0; power < 5; power++) {
                s[power] = s[power].add(kp);
                if (power < 3) {
                    t[power] = t[power].add(values[i].multiply(kp));
                }
                kp = kp.multiply(k);
            }
        }
        Fraction[][] matrix = {{s[4], s[3], s[2]}, {s[3], s[2], s[1]}, {s[2], s[1], s[0]}};
        Fraction[] rhs = {t[2], t[1], t[0]};
        Fraction det = determinant(matrix);
        Fraction[] coefficients = new Fraction[3];
        for (int column = 0; column < 3; column++) {
            Fraction[][] replaced = new Fraction[3][3];
            for (int row = 0; row < 3; row++) {
                for (int j = 0; j < 3; j++) {
                    replaced[row][j] = j == column ? rhs[row] : matrix[row][j];
                }
            }
            coefficients[column] = determinant(replaced).divide(det);
        }
        return coefficients;
    }

    static Parabola buildParabola(List<CurvePoint> curve) {
        if (curve.size() < 3) {
            return null;
        }
        int[] ks = new int[curve.size()];
        Fraction[] values = new Fraction[curve.size()];
        for (int i = 0; i < ks.length; i++) {
            ks[i] = curve.get(i).reveals();
            values[i] = curve.get(i).value();
        }
        Fraction[] fit = fitParabola(ks, values);
        Fraction a = fit[0];
        Fraction b = fit[1];
        Fraction c = fit[2];
        Fraction residual = Fraction.ZERO;
        Fraction bestFitted = null;
        int fittedChoice = 0;
        for (CurvePoint point : curve) {
            Fraction k = Fraction.of(point.reveals());
            Fraction fitted = a.multiply(k).multiply(k).add(b.multiply(k)).add(c);
            Fraction error = fitted.subtract(point.value());
            residual = residual.add(error.multiply(error));
            if (bestFitted == null || fitted.compareTo(bestFitted) > 0) {
                bestFitted = fitted;
                fittedChoice = point.reveals();
            }
        }
        if (a.isZero()) {
            return new Parabola(a, b, c, residual, null, null, fittedChoice, null);
        }
        Fraction two = Fraction.of(2);
        Fraction vertex = b.negate().divide(two.multiply(a));
        int highest = curve.get(curve.size() - 1).reveals();
        long floored = vertex.add(Fraction.HALF).floor()
                .max(BigInteger.ZERO).min(BigInteger.valueOf(highest)).longValueExact();
        Fraction vertexValue = c.subtract(b.multiply(b).divide(Fraction.of(4).multiply(a)));
        return new Parabola(a, b, c, residual, vertex, vertexValue, fittedChoice, (int) floored);
    }

    public static Result curve(Scenario scenario, Strategy strategy, Fraction cost) {
        if (scenario.observed() != null) {
            throw new ScenarioException("optimum does not accept an observed reveal");
        }
        if (cost.signum() < 0) {
            throw new ScenarioException("cost must be a non-negative fraction");
        }
        List<CurvePoint> curve = new ArrayList<>();
        for (int reveals = 0; reveals <= scenario.maxReveals(); reveals++) {
            Fraction win = Solver.solve(scenario.withReveals(reveals)).win(strategy, scenario.mixed());
            if (win == null) {
                throw new ScenarioException("optimum is undefined when the host never offers a decision");
            }
            curve.add(new CurvePoint(reveals, win, win.subtract(cost.multiply(reveals))));
        }
        CurvePoint best = curve.get(0);
        for (CurvePoint point : curve.subList(1, curve.size())) {
            if (point.value().compareTo(best.value()) > 0) {
                best = point;
            }
        }
        return new Result(strategy, cost, List.copyOf(curve), best, buildParabola(curve));
    }
}
