/* Exact solver: closed forms for unobserved games, full enumeration for observed reveals. */
#include "solver.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

uint64_t mh_comb(int n, int k) {
    if (k < 0 || k > n) {
        return 0;
    }
    if (k > n - k) {
        k = n - k;
    }
    mh_u128 result = 1;
    for (int i = 1; i <= k; i++) {
        result = result * (mh_u128)(uint64_t)(n - k + i) / (mh_u128)(uint64_t)i;
    }
    return (uint64_t)result;
}

static void frac_u64(mh_frac *r, uint64_t num, uint64_t den) {
    mh_big n;
    mh_big d;
    mh_big_set_u64(&n, num);
    mh_big_set_u64(&d, den);
    mh_frac_set_parts(r, false, &n, &d);
}

static bool require_enumerable(const mh_scenario *scenario, char *error, size_t error_size) {
    if (scenario->doors > MH_ENUMERATION_MAX_DOORS) {
        snprintf(error, error_size,
                 "weighted priors and observed reveals support at most %d doors",
                 MH_ENUMERATION_MAX_DOORS);
        return false;
    }
    return true;
}

typedef struct {
    size_t size;
    bool *present;
    mh_frac *probability;
} mh_distribution;

static void distribution_free(mh_distribution *d) {
    free(d->present);
    free(d->probability);
    d->present = NULL;
    d->probability = NULL;
}

static bool distribution_alloc(mh_distribution *d, size_t size) {
    d->size = size;
    d->present = calloc(size, sizeof *d->present);
    d->probability = malloc(size * sizeof *d->probability);
    if (d->present == NULL || d->probability == NULL) {
        distribution_free(d);
        return false;
    }
    return true;
}

static bool prize_set_distribution(const mh_scenario *scenario, mh_distribution *out, char *error,
                                   size_t error_size) {
    int n = scenario->doors;
    size_t size = (size_t)1 << n;
    mh_distribution layer;
    mh_distribution following;
    if (!distribution_alloc(&layer, size)) {
        snprintf(error, error_size, "out of memory");
        return false;
    }
    if (!distribution_alloc(&following, size)) {
        distribution_free(&layer);
        snprintf(error, error_size, "out of memory");
        return false;
    }
    uint64_t total = 0;
    for (int door = 0; door < n; door++) {
        total += mh_prior_weight(scenario, door);
    }
    layer.present[0] = true;
    mh_frac_set_i64(&layer.probability[0], 1, 1);
    for (int step = 0; step < scenario->prizes; step++) {
        memset(following.present, 0, size * sizeof *following.present);
        for (size_t mask = 0; mask < size; mask++) {
            if (!layer.present[mask]) {
                continue;
            }
            uint64_t remaining = total;
            for (int door = 0; door < n; door++) {
                if ((mask >> door & 1U) != 0) {
                    remaining -= mh_prior_weight(scenario, door);
                }
            }
            for (int door = 0; door < n; door++) {
                uint32_t weight = mh_prior_weight(scenario, door);
                if ((mask >> door & 1U) != 0 || weight == 0) {
                    continue;
                }
                size_t key = mask | (size_t)1 << door;
                mh_frac share;
                mh_frac term;
                frac_u64(&share, weight, remaining);
                mh_frac_mul(&term, &layer.probability[mask], &share);
                if (following.present[key]) {
                    mh_frac_add(&following.probability[key], &following.probability[key], &term);
                } else {
                    following.present[key] = true;
                    following.probability[key] = term;
                }
            }
        }
        mh_distribution swap = layer;
        layer = following;
        following = swap;
    }
    distribution_free(&following);
    *out = layer;
    return true;
}

bool mh_prize_at_pick(const mh_scenario *scenario, mh_frac *out, char *error, size_t error_size) {
    if (!scenario->has_prior) {
        frac_u64(out, (uint64_t)scenario->prizes, (uint64_t)scenario->doors);
        return true;
    }
    if (!require_enumerable(scenario, error, error_size)) {
        return false;
    }
    mh_distribution distribution;
    if (!prize_set_distribution(scenario, &distribution, error, error_size)) {
        return false;
    }
    mh_frac_set_i64(out, 0, 1);
    for (size_t mask = 0; mask < distribution.size; mask++) {
        if (distribution.present[mask] && (mask >> scenario->pick & 1U) != 0) {
            mh_frac_add(out, out, &distribution.probability[mask]);
        }
    }
    distribution_free(&distribution);
    return true;
}

static bool conditional(mh_frac *out, const mh_frac *numerator, const mh_frac *denominator) {
    if (mh_frac_is_zero(denominator)) {
        return false;
    }
    mh_frac_div(out, numerator, denominator);
    return true;
}

void mh_closed_form(const mh_scenario *scenario, const mh_frac *pi, mh_exact *out) {
    int n = scenario->doors;
    int m = scenario->prizes;
    int k = scenario->reveals;
    mh_frac remaining;
    mh_frac one;
    mh_frac m_frac;
    frac_u64(&remaining, (uint64_t)(n - 1 - k), 1);
    mh_frac_set_i64(&one, 1, 1);
    mh_frac_set_i64(&m_frac, m, 1);
    memset(out, 0, sizeof *out);
    out->prize_at_pick = *pi;
    mh_frac_set_i64(&out->void_, 0, 1);
    mh_frac_set_i64(&out->no_offer, 0, 1);
    mh_frac_set_i64(&out->observed, 0, 1);
    mh_frac_set_i64(&out->stay, 0, 1);
    mh_frac_set_i64(&out->switch_, 0, 1);
    out->has_observed = false;
    if (scenario->host == MH_HOST_INFORMED || scenario->host == MH_HOST_BIASED) {
        mh_frac numerator;
        out->decision = one;
        out->has_stay = true;
        out->stay = *pi;
        out->has_switch = true;
        mh_frac_sub(&numerator, &m_frac, pi);
        mh_frac_div(&out->switch_, &numerator, &remaining);
        return;
    }
    if (scenario->host == MH_HOST_ADVERSARIAL) {
        out->decision = *pi;
        mh_frac_sub(&out->no_offer, &one, pi);
        if (!mh_frac_is_zero(pi)) {
            out->has_stay = true;
            out->stay = one;
            out->has_switch = true;
            frac_u64(&out->switch_, (uint64_t)(m - 1), (uint64_t)(n - 1 - k));
        }
        return;
    }
    uint64_t all = mh_comb(n - 1, k);
    mh_frac hit;
    mh_frac miss;
    mh_frac not_pi;
    mh_frac pi_hit;
    mh_frac not_pi_miss;
    mh_frac numerator;
    mh_frac term;
    mh_frac prizes_less_one;
    frac_u64(&hit, mh_comb(n - m, k), all);
    frac_u64(&miss, mh_comb(n - 1 - m, k), all);
    mh_frac_sub(&not_pi, &one, pi);
    mh_frac_mul(&pi_hit, pi, &hit);
    mh_frac_mul(&not_pi_miss, &not_pi, &miss);
    mh_frac_add(&out->decision, &pi_hit, &not_pi_miss);
    mh_frac_sub(&out->void_, &one, &out->decision);
    out->has_stay = conditional(&out->stay, &pi_hit, &out->decision);
    mh_frac_set_i64(&prizes_less_one, m - 1, 1);
    mh_frac_mul(&numerator, &pi_hit, &prizes_less_one);
    mh_frac_mul(&term, &not_pi_miss, &m_frac);
    mh_frac_add(&numerator, &numerator, &term);
    mh_frac_div(&numerator, &numerator, &remaining);
    out->has_switch = conditional(&out->switch_, &numerator, &out->decision);
    if (!out->has_stay) {
        mh_frac_set_i64(&out->stay, 0, 1);
    }
    if (!out->has_switch) {
        mh_frac_set_i64(&out->switch_, 0, 1);
    }
}

static bool ordered_sample_probability(const int *chosen, int size, uint64_t pool_weight,
                                       const uint32_t *weights, mh_frac *out) {
    size_t states = (size_t)1 << size;
    mh_frac *probability = malloc(states * sizeof *probability);
    bool *present = calloc(states, sizeof *present);
    if (probability == NULL || present == NULL) {
        free(probability);
        free(present);
        return false;
    }
    present[0] = true;
    mh_frac_set_i64(&probability[0], 1, 1);
    for (size_t mask = 0; mask < states; mask++) {
        if (!present[mask]) {
            continue;
        }
        uint64_t used = 0;
        for (int i = 0; i < size; i++) {
            if ((mask >> i & 1U) != 0) {
                used += weights[chosen[i]];
            }
        }
        for (int i = 0; i < size; i++) {
            if ((mask >> i & 1U) != 0) {
                continue;
            }
            size_t key = mask | (size_t)1 << i;
            mh_frac share;
            mh_frac term;
            frac_u64(&share, weights[chosen[i]], pool_weight - used);
            mh_frac_mul(&term, &probability[mask], &share);
            if (present[key]) {
                mh_frac_add(&probability[key], &probability[key], &term);
            } else {
                present[key] = true;
                probability[key] = term;
            }
        }
    }
    *out = probability[states - 1];
    free(probability);
    free(present);
    return true;
}

static bool reveal_probability(const mh_scenario *scenario, uint64_t prizes, mh_frac *out) {
    int n = scenario->doors;
    int pick = scenario->pick;
    int k = scenario->reveals;
    uint64_t observed = 0;
    for (int i = 0; i < scenario->observed_count; i++) {
        observed |= (uint64_t)1 << scenario->observed[i];
    }
    if (scenario->host == MH_HOST_RANDOM) {
        if ((prizes & observed) != 0) {
            mh_frac_set_i64(out, 0, 1);
            return true;
        }
        frac_u64(out, 1, mh_comb(n - 1, k));
        return true;
    }
    if (scenario->host == MH_HOST_ADVERSARIAL && (prizes >> pick & 1U) == 0) {
        mh_frac_set_i64(out, 0, 1);
        return true;
    }
    uint64_t valid = 0;
    int valid_count = 0;
    uint64_t valid_weight = 0;
    for (int door = 0; door < n; door++) {
        if (door != pick && (prizes >> door & 1U) == 0) {
            valid |= (uint64_t)1 << door;
            valid_count++;
            valid_weight += scenario->has_host_weights ? scenario->host_weights[door] : 1U;
        }
    }
    if ((observed & ~valid) != 0) {
        mh_frac_set_i64(out, 0, 1);
        return true;
    }
    if (scenario->host == MH_HOST_BIASED && scenario->has_host_weights) {
        return ordered_sample_probability(scenario->observed, scenario->observed_count,
                                          valid_weight, scenario->host_weights, out);
    }
    frac_u64(out, 1, mh_comb(valid_count, k));
    return true;
}

static int popcount(uint64_t value) {
    int count = 0;
    while (value != 0) {
        value &= value - 1U;
        count++;
    }
    return count;
}

bool mh_enumerate_observed(const mh_scenario *scenario, const mh_frac *pi, mh_exact *out,
                           char *error, size_t error_size) {
    if (!require_enumerable(scenario, error, error_size)) {
        return false;
    }
    int n = scenario->doors;
    int pick = scenario->pick;
    uint64_t remaining = 0;
    for (int door = 0; door < n; door++) {
        remaining |= (uint64_t)1 << door;
    }
    remaining &= ~((uint64_t)1 << pick);
    for (int i = 0; i < scenario->observed_count; i++) {
        remaining &= ~((uint64_t)1 << scenario->observed[i]);
    }
    int remaining_count = popcount(remaining);
    mh_distribution distribution;
    if (!prize_set_distribution(scenario, &distribution, error, error_size)) {
        return false;
    }
    mh_frac joint;
    mh_frac stay;
    mh_frac switch_;
    mh_frac_set_i64(&joint, 0, 1);
    mh_frac_set_i64(&stay, 0, 1);
    mh_frac_set_i64(&switch_, 0, 1);
    for (size_t mask = 0; mask < distribution.size; mask++) {
        if (!distribution.present[mask]) {
            continue;
        }
        mh_frac reveal;
        mh_frac weight;
        if (!reveal_probability(scenario, (uint64_t)mask, &reveal)) {
            distribution_free(&distribution);
            snprintf(error, error_size, "out of memory");
            return false;
        }
        mh_frac_mul(&weight, &distribution.probability[mask], &reveal);
        if (mh_frac_is_zero(&weight)) {
            continue;
        }
        mh_frac_add(&joint, &joint, &weight);
        if ((mask >> pick & 1U) != 0) {
            mh_frac_add(&stay, &stay, &weight);
        }
        mh_frac share;
        mh_frac term;
        frac_u64(&share, (uint64_t)popcount(remaining & (uint64_t)mask), (uint64_t)remaining_count);
        mh_frac_mul(&term, &weight, &share);
        mh_frac_add(&switch_, &switch_, &term);
    }
    distribution_free(&distribution);
    mh_exact unobserved;
    mh_closed_form(scenario, pi, &unobserved);
    *out = unobserved;
    out->has_observed = true;
    out->observed = joint;
    out->has_stay = conditional(&out->stay, &stay, &joint);
    out->has_switch = conditional(&out->switch_, &switch_, &joint);
    return true;
}

bool mh_solve(const mh_scenario *scenario, mh_exact *out, char *error, size_t error_size) {
    mh_frac pi;
    if (!mh_prize_at_pick(scenario, &pi, error, error_size)) {
        return false;
    }
    if (scenario->has_observed) {
        return mh_enumerate_observed(scenario, &pi, out, error, error_size);
    }
    mh_closed_form(scenario, &pi, out);
    return true;
}

bool mh_exact_win(const mh_exact *result, mh_strategy strategy, const mh_frac *q, mh_frac *out) {
    if (strategy == MH_STAY) {
        *out = result->stay;
        return result->has_stay;
    }
    if (strategy == MH_SWITCH) {
        *out = result->switch_;
        return result->has_switch;
    }
    if (!result->has_stay || !result->has_switch) {
        return false;
    }
    mh_frac one;
    mh_frac complement;
    mh_frac left;
    mh_frac right;
    mh_frac_set_i64(&one, 1, 1);
    mh_frac_sub(&complement, &one, q);
    mh_frac_mul(&left, &complement, &result->stay);
    mh_frac_mul(&right, q, &result->switch_);
    mh_frac_add(out, &left, &right);
    return true;
}
