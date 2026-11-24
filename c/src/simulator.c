/* Seeded Monte Carlo simulator whose random stream is fixed by spec/prng.md. */
#include "simulator.h"

#include "prng.h"

#include <math.h>
#include <stdio.h>
#include <string.h>

#define MH_Z95 1.959963984540054

int64_t mh_sample_size(const mh_counts *counts) {
    return counts->has_observed ? counts->observed : counts->decision;
}

static uint64_t door_mask(const int *doors, size_t count) {
    uint64_t mask = 0;
    for (size_t i = 0; i < count; i++) {
        mask |= (uint64_t)1 << doors[i];
    }
    return mask;
}

bool mh_simulate(const mh_scenario *scenario, int64_t trials, int64_t seed, mh_counts *out,
                 char *error, size_t error_size) {
    if (trials < 1 || trials > MH_MAX_TRIALS) {
        snprintf(error, error_size, "trials must be between 1 and %d", MH_MAX_TRIALS);
        return false;
    }
    if (seed < 0) {
        snprintf(error, error_size, "seed must be between 0 and %lld", (long long)MH_MAX_SEED);
        return false;
    }
    int n = scenario->doors;
    int pick = scenario->pick;
    int doors[MH_MAX_DOORS];
    uint64_t prior[MH_MAX_DOORS];
    for (int door = 0; door < n; door++) {
        doors[door] = door;
        prior[door] = mh_prior_weight(scenario, door);
    }
    uint64_t observed = door_mask(scenario->observed, (size_t)scenario->observed_count);
    uint64_t q_num = 0;
    uint64_t q_den = 0;
    bool q_fits = mh_big_to_u64(&scenario->mixed.num, &q_num) &&
                  mh_big_to_u64(&scenario->mixed.den, &q_den);
    mh_rng rng;
    mh_rng_init(&rng, (uint64_t)seed);
    memset(out, 0, sizeof *out);
    out->trials = trials;
    out->seed = seed;
    out->has_observed = scenario->has_observed;
    for (int64_t trial = 0; trial < trials; trial++) {
        int chosen[MH_MAX_DOORS];
        mh_rng_weighted_sample(&rng, doors, prior, (size_t)n, (size_t)scenario->prizes, chosen);
        uint64_t prizes = door_mask(chosen, (size_t)scenario->prizes);
        bool pick_wins = (prizes >> pick & 1U) != 0;
        if (scenario->host == MH_HOST_ADVERSARIAL && !pick_wins) {
            out->no_offer++;
            continue;
        }
        int candidates[MH_MAX_DOORS];
        uint64_t weights[MH_MAX_DOORS];
        size_t candidate_count = 0;
        for (int door = 0; door < n; door++) {
            if (door == pick) {
                continue;
            }
            if (scenario->host != MH_HOST_RANDOM && (prizes >> door & 1U) != 0) {
                continue;
            }
            candidates[candidate_count] = door;
            weights[candidate_count] = scenario->has_host_weights ? scenario->host_weights[door] : 1U;
            candidate_count++;
        }
        int opened_doors[MH_MAX_DOORS];
        mh_rng_weighted_sample(&rng, candidates, weights, candidate_count,
                               (size_t)scenario->reveals, opened_doors);
        uint64_t opened = door_mask(opened_doors, (size_t)scenario->reveals);
        if (scenario->host == MH_HOST_RANDOM && (opened & prizes) != 0) {
            out->void_++;
            continue;
        }
        out->decision++;
        int remaining[MH_MAX_DOORS];
        uint64_t remaining_count = 0;
        for (int door = 0; door < n; door++) {
            if (door != pick && (opened >> door & 1U) == 0) {
                remaining[remaining_count++] = door;
            }
        }
        int target = remaining[mh_rng_bounded(&rng, remaining_count)];
        if (!q_fits) {
            snprintf(error, error_size, "bound must be between 1 and 2^64 - 1");
            return false;
        }
        bool switching = mh_rng_bounded(&rng, q_den) < q_num;
        if (scenario->has_observed) {
            if (opened != observed) {
                continue;
            }
            out->observed++;
        }
        bool switch_wins = (prizes >> target & 1U) != 0;
        out->stay_wins += pick_wins ? 1 : 0;
        out->switch_wins += switch_wins ? 1 : 0;
        out->mixed_wins += (switching ? switch_wins : pick_wins) ? 1 : 0;
    }
    return true;
}

mh_interval mh_wilson95(int64_t successes, int64_t trials) {
    double z = MH_Z95;
    double z_squared = z * z;
    double n = (double)trials;
    double rate = (double)successes / n;
    double denominator = 1.0 + z_squared / n;
    double center = (rate + z_squared / (2.0 * n)) / denominator;
    double margin = z * sqrt(rate * (1.0 - rate) / n + z_squared / (4.0 * (n * n))) / denominator;
    mh_interval interval;
    interval.lower = successes == 0 ? 0.0 : fmax(0.0, center - margin);
    interval.upper = successes == trials ? 1.0 : fmin(1.0, center + margin);
    return interval;
}
