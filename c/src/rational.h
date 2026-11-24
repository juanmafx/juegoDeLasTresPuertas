/* Exact rationals over arbitrary-precision unsigned integers with 64-bit limbs. */
#ifndef MH_RATIONAL_H
#define MH_RATIONAL_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#define MH_BIG_LIMBS 65536
#define MH_BIG_BITS (MH_BIG_LIMBS * 64)
#define MH_FRAC_TEXT 2600

__extension__ typedef unsigned __int128 mh_u128;

typedef struct {
    size_t len;
    uint64_t word;
    const uint64_t *heap;
} mh_big;

typedef struct {
    bool negative;
    mh_big num;
    mh_big den;
} mh_frac;

bool mh_arith_failed(void);
void mh_arith_reset(void);

size_t mh_arena_mark(void);
void mh_arena_keep(size_t mark, const mh_big *const *keep, size_t count);
void mh_arena_keep_fracs(size_t mark, const mh_frac *const *keep, size_t count);
void mh_arena_release_all(void);

void mh_big_set_u64(mh_big *r, uint64_t value);
bool mh_big_is_zero(const mh_big *a);
int mh_big_cmp(const mh_big *a, const mh_big *b);
size_t mh_big_bits(const mh_big *a);
void mh_big_add(mh_big *r, const mh_big *a, const mh_big *b);
void mh_big_sub(mh_big *r, const mh_big *a, const mh_big *b);
void mh_big_mul(mh_big *r, const mh_big *a, const mh_big *b);
void mh_big_shl(mh_big *r, const mh_big *a, size_t bits);
void mh_big_shr(mh_big *r, const mh_big *a, size_t bits);
void mh_big_divmod(mh_big *quotient, mh_big *remainder, const mh_big *a, const mh_big *b);
void mh_big_gcd(mh_big *r, const mh_big *a, const mh_big *b);
bool mh_big_to_u64(const mh_big *a, uint64_t *out);
bool mh_big_parse(mh_big *r, const char *digits, size_t length);
bool mh_parse_integer(const char *text, size_t length, bool *negative, mh_big *magnitude);
bool mh_parse_i64(const char *text, size_t length, int64_t *out);
size_t mh_big_format(const mh_big *a, char *buffer, size_t size);
size_t mh_big_digits_bound(const mh_big *a);

void mh_frac_set_i64(mh_frac *r, int64_t num, int64_t den);
void mh_frac_set_parts(mh_frac *r, bool negative, const mh_big *num, const mh_big *den);
void mh_frac_add(mh_frac *r, const mh_frac *a, const mh_frac *b);
void mh_frac_sub(mh_frac *r, const mh_frac *a, const mh_frac *b);
void mh_frac_mul(mh_frac *r, const mh_frac *a, const mh_frac *b);
void mh_frac_div(mh_frac *r, const mh_frac *a, const mh_frac *b);
void mh_frac_neg(mh_frac *r, const mh_frac *a);
int mh_frac_cmp(const mh_frac *a, const mh_frac *b);
int mh_frac_sign(const mh_frac *a);
bool mh_frac_is_zero(const mh_frac *a);
void mh_frac_floor(mh_frac *r, const mh_frac *a);
bool mh_frac_parse(mh_frac *r, const char *text);
const char *mh_frac_format(const mh_frac *a, char *buffer, size_t size);
char *mh_frac_to_string(const mh_frac *a);

#endif
