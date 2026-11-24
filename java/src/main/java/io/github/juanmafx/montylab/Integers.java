// Strict decimal integer and integer-list parsing shared by the CLI and the fraction parser.
package io.github.juanmafx.montylab;

import java.math.BigInteger;
import java.util.ArrayList;
import java.util.List;
import java.util.regex.Pattern;

public final class Integers {
    private static final Pattern DECIMAL = Pattern.compile("[+-]?[0-9]+");

    private Integers() {
    }

    public static BigInteger parse(String text) {
        String trimmed = text.strip();
        if (!DECIMAL.matcher(trimmed).matches()) {
            throw new NumberFormatException("invalid integer '" + text + "'");
        }
        return new BigInteger(trimmed.startsWith("+") ? trimmed.substring(1) : trimmed);
    }

    public static long parseLong(String name, String text) {
        return parseInRange(name, text, Long.MIN_VALUE, Long.MAX_VALUE);
    }

    public static long parseInRange(String name, String text, long minimum, long maximum) {
        BigInteger value;
        try {
            value = parse(text);
        } catch (NumberFormatException error) {
            throw new ScenarioException("argument --" + name + ": invalid int value '" + text + "'");
        }
        if (value.compareTo(BigInteger.valueOf(minimum)) < 0 || value.compareTo(BigInteger.valueOf(maximum)) > 0) {
            throw new ScenarioException(name + " must be between " + minimum + " and " + maximum);
        }
        return value.longValueExact();
    }

    public static List<BigInteger> parseList(String text) {
        List<BigInteger> values = new ArrayList<>();
        if (text.strip().isEmpty()) {
            return values;
        }
        try {
            for (String part : text.split(",", -1)) {
                values.add(parse(part));
            }
        } catch (NumberFormatException error) {
            throw new ScenarioException("invalid integer list '" + text + "'");
        }
        return values;
    }
}
