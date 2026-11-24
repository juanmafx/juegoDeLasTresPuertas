/* Scenario model shared by the exact solver, the simulator and the optimum curve. */
#ifndef MH_MODEL_H
#define MH_MODEL_H

#include "rational.h"

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#define MH_MIN_DOORS 3
#define MH_MAX_DOORS 64
#define MH_MAX_WEIGHT 1000000
#define MH_ENUMERATION_MAX_DOORS 10
#define MH_MAX_TRIALS 100000000
#define MH_MAX_SEED INT64_MAX
#define MH_ERROR_SIZE 256

typedef enum { MH_HOST_INFORMED, MH_HOST_RANDOM, MH_HOST_BIASED, MH_HOST_ADVERSARIAL } mh_host;
typedef enum { MH_STAY, MH_SWITCH, MH_MIXED } mh_strategy;

typedef struct {
    int doors;
    int prizes;
    int pick;
    int reveals;
    mh_host host;
    bool has_prior;
    uint32_t prior[MH_MAX_DOORS];
    bool has_host_weights;
    uint32_t host_weights[MH_MAX_DOORS];
    mh_frac mixed;
    bool has_observed;
    int observed_count;
    int observed[MH_MAX_DOORS];
} mh_scenario;

typedef struct {
    int64_t doors;
    int64_t prizes;
    int64_t pick;
    int64_t reveals;
    mh_host host;
    bool has_prior;
    size_t prior_count;
    int64_t prior[MH_MAX_DOORS + 1];
    bool has_host_weights;
    size_t host_weights_count;
    int64_t host_weights[MH_MAX_DOORS + 1];
    mh_frac mixed;
    bool has_observed;
    size_t observed_count;
    int64_t observed[MH_MAX_DOORS + 1];
} mh_scenario_input;

void mh_scenario_input_default(mh_scenario_input *input);
bool mh_scenario_build(const mh_scenario_input *input, mh_scenario *out, char *error,
                       size_t error_size);
int mh_max_reveals(const mh_scenario *scenario);
uint32_t mh_prior_weight(const mh_scenario *scenario, int door);
const char *mh_host_name(mh_host host);
bool mh_host_parse(const char *text, mh_host *out);
const char *mh_strategy_name(mh_strategy strategy);
bool mh_strategy_parse(const char *text, mh_strategy *out);

#endif
