/* Exploration value curve V(K) = P(win) - c*K, its exact optimum and its least-squares parabola. */
#include "optimum.h"

#include "solver.h"

#include <stdio.h>
#include <string.h>

const char *mh_parabola_shape(const mh_parabola *parabola) {
    int sign = mh_frac_sign(&parabola->a);
    if (sign < 0) {
        return "concave";
    }
    return sign > 0 ? "convex" : "linear";
}

static void determinant(const mh_frac m[3][3], mh_frac *out) {
    mh_frac x;
    mh_frac y;
    mh_frac minor;
    mh_frac term;
    mh_frac_set_i64(out, 0, 1);
    for (int column = 0; column < 3; column++) {
        int left = column == 0 ? 1 : 0;
        int right = column == 2 ? 1 : 2;
        mh_frac_mul(&x, &m[1][left], &m[2][right]);
        mh_frac_mul(&y, &m[1][right], &m[2][left]);
        mh_frac_sub(&minor, &x, &y);
        mh_frac_mul(&term, &m[0][column], &minor);
        if (column == 1) {
            mh_frac_sub(out, out, &term);
        } else {
            mh_frac_add(out, out, &term);
        }
    }
}

void mh_fit_parabola(const int *reveals, const mh_frac *values, int count, mh_frac *a, mh_frac *b,
                     mh_frac *c) {
    mh_frac s[5];
    mh_frac t[3];
    for (int power = 0; power < 5; power++) {
        int64_t sum = 0;
        for (int i = 0; i < count; i++) {
            int64_t term = 1;
            for (int e = 0; e < power; e++) {
                term *= reveals[i];
            }
            sum += term;
        }
        mh_frac_set_i64(&s[power], sum, 1);
    }
    for (int power = 0; power < 3; power++) {
        mh_frac_set_i64(&t[power], 0, 1);
        for (int i = 0; i < count; i++) {
            int64_t factor = 1;
            for (int e = 0; e < power; e++) {
                factor *= reveals[i];
            }
            mh_frac scale;
            mh_frac term;
            mh_frac_set_i64(&scale, factor, 1);
            mh_frac_mul(&term, &values[i], &scale);
            mh_frac_add(&t[power], &t[power], &term);
        }
    }
    mh_frac matrix[3][3] = {{s[4], s[3], s[2]}, {s[3], s[2], s[1]}, {s[2], s[1], s[0]}};
    mh_frac rhs[3] = {t[2], t[1], t[0]};
    mh_frac base;
    mh_frac coefficients[3];
    determinant((const mh_frac(*)[3])matrix, &base);
    for (int column = 0; column < 3; column++) {
        mh_frac replaced[3][3];
        mh_frac numerator;
        memcpy(replaced, matrix, sizeof replaced);
        for (int row = 0; row < 3; row++) {
            replaced[row][column] = rhs[row];
        }
        determinant((const mh_frac(*)[3])replaced, &numerator);
        mh_frac_div(&coefficients[column], &numerator, &base);
    }
    *a = coefficients[0];
    *b = coefficients[1];
    *c = coefficients[2];
}

static void evaluate(const mh_parabola *p, const mh_frac *k, mh_frac *out) {
    mh_frac square;
    mh_frac term;
    mh_frac_mul(&square, k, k);
    mh_frac_mul(out, &p->a, &square);
    mh_frac_mul(&term, &p->b, k);
    mh_frac_add(out, out, &term);
    mh_frac_add(out, out, &p->c);
}

static void build_parabola(mh_optimum *result) {
    int count = result->count;
    int reveals[MH_MAX_DOORS];
    mh_frac values[MH_MAX_DOORS];
    mh_parabola *p = &result->parabola;
    for (int i = 0; i < count; i++) {
        reveals[i] = result->curve[i].reveals;
        values[i] = result->curve[i].value;
    }
    mh_fit_parabola(reveals, values, count, &p->a, &p->b, &p->c);
    mh_frac_set_i64(&p->residual_sum_of_squares, 0, 1);
    mh_frac best_fitted;
    p->fitted_choice = 0;
    for (int i = 0; i < count; i++) {
        mh_frac k;
        mh_frac fitted;
        mh_frac error;
        mh_frac square;
        mh_frac_set_i64(&k, reveals[i], 1);
        evaluate(p, &k, &fitted);
        mh_frac_sub(&error, &fitted, &values[i]);
        mh_frac_mul(&square, &error, &error);
        mh_frac_add(&p->residual_sum_of_squares, &p->residual_sum_of_squares, &square);
        if (i == 0 || mh_frac_cmp(&fitted, &best_fitted) > 0) {
            best_fitted = fitted;
            p->fitted_choice = reveals[i];
        }
    }
    p->has_vertex = !mh_frac_is_zero(&p->a);
    p->rounded_vertex = 0;
    if (!p->has_vertex) {
        return;
    }
    mh_frac two_a;
    mh_frac four_a;
    mh_frac two;
    mh_frac four;
    mh_frac negated_b;
    mh_frac b_squared;
    mh_frac quotient;
    mh_frac_set_i64(&two, 2, 1);
    mh_frac_set_i64(&four, 4, 1);
    mh_frac_mul(&two_a, &two, &p->a);
    mh_frac_mul(&four_a, &four, &p->a);
    mh_frac_neg(&negated_b, &p->b);
    mh_frac_div(&p->vertex_reveals, &negated_b, &two_a);
    mh_frac_mul(&b_squared, &p->b, &p->b);
    mh_frac_div(&quotient, &b_squared, &four_a);
    mh_frac_sub(&p->vertex_value, &p->c, &quotient);
    mh_frac half;
    mh_frac shifted;
    mh_frac rounded;
    mh_frac zero;
    mh_frac highest;
    int last = result->curve[count - 1].reveals;
    mh_frac_set_i64(&half, 1, 2);
    mh_frac_set_i64(&zero, 0, 1);
    mh_frac_set_i64(&highest, last, 1);
    mh_frac_add(&shifted, &p->vertex_reveals, &half);
    mh_frac_floor(&rounded, &shifted);
    if (mh_frac_cmp(&rounded, &zero) <= 0) {
        p->rounded_vertex = 0;
    } else if (mh_frac_cmp(&rounded, &highest) >= 0) {
        p->rounded_vertex = last;
    } else {
        uint64_t value = 0;
        mh_big_to_u64(&rounded.num, &value);
        p->rounded_vertex = (int)value;
    }
}

bool mh_optimum_curve(const mh_scenario *scenario, mh_strategy strategy, const mh_frac *cost,
                      mh_optimum *out, char *error, size_t error_size) {
    if (scenario->has_observed) {
        snprintf(error, error_size, "optimum does not accept an observed reveal");
        return false;
    }
    if (mh_frac_sign(cost) < 0) {
        snprintf(error, error_size, "cost must be a non-negative fraction");
        return false;
    }
    mh_frac pi;
    if (!mh_prize_at_pick(scenario, &pi, error, error_size)) {
        return false;
    }
    memset(out, 0, sizeof *out);
    out->strategy = strategy;
    out->cost = *cost;
    out->count = mh_max_reveals(scenario) + 1;
    for (int k = 0; k < out->count; k++) {
        mh_scenario step = *scenario;
        mh_exact exact;
        mh_frac reveals;
        mh_frac charge;
        step.reveals = k;
        step.has_observed = false;
        step.observed_count = 0;
        mh_closed_form(&step, &pi, &exact);
        mh_curve_point *point = &out->curve[k];
        point->reveals = k;
        if (!mh_exact_win(&exact, strategy, &scenario->mixed, &point->win)) {
            snprintf(error, error_size,
                     "optimum is undefined when the host never offers a decision");
            return false;
        }
        mh_frac_set_i64(&reveals, k, 1);
        mh_frac_mul(&charge, cost, &reveals);
        mh_frac_sub(&point->value, &point->win, &charge);
    }
    out->best = 0;
    for (int k = 1; k < out->count; k++) {
        if (mh_frac_cmp(&out->curve[k].value, &out->curve[out->best].value) > 0) {
            out->best = k;
        }
    }
    out->has_parabola = out->count >= 3;
    if (out->has_parabola) {
        build_parabola(out);
    }
    return true;
}
