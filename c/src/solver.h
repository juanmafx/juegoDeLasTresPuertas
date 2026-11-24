/* Exact solver: closed forms for unobserved games, full enumeration for observed reveals. */
#ifndef MH_SOLVER_H
#define MH_SOLVER_H

#include "model.h"

typedef struct {
    mh_frac prize_at_pick;
    mh_frac decision;
    mh_frac void_;
    mh_frac no_offer;
    bool has_observed;
    mh_frac observed;
    bool has_stay;
    mh_frac stay;
    bool has_switch;
    mh_frac switch_;
} mh_exact;

bool mh_prize_at_pick(const mh_scenario *scenario, mh_frac *out, char *error, size_t error_size);
void mh_closed_form(const mh_scenario *scenario, const mh_frac *pi, mh_exact *out);
bool mh_enumerate_observed(const mh_scenario *scenario, const mh_frac *pi, mh_exact *out,
                           char *error, size_t error_size);
bool mh_solve(const mh_scenario *scenario, mh_exact *out, char *error, size_t error_size);
bool mh_exact_win(const mh_exact *result, mh_strategy strategy, const mh_frac *q, mh_frac *out);
uint64_t mh_comb(int n, int k);

#endif
