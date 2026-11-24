// Test helper: a small JSON reader and loaders for the shared files in spec/.
package io.github.juanmafx.montylab;

import java.io.IOException;
import java.math.BigInteger;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

final class SpecData {
    static final Path SPEC = Path.of(System.getProperty("montylab.spec", "../spec")).toAbsolutePath().normalize();

    private final String text;
    private int position;

    private SpecData(String text) {
        this.text = text;
    }

    static Object read(String fileName) {
        try {
            return parse(Files.readString(SPEC.resolve(fileName), StandardCharsets.UTF_8));
        } catch (IOException error) {
            throw new IllegalStateException("cannot read spec file " + fileName, error);
        }
    }

    @SuppressWarnings("unchecked")
    static List<Map<String, Object>> list(Object document, String key) {
        return (List<Map<String, Object>>) ((Map<String, Object>) document).get(key);
    }

    @SuppressWarnings("unchecked")
    static Map<String, Object> map(Object value) {
        return (Map<String, Object>) value;
    }

    static Object parse(String text) {
        SpecData reader = new SpecData(text);
        Object value = reader.value();
        reader.skipWhitespace();
        if (reader.position != text.length()) {
            throw new IllegalArgumentException("trailing JSON content at " + reader.position);
        }
        return value;
    }

    static Scenario scenario(Map<String, Object> json) {
        Scenario.Builder builder = Scenario.builder()
                .doors(number(json.get("doors")))
                .prizes(number(json.get("prizes")))
                .pick(number(json.get("pick")))
                .reveals(number(json.get("reveals")))
                .host(Host.parse((String) json.get("host")))
                .mixed(Fraction.parse((String) json.get("mixed")));
        if (!"uniform".equals(json.get("prior"))) {
            builder.prior(bigList(json.get("prior")));
        }
        if (json.get("host_weights") != null) {
            builder.hostWeights(bigList(json.get("host_weights")));
        }
        if (json.get("observed") != null) {
            builder.observed(bigList(json.get("observed")));
        }
        return builder.build();
    }

    static long number(Object value) {
        return ((BigInteger) value).longValueExact();
    }

    static List<BigInteger> bigList(Object value) {
        List<BigInteger> result = new ArrayList<>();
        for (Object item : (List<?>) value) {
            result.add((BigInteger) item);
        }
        return result;
    }

    private void skipWhitespace() {
        while (position < text.length() && Character.isWhitespace(text.charAt(position))) {
            position++;
        }
    }

    private Object value() {
        skipWhitespace();
        char ch = text.charAt(position);
        if (ch == '{') {
            return object();
        }
        if (ch == '[') {
            return array();
        }
        if (ch == '"') {
            return string();
        }
        if (text.startsWith("null", position)) {
            position += 4;
            return null;
        }
        if (text.startsWith("true", position)) {
            position += 4;
            return Boolean.TRUE;
        }
        if (text.startsWith("false", position)) {
            position += 5;
            return Boolean.FALSE;
        }
        return number();
    }

    private Map<String, Object> object() {
        Map<String, Object> result = new LinkedHashMap<>();
        position++;
        skipWhitespace();
        if (text.charAt(position) == '}') {
            position++;
            return result;
        }
        while (true) {
            skipWhitespace();
            String key = string();
            skipWhitespace();
            expect(':');
            result.put(key, value());
            skipWhitespace();
            if (text.charAt(position) == ',') {
                position++;
                continue;
            }
            expect('}');
            return result;
        }
    }

    private List<Object> array() {
        List<Object> result = new ArrayList<>();
        position++;
        skipWhitespace();
        if (text.charAt(position) == ']') {
            position++;
            return result;
        }
        while (true) {
            result.add(value());
            skipWhitespace();
            if (text.charAt(position) == ',') {
                position++;
                continue;
            }
            expect(']');
            return result;
        }
    }

    private void expect(char ch) {
        if (text.charAt(position) != ch) {
            throw new IllegalArgumentException("expected '" + ch + "' at " + position);
        }
        position++;
    }

    private String string() {
        expect('"');
        StringBuilder out = new StringBuilder();
        while (true) {
            char ch = text.charAt(position++);
            if (ch == '"') {
                return out.toString();
            }
            if (ch != '\\') {
                out.append(ch);
                continue;
            }
            char escape = text.charAt(position++);
            switch (escape) {
                case 'n' -> out.append('\n');
                case 't' -> out.append('\t');
                case 'r' -> out.append('\r');
                case 'b' -> out.append('\b');
                case 'f' -> out.append('\f');
                case 'u' -> {
                    out.append((char) Integer.parseInt(text.substring(position, position + 4), 16));
                    position += 4;
                }
                default -> out.append(escape);
            }
        }
    }

    private Object number() {
        int start = position;
        while (position < text.length() && "+-0123456789.eE".indexOf(text.charAt(position)) >= 0) {
            position++;
        }
        String literal = text.substring(start, position);
        if (literal.isEmpty()) {
            throw new IllegalArgumentException("unexpected JSON content at " + start);
        }
        if (literal.contains(".") || literal.contains("e") || literal.contains("E")) {
            return Double.parseDouble(literal);
        }
        return new BigInteger(literal);
    }
}
