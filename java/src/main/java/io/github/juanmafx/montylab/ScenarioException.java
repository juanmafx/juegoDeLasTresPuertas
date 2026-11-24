// Invalid input: the CLI maps it to exit code 2 and an "error: ..." message.
package io.github.juanmafx.montylab;

public final class ScenarioException extends IllegalArgumentException {
    private static final long serialVersionUID = 1L;

    public ScenarioException(String message) {
        super(message);
    }
}
