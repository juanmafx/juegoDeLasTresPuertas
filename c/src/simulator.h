/* Seeded Monte Carlo simulator whose random stream is fixed by spec/prng.md. */
#ifndef MH_SIMULATOR_H
#define MH_SIMULATOR_H

#include "model.h"

typedef struct {
    int64_t trials;
    int64_t seed;
    int64_t decision;
    int64_t void_;
    int64_t no_offer;
    bool has_observed;
    int64_t observed;
    int64_t stay_wins;
    int64_t switch_wins;
    int64_t mixed_wins;
} mh_counts;

int64_t mh_sample_size(const mh_counts *counts);
bool mh_simulate(const mh_scenario *scenario, int64_t trials, int64_t seed, mh_counts *out,
                 char *error, size_t error_size);

typedef struct {
    double lower;
    double upper;
} mh_interval;

mh_interval mh_wilson95(int64_t successes, int64_t trials);

#endif
