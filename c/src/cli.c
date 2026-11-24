/* monty-lab command-line contract defined in spec/cli.md. */
#include "cli.h"

#include "json.h"
#include "model.h"
#include "optimum.h"
#include "prng.h"
#include "simulator.h"
#include "solver.h"

#include <errno.h>
#include <stdarg.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>

#define MH_MAX_PRNG_COUNT 100000
#define MH_MAX_SHUFFLE_SIZE 10000
#define MH_MAX_OPTIONS 12

typedef enum { CMD_EXACT, CMD_SIMULATE, CMD_OPTIMUM, CMD_PRNG } command_kind;

typedef struct {
    const char *name;
    const char *value;
} option;

typedef struct {
    command_kind kind;
    const char *command;
    size_t count;
    option options[MH_MAX_OPTIONS];
    char error[MH_ERROR_SIZE];
} invocation;

static const char *const scenario_flags[] = {"doors", "prizes", "prior", "pick",
                                             "host", "host-weights", "mixed"};

static const char usage_text[] =
    "usage: monty-lab {exact,simulate,optimum,prng} [options]\n"
    "\n"
    "Generalized Monty Hall decision lab (cross-language contract).\n"
    "\n"
    "  exact     [scenario flags] [--reveals K] [--observed D,...]\n"
    "  simulate  [scenario flags] [--reveals K] [--observed D,...] --seed S [--trials T]\n"
    "  optimum   [scenario flags] --strategy stay|switch|mixed [--cost C]\n"
    "  prng      --seed S --kind splitmix|words|bounded|weighted|shuffle\n"
    "            [--count C] [--bound B] [--weights W] [--size Z]\n"
    "\n"
    "scenario flags: --doors N --prizes M --prior uniform|W,... --pick D\n"
    "                --host informed|random|biased|adversarial --host-weights W,... --mixed Q\n";

static bool fail(invocation *inv, const char *format, ...) {
    va_list args;
    va_start(args, format);
    vsnprintf(inv->error, sizeof inv->error, format, args);
    va_end(args);
    return false;
}

static void add_name(invocation *inv, const char *name) {
    inv->options[inv->count].name = name;
    inv->options[inv->count].value = NULL;
    inv->count++;
}

static void declare_options(invocation *inv) {
    inv->count = 0;
    if (inv->kind == CMD_PRNG) {
        add_name(inv, "seed");
        add_name(inv, "kind");
        add_name(inv, "count");
        add_name(inv, "bound");
        add_name(inv, "weights");
        add_name(inv, "size");
        return;
    }
    for (size_t i = 0; i < sizeof scenario_flags / sizeof scenario_flags[0]; i++) {
        add_name(inv, scenario_flags[i]);
    }
    if (inv->kind == CMD_OPTIMUM) {
        add_name(inv, "strategy");
        add_name(inv, "cost");
        return;
    }
    add_name(inv, "reveals");
    add_name(inv, "observed");
    if (inv->kind == CMD_SIMULATE) {
        add_name(inv, "trials");
        add_name(inv, "seed");
    }
}

static option *find_option(invocation *inv, const char *name, size_t length, bool *ambiguous) {
    option *match = NULL;
    size_t matches = 0;
    *ambiguous = false;
    for (size_t i = 0; i < inv->count; i++) {
        const char *candidate = inv->options[i].name;
        if (strlen(candidate) == length && strncmp(candidate, name, length) == 0) {
            return &inv->options[i];
        }
        if (strncmp(candidate, name, length) == 0) {
            match = &inv->options[i];
            matches++;
        }
    }
    if (matches > 1) {
        *ambiguous = true;
        return NULL;
    }
    return match;
}

static const char *value_of(const invocation *inv, const char *name) {
    for (size_t i = 0; i < inv->count; i++) {
        if (strcmp(inv->options[i].name, name) == 0) {
            return inv->options[i].value;
        }
    }
    return NULL;
}

static bool parse_options(invocation *inv, int argc, char **argv, bool *help) {
    *help = false;
    for (int i = 2; i < argc; i++) {
        const char *arg = argv[i];
        if (strcmp(arg, "-h") == 0 || strcmp(arg, "--help") == 0) {
            *help = true;
            return true;
        }
        if (strncmp(arg, "--", 2) != 0 || arg[2] == '\0') {
            return fail(inv, "unrecognized arguments: %s", arg);
        }
        const char *name = arg + 2;
        const char *equals = strchr(name, '=');
        size_t length = equals == NULL ? strlen(name) : (size_t)(equals - name);
        bool ambiguous;
        option *target = find_option(inv, name, length, &ambiguous);
        if (ambiguous) {
            return fail(inv, "ambiguous option: %s", arg);
        }
        if (target == NULL) {
            return fail(inv, "unrecognized arguments: %s", arg);
        }
        if (equals != NULL) {
            target->value = equals + 1;
        } else if (i + 1 < argc && strncmp(argv[i + 1], "--", 2) != 0) {
            target->value = argv[++i];
        } else {
            return fail(inv, "argument --%s: expected one argument", target->name);
        }
    }
    return true;
}

static bool integer_flag(invocation *inv, const char *name, int64_t fallback, int64_t *out) {
    const char *text = value_of(inv, name);
    if (text == NULL) {
        *out = fallback;
        return true;
    }
    if (!mh_parse_i64(text, strlen(text), out)) {
        return fail(inv, "argument --%s: invalid int value: '%s'", name, text);
    }
    return true;
}

static bool is_blank(const char *text) {
    for (; *text != '\0'; text++) {
        if (*text != ' ' && *text != '\t' && *text != '\n' && *text != '\r' && *text != '\v' &&
            *text != '\f') {
            return false;
        }
    }
    return true;
}

static size_t list_length(const char *text) {
    if (is_blank(text)) {
        return 0;
    }
    size_t count = 1;
    for (; *text != '\0'; text++) {
        count += *text == ',' ? 1U : 0U;
    }
    return count;
}

static bool integer_list(invocation *inv, const char *text, int64_t *values, size_t capacity,
                         size_t *count) {
    *count = 0;
    if (is_blank(text)) {
        return true;
    }
    const char *start = text;
    for (;;) {
        const char *comma = strchr(start, ',');
        size_t length = comma == NULL ? strlen(start) : (size_t)(comma - start);
        int64_t value;
        if (!mh_parse_i64(start, length, &value)) {
            return fail(inv, "invalid integer list '%s'", text);
        }
        if (*count < capacity) {
            values[*count] = value;
        }
        (*count)++;
        if (comma == NULL) {
            break;
        }
        start = comma + 1;
    }
    if (*count > capacity) {
        *count = capacity;
    }
    return true;
}

static bool fraction_flag(invocation *inv, const char *text, mh_frac *out) {
    if (!mh_frac_parse(out, text)) {
        return fail(inv, "invalid fraction '%s'", text);
    }
    return true;
}

static bool build_scenario(invocation *inv, mh_scenario *scenario) {
    mh_scenario_input input;
    mh_scenario_input_default(&input);
    if (inv->kind == CMD_OPTIMUM) {
        input.reveals = 0;
    }
    const char *host = value_of(inv, "host");
    if (host != NULL && !mh_host_parse(host, &input.host)) {
        return fail(inv,
                    "argument --host: invalid choice: '%s' (choose from informed, random, "
                    "biased, adversarial)",
                    host);
    }
    if (!integer_flag(inv, "doors", 3, &input.doors) ||
        !integer_flag(inv, "prizes", 1, &input.prizes) ||
        !integer_flag(inv, "pick", 0, &input.pick)) {
        return false;
    }
    if (inv->kind != CMD_OPTIMUM && !integer_flag(inv, "reveals", 1, &input.reveals)) {
        return false;
    }
    const char *prior = value_of(inv, "prior");
    if (prior != NULL && strcmp(prior, "uniform") != 0) {
        input.has_prior = true;
        if (!integer_list(inv, prior, input.prior, MH_MAX_DOORS + 1, &input.prior_count)) {
            return false;
        }
    }
    const char *host_weights = value_of(inv, "host-weights");
    if (host_weights != NULL) {
        input.has_host_weights = true;
        if (!integer_list(inv, host_weights, input.host_weights, MH_MAX_DOORS + 1,
                          &input.host_weights_count)) {
            return false;
        }
    }
    const char *mixed = value_of(inv, "mixed");
    if (!fraction_flag(inv, mixed == NULL ? "1/2" : mixed, &input.mixed)) {
        return false;
    }
    const char *observed = inv->kind == CMD_OPTIMUM ? NULL : value_of(inv, "observed");
    if (observed != NULL) {
        input.has_observed = true;
        if (!integer_list(inv, observed, input.observed, MH_MAX_DOORS + 1,
                          &input.observed_count)) {
            return false;
        }
    }
    if (!mh_scenario_build(&input, scenario, inv->error, sizeof inv->error)) {
        return false;
    }
    return true;
}

static void write_int_list(mh_json *w, const uint32_t *values, int count) {
    mh_json_begin_array(w);
    for (int i = 0; i < count; i++) {
        mh_json_int(w, values[i]);
    }
    mh_json_end_array(w);
}

static void write_scenario(mh_json *w, const mh_scenario *s, bool reveals_null) {
    mh_json_key(w, "scenario");
    mh_json_begin_object(w);
    mh_json_key(w, "doors");
    mh_json_int(w, s->doors);
    mh_json_key(w, "prizes");
    mh_json_int(w, s->prizes);
    mh_json_key(w, "prior");
    if (s->has_prior) {
        write_int_list(w, s->prior, s->doors);
    } else {
        mh_json_string(w, "uniform");
    }
    mh_json_key(w, "pick");
    mh_json_int(w, s->pick);
    mh_json_key(w, "reveals");
    if (reveals_null) {
        mh_json_null(w);
    } else {
        mh_json_int(w, s->reveals);
    }
    mh_json_key(w, "host");
    mh_json_string(w, mh_host_name(s->host));
    mh_json_key(w, "host_weights");
    if (s->has_host_weights) {
        write_int_list(w, s->host_weights, s->doors);
    } else {
        mh_json_null(w);
    }
    mh_json_key(w, "mixed");
    mh_json_frac(w, &s->mixed);
    mh_json_key(w, "observed");
    if (s->has_observed) {
        mh_json_begin_array(w);
        for (int i = 0; i < s->observed_count; i++) {
            mh_json_int(w, s->observed[i]);
        }
        mh_json_end_array(w);
    } else {
        mh_json_null(w);
    }
    mh_json_end_object(w);
}

static void optional_frac(mh_json *w, const char *key, bool present, const mh_frac *value) {
    mh_json_key(w, key);
    if (present) {
        mh_json_frac(w, value);
    } else {
        mh_json_null(w);
    }
}

static bool run_exact(invocation *inv, mh_json *w) {
    mh_scenario scenario;
    mh_exact result;
    mh_frac mixed;
    if (!build_scenario(inv, &scenario) ||
        !mh_solve(&scenario, &result, inv->error, sizeof inv->error)) {
        return false;
    }
    bool has_mixed = mh_exact_win(&result, MH_MIXED, &scenario.mixed, &mixed);
    mh_json_begin_object(w);
    mh_json_key(w, "command");
    mh_json_string(w, "exact");
    write_scenario(w, &scenario, false);
    mh_json_key(w, "prize_at_pick");
    mh_json_frac(w, &result.prize_at_pick);
    mh_json_key(w, "outcomes");
    mh_json_begin_object(w);
    optional_frac(w, "decision", true, &result.decision);
    optional_frac(w, "void", true, &result.void_);
    optional_frac(w, "no_offer", true, &result.no_offer);
    optional_frac(w, "observed", result.has_observed, &result.observed);
    mh_json_end_object(w);
    mh_json_key(w, "win");
    mh_json_begin_object(w);
    optional_frac(w, "stay", result.has_stay, &result.stay);
    optional_frac(w, "switch", result.has_switch, &result.switch_);
    optional_frac(w, "mixed", has_mixed, &mixed);
    mh_json_end_object(w);
    mh_json_end_object(w);
    return true;
}

static void strategy_summary(mh_json *w, const char *name, int64_t wins, int64_t sample) {
    mh_json_key(w, name);
    mh_json_begin_object(w);
    mh_json_key(w, "wins");
    mh_json_int(w, wins);
    mh_json_key(w, "rate");
    if (sample == 0) {
        mh_json_null(w);
        mh_json_key(w, "wilson95");
        mh_json_null(w);
    } else {
        mh_interval interval = mh_wilson95(wins, sample);
        mh_json_double(w, (double)wins / (double)sample);
        mh_json_key(w, "wilson95");
        mh_json_begin_array(w);
        mh_json_double(w, interval.lower);
        mh_json_double(w, interval.upper);
        mh_json_end_array(w);
    }
    mh_json_end_object(w);
}

static bool run_simulate(invocation *inv, mh_json *w) {
    mh_scenario scenario;
    mh_counts counts;
    int64_t trials;
    int64_t seed;
    if (!build_scenario(inv, &scenario)) {
        return false;
    }
    if (!integer_flag(inv, "trials", 100000, &trials)) {
        return false;
    }
    if (value_of(inv, "seed") == NULL) {
        return fail(inv, "the following arguments are required: --seed");
    }
    if (!integer_flag(inv, "seed", 0, &seed)) {
        return false;
    }
    if (!mh_simulate(&scenario, trials, seed, &counts, inv->error, sizeof inv->error)) {
        return false;
    }
    int64_t sample = mh_sample_size(&counts);
    mh_json_begin_object(w);
    mh_json_key(w, "command");
    mh_json_string(w, "simulate");
    write_scenario(w, &scenario, false);
    mh_json_key(w, "seed");
    mh_json_int(w, seed);
    mh_json_key(w, "trials");
    mh_json_int(w, trials);
    mh_json_key(w, "counts");
    mh_json_begin_object(w);
    mh_json_key(w, "decision");
    mh_json_int(w, counts.decision);
    mh_json_key(w, "void");
    mh_json_int(w, counts.void_);
    mh_json_key(w, "no_offer");
    mh_json_int(w, counts.no_offer);
    mh_json_key(w, "observed");
    if (counts.has_observed) {
        mh_json_int(w, counts.observed);
    } else {
        mh_json_null(w);
    }
    mh_json_end_object(w);
    mh_json_key(w, "sample_size");
    mh_json_int(w, sample);
    mh_json_key(w, "strategies");
    mh_json_begin_object(w);
    strategy_summary(w, "stay", counts.stay_wins, sample);
    strategy_summary(w, "switch", counts.switch_wins, sample);
    strategy_summary(w, "mixed", counts.mixed_wins, sample);
    mh_json_end_object(w);
    mh_json_end_object(w);
    return true;
}

static void write_choice(mh_json *w, const char *key, const mh_optimum *result, int reveals) {
    mh_frac regret;
    const mh_frac *value = &result->curve[reveals].value;
    mh_frac_sub(&regret, &result->curve[result->best].value, value);
    mh_json_key(w, key);
    mh_json_begin_object(w);
    mh_json_key(w, "reveals");
    mh_json_int(w, reveals);
    mh_json_key(w, "value");
    mh_json_frac(w, value);
    mh_json_key(w, "regret");
    mh_json_frac(w, &regret);
    mh_json_end_object(w);
}

static void write_parabola(mh_json *w, const mh_optimum *result) {
    const mh_parabola *p = &result->parabola;
    const mh_curve_point *best = &result->curve[result->best];
    mh_json_key(w, "parabola");
    if (!result->has_parabola) {
        mh_json_null(w);
        return;
    }
    mh_json_begin_object(w);
    optional_frac(w, "a", true, &p->a);
    optional_frac(w, "b", true, &p->b);
    optional_frac(w, "c", true, &p->c);
    mh_json_key(w, "shape");
    mh_json_string(w, mh_parabola_shape(p));
    optional_frac(w, "residual_sum_of_squares", true, &p->residual_sum_of_squares);
    if (p->has_vertex) {
        mh_frac best_reveals;
        mh_frac offset;
        mh_frac gap;
        mh_frac_set_i64(&best_reveals, best->reveals, 1);
        mh_frac_sub(&offset, &p->vertex_reveals, &best_reveals);
        mh_frac_sub(&gap, &p->vertex_value, &best->value);
        mh_json_key(w, "vertex");
        mh_json_begin_object(w);
        optional_frac(w, "reveals", true, &p->vertex_reveals);
        optional_frac(w, "value", true, &p->vertex_value);
        mh_json_end_object(w);
        optional_frac(w, "vertex_offset", true, &offset);
        optional_frac(w, "vertex_value_gap", true, &gap);
        write_choice(w, "rounded_vertex", result, p->rounded_vertex);
    } else {
        mh_json_key(w, "vertex");
        mh_json_null(w);
        mh_json_key(w, "vertex_offset");
        mh_json_null(w);
        mh_json_key(w, "vertex_value_gap");
        mh_json_null(w);
        mh_json_key(w, "rounded_vertex");
        mh_json_null(w);
    }
    write_choice(w, "fitted_choice", result, p->fitted_choice);
    mh_json_end_object(w);
}

static bool run_optimum(invocation *inv, mh_json *w) {
    mh_scenario scenario;
    mh_strategy strategy;
    mh_frac cost;
    if (!build_scenario(inv, &scenario)) {
        return false;
    }
    const char *strategy_text = value_of(inv, "strategy");
    if (strategy_text == NULL) {
        return fail(inv, "the following arguments are required: --strategy");
    }
    if (!mh_strategy_parse(strategy_text, &strategy)) {
        return fail(inv,
                    "argument --strategy: invalid choice: '%s' (choose from stay, switch, mixed)",
                    strategy_text);
    }
    const char *cost_text = value_of(inv, "cost");
    if (!fraction_flag(inv, cost_text == NULL ? "0" : cost_text, &cost)) {
        return false;
    }
    mh_optimum *result = malloc(sizeof *result);
    if (result == NULL) {
        return fail(inv, "out of memory");
    }
    if (!mh_optimum_curve(&scenario, strategy, &cost, result, inv->error, sizeof inv->error)) {
        free(result);
        return false;
    }
    mh_json_begin_object(w);
    mh_json_key(w, "command");
    mh_json_string(w, "optimum");
    write_scenario(w, &scenario, true);
    mh_json_key(w, "strategy");
    mh_json_string(w, mh_strategy_name(strategy));
    optional_frac(w, "cost", true, &result->cost);
    mh_json_key(w, "curve");
    mh_json_begin_array(w);
    for (int k = 0; k < result->count; k++) {
        mh_json_begin_object(w);
        mh_json_key(w, "reveals");
        mh_json_int(w, result->curve[k].reveals);
        optional_frac(w, "win", true, &result->curve[k].win);
        optional_frac(w, "value", true, &result->curve[k].value);
        mh_json_end_object(w);
    }
    mh_json_end_array(w);
    mh_json_key(w, "optimum");
    mh_json_begin_object(w);
    mh_json_key(w, "reveals");
    mh_json_int(w, result->curve[result->best].reveals);
    optional_frac(w, "value", true, &result->curve[result->best].value);
    mh_json_end_object(w);
    write_parabola(w, result);
    mh_json_end_object(w);
    free(result);
    return true;
}

static bool prng_weights(invocation *inv, const char *text, uint64_t **weights, size_t *count,
                         uint64_t *total) {
    size_t capacity = list_length(text);
    int64_t *values = malloc((capacity == 0 ? 1 : capacity) * sizeof *values);
    if (values == NULL) {
        return fail(inv, "out of memory");
    }
    if (!integer_list(inv, text, values, capacity, count)) {
        free(values);
        return false;
    }
    *total = 0;
    bool valid = *count > 0;
    for (size_t i = 0; valid && i < *count; i++) {
        if (values[i] < 0) {
            valid = false;
        } else if ((uint64_t)values[i] > (uint64_t)MH_MAX_SEED - *total) {
            free(values);
            return fail(inv, "weights must sum to at most %lld", (long long)MH_MAX_SEED);
        } else {
            *total += (uint64_t)values[i];
        }
    }
    if (!valid || *total == 0) {
        free(values);
        return fail(inv, "weights must be non-negative integers with a positive total");
    }
    *weights = malloc(*count * sizeof **weights);
    if (*weights == NULL) {
        free(values);
        return fail(inv, "out of memory");
    }
    for (size_t i = 0; i < *count; i++) {
        (*weights)[i] = (uint64_t)values[i];
    }
    free(values);
    return true;
}

static bool run_prng(invocation *inv, mh_json *w) {
    int64_t seed;
    int64_t count;
    const char *kind = value_of(inv, "kind");
    if (value_of(inv, "seed") == NULL || kind == NULL) {
        return fail(inv, "the following arguments are required: --seed, --kind");
    }
    if (strcmp(kind, "splitmix") != 0 && strcmp(kind, "words") != 0 &&
        strcmp(kind, "bounded") != 0 && strcmp(kind, "weighted") != 0 &&
        strcmp(kind, "shuffle") != 0) {
        return fail(inv,
                    "argument --kind: invalid choice: '%s' (choose from splitmix, words, "
                    "bounded, weighted, shuffle)",
                    kind);
    }
    if (!integer_flag(inv, "seed", 0, &seed) || !integer_flag(inv, "count", 1, &count)) {
        return false;
    }
    int64_t bound = 0;
    int64_t size = 0;
    if (!integer_flag(inv, "bound", 0, &bound) || !integer_flag(inv, "size", 0, &size)) {
        return false;
    }
    if (seed < 0) {
        return fail(inv, "seed must be between 0 and %lld", (long long)MH_MAX_SEED);
    }
    if (count < 1 || count > MH_MAX_PRNG_COUNT) {
        return fail(inv, "count must be between 1 and %d", MH_MAX_PRNG_COUNT);
    }
    mh_rng rng;
    mh_rng_init(&rng, (uint64_t)seed);
    if (strcmp(kind, "bounded") == 0 && (value_of(inv, "bound") == NULL || bound < 1)) {
        return fail(inv, "bound must be between 1 and %lld", (long long)MH_MAX_SEED);
    }
    if (strcmp(kind, "shuffle") == 0 &&
        (value_of(inv, "size") == NULL || size < 1 || size > MH_MAX_SHUFFLE_SIZE)) {
        return fail(inv, "size must be between 1 and %d", MH_MAX_SHUFFLE_SIZE);
    }
    uint64_t *weights = NULL;
    size_t weight_count = 0;
    uint64_t total = 0;
    if (strcmp(kind, "weighted") == 0) {
        const char *text = value_of(inv, "weights");
        if (!prng_weights(inv, text == NULL ? "" : text, &weights, &weight_count, &total)) {
            return false;
        }
    }
    mh_json_begin_object(w);
    mh_json_key(w, "command");
    mh_json_string(w, "prng");
    mh_json_key(w, "seed");
    mh_json_int(w, seed);
    mh_json_key(w, "kind");
    mh_json_string(w, kind);
    if (strcmp(kind, "splitmix") == 0) {
        mh_splitmix expander;
        mh_splitmix_init(&expander, (uint64_t)seed);
        mh_json_key(w, "values");
        mh_json_begin_array(w);
        for (int64_t i = 0; i < count; i++) {
            char text[24];
            snprintf(text, sizeof text, "%llu", (unsigned long long)mh_splitmix_next(&expander));
            mh_json_string(w, text);
        }
        mh_json_end_array(w);
    } else if (strcmp(kind, "words") == 0) {
        mh_json_key(w, "values");
        mh_json_begin_array(w);
        for (int64_t i = 0; i < count; i++) {
            char text[24];
            snprintf(text, sizeof text, "%llu", (unsigned long long)mh_rng_next(&rng));
            mh_json_string(w, text);
        }
        mh_json_end_array(w);
    } else if (strcmp(kind, "bounded") == 0) {
        mh_json_key(w, "bound");
        mh_json_int(w, bound);
        mh_json_key(w, "values");
        mh_json_begin_array(w);
        for (int64_t i = 0; i < count; i++) {
            mh_json_uint(w, mh_rng_bounded(&rng, (uint64_t)bound));
        }
        mh_json_end_array(w);
    } else if (strcmp(kind, "weighted") == 0) {
        mh_json_key(w, "weights");
        mh_json_begin_array(w);
        for (size_t i = 0; i < weight_count; i++) {
            mh_json_uint(w, weights[i]);
        }
        mh_json_end_array(w);
        mh_json_key(w, "values");
        mh_json_begin_array(w);
        for (int64_t i = 0; i < count; i++) {
            mh_json_uint(w, mh_rng_weighted_index(&rng, weights, weight_count, total));
        }
        mh_json_end_array(w);
    } else {
        uint64_t *items = malloc((size_t)size * sizeof *items);
        if (items == NULL) {
            return fail(inv, "out of memory");
        }
        for (int64_t i = 0; i < size; i++) {
            items[i] = (uint64_t)i;
        }
        mh_rng_shuffle(&rng, items, (size_t)size);
        mh_json_key(w, "size");
        mh_json_int(w, size);
        mh_json_key(w, "values");
        mh_json_begin_array(w);
        for (int64_t i = 0; i < size; i++) {
            mh_json_uint(w, items[i]);
        }
        mh_json_end_array(w);
        free(items);
    }
    mh_json_end_object(w);
    free(weights);
    return true;
}

static bool select_command(invocation *inv, const char *name) {
    static const char *const names[] = {"exact", "simulate", "optimum", "prng"};
    for (int i = 0; i < 4; i++) {
        if (strcmp(name, names[i]) == 0) {
            inv->kind = (command_kind)i;
            inv->command = names[i];
            return true;
        }
    }
    return fail(inv, "argument command: invalid choice: '%s' (choose from exact, simulate, "
                     "optimum, prng)",
                name);
}

static int usage_error(FILE *err, const char *message) {
    fputs("usage: monty-lab {exact,simulate,optimum,prng} [options]\n", err);
    fprintf(err, "error: %s\n", message);
    return MH_EXIT_USAGE;
}

static int emit(FILE *out, const char *buffer, size_t length) {
    if (length > 0 && fwrite(buffer, 1, length, out) != length) {
        return errno == EPIPE ? MH_EXIT_BROKEN_PIPE : 1;
    }
    if (fflush(out) != 0) {
        return errno == EPIPE ? MH_EXIT_BROKEN_PIPE : 1;
    }
    return MH_EXIT_OK;
}

int mh_cli_main(int argc, char **argv, FILE *out, FILE *err) {
    invocation inv;
    memset(&inv, 0, sizeof inv);
    mh_arith_reset();
    if (argc < 2) {
        return usage_error(err, "the following arguments are required: command");
    }
    if (strcmp(argv[1], "-h") == 0 || strcmp(argv[1], "--help") == 0) {
        return emit(out, usage_text, strlen(usage_text));
    }
    if (strcmp(argv[1], "--version") == 0) {
        static const char version[] = "monty-lab " MH_VERSION "\n";
        return emit(out, version, strlen(version));
    }
    if (!select_command(&inv, argv[1])) {
        return usage_error(err, inv.error);
    }
    declare_options(&inv);
    bool help;
    if (!parse_options(&inv, argc, argv, &help)) {
        return usage_error(err, inv.error);
    }
    if (help) {
        return emit(out, usage_text, strlen(usage_text));
    }
    char *buffer = NULL;
    size_t length = 0;
    FILE *memory = open_memstream(&buffer, &length);
    if (memory == NULL) {
        fprintf(err, "error: out of memory\n");
        return 1;
    }
    mh_json w;
    mh_json_init(&w, memory);
    bool ok;
    switch (inv.kind) {
    case CMD_EXACT:
        ok = run_exact(&inv, &w);
        break;
    case CMD_SIMULATE:
        ok = run_simulate(&inv, &w);
        break;
    case CMD_OPTIMUM:
        ok = run_optimum(&inv, &w);
        break;
    default:
        ok = run_prng(&inv, &w);
        break;
    }
    if (ok) {
        mh_json_finish(&w);
    }
    bool stream_failed = fclose(memory) != 0;
    if (ok && mh_arith_failed()) {
        ok = false;
        snprintf(inv.error, sizeof inv.error,
                 "exact arithmetic exceeds the %d-bit integer capacity", MH_BIG_BITS);
    }
    if (ok && stream_failed) {
        ok = false;
        snprintf(inv.error, sizeof inv.error, "out of memory");
    }
    if (!ok) {
        free(buffer);
        fprintf(err, "error: %s\n", inv.error);
        return MH_EXIT_USAGE;
    }
    int code = emit(out, buffer, length);
    free(buffer);
    return code;
}
