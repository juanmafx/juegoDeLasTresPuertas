/* Exact rationals over arbitrary-precision unsigned integers with 64-bit limbs. */
#include "rational.h"

#include <ctype.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

static bool arith_failed = false;
static uint64_t **blocks = NULL;
static size_t block_count = 0;
static size_t block_capacity = 0;

bool mh_arith_failed(void) { return arith_failed; }

void mh_arith_reset(void) { arith_failed = false; }

static void fail(mh_big *r) {
    arith_failed = true;
    r->len = 0;
    r->word = 0;
    r->heap = NULL;
}

static uint64_t *scratch(size_t limbs) {
    uint64_t *p = calloc(limbs == 0 ? 1 : limbs, sizeof *p);
    if (p == NULL) {
        arith_failed = true;
    }
    return p;
}

static uint64_t *arena_alloc(size_t limbs) {
    if (block_count == block_capacity) {
        size_t grown = block_capacity == 0 ? 256 : block_capacity * 2;
        uint64_t **next = realloc(blocks, grown * sizeof *next);
        if (next == NULL) {
            return NULL;
        }
        blocks = next;
        block_capacity = grown;
    }
    uint64_t *p = malloc(limbs * sizeof *p);
    if (p == NULL) {
        return NULL;
    }
    blocks[block_count++] = p;
    return p;
}

static int compare_pointers(const void *left, const void *right) {
    uintptr_t a = (uintptr_t) * (const uint64_t *const *)left;
    uintptr_t b = (uintptr_t) * (const uint64_t *const *)right;
    return a < b ? -1 : a > b ? 1 : 0;
}

size_t mh_arena_mark(void) { return block_count; }

void mh_arena_keep(size_t mark, const mh_big *const *keep, size_t count) {
    if (mark >= block_count) {
        return;
    }
    const uint64_t **kept = malloc((count == 0 ? 1 : count) * sizeof *kept);
    if (kept == NULL) {
        return;
    }
    size_t kept_count = 0;
    for (size_t i = 0; i < count; i++) {
        if (keep[i]->len >= 2 && keep[i]->heap != NULL) {
            kept[kept_count++] = keep[i]->heap;
        }
    }
    qsort(kept, kept_count, sizeof *kept, compare_pointers);
    size_t write = mark;
    for (size_t i = mark; i < block_count; i++) {
        const uint64_t *block = blocks[i];
        if (kept_count > 0 && bsearch(&block, kept, kept_count, sizeof *kept, compare_pointers)) {
            blocks[write++] = blocks[i];
        } else {
            free(blocks[i]);
        }
    }
    block_count = write;
    free(kept);
}

void mh_arena_keep_fracs(size_t mark, const mh_frac *const *keep, size_t count) {
    if (mark >= block_count) {
        return;
    }
    const mh_big **bigs = malloc((count == 0 ? 1 : 2 * count) * sizeof *bigs);
    if (bigs == NULL) {
        return;
    }
    for (size_t i = 0; i < count; i++) {
        bigs[2 * i] = &keep[i]->num;
        bigs[2 * i + 1] = &keep[i]->den;
    }
    mh_arena_keep(mark, bigs, 2 * count);
    free(bigs);
}

void mh_arena_release_all(void) {
    for (size_t i = 0; i < block_count; i++) {
        free(blocks[i]);
    }
    free(blocks);
    blocks = NULL;
    block_count = 0;
    block_capacity = 0;
}

static void keep_frac(size_t mark, const mh_frac *value) {
    const mh_frac *keep[1] = {value};
    mh_arena_keep_fracs(mark, keep, 1);
}

static const uint64_t *limbs_of(const mh_big *a) { return a->len <= 1 ? &a->word : a->heap; }

static void store(mh_big *r, const uint64_t *limbs, size_t len) {
    while (len > 0 && limbs[len - 1] == 0) {
        len--;
    }
    if (len > MH_BIG_LIMBS) {
        fail(r);
        return;
    }
    if (len <= 1) {
        uint64_t word = len == 0 ? 0 : limbs[0];
        r->len = len;
        r->word = word;
        r->heap = NULL;
        return;
    }
    uint64_t *copy = arena_alloc(len);
    if (copy == NULL) {
        fail(r);
        return;
    }
    memcpy(copy, limbs, len * sizeof *copy);
    r->len = len;
    r->word = 0;
    r->heap = copy;
}

static int cmp_raw(const uint64_t *a, size_t an, const uint64_t *b, size_t bn) {
    if (an != bn) {
        return an < bn ? -1 : 1;
    }
    for (size_t i = an; i-- > 0;) {
        if (a[i] != b[i]) {
            return a[i] < b[i] ? -1 : 1;
        }
    }
    return 0;
}

static size_t trim_raw(const uint64_t *a, size_t n) {
    while (n > 0 && a[n - 1] == 0) {
        n--;
    }
    return n;
}

static size_t trailing_zeros_raw(const uint64_t *a, size_t n) {
    size_t count = 0;
    for (size_t i = 0; i < n; i++) {
        if (a[i] == 0) {
            count += 64;
            continue;
        }
        uint64_t word = a[i];
        while ((word & 1U) == 0) {
            count++;
            word >>= 1;
        }
        return count;
    }
    return count;
}

static size_t shr_raw(uint64_t *a, size_t n, size_t bits) {
    size_t words = bits / 64;
    unsigned shift = (unsigned)(bits % 64);
    if (words >= n) {
        return 0;
    }
    size_t out = n - words;
    for (size_t i = 0; i < out; i++) {
        uint64_t low = a[i + words] >> shift;
        uint64_t high = 0;
        if (shift != 0 && i + words + 1 < n) {
            high = a[i + words + 1] << (64 - shift);
        }
        a[i] = low | high;
    }
    return trim_raw(a, out);
}

static size_t sub_raw(uint64_t *a, size_t an, const uint64_t *b, size_t bn) {
    uint64_t borrow = 0;
    for (size_t i = 0; i < an; i++) {
        uint64_t y = i < bn ? b[i] : 0;
        uint64_t first = a[i] - y;
        uint64_t borrow_first = a[i] < y;
        uint64_t second = first - borrow;
        uint64_t borrow_second = first < borrow;
        a[i] = second;
        borrow = borrow_first | borrow_second;
    }
    return trim_raw(a, an);
}

static unsigned leading_zeros(uint64_t x) {
    unsigned count = 0;
    while ((x & ((uint64_t)1 << 63)) == 0) {
        x <<= 1;
        count++;
    }
    return count;
}

void mh_big_set_u64(mh_big *r, uint64_t value) {
    r->len = value == 0 ? 0 : 1;
    r->word = value;
    r->heap = NULL;
}

bool mh_big_is_zero(const mh_big *a) { return a->len == 0; }

int mh_big_cmp(const mh_big *a, const mh_big *b) {
    return cmp_raw(limbs_of(a), a->len, limbs_of(b), b->len);
}

size_t mh_big_bits(const mh_big *a) {
    if (a->len == 0) {
        return 0;
    }
    uint64_t top = limbs_of(a)[a->len - 1];
    size_t bits = 0;
    while (top != 0) {
        bits++;
        top >>= 1;
    }
    return (a->len - 1) * 64 + bits;
}

void mh_big_add(mh_big *r, const mh_big *a, const mh_big *b) {
    size_t n = a->len > b->len ? a->len : b->len;
    uint64_t *t = scratch(n + 1);
    if (t == NULL) {
        fail(r);
        return;
    }
    const uint64_t *x = limbs_of(a);
    const uint64_t *y = limbs_of(b);
    uint64_t carry = 0;
    for (size_t i = 0; i < n; i++) {
        mh_u128 sum = (mh_u128)(i < a->len ? x[i] : 0) + (i < b->len ? y[i] : 0) + carry;
        t[i] = (uint64_t)sum;
        carry = (uint64_t)(sum >> 64);
    }
    t[n] = carry;
    store(r, t, n + 1);
    free(t);
}

void mh_big_sub(mh_big *r, const mh_big *a, const mh_big *b) {
    if (mh_big_cmp(a, b) < 0) {
        fail(r);
        return;
    }
    uint64_t *t = scratch(a->len);
    if (t == NULL) {
        fail(r);
        return;
    }
    memcpy(t, limbs_of(a), a->len * sizeof *t);
    size_t n = sub_raw(t, a->len, limbs_of(b), b->len);
    store(r, t, n);
    free(t);
}

void mh_big_mul(mh_big *r, const mh_big *a, const mh_big *b) {
    if (a->len == 0 || b->len == 0) {
        mh_big_set_u64(r, 0);
        return;
    }
    if (a->len + b->len - 1 > MH_BIG_LIMBS) {
        fail(r);
        return;
    }
    size_t n = a->len + b->len;
    uint64_t *wide = scratch(n);
    if (wide == NULL) {
        fail(r);
        return;
    }
    const uint64_t *x = limbs_of(a);
    const uint64_t *y = limbs_of(b);
    for (size_t i = 0; i < a->len; i++) {
        uint64_t carry = 0;
        for (size_t j = 0; j < b->len; j++) {
            mh_u128 product = (mh_u128)x[i] * y[j] + wide[i + j] + carry;
            wide[i + j] = (uint64_t)product;
            carry = (uint64_t)(product >> 64);
        }
        wide[i + b->len] = carry;
    }
    store(r, wide, n);
    free(wide);
}

void mh_big_shl(mh_big *r, const mh_big *a, size_t bits) {
    if (a->len == 0) {
        mh_big_set_u64(r, 0);
        return;
    }
    if (bits > MH_BIG_BITS || mh_big_bits(a) + bits > MH_BIG_BITS) {
        fail(r);
        return;
    }
    size_t words = bits / 64;
    unsigned shift = (unsigned)(bits % 64);
    size_t n = a->len + words + 1;
    uint64_t *t = scratch(n);
    if (t == NULL) {
        fail(r);
        return;
    }
    const uint64_t *x = limbs_of(a);
    for (size_t i = 0; i < a->len; i++) {
        t[i + words] |= x[i] << shift;
        if (shift != 0) {
            t[i + words + 1] |= x[i] >> (64 - shift);
        }
    }
    store(r, t, n);
    free(t);
}

void mh_big_shr(mh_big *r, const mh_big *a, size_t bits) {
    if (a->len == 0) {
        mh_big_set_u64(r, 0);
        return;
    }
    uint64_t *t = scratch(a->len);
    if (t == NULL) {
        fail(r);
        return;
    }
    memcpy(t, limbs_of(a), a->len * sizeof *t);
    size_t n = shr_raw(t, a->len, bits);
    store(r, t, n);
    free(t);
}

static bool divide_raw(const uint64_t *u, size_t m, const uint64_t *v, size_t n, mh_big *quotient,
                       mh_big *remainder) {
    if (n == 1) {
        uint64_t *q = scratch(m);
        if (q == NULL) {
            return false;
        }
        mh_u128 rest = 0;
        for (size_t i = m; i-- > 0;) {
            mh_u128 current = (rest << 64) | u[i];
            q[i] = (uint64_t)(current / v[0]);
            rest = current % v[0];
        }
        store(quotient, q, m);
        mh_big_set_u64(remainder, (uint64_t)rest);
        free(q);
        return true;
    }
    unsigned s = leading_zeros(v[n - 1]);
    uint64_t *vn = scratch(n);
    uint64_t *un = scratch(m + 1);
    uint64_t *q = scratch(m - n + 1);
    if (vn == NULL || un == NULL || q == NULL) {
        free(vn);
        free(un);
        free(q);
        return false;
    }
    for (size_t i = n - 1; i > 0; i--) {
        vn[i] = s == 0 ? v[i] : (v[i] << s) | (v[i - 1] >> (64 - s));
    }
    vn[0] = v[0] << s;
    un[m] = s == 0 ? 0 : u[m - 1] >> (64 - s);
    for (size_t i = m - 1; i > 0; i--) {
        un[i] = s == 0 ? u[i] : (u[i] << s) | (u[i - 1] >> (64 - s));
    }
    un[0] = u[0] << s;
    for (size_t j = m - n + 1; j-- > 0;) {
        mh_u128 top = ((mh_u128)un[j + n] << 64) | un[j + n - 1];
        mh_u128 qhat = top / vn[n - 1];
        mh_u128 rhat = top % vn[n - 1];
        while ((qhat >> 64) != 0 || qhat * vn[n - 2] > ((rhat << 64) | un[j + n - 2])) {
            qhat--;
            rhat += vn[n - 1];
            if ((rhat >> 64) != 0) {
                break;
            }
        }
        uint64_t borrow = 0;
        uint64_t carry = 0;
        for (size_t i = 0; i < n; i++) {
            mh_u128 product = (mh_u128)(uint64_t)qhat * vn[i] + carry;
            carry = (uint64_t)(product >> 64);
            uint64_t low = (uint64_t)product;
            uint64_t first = un[i + j] - low;
            uint64_t borrow_first = un[i + j] < low;
            uint64_t second = first - borrow;
            uint64_t borrow_second = first < borrow;
            un[i + j] = second;
            borrow = borrow_first | borrow_second;
        }
        uint64_t first = un[j + n] - carry;
        uint64_t borrow_first = un[j + n] < carry;
        uint64_t second = first - borrow;
        uint64_t borrow_second = first < borrow;
        un[j + n] = second;
        q[j] = (uint64_t)qhat;
        if ((borrow_first | borrow_second) != 0) {
            q[j]--;
            uint64_t add_carry = 0;
            for (size_t i = 0; i < n; i++) {
                mh_u128 sum = (mh_u128)un[i + j] + vn[i] + add_carry;
                un[i + j] = (uint64_t)sum;
                add_carry = (uint64_t)(sum >> 64);
            }
            un[j + n] += add_carry;
        }
    }
    for (size_t i = 0; i < n; i++) {
        un[i] = s == 0 ? un[i] : (un[i] >> s) | (un[i + 1] << (64 - s));
    }
    store(quotient, q, m - n + 1);
    store(remainder, un, n);
    free(vn);
    free(un);
    free(q);
    return true;
}

void mh_big_divmod(mh_big *quotient, mh_big *remainder, const mh_big *a, const mh_big *b) {
    if (b->len == 0) {
        fail(quotient);
        fail(remainder);
        return;
    }
    mh_big q;
    mh_big rem;
    if (mh_big_cmp(a, b) < 0) {
        rem = *a;
        mh_big_set_u64(&q, 0);
    } else if (!divide_raw(limbs_of(a), a->len, limbs_of(b), b->len, &q, &rem)) {
        fail(quotient);
        fail(remainder);
        return;
    }
    *quotient = q;
    *remainder = rem;
}

void mh_big_gcd(mh_big *r, const mh_big *a, const mh_big *b) {
    if (a->len == 0) {
        *r = *b;
        return;
    }
    if (b->len == 0) {
        *r = *a;
        return;
    }
    size_t capacity = a->len > b->len ? a->len : b->len;
    uint64_t *u = scratch(capacity + 1);
    uint64_t *v = scratch(capacity + 1);
    if (u == NULL || v == NULL) {
        free(u);
        free(v);
        fail(r);
        return;
    }
    memcpy(u, limbs_of(a), a->len * sizeof *u);
    memcpy(v, limbs_of(b), b->len * sizeof *v);
    size_t un = a->len;
    size_t vn = b->len;
    size_t zu = trailing_zeros_raw(u, un);
    size_t zv = trailing_zeros_raw(v, vn);
    size_t shift = zu < zv ? zu : zv;
    un = shr_raw(u, un, zu);
    while (vn != 0) {
        vn = shr_raw(v, vn, trailing_zeros_raw(v, vn));
        if (cmp_raw(u, un, v, vn) > 0) {
            uint64_t *swap = u;
            u = v;
            v = swap;
            size_t swap_len = un;
            un = vn;
            vn = swap_len;
        }
        vn = sub_raw(v, vn, u, un);
    }
    mh_big odd;
    store(&odd, u, un);
    free(u);
    free(v);
    mh_big_shl(r, &odd, shift);
}

bool mh_big_to_u64(const mh_big *a, uint64_t *out) {
    if (a->len > 1) {
        return false;
    }
    *out = a->len == 0 ? 0 : a->word;
    return true;
}

bool mh_big_parse(mh_big *r, const char *digits, size_t length) {
    mh_big_set_u64(r, 0);
    if (length == 0) {
        return false;
    }
    size_t capacity = length / 19 + 2;
    if (capacity > MH_BIG_LIMBS + 1) {
        return false;
    }
    uint64_t *t = scratch(capacity);
    if (t == NULL) {
        return false;
    }
    size_t used = 0;
    for (size_t i = 0; i < length; i++) {
        if (!isdigit((unsigned char)digits[i])) {
            free(t);
            return false;
        }
        uint64_t carry = (uint64_t)(digits[i] - '0');
        for (size_t j = 0; j < used; j++) {
            mh_u128 product = (mh_u128)t[j] * 10U + carry;
            t[j] = (uint64_t)product;
            carry = (uint64_t)(product >> 64);
        }
        if (carry != 0) {
            t[used++] = carry;
        }
    }
    used = trim_raw(t, used);
    if (used > MH_BIG_LIMBS) {
        free(t);
        return false;
    }
    store(r, t, used);
    free(t);
    return used < 2 || r->heap != NULL;
}

bool mh_parse_integer(const char *text, size_t length, bool *negative, mh_big *magnitude) {
    size_t start = 0;
    size_t end = length;
    while (start < end && isspace((unsigned char)text[start])) {
        start++;
    }
    while (end > start && isspace((unsigned char)text[end - 1])) {
        end--;
    }
    *negative = false;
    if (start < end && (text[start] == '+' || text[start] == '-')) {
        *negative = text[start] == '-';
        start++;
    }
    if (!mh_big_parse(magnitude, text + start, end - start)) {
        return false;
    }
    if (magnitude->len == 0) {
        *negative = false;
    }
    return true;
}

bool mh_parse_i64(const char *text, size_t length, int64_t *out) {
    bool negative;
    mh_big magnitude;
    uint64_t value;
    size_t mark = mh_arena_mark();
    bool parsed = mh_parse_integer(text, length, &negative, &magnitude) &&
                  mh_big_to_u64(&magnitude, &value);
    mh_arena_keep(mark, NULL, 0);
    if (!parsed) {
        return false;
    }
    if (negative) {
        if (value > (uint64_t)INT64_MAX + 1U) {
            return false;
        }
        *out = value == (uint64_t)INT64_MAX + 1U ? INT64_MIN : -(int64_t)value;
        return true;
    }
    if (value > (uint64_t)INT64_MAX) {
        return false;
    }
    *out = (int64_t)value;
    return true;
}

size_t mh_big_digits_bound(const mh_big *a) { return mh_big_bits(a) / 3 + 2; }

size_t mh_big_format(const mh_big *a, char *buffer, size_t size) {
    static const uint64_t chunk = 10000000000000000000ULL;
    size_t bound = mh_big_digits_bound(a) + 19;
    char *digits = malloc(bound);
    uint64_t *t = scratch(a->len);
    if (digits == NULL || t == NULL) {
        free(digits);
        free(t);
        return 0;
    }
    memcpy(t, limbs_of(a), a->len * sizeof *t);
    size_t n = a->len;
    size_t count = 0;
    if (n == 0) {
        digits[count++] = '0';
    }
    while (n != 0) {
        uint64_t rem = 0;
        for (size_t i = n; i-- > 0;) {
            mh_u128 current = ((mh_u128)rem << 64) | t[i];
            t[i] = (uint64_t)(current / chunk);
            rem = (uint64_t)(current % chunk);
        }
        n = trim_raw(t, n);
        for (int d = 0; d < 19; d++) {
            if (n == 0 && rem == 0 && d > 0) {
                break;
            }
            digits[count++] = (char)('0' + rem % 10);
            rem /= 10;
        }
    }
    free(t);
    if (count + 1 > size) {
        free(digits);
        return 0;
    }
    for (size_t i = 0; i < count; i++) {
        buffer[i] = digits[count - 1 - i];
    }
    buffer[count] = '\0';
    free(digits);
    return count;
}

static void set_reduced(mh_frac *r, bool negative, const mh_big *num, const mh_big *den) {
    r->negative = negative && num->len != 0;
    r->num = *num;
    if (num->len == 0) {
        mh_big_set_u64(&r->den, 1);
    } else {
        r->den = *den;
    }
}

void mh_frac_set_parts(mh_frac *r, bool negative, const mh_big *num, const mh_big *den) {
    if (den->len == 0) {
        arith_failed = true;
        r->negative = false;
        mh_big_set_u64(&r->num, 0);
        mh_big_set_u64(&r->den, 1);
        return;
    }
    if (num->len == 0) {
        r->negative = false;
        mh_big_set_u64(&r->num, 0);
        mh_big_set_u64(&r->den, 1);
        return;
    }
    size_t mark = mh_arena_mark();
    mh_big g;
    mh_big rem;
    mh_big n;
    mh_big d;
    mh_big_gcd(&g, num, den);
    mh_big_divmod(&n, &rem, num, &g);
    mh_big_divmod(&d, &rem, den, &g);
    if (d.len == 0) {
        mh_big_set_u64(&d, 1);
        mh_big_set_u64(&n, 0);
    }
    set_reduced(r, negative, &n, &d);
    keep_frac(mark, r);
}

void mh_frac_set_i64(mh_frac *r, int64_t num, int64_t den) {
    mh_big n;
    mh_big d;
    uint64_t un = num < 0 ? (uint64_t)0 - (uint64_t)num : (uint64_t)num;
    uint64_t ud = den < 0 ? (uint64_t)0 - (uint64_t)den : (uint64_t)den;
    mh_big_set_u64(&n, un);
    mh_big_set_u64(&d, ud);
    mh_frac_set_parts(r, (num < 0) != (den < 0), &n, &d);
}

static bool is_one(const mh_big *a) { return a->len == 1 && a->word == 1; }

static void exact_quotient(mh_big *r, const mh_big *a, const mh_big *b) {
    if (is_one(b)) {
        *r = *a;
        return;
    }
    mh_big rem;
    mh_big_divmod(r, &rem, a, b);
}

void mh_frac_add(mh_frac *r, const mh_frac *a, const mh_frac *b) {
    if (a->num.len == 0) {
        *r = *b;
        return;
    }
    if (b->num.len == 0) {
        *r = *a;
        return;
    }
    size_t mark = mh_arena_mark();
    mh_big g;
    mh_big_gcd(&g, &a->den, &b->den);
    mh_big a_scale;
    mh_big b_scale;
    exact_quotient(&a_scale, &b->den, &g);
    exact_quotient(&b_scale, &a->den, &g);
    mh_big x;
    mh_big y;
    mh_big_mul(&x, &a->num, &a_scale);
    mh_big_mul(&y, &b->num, &b_scale);
    mh_big t;
    bool negative;
    if (a->negative == b->negative) {
        mh_big_add(&t, &x, &y);
        negative = a->negative;
    } else if (mh_big_cmp(&x, &y) >= 0) {
        mh_big_sub(&t, &x, &y);
        negative = a->negative;
    } else {
        mh_big_sub(&t, &y, &x);
        negative = b->negative;
    }
    mh_frac result;
    if (t.len == 0) {
        result.negative = false;
        mh_big_set_u64(&result.num, 0);
        mh_big_set_u64(&result.den, 1);
    } else if (is_one(&g)) {
        mh_big den;
        mh_big_mul(&den, &a->den, &b->den);
        set_reduced(&result, negative, &t, &den);
    } else {
        mh_big g2;
        mh_big_gcd(&g2, &t, &g);
        mh_big num;
        mh_big den_part;
        mh_big den;
        exact_quotient(&num, &t, &g2);
        exact_quotient(&den_part, &b->den, &g2);
        mh_big_mul(&den, &b_scale, &den_part);
        set_reduced(&result, negative, &num, &den);
    }
    *r = result;
    keep_frac(mark, r);
}

void mh_frac_neg(mh_frac *r, const mh_frac *a) {
    *r = *a;
    r->negative = a->num.len != 0 && !a->negative;
}

void mh_frac_sub(mh_frac *r, const mh_frac *a, const mh_frac *b) {
    mh_frac negated;
    mh_frac_neg(&negated, b);
    mh_frac_add(r, a, &negated);
}

static void multiply_reduced(mh_frac *r, bool negative, const mh_big *an, const mh_big *ad,
                             const mh_big *bn, const mh_big *bd) {
    if (an->len == 0 || bn->len == 0) {
        r->negative = false;
        mh_big_set_u64(&r->num, 0);
        mh_big_set_u64(&r->den, 1);
        return;
    }
    size_t mark = mh_arena_mark();
    mh_big g1;
    mh_big g2;
    mh_big_gcd(&g1, an, bd);
    mh_big_gcd(&g2, bn, ad);
    mh_big n1;
    mh_big n2;
    mh_big d1;
    mh_big d2;
    exact_quotient(&n1, an, &g1);
    exact_quotient(&d2, bd, &g1);
    exact_quotient(&n2, bn, &g2);
    exact_quotient(&d1, ad, &g2);
    mh_big num;
    mh_big den;
    mh_big_mul(&num, &n1, &n2);
    mh_big_mul(&den, &d1, &d2);
    mh_frac result;
    set_reduced(&result, negative, &num, &den);
    *r = result;
    keep_frac(mark, r);
}

void mh_frac_mul(mh_frac *r, const mh_frac *a, const mh_frac *b) {
    multiply_reduced(r, a->negative != b->negative, &a->num, &a->den, &b->num, &b->den);
}

void mh_frac_div(mh_frac *r, const mh_frac *a, const mh_frac *b) {
    if (b->num.len == 0) {
        arith_failed = true;
        r->negative = false;
        mh_big_set_u64(&r->num, 0);
        mh_big_set_u64(&r->den, 1);
        return;
    }
    multiply_reduced(r, a->negative != b->negative, &a->num, &a->den, &b->den, &b->num);
}

int mh_frac_sign(const mh_frac *a) {
    if (a->num.len == 0) {
        return 0;
    }
    return a->negative ? -1 : 1;
}

bool mh_frac_is_zero(const mh_frac *a) { return a->num.len == 0; }

int mh_frac_cmp(const mh_frac *a, const mh_frac *b) {
    int sa = mh_frac_sign(a);
    int sb = mh_frac_sign(b);
    if (sa != sb) {
        return sa < sb ? -1 : 1;
    }
    if (sa == 0) {
        return 0;
    }
    size_t mark = mh_arena_mark();
    mh_big x;
    mh_big y;
    mh_big_mul(&x, &a->num, &b->den);
    mh_big_mul(&y, &b->num, &a->den);
    int magnitude = mh_big_cmp(&x, &y);
    mh_arena_keep(mark, NULL, 0);
    return sa > 0 ? magnitude : -magnitude;
}

void mh_frac_floor(mh_frac *r, const mh_frac *a) {
    size_t mark = mh_arena_mark();
    mh_big q;
    mh_big rem;
    mh_big one;
    mh_big_divmod(&q, &rem, &a->num, &a->den);
    if (a->negative && rem.len != 0) {
        mh_big_set_u64(&one, 1);
        mh_big_add(&q, &q, &one);
    }
    mh_big_set_u64(&one, 1);
    mh_frac result;
    set_reduced(&result, a->negative, &q, &one);
    *r = result;
    keep_frac(mark, r);
}

bool mh_frac_parse(mh_frac *r, const char *text) {
    size_t length = strlen(text);
    const char *slash = memchr(text, '/', length);
    bool num_negative;
    bool den_negative = false;
    mh_big num;
    mh_big den;
    size_t mark = mh_arena_mark();
    if (slash == NULL) {
        if (!mh_parse_integer(text, length, &num_negative, &num)) {
            mh_arena_keep(mark, NULL, 0);
            return false;
        }
        mh_big_set_u64(&den, 1);
    } else {
        size_t head = (size_t)(slash - text);
        if (!mh_parse_integer(text, head, &num_negative, &num) ||
            !mh_parse_integer(slash + 1, length - head - 1, &den_negative, &den)) {
            mh_arena_keep(mark, NULL, 0);
            return false;
        }
    }
    if (den.len == 0) {
        mh_arena_keep(mark, NULL, 0);
        return false;
    }
    mh_frac result;
    mh_frac_set_parts(&result, num_negative != den_negative, &num, &den);
    *r = result;
    keep_frac(mark, r);
    return true;
}

const char *mh_frac_format(const mh_frac *a, char *buffer, size_t size) {
    size_t used = 0;
    if (size < 4) {
        return NULL;
    }
    if (a->negative) {
        buffer[used++] = '-';
    }
    size_t written = mh_big_format(&a->num, buffer + used, size - used);
    if (written == 0) {
        return NULL;
    }
    used += written;
    if (used + 2 > size) {
        return NULL;
    }
    buffer[used++] = '/';
    written = mh_big_format(&a->den, buffer + used, size - used);
    if (written == 0) {
        return NULL;
    }
    return buffer;
}

char *mh_frac_to_string(const mh_frac *a) {
    size_t size = mh_big_digits_bound(&a->num) + mh_big_digits_bound(&a->den) + 4;
    char *buffer = malloc(size);
    if (buffer == NULL) {
        return NULL;
    }
    if (mh_frac_format(a, buffer, size) == NULL) {
        free(buffer);
        return NULL;
    }
    return buffer;
}
