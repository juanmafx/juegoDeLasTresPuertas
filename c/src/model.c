/* Scenario model shared by the exact solver, the simulator and the optimum curve. */
#include "model.h"

#include <stdio.h>
#include <string.h>

void mh_scenario_input_default(mh_scenario_input *input) {
    memset(input, 0, sizeof *input);
    input->doors = 3;
    input->prizes = 1;
    input->pick = 0;
    input->reveals = 1;
    input->host = MH_HOST_INFORMED;
    mh_frac_set_i64(&input->mixed, 1, 2);
}

static bool reject(char *error, size_t error_size, const char *message) {
    snprintf(error, error_size, "%s", message);
    return false;
}

static bool weights_valid(const int64_t *weights, size_t count, int64_t doors, int64_t minimum) {
    if ((int64_t)count != doors) {
        return false;
    }
    for (size_t i = 0; i < count; i++) {
        if (weights[i] < minimum || weights[i] > MH_MAX_WEIGHT) {
            return false;
        }
    }
    return true;
}

bool mh_scenario_build(const mh_scenario_input *input, mh_scenario *out, char *error,
                       size_t error_size) {
    if (input->doors < MH_MIN_DOORS || input->doors > MH_MAX_DOORS) {
        snprintf(error, error_size, "doors must be between %d and %d", MH_MIN_DOORS,
                 MH_MAX_DOORS);
        return false;
    }
    if (input->prizes < 1 || input->prizes > input->doors - 2) {
        return reject(error, error_size, "prizes must be between 1 and doors - 2");
    }
    if (input->pick < 0 || input->pick >= input->doors) {
        return reject(error, error_size, "pick must be a door index between 0 and doors - 1");
    }
    if (input->reveals < 0 || input->reveals > input->doors - input->prizes - 1) {
        return reject(error, error_size, "reveals must be between 0 and doors - prizes - 1");
    }
    if (input->has_prior) {
        if (!weights_valid(input->prior, input->prior_count, input->doors, 0)) {
            if ((int64_t)input->prior_count != input->doors) {
                return reject(error, error_size, "prior must list exactly one weight per door");
            }
            return reject(error, error_size, "prior entries must be between 0 and 1000000");
        }
        int64_t positive = 0;
        for (size_t i = 0; i < input->prior_count; i++) {
            positive += input->prior[i] > 0 ? 1 : 0;
        }
        if (positive < input->prizes) {
            return reject(error, error_size,
                          "prior must give positive weight to at least prizes doors");
        }
    }
    if ((input->host == MH_HOST_BIASED) != input->has_host_weights) {
        return reject(error, error_size,
                      "host weights are required for, and only for, the biased host");
    }
    if (input->has_host_weights &&
        !weights_valid(input->host_weights, input->host_weights_count, input->doors, 1)) {
        if ((int64_t)input->host_weights_count != input->doors) {
            return reject(error, error_size, "host weights must list exactly one weight per door");
        }
        return reject(error, error_size, "host weights entries must be between 1 and 1000000");
    }
    mh_frac one;
    mh_frac_set_i64(&one, 1, 1);
    if (mh_frac_sign(&input->mixed) < 0 || mh_frac_cmp(&input->mixed, &one) > 0) {
        return reject(error, error_size, "mixed must be a fraction between 0 and 1");
    }
    if (input->has_observed) {
        bool valid = (int64_t)input->observed_count == input->reveals;
        uint64_t seen = 0;
        for (size_t i = 0; valid && i < input->observed_count; i++) {
            int64_t door = input->observed[i];
            if (door < 0 || door >= input->doors || door == input->pick ||
                (seen >> door & 1U) != 0) {
                valid = false;
                break;
            }
            seen |= (uint64_t)1 << door;
        }
        if (!valid) {
            return reject(error, error_size,
                          "observed must list reveals distinct doors other than the pick");
        }
    }
    memset(out, 0, sizeof *out);
    out->doors = (int)input->doors;
    out->prizes = (int)input->prizes;
    out->pick = (int)input->pick;
    out->reveals = (int)input->reveals;
    out->host = input->host;
    out->has_prior = input->has_prior;
    for (size_t i = 0; input->has_prior && i < input->prior_count; i++) {
        out->prior[i] = (uint32_t)input->prior[i];
    }
    out->has_host_weights = input->has_host_weights;
    for (size_t i = 0; input->has_host_weights && i < input->host_weights_count; i++) {
        out->host_weights[i] = (uint32_t)input->host_weights[i];
    }
    out->mixed = input->mixed;
    out->has_observed = input->has_observed;
    if (input->has_observed) {
        int count = 0;
        for (int door = 0; door < out->doors; door++) {
            for (size_t i = 0; i < input->observed_count; i++) {
                if (input->observed[i] == door) {
                    out->observed[count++] = door;
                }
            }
        }
        out->observed_count = count;
    }
    return true;
}

int mh_max_reveals(const mh_scenario *scenario) { return scenario->doors - scenario->prizes - 1; }

uint32_t mh_prior_weight(const mh_scenario *scenario, int door) {
    return scenario->has_prior ? scenario->prior[door] : 1U;
}

static const char *const host_names[] = {"informed", "random", "biased", "adversarial"};
static const char *const strategy_names[] = {"stay", "switch", "mixed"};

const char *mh_host_name(mh_host host) { return host_names[host]; }

bool mh_host_parse(const char *text, mh_host *out) {
    for (int i = 0; i < 4; i++) {
        if (strcmp(text, host_names[i]) == 0) {
            *out = (mh_host)i;
            return true;
        }
    }
    return false;
}

const char *mh_strategy_name(mh_strategy strategy) { return strategy_names[strategy]; }

bool mh_strategy_parse(const char *text, mh_strategy *out) {
    for (int i = 0; i < 3; i++) {
        if (strcmp(text, strategy_names[i]) == 0) {
            *out = (mh_strategy)i;
            return true;
        }
    }
    return false;
}
