// Wilson score interval at 95% confidence with the z value fixed by spec/cli.md.
package io.github.juanmafx.montylab;

public final class Wilson {
    public static final double Z95 = 1.959963984540054;

    private Wilson() {
    }

    public static double[] interval(long successes, long trials) {
        if (trials <= 0) {
            throw new IllegalArgumentException("trials must be positive");
        }
        if (successes < 0 || successes > trials) {
            throw new IllegalArgumentException("successes must be between 0 and trials");
        }
        double zSquared = Z95 * Z95;
        double rate = (double) successes / (double) trials;
        double denominator = 1 + zSquared / trials;
        double center = (rate + zSquared / (double) (2 * trials)) / denominator;
        double margin = Z95 * Math.sqrt(rate * (1 - rate) / trials + zSquared / (double) (4 * trials * trials))
                / denominator;
        double lower = successes == 0 ? 0.0 : Math.max(0.0, center - margin);
        double upper = successes == trials ? 1.0 : Math.min(1.0, center + margin);
        return new double[] {lower, upper};
    }
}
