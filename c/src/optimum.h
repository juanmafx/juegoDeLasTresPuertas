/* Exploration value curve V(K) = P(win) - c*K, its exact optimum and its least-squares parabola. */
#ifndef MH_OPTIMUM_H
#define MH_OPTIMUM_H

#include "model.h"

typedef struct {
    int reveals;
    mh_frac win;
    mh_frac value;
} mh_curve_point;

typedef struct {
    mh_frac a;
    mh_frac b;
    mh_frac c;
    mh_frac residual_sum_of_squares;
    bool has_vertex;
    mh_frac vertex_reveals;
    mh_frac vertex_value;
    int fitted_choice;
    int rounded_vertex;
} mh_parabola;

typedef struct {
    mh_strategy strategy;
    mh_frac cost;
    int count;
    mh_curve_point curve[MH_MAX_DOORS];
    int best;
    bool has_parabola;
    mh_parabola parabola;
} mh_optimum;

const char *mh_parabola_shape(const mh_parabola *parabola);
void mh_fit_parabola(const int *reveals, const mh_frac *values, int count, mh_frac *a, mh_frac *b,
                     mh_frac *c);
bool mh_optimum_curve(const mh_scenario *scenario, mh_strategy strategy, const mh_frac *cost,
                      mh_optimum *out, char *error, size_t error_size);

#endif
