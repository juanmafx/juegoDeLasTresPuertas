// Exact probabilities for one scenario; win values are null when the conditioning event is impossible.
package io.github.juanmafx.montylab;

public record ExactResult(Fraction prizeAtPick, Fraction decision, Fraction voided, Fraction noOffer,
        Fraction observed, Fraction stay, Fraction switched) {

    public Fraction mixed(Fraction q) {
        if (stay == null || switched == null) {
            return null;
        }
        return Fraction.ONE.subtract(q).multiply(stay).add(q.multiply(switched));
    }

    public Fraction win(Strategy strategy, Fraction q) {
        return switch (strategy) {
            case STAY -> stay;
            case SWITCH -> switched;
            case MIXED -> mixed(q);
        };
    }
}
