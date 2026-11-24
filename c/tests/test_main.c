/* Self-contained unit tests for the C monty-lab implementation; golden values come from spec/. */
#include "cli.h"
#include "json.h"
#include "model.h"
#include "optimum.h"
#include "prng.h"
#include "rational.h"
#include "simulator.h"
#include "solver.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int tests_run = 0;
static int tests_failed = 0;
static int checks_failed_in_test = 0;

#define CHECK(condition)                                                                       \
    do {                                                                                       \
        if (!(condition)) {                                                                    \
            fprintf(stderr, "  check failed at %s:%d: %s\n", __FILE__, __LINE__, #condition);  \
            checks_failed_in_test++;                                                           \
        }                                                                                      \
    } while (0)

#define CHECK_FRAC(value, expected) check_frac(&(value), expected, __FILE__, __LINE__)

static void check_frac(const mh_frac *value, const char *expected, const char *file, int line) {
    char text[MH_FRAC_TEXT];
    const char *got = mh_frac_format(value, text, sizeof text);
    if (got == NULL || strcmp(got, expected) != 0) {
        fprintf(stderr, "  check failed at %s:%d: got %s, expected %s\n", file, line,
                got == NULL ? "(unformattable)" : got, expected);
        checks_failed_in_test++;
    }
}

static void run_test(const char *name, void (*test)(void)) {
    checks_failed_in_test = 0;
    mh_arith_reset();
    test();
    tests_run++;
    if (checks_failed_in_test > 0) {
        tests_failed++;
        printf("FAIL %s\n", name);
    } else {
        printf("PASS %s\n", name);
    }
}

static mh_frac frac(const char *text) {
    mh_frac value;
    if (!mh_frac_parse(&value, text)) {
        fprintf(stderr, "  invalid fraction literal %s\n", text);
        checks_failed_in_test++;
        mh_frac_set_i64(&value, 0, 1);
    }
    return value;
}

static void test_fraction_parse_and_format(void) {
    mh_frac value;
    CHECK(mh_frac_parse(&value, "6/8"));
    CHECK_FRAC(value, "3/4");
    CHECK(mh_frac_parse(&value, "-3/-4"));
    CHECK_FRAC(value, "3/4");
    CHECK(mh_frac_parse(&value, "3/-20"));
    CHECK_FRAC(value, "-3/20");
    CHECK(mh_frac_parse(&value, "-0/5"));
    CHECK_FRAC(value, "0/1");
    CHECK(mh_frac_parse(&value, " 7 "));
    CHECK_FRAC(value, "7/1");
    CHECK(mh_frac_parse(&value, "1_000/10"));
    CHECK_FRAC(value, "100/1");
    CHECK(!mh_frac_parse(&value, "1/0"));
    CHECK(!mh_frac_parse(&value, ""));
    CHECK(!mh_frac_parse(&value, "1/"));
    CHECK(!mh_frac_parse(&value, "a/2"));
    CHECK(!mh_frac_parse(&value, "_1"));
    CHECK(!mh_frac_parse(&value, "1_"));
    CHECK(!mh_frac_parse(&value, "1__0"));
    CHECK(!mh_frac_parse(&value, "1.5"));
}

static void test_fraction_arithmetic(void) {
    mh_frac a = frac("1/3");
    mh_frac b = frac("1/6");
    mh_frac r;
    mh_frac_add(&r, &a, &b);
    CHECK_FRAC(r, "1/2");
    mh_frac_sub(&r, &b, &a);
    CHECK_FRAC(r, "-1/6");
    mh_frac_mul(&r, &a, &b);
    CHECK_FRAC(r, "1/18");
    mh_frac_div(&r, &a, &b);
    CHECK_FRAC(r, "2/1");
    mh_frac_neg(&r, &a);
    CHECK_FRAC(r, "-1/3");
    CHECK(mh_frac_cmp(&a, &b) > 0);
    CHECK(mh_frac_cmp(&b, &a) < 0);
    CHECK(mh_frac_cmp(&a, &a) == 0);
    mh_frac_sub(&r, &a, &a);
    CHECK(mh_frac_is_zero(&r));
    CHECK(mh_frac_sign(&r) == 0);
    CHECK(!mh_arith_failed());
}

static void test_fraction_floor(void) {
    mh_frac r;
    mh_frac x = frac("7/2");
    mh_frac_floor(&r, &x);
    CHECK_FRAC(r, "3/1");
    x = frac("-7/2");
    mh_frac_floor(&r, &x);
    CHECK_FRAC(r, "-4/1");
    x = frac("-4");
    mh_frac_floor(&r, &x);
    CHECK_FRAC(r, "-4/1");
    x = frac("1/3");
    mh_frac_floor(&r, &x);
    CHECK_FRAC(r, "0/1");
}

static void test_big_integers_beyond_64_bits(void) {
    mh_frac big = frac("340282366920938463463374607431768211456/3");
    mh_frac r;
    mh_frac_mul(&r, &big, &big);
    CHECK_FRAC(r, "115792089237316195423570985008687907853269984665640564039457584007913129639936/9");
    mh_frac_div(&r, &r, &big);
    CHECK_FRAC(r, "340282366920938463463374607431768211456/3");
    mh_big a;
    mh_big b;
    mh_big g;
    CHECK(mh_big_parse(&a, "123456789012345678901234567890", 30));
    CHECK(mh_big_parse(&b, "987654321098765432109876543210", 30));
    mh_big_gcd(&g, &a, &b);
    char text[64];
    CHECK(mh_big_format(&g, text, sizeof text) > 0);
    CHECK(strcmp(text, "9000000000900000000090") == 0);
    mh_big q;
    mh_big rem;
    mh_big_divmod(&q, &rem, &b, &a);
    CHECK(mh_big_format(&q, text, sizeof text) > 0);
    CHECK(strcmp(text, "8") == 0);
    CHECK(mh_big_format(&rem, text, sizeof text) > 0);
    CHECK(strcmp(text, "9000000000900000000090") == 0);
    mh_big_set_u64(&a, 10000000000000000000ULL);
    CHECK(mh_big_format(&a, text, sizeof text) > 0);
    CHECK(strcmp(text, "10000000000000000000") == 0);
    CHECK(!mh_arith_failed());
}

static void test_overflow_is_detected(void) {
    mh_big one;
    mh_big wide;
    mh_big product;
    mh_big_set_u64(&one, 1);
    mh_big_shl(&wide, &one, MH_BIG_BITS - 1);
    CHECK(!mh_arith_failed());
    CHECK(mh_big_bits(&wide) == MH_BIG_BITS);
    mh_big_mul(&product, &wide, &wide);
    CHECK(mh_arith_failed());
    CHECK(mh_big_is_zero(&product));
    mh_arith_reset();
    mh_big_add(&product, &wide, &wide);
    CHECK(mh_arith_failed());
    mh_arith_reset();
    mh_big_shl(&product, &one, MH_BIG_BITS);
    CHECK(mh_arith_failed());
    mh_arith_reset();
    mh_big_sub(&product, &one, &wide);
    CHECK(mh_arith_failed());
    mh_arith_reset();
    char digits[1300];
    memset(digits, '9', sizeof digits);
    CHECK(!mh_big_parse(&product, digits, sizeof digits));
    CHECK(!mh_arith_failed());
}

static void test_parse_i64_bounds(void) {
    int64_t value;
    CHECK(mh_parse_i64("9223372036854775807", 19, &value) && value == INT64_MAX);
    CHECK(mh_parse_i64("-9223372036854775808", 20, &value) && value == INT64_MIN);
    CHECK(!mh_parse_i64("9223372036854775808", 19, &value));
    CHECK(mh_parse_i64(" +12 ", 5, &value) && value == 12);
    CHECK(!mh_parse_i64("", 0, &value));
    CHECK(!mh_parse_i64("1 2", 3, &value));
}

static void test_splitmix_and_words(void) {
    mh_splitmix expander;
    mh_splitmix_init(&expander, 0);
    CHECK(mh_splitmix_next(&expander) == 16294208416658607535ULL);
    CHECK(mh_splitmix_next(&expander) == 7960286522194355700ULL);
    static const uint64_t words[] = {11091344671253066420ULL, 13793997310169335082ULL,
                                     1900383378846508768ULL,  7684712102626143532ULL,
                                     13521403990117723737ULL, 18442103541295991498ULL,
                                     7788427924976520344ULL,  9881088229871127103ULL};
    mh_rng rng;
    mh_rng_init(&rng, 0);
    for (size_t i = 0; i < sizeof words / sizeof words[0]; i++) {
        CHECK(mh_rng_next(&rng) == words[i]);
    }
}

static void test_bounded_vectors(void) {
    static const uint64_t bound_two_seed_zero[] = {1, 1, 0, 0, 1, 1, 0, 1};
    static const uint64_t bound_million_seed_one[] = {702923, 520438, 574107, 391329,
                                                      697180, 143572, 71045,  381185};
    static const uint64_t bound_max_seed_one[] = {
        6483309580052039777ULL, 4800180567299270260ULL, 5295190459760845449ULL,
        3609369285294772691ULL, 6430335911997840184ULL, 1324218308982920080ULL,
        655276459245078642ULL,  3515805966490203214ULL};
    static const uint64_t bound_half_seed_one[] = {
        3241654790026019889ULL, 2647595229880422725ULL, 3215167955998920093ULL,
        662109154491460040ULL,  327638229622539321ULL,  1757902983245101607ULL,
        2544312663319080052ULL, 4414389636805556778ULL};
    mh_rng rng;
    mh_rng_init(&rng, 0);
    for (int i = 0; i < 8; i++) {
        CHECK(mh_rng_bounded(&rng, 2) == bound_two_seed_zero[i]);
    }
    mh_rng_init(&rng, 1);
    for (int i = 0; i < 8; i++) {
        CHECK(mh_rng_bounded(&rng, 1000003) == bound_million_seed_one[i]);
    }
    mh_rng_init(&rng, 1);
    for (int i = 0; i < 8; i++) {
        CHECK(mh_rng_bounded(&rng, 9223372036854775807ULL) == bound_max_seed_one[i]);
    }
    mh_rng_init(&rng, 1);
    for (int i = 0; i < 8; i++) {
        CHECK(mh_rng_bounded(&rng, 4611686018427387905ULL) == bound_half_seed_one[i]);
    }
}

static void test_weighted_and_shuffle_vectors(void) {
    static const uint64_t weights[] = {0, 5, 0, 2};
    static const size_t expected_weighted[] = {1, 1, 1, 1, 1, 1, 1, 1, 3, 1, 3, 3};
    static const uint64_t expected_shuffle[] = {3, 6, 1, 5, 0, 9, 2, 8, 4, 7};
    mh_rng rng;
    mh_rng_init(&rng, 1);
    for (int i = 0; i < 12; i++) {
        CHECK(mh_rng_weighted_index(&rng, weights, 4, 7) == expected_weighted[i]);
    }
    uint64_t items[10];
    for (uint64_t i = 0; i < 10; i++) {
        items[i] = i;
    }
    mh_rng_init(&rng, 1);
    mh_rng_shuffle(&rng, items, 10);
    CHECK(memcmp(items, expected_shuffle, sizeof items) == 0);
}

static mh_scenario make_scenario(int doors, int prizes, int pick, int reveals, mh_host host) {
    mh_scenario_input input;
    mh_scenario scenario;
    char error[MH_ERROR_SIZE];
    mh_scenario_input_default(&input);
    input.doors = doors;
    input.prizes = prizes;
    input.pick = pick;
    input.reveals = reveals;
    input.host = host;
    if (host == MH_HOST_BIASED) {
        input.has_host_weights = true;
        input.host_weights_count = (size_t)doors;
        for (int i = 0; i < doors; i++) {
            input.host_weights[i] = 1;
        }
    }
    if (!mh_scenario_build(&input, &scenario, error, sizeof error)) {
        fprintf(stderr, "  scenario rejected: %s\n", error);
        checks_failed_in_test++;
        memset(&scenario, 0, sizeof scenario);
    }
    return scenario;
}

static void test_scenario_validation(void) {
    mh_scenario_input input;
    mh_scenario scenario;
    char error[MH_ERROR_SIZE];
    mh_scenario_input_default(&input);
    CHECK(mh_scenario_build(&input, &scenario, error, sizeof error));
    input.doors = 65;
    CHECK(!mh_scenario_build(&input, &scenario, error, sizeof error));
    mh_scenario_input_default(&input);
    input.reveals = 2;
    CHECK(!mh_scenario_build(&input, &scenario, error, sizeof error));
    mh_scenario_input_default(&input);
    input.host = MH_HOST_BIASED;
    CHECK(!mh_scenario_build(&input, &scenario, error, sizeof error));
    mh_scenario_input_default(&input);
    input.has_prior = true;
    input.prior_count = 3;
    CHECK(!mh_scenario_build(&input, &scenario, error, sizeof error));
    CHECK(strstr(error, "positive weight") != NULL);
    mh_scenario_input_default(&input);
    input.mixed = frac("3/2");
    CHECK(!mh_scenario_build(&input, &scenario, error, sizeof error));
    mh_scenario_input_default(&input);
    input.doors = 5;
    input.reveals = 2;
    input.has_observed = true;
    input.observed_count = 2;
    input.observed[0] = 4;
    input.observed[1] = 2;
    CHECK(mh_scenario_build(&input, &scenario, error, sizeof error));
    CHECK(scenario.observed[0] == 2 && scenario.observed[1] == 4);
    input.observed[1] = 4;
    CHECK(!mh_scenario_build(&input, &scenario, error, sizeof error));
    input.observed[1] = 0;
    CHECK(!mh_scenario_build(&input, &scenario, error, sizeof error));
}

static void test_exact_classic_hosts(void) {
    char error[MH_ERROR_SIZE];
    mh_exact result;
    mh_frac mixed;
    mh_scenario scenario = make_scenario(3, 1, 0, 1, MH_HOST_INFORMED);
    CHECK(mh_solve(&scenario, &result, error, sizeof error));
    CHECK_FRAC(result.stay, "1/3");
    CHECK_FRAC(result.switch_, "2/3");
    CHECK(mh_exact_win(&result, MH_MIXED, &scenario.mixed, &mixed));
    CHECK_FRAC(mixed, "1/2");
    scenario = make_scenario(3, 1, 0, 1, MH_HOST_RANDOM);
    CHECK(mh_solve(&scenario, &result, error, sizeof error));
    CHECK_FRAC(result.decision, "2/3");
    CHECK_FRAC(result.void_, "1/3");
    CHECK_FRAC(result.stay, "1/2");
    CHECK_FRAC(result.switch_, "1/2");
    scenario = make_scenario(3, 1, 0, 1, MH_HOST_ADVERSARIAL);
    CHECK(mh_solve(&scenario, &result, error, sizeof error));
    CHECK_FRAC(result.decision, "1/3");
    CHECK_FRAC(result.no_offer, "2/3");
    CHECK_FRAC(result.stay, "1/1");
    CHECK_FRAC(result.switch_, "0/1");
}

static void test_exact_biased_observed(void) {
    char error[MH_ERROR_SIZE];
    mh_exact result;
    mh_frac mixed;
    mh_scenario scenario = make_scenario(5, 2, 0, 2, MH_HOST_BIASED);
    for (int i = 0; i < 5; i++) {
        scenario.host_weights[i] = (uint32_t)i + 1U;
    }
    scenario.has_observed = true;
    scenario.observed_count = 2;
    scenario.observed[0] = 1;
    scenario.observed[1] = 2;
    CHECK(mh_solve(&scenario, &result, error, sizeof error));
    CHECK(result.has_observed);
    CHECK_FRAC(result.observed, "689/5040");
    CHECK_FRAC(result.stay, "185/689");
    CHECK_FRAC(result.switch_, "1193/1378");
    CHECK(mh_exact_win(&result, MH_MIXED, &scenario.mixed, &mixed));
    CHECK_FRAC(mixed, "1563/2756");
}

static void test_exact_weighted_prior(void) {
    char error[MH_ERROR_SIZE];
    mh_exact result;
    mh_scenario scenario = make_scenario(6, 3, 5, 2, MH_HOST_BIASED);
    scenario.has_prior = true;
    for (int i = 0; i < 6; i++) {
        scenario.prior[i] = (uint32_t)i + 1U;
        scenario.host_weights[i] = 6U - (uint32_t)i;
    }
    scenario.has_observed = true;
    scenario.observed_count = 2;
    scenario.observed[0] = 0;
    scenario.observed[1] = 1;
    CHECK(mh_solve(&scenario, &result, error, sizeof error));
    CHECK_FRAC(result.prize_at_pick, "2603219/3527160");
    CHECK_FRAC(result.observed, "275185741/935625600");
    CHECK_FRAC(result.stay, "202042741/275185741");
    CHECK_FRAC(result.switch_, "623514482/825557223");
    scenario = make_scenario(4, 1, 0, 1, MH_HOST_ADVERSARIAL);
    scenario.has_prior = true;
    scenario.prior[0] = 0;
    scenario.prior[1] = scenario.prior[2] = scenario.prior[3] = 1;
    CHECK(mh_solve(&scenario, &result, error, sizeof error));
    CHECK(!result.has_stay && !result.has_switch);
    CHECK_FRAC(result.no_offer, "1/1");
}

static void test_exact_enumeration_limit(void) {
    char error[MH_ERROR_SIZE];
    mh_exact result;
    mh_scenario scenario = make_scenario(11, 1, 0, 1, MH_HOST_INFORMED);
    scenario.has_prior = true;
    for (int i = 0; i < 11; i++) {
        scenario.prior[i] = 1;
    }
    CHECK(!mh_solve(&scenario, &result, error, sizeof error));
    CHECK(strstr(error, "at most 10 doors") != NULL);
}

static void test_exact_sixty_four_doors(void) {
    char error[MH_ERROR_SIZE];
    mh_exact result;
    mh_scenario scenario = make_scenario(64, 32, 0, 31, MH_HOST_RANDOM);
    CHECK(mh_solve(&scenario, &result, error, sizeof error));
    CHECK_FRAC(result.decision, "1/55534064877048198");
    CHECK_FRAC(result.void_, "55534064877048197/55534064877048198");
    CHECK_FRAC(result.stay, "32/33");
    CHECK_FRAC(result.switch_, "32/33");
    CHECK(mh_comb(63, 31) == 916312070471295267ULL);
}

static void test_optimum_five_doors(void) {
    char error[MH_ERROR_SIZE];
    mh_optimum *result = malloc(sizeof *result);
    mh_scenario scenario = make_scenario(5, 1, 0, 0, MH_HOST_INFORMED);
    mh_frac cost = frac("1/20");
    CHECK(result != NULL);
    if (result == NULL) {
        return;
    }
    CHECK(mh_optimum_curve(&scenario, MH_SWITCH, &cost, result, error, sizeof error));
    CHECK(result->count == 4);
    CHECK_FRAC(result->curve[0].win, "1/5");
    CHECK(result->best == 3);
    CHECK_FRAC(result->curve[3].value, "13/20");
    CHECK(result->has_parabola);
    CHECK_FRAC(result->parabola.a, "1/12");
    CHECK_FRAC(result->parabola.b, "-8/75");
    CHECK_FRAC(result->parabola.c, "21/100");
    CHECK(strcmp(mh_parabola_shape(&result->parabola), "convex") == 0);
    CHECK_FRAC(result->parabola.residual_sum_of_squares, "1/500");
    CHECK(result->parabola.has_vertex);
    CHECK_FRAC(result->parabola.vertex_reveals, "16/25");
    CHECK_FRAC(result->parabola.vertex_value, "1319/7500");
    CHECK(result->parabola.rounded_vertex == 1);
    CHECK(result->parabola.fitted_choice == 3);
    free(result);
}

static void test_optimum_sixty_four_doors(void) {
    char error[MH_ERROR_SIZE];
    mh_optimum *result = malloc(sizeof *result);
    mh_scenario scenario = make_scenario(64, 1, 0, 0, MH_HOST_INFORMED);
    mh_frac cost = frac("1/1000");
    CHECK(result != NULL);
    if (result == NULL) {
        return;
    }
    CHECK(mh_optimum_curve(&scenario, MH_SWITCH, &cost, result, error, sizeof error));
    CHECK(result->count == 63);
    CHECK(result->best == 62);
    CHECK_FRAC(result->curve[62].value, "7379/8000");
    CHECK_FRAC(result->parabola.a,
               "119577992924372514353292337/529935805117259118901092689920");
    CHECK_FRAC(result->parabola.vertex_value,
               "-424635816104497479524528908004304757860907049817485583359/"
               "9901353117919259781868600944436443893671994868039553600000");
    CHECK(result->parabola.rounded_vertex == 24);
    CHECK(result->parabola.fitted_choice == 62);
    CHECK(!mh_arith_failed());
    free(result);
}

static void test_optimum_linear_and_short_curves(void) {
    char error[MH_ERROR_SIZE];
    mh_optimum *result = malloc(sizeof *result);
    mh_scenario scenario = make_scenario(6, 1, 0, 0, MH_HOST_INFORMED);
    mh_frac cost = frac("1/50");
    CHECK(result != NULL);
    if (result == NULL) {
        return;
    }
    CHECK(mh_optimum_curve(&scenario, MH_STAY, &cost, result, error, sizeof error));
    CHECK(strcmp(mh_parabola_shape(&result->parabola), "linear") == 0);
    CHECK(!result->parabola.has_vertex);
    CHECK_FRAC(result->parabola.b, "-1/50");
    CHECK_FRAC(result->parabola.residual_sum_of_squares, "0/1");
    CHECK(result->parabola.fitted_choice == 0);
    cost = frac("0");
    CHECK(mh_optimum_curve(&scenario, MH_STAY, &cost, result, error, sizeof error));
    CHECK(result->best == 0);
    CHECK_FRAC(result->curve[4].value, "1/6");
    CHECK(result->parabola.fitted_choice == 0);
    CHECK_FRAC(result->parabola.a, "0/1");
    CHECK_FRAC(result->parabola.b, "0/1");
    cost = frac("1/50");
    scenario = make_scenario(4, 2, 0, 0, MH_HOST_INFORMED);
    CHECK(mh_optimum_curve(&scenario, MH_SWITCH, &cost, result, error, sizeof error));
    CHECK(result->count == 2);
    CHECK(!result->has_parabola);
    cost = frac("-1/2");
    CHECK(!mh_optimum_curve(&scenario, MH_SWITCH, &cost, result, error, sizeof error));
    free(result);
}

static void test_simulation_matches_reference(void) {
    char error[MH_ERROR_SIZE];
    mh_counts counts;
    mh_scenario scenario = make_scenario(3, 1, 0, 1, MH_HOST_INFORMED);
    CHECK(mh_simulate(&scenario, 30000, 20190925, &counts, error, sizeof error));
    CHECK(counts.decision == 30000);
    CHECK(counts.stay_wins == 10024 && counts.switch_wins == 19976 && counts.mixed_wins == 15122);
    scenario = make_scenario(3, 1, 0, 1, MH_HOST_RANDOM);
    CHECK(mh_simulate(&scenario, 30000, 1, &counts, error, sizeof error));
    CHECK(counts.decision == 20044 && counts.void_ == 9956);
    CHECK(counts.stay_wins == 10029 && counts.switch_wins == 10015 && counts.mixed_wins == 9995);
    scenario = make_scenario(3, 1, 0, 1, MH_HOST_ADVERSARIAL);
    CHECK(mh_simulate(&scenario, 30000, 2, &counts, error, sizeof error));
    CHECK(counts.decision == 10182 && counts.no_offer == 19818);
    CHECK(counts.stay_wins == 10182 && counts.switch_wins == 0 && counts.mixed_wins == 5121);
    scenario = make_scenario(3, 1, 0, 1, MH_HOST_BIASED);
    scenario.host_weights[1] = 3;
    scenario.has_observed = true;
    scenario.observed_count = 1;
    scenario.observed[0] = 1;
    CHECK(mh_simulate(&scenario, 40000, 3, &counts, error, sizeof error));
    CHECK(counts.has_observed && counts.observed == 23090);
    CHECK(mh_sample_size(&counts) == 23090);
    CHECK(counts.stay_wins == 9917 && counts.switch_wins == 13173 && counts.mixed_wins == 11438);
}

static void test_simulation_rejects_bad_runs(void) {
    char error[MH_ERROR_SIZE];
    mh_counts counts;
    mh_scenario scenario = make_scenario(3, 1, 0, 1, MH_HOST_INFORMED);
    CHECK(!mh_simulate(&scenario, 0, 1, &counts, error, sizeof error));
    CHECK(!mh_simulate(&scenario, MH_MAX_TRIALS + 1, 1, &counts, error, sizeof error));
    CHECK(!mh_simulate(&scenario, 10, -1, &counts, error, sizeof error));
}

static void test_wilson_interval(void) {
    mh_interval none = mh_wilson95(0, 10);
    mh_interval all = mh_wilson95(10, 10);
    mh_interval half = mh_wilson95(50, 100);
    CHECK(none.lower == 0.0 && none.upper > 0.0 && none.upper < 1.0);
    CHECK(all.upper == 1.0 && all.lower > 0.0 && all.lower < 1.0);
    CHECK(half.lower < 0.5 && half.upper > 0.5);
    CHECK(half.lower > 0.4038 && half.lower < 0.4039);
}

typedef struct {
    int code;
    char *out;
    char *err;
} cli_result;

static cli_result run_cli(int argc, const char *const *argv) {
    cli_result result = {0, NULL, NULL};
    size_t out_length = 0;
    size_t err_length = 0;
    FILE *out = open_memstream(&result.out, &out_length);
    FILE *err = open_memstream(&result.err, &err_length);
    char *copies[32];
    for (int i = 0; i < argc; i++) {
        copies[i] = (char *)argv[i];
    }
    result.code = mh_cli_main(argc, copies, out, err);
    fclose(out);
    fclose(err);
    return result;
}

static void free_cli(cli_result *result) {
    free(result->out);
    free(result->err);
}

static void test_cli_exact_output(void) {
    const char *argv[] = {"monty-lab", "exact", "--doors=4", "--reveals", "2", "--observed",
                          "3,1"};
    cli_result result = run_cli(7, argv);
    CHECK(result.code == 0);
    CHECK(strstr(result.out, "\"command\": \"exact\"") != NULL);
    CHECK(strstr(result.out, "\"observed\": [\n      1,\n      3\n    ]") != NULL);
    CHECK(strstr(result.out, "\"switch\": \"3/4\"") != NULL);
    CHECK(strcmp(result.err, "") == 0);
    free_cli(&result);
}

static void test_cli_simulate_and_prng(void) {
    const char *simulate[] = {"monty-lab", "simulate", "--host", "random", "--seed", "1",
                              "--trials", "1000"};
    cli_result result = run_cli(8, simulate);
    CHECK(result.code == 0);
    CHECK(strstr(result.out, "\"decision\": 675") != NULL);
    CHECK(strstr(result.out, "\"wins\": 343") != NULL);
    CHECK(strstr(result.out, "\"wins\": 332") != NULL);
    CHECK(strstr(result.out, "\"wins\": 346") != NULL);
    free_cli(&result);
    const char *prng[] = {"monty-lab", "prng", "--seed", "0", "--kind", "splitmix"};
    result = run_cli(6, prng);
    CHECK(result.code == 0);
    CHECK(strstr(result.out, "\"16294208416658607535\"") != NULL);
    free_cli(&result);
}

static void test_cli_optimum_output(void) {
    const char *argv[] = {"monty-lab", "optimum", "--doors", "5", "--strategy", "switch",
                          "--cost", "1/20"};
    cli_result result = run_cli(8, argv);
    CHECK(result.code == 0);
    CHECK(strstr(result.out, "\"reveals\": null") != NULL);
    CHECK(strstr(result.out, "\"vertex_offset\": \"-59/25\"") != NULL);
    CHECK(strstr(result.out, "\"vertex_value_gap\": \"-889/1875\"") != NULL);
    CHECK(strstr(result.out, "\"regret\": \"13/30\"") != NULL);
    free_cli(&result);
}

static void test_cli_rejects_invalid_input(void) {
    static const char *const cases[][12] = {
        {"exact", "--doors", "2"},
        {"exact", "--doors", "65"},
        {"exact", "--doors", "5", "--prizes", "4"},
        {"exact", "--pick", "3"},
        {"exact", "--observed", "0"},
        {"exact", "--host", "biased"},
        {"exact", "--host-weights", "1,1,1"},
        {"exact", "--mixed", "1/0"},
        {"exact", "--doors", "abc"},
        {"exact", "--unknown", "1"},
        {"exact", "--doors"},
        {"simulate", "--seed", "-1"},
        {"simulate", "--trials", "5"},
        {"optimum", "--strategy", "switch", "--cost", "-1/2"},
        {"optimum", "--strategy", "maybe"},
        {"prng", "--seed", "1", "--kind", "bounded", "--bound", "0"},
        {"prng", "--seed", "1", "--kind", "words", "--count", "100001"},
        {"launch"},
    };
    for (size_t i = 0; i < sizeof cases / sizeof cases[0]; i++) {
        const char *argv[13] = {"monty-lab"};
        int argc = 1;
        for (int j = 0; j < 12 && cases[i][j] != NULL; j++) {
            argv[argc++] = cases[i][j];
        }
        cli_result result = run_cli(argc, argv);
        CHECK(result.code == MH_EXIT_USAGE);
        CHECK(strcmp(result.out, "") == 0);
        CHECK(strstr(result.err, "error") != NULL);
        free_cli(&result);
    }
}

static void test_cli_help_and_version(void) {
    const char *help[] = {"monty-lab", "--help"};
    const char *version[] = {"monty-lab", "--version"};
    cli_result result = run_cli(2, help);
    CHECK(result.code == 0);
    CHECK(strstr(result.out, "usage: monty-lab") != NULL);
    free_cli(&result);
    result = run_cli(2, version);
    CHECK(result.code == 0);
    CHECK(strcmp(result.out, "monty-lab " MH_VERSION "\n") == 0);
    free_cli(&result);
}

static void test_json_double_format(void) {
    char *buffer = NULL;
    size_t length = 0;
    FILE *memory = open_memstream(&buffer, &length);
    mh_json w;
    mh_json_init(&w, memory);
    mh_json_begin_array(&w);
    mh_json_double(&w, 1.0);
    mh_json_double(&w, 0.5081);
    mh_json_double(&w, 0.1);
    mh_json_end_array(&w);
    fclose(memory);
    CHECK(strcmp(buffer, "[\n  1.0,\n  0.5081,\n  0.1\n]") == 0);
    free(buffer);
}

int main(void) {
    run_test("fraction_parse_and_format", test_fraction_parse_and_format);
    run_test("fraction_arithmetic", test_fraction_arithmetic);
    run_test("fraction_floor", test_fraction_floor);
    run_test("big_integers_beyond_64_bits", test_big_integers_beyond_64_bits);
    run_test("overflow_is_detected", test_overflow_is_detected);
    run_test("parse_i64_bounds", test_parse_i64_bounds);
    run_test("splitmix_and_words", test_splitmix_and_words);
    run_test("bounded_vectors", test_bounded_vectors);
    run_test("weighted_and_shuffle_vectors", test_weighted_and_shuffle_vectors);
    run_test("scenario_validation", test_scenario_validation);
    run_test("exact_classic_hosts", test_exact_classic_hosts);
    run_test("exact_biased_observed", test_exact_biased_observed);
    run_test("exact_weighted_prior", test_exact_weighted_prior);
    run_test("exact_enumeration_limit", test_exact_enumeration_limit);
    run_test("exact_sixty_four_doors", test_exact_sixty_four_doors);
    run_test("optimum_five_doors", test_optimum_five_doors);
    run_test("optimum_sixty_four_doors", test_optimum_sixty_four_doors);
    run_test("optimum_linear_and_short_curves", test_optimum_linear_and_short_curves);
    run_test("simulation_matches_reference", test_simulation_matches_reference);
    run_test("simulation_rejects_bad_runs", test_simulation_rejects_bad_runs);
    run_test("wilson_interval", test_wilson_interval);
    run_test("cli_exact_output", test_cli_exact_output);
    run_test("cli_simulate_and_prng", test_cli_simulate_and_prng);
    run_test("cli_optimum_output", test_cli_optimum_output);
    run_test("cli_rejects_invalid_input", test_cli_rejects_invalid_input);
    run_test("cli_help_and_version", test_cli_help_and_version);
    run_test("json_double_format", test_json_double_format);
    printf("%d tests, %d passed, %d failed\n", tests_run, tests_run - tests_failed, tests_failed);
    return tests_failed == 0 ? 0 : 1;
}
