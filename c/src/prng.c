/* Cross-language deterministic generator: SplitMix64 seeding, xoshiro256**, Lemire bounded draws. */
#include "prng.h"

#include "rational.h"

#include <string.h>

#define MH_SAMPLE_MAX 64

static uint64_t rotl(uint64_t value, unsigned shift) {
    return (value << shift) | (value >> (64U - shift));
}

void mh_splitmix_init(mh_splitmix *g, uint64_t seed) { g->state = seed; }

uint64_t mh_splitmix_next(mh_splitmix *g) {
    g->state += 0x9E3779B97F4A7C15ULL;
    uint64_t z = g->state;
    z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ULL;
    z = (z ^ (z >> 27)) * 0x94D049BB133111EBULL;
    return z ^ (z >> 31);
}

void mh_rng_init(mh_rng *g, uint64_t seed) {
    mh_splitmix expander;
    mh_splitmix_init(&expander, seed);
    for (int i = 0; i < 4; i++) {
        g->s[i] = mh_splitmix_next(&expander);
    }
}

uint64_t mh_rng_next(mh_rng *g) {
    uint64_t *s = g->s;
    uint64_t result = rotl(s[1] * 5U, 7) * 9U;
    uint64_t t = s[1] << 17;
    s[2] ^= s[0];
    s[3] ^= s[1];
    s[1] ^= s[2];
    s[0] ^= s[3];
    s[2] ^= t;
    s[3] = rotl(s[3], 45);
    return result;
}

uint64_t mh_rng_bounded(mh_rng *g, uint64_t bound) {
    mh_u128 product = (mh_u128)mh_rng_next(g) * bound;
    uint64_t low = (uint64_t)product;
    if (low < bound) {
        uint64_t threshold = (0U - bound) % bound;
        while (low < threshold) {
            product = (mh_u128)mh_rng_next(g) * bound;
            low = (uint64_t)product;
        }
    }
    return (uint64_t)(product >> 64);
}

size_t mh_rng_weighted_index(mh_rng *g, const uint64_t *weights, size_t count, uint64_t total) {
    uint64_t draw = mh_rng_bounded(g, total);
    uint64_t cumulative = 0;
    for (size_t i = 0; i < count; i++) {
        cumulative += weights[i];
        if (draw < cumulative) {
            return i;
        }
    }
    return count - 1;
}

void mh_rng_shuffle(mh_rng *g, uint64_t *items, size_t count) {
    for (size_t i = count; i-- > 1;) {
        size_t j = (size_t)mh_rng_bounded(g, (uint64_t)i + 1U);
        uint64_t swap = items[i];
        items[i] = items[j];
        items[j] = swap;
    }
}

size_t mh_rng_weighted_sample(mh_rng *g, const int *items, const uint64_t *weights, size_t count,
                              size_t draws, int *chosen) {
    int pool[MH_SAMPLE_MAX];
    uint64_t pool_weights[MH_SAMPLE_MAX];
    uint64_t total = 0;
    memcpy(pool, items, count * sizeof pool[0]);
    memcpy(pool_weights, weights, count * sizeof pool_weights[0]);
    for (size_t i = 0; i < count; i++) {
        total += weights[i];
    }
    for (size_t d = 0; d < draws; d++) {
        size_t index = mh_rng_weighted_index(g, pool_weights, count, total);
        chosen[d] = pool[index];
        total -= pool_weights[index];
        memmove(pool + index, pool + index + 1, (count - index - 1) * sizeof pool[0]);
        memmove(pool_weights + index, pool_weights + index + 1,
                (count - index - 1) * sizeof pool_weights[0]);
        count--;
    }
    return draws;
}
