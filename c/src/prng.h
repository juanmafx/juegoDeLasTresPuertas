/* Cross-language deterministic generator: SplitMix64 seeding, xoshiro256**, Lemire bounded draws. */
#ifndef MH_PRNG_H
#define MH_PRNG_H

#include <stddef.h>
#include <stdint.h>

typedef struct {
    uint64_t state;
} mh_splitmix;

typedef struct {
    uint64_t s[4];
} mh_rng;

void mh_splitmix_init(mh_splitmix *g, uint64_t seed);
uint64_t mh_splitmix_next(mh_splitmix *g);

void mh_rng_init(mh_rng *g, uint64_t seed);
uint64_t mh_rng_next(mh_rng *g);
uint64_t mh_rng_bounded(mh_rng *g, uint64_t bound);
size_t mh_rng_weighted_index(mh_rng *g, const uint64_t *weights, size_t count, uint64_t total);
void mh_rng_shuffle(mh_rng *g, uint64_t *items, size_t count);
size_t mh_rng_weighted_sample(mh_rng *g, const int *items, const uint64_t *weights, size_t count,
                              size_t draws, int *chosen);

#endif
