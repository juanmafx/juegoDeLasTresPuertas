// Host policies of the generalized game.
package io.github.juanmafx.montylab;

import java.util.Locale;

public enum Host {
    INFORMED, RANDOM, BIASED, ADVERSARIAL;

    public String label() {
        return name().toLowerCase(Locale.ROOT);
    }

    public static Host parse(String text) {
        for (Host host : values()) {
            if (host.label().equals(text)) {
                return host;
            }
        }
        throw new ScenarioException("argument --host: invalid choice '" + text
                + "' (choose from informed, random, biased, adversarial)");
    }
}
