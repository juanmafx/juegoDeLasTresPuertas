// Player strategies: stay, switch uniformly, or switch with probability q.
package io.github.juanmafx.montylab;

import java.util.Locale;

public enum Strategy {
    STAY, SWITCH, MIXED;

    public String label() {
        return name().toLowerCase(Locale.ROOT);
    }

    public static Strategy parse(String text) {
        for (Strategy strategy : values()) {
            if (strategy.label().equals(text)) {
                return strategy;
            }
        }
        throw new ScenarioException("argument --strategy: invalid choice '" + text
                + "' (choose from stay, switch, mixed)");
    }
}
