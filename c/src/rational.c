/* Exact rationals over fixed-capacity unsigned integers with 64-bit limbs and checked overflow. */
#include "rational.h"

#include <ctype.h>
#include <string.h>

static bool arith_failed = false;

bool mh_arith_failed(void) { return arith_failed; }

void mh_arith_reset(void) { arith_failed = false; }

static void fail(mh_big *r) {
    arith_failed = true;
    r->len = 0;
}

static void normalize(mh_big *a) {
    while (a->len > 0 && a->limb[a->len - 1] == 0) {
        a->len--;
    }
}

void mh_big_set_u64(mh_big *r, uint64_t value) {
    r->len = value == 0 ? 0 : 1;
    r->limb[0] = value;
}

bool mh_big_is_zero(const mh_big *a) { return a->len == 0; }

int mh_big_cmp(const mh_big *a, const mh_big *b) {
    if (a->len != b->len) {
        return a->len < b->len ? -1 : 1;
    }
    for (size_t i = a->len; i-- > 0;) {
        if (a->limb[i] != b->limb[i]) {
            return a->limb[i] < b->limb[i] ? -1 : 1;
        }
    }
    return 0;
}

size_t mh_big_bits(const mh_big *a) {
    if (a->len == 0) {
        return 0;
    }
    uint64_t top = a->limb[a->len - 1];
    size_t bits = 0;
    while (top != 0) {
        bits++;
        top >>= 1;
    }
    return (a->len - 1) * 64 + bits;
}

static bool bit_at(const mh_big *a, size_t bit) {
    size_t index = bit / 64;
    return index < a->len && ((a->limb[index] >> (bit % 64)) & 1U) != 0;
}

void mh_big_add(mh_big *r, const mh_big *a, const mh_big *b) {
    mh_big t;
    size_t n = a->len > b->len ? a->len : b->len;
    uint64_t carry = 0;
    for (size_t i = 0; i < n; i++) {
        uint64_t x = i < a->len ? a->limb[i] : 0;
        uint64_t y = i < b->len ? b->limb[i] : 0;
        mh_u128 sum = (mh_u128)x + y + carry;
        t.limb[i] = (uint64_t)sum;
        carry = (uint64_t)(sum >> 64);
    }
    t.len = n;
    if (carry != 0) {
        if (n == MH_BIG_LIMBS) {
            fail(r);
            return;
        }
        t.limb[n] = carry;
        t.len = n + 1;
    }
    *r = t;
}

void mh_big_sub(mh_big *r, const mh_big *a, const mh_big *b) {
    if (mh_big_cmp(a, b) < 0) {
        fail(r);
        return;
    }
    mh_big t;
    uint64_t borrow = 0;
    for (size_t i = 0; i < a->len; i++) {
        uint64_t y = i < b->len ? b->limb[i] : 0;
        mh_u128 subtrahend = (mh_u128)y + borrow;
        if ((mh_u128)a->limb[i] >= subtrahend) {
            t.limb[i] = (uint64_t)((mh_u128)a->limb[i] - subtrahend);
            borrow = 0;
        } else {
            t.limb[i] = (uint64_t)(((mh_u128)1 << 64) + a->limb[i] - subtrahend);
            borrow = 1;
        }
    }
    t.len = a->len;
    normalize(&t);
    *r = t;
}

void mh_big_mul(mh_big *r, const mh_big *a, const mh_big *b) {
    if (a->len == 0 || b->len == 0) {
        r->len = 0;
        return;
    }
    if (a->len + b->len - 1 > MH_BIG_LIMBS) {
        fail(r);
        return;
    }
    uint64_t wide[2 * MH_BIG_LIMBS];
    size_t n = a->len + b->len;
    memset(wide, 0, n * sizeof wide[0]);
    for (size_t i = 0; i < a->len; i++) {
        uint64_t carry = 0;
        for (size_t j = 0; j < b->len; j++) {
            mh_u128 product = (mh_u128)a->limb[i] * b->limb[j] + wide[i + j] + carry;
            wide[i + j] = (uint64_t)product;
            carry = (uint64_t)(product >> 64);
        }
        wide[i + b->len] = carry;
    }
    while (n > 0 && wide[n - 1] == 0) {
        n--;
    }
    if (n > MH_BIG_LIMBS) {
        fail(r);
        return;
    }
    memcpy(r->limb, wide, n * sizeof wide[0]);
    r->len = n;
}

void mh_big_shl(mh_big *r, const mh_big *a, size_t bits) {
    if (a->len == 0) {
        r->len = 0;
        return;
    }
    if (mh_big_bits(a) + bits > MH_BIG_BITS) {
        fail(r);
        return;
    }
    mh_big t;
    size_t words = bits / 64;
    unsigned shift = (unsigned)(bits % 64);
    size_t n = a->len + words + 1;
    if (n > MH_BIG_LIMBS) {
        n = MH_BIG_LIMBS;
    }
    memset(t.limb, 0, n * sizeof t.limb[0]);
    for (size_t i = 0; i < a->len; i++) {
        size_t target = i + words;
        t.limb[target] |= a->limb[i] << shift;
        if (shift != 0 && target + 1 < n) {
            t.limb[target + 1] |= a->limb[i] >> (64 - shift);
        }
    }
    t.len = n;
    normalize(&t);
    *r = t;
}

void mh_big_shr(mh_big *r, const mh_big *a, size_t bits) {
    size_t words = bits / 64;
    unsigned shift = (unsigned)(bits % 64);
    if (words >= a->len) {
        r->len = 0;
        return;
    }
    mh_big t;
    size_t n = a->len - words;
    for (size_t i = 0; i < n; i++) {
        uint64_t low = a->limb[i + words] >> shift;
        uint64_t high = 0;
        if (shift != 0 && i + words + 1 < a->len) {
            high = a->limb[i + words + 1] << (64 - shift);
        }
        t.limb[i] = low | high;
    }
    t.len = n;
    normalize(&t);
    *r = t;
}

static size_t trailing_zeros(const mh_big *a) {
    size_t count = 0;
    for (size_t i = 0; i < a->len; i++) {
        if (a->limb[i] == 0) {
            count += 64;
            continue;
        }
        uint64_t word = a->limb[i];
        while ((word & 1U) == 0) {
            count++;
            word >>= 1;
        }
        return count;
    }
    return count;
}

void mh_big_divmod(mh_big *quotient, mh_big *remainder, const mh_big *a, const mh_big *b) {
    if (b->len == 0) {
        fail(quotient);
        fail(remainder);
        return;
    }
    mh_big q;
    mh_big rem;
    q.len = a->len;
    memset(q.limb, 0, a->len * sizeof q.limb[0]);
    rem.len = 0;
    for (size_t bit = mh_big_bits(a); bit-- > 0;) {
        uint64_t carry = 0;
        for (size_t i = 0; i < rem.len; i++) {
            uint64_t next = rem.limb[i] >> 63;
            rem.limb[i] = (rem.limb[i] << 1) | carry;
            carry = next;
        }
        if (carry != 0) {
            if (rem.len == MH_BIG_LIMBS) {
                fail(quotient);
                fail(remainder);
                return;
            }
            rem.limb[rem.len++] = carry;
        }
        if (bit_at(a, bit)) {
            if (rem.len == 0) {
                rem.limb[0] = 0;
                rem.len = 1;
            }
            rem.limb[0] |= 1U;
        }
        if (mh_big_cmp(&rem, b) >= 0) {
            mh_big_sub(&rem, &rem, b);
            q.limb[bit / 64] |= (uint64_t)1 << (bit % 64);
        }
    }
    normalize(&q);
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
    mh_big u = *a;
    mh_big v = *b;
    size_t zu = trailing_zeros(&u);
    size_t zv = trailing_zeros(&v);
    size_t shift = zu < zv ? zu : zv;
    mh_big_shr(&u, &u, zu);
    while (v.len != 0) {
        mh_big_shr(&v, &v, trailing_zeros(&v));
        if (mh_big_cmp(&u, &v) > 0) {
            mh_big swap = u;
            u = v;
            v = swap;
        }
        mh_big_sub(&v, &v, &u);
    }
    mh_big_shl(r, &u, shift);
}

bool mh_big_to_u64(const mh_big *a, uint64_t *out) {
    if (a->len > 1) {
        return false;
    }
    *out = a->len == 0 ? 0 : a->limb[0];
    return true;
}

static bool mul_small_add(mh_big *r, uint64_t factor, uint64_t addend) {
    uint64_t carry = addend;
    for (size_t i = 0; i < r->len; i++) {
        mh_u128 product = (mh_u128)r->limb[i] * factor + carry;
        r->limb[i] = (uint64_t)product;
        carry = (uint64_t)(product >> 64);
    }
    if (carry != 0) {
        if (r->len == MH_BIG_LIMBS) {
            return false;
        }
        r->limb[r->len++] = carry;
    }
    return true;
}

bool mh_big_parse(mh_big *r, const char *digits, size_t length) {
    r->len = 0;
    if (length == 0) {
        return false;
    }
    bool saw_digit = false;
    for (size_t i = 0; i < length; i++) {
        char c = digits[i];
        if (c == '_') {
            if (!saw_digit || i + 1 >= length || !isdigit((unsigned char)digits[i + 1])) {
                return false;
            }
            continue;
        }
        if (!isdigit((unsigned char)c)) {
            return false;
        }
        saw_digit = true;
        if (!mul_small_add(r, 10, (uint64_t)(c - '0'))) {
            r->len = 0;
            return false;
        }
    }
    return saw_digit;
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
    if (!mh_parse_integer(text, length, &negative, &magnitude) ||
        !mh_big_to_u64(&magnitude, &value)) {
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

size_t mh_big_format(const mh_big *a, char *buffer, size_t size) {
    static const uint64_t chunk = 10000000000000000000ULL;
    char digits[MH_BIG_BITS / 3 + 2];
    size_t count = 0;
    mh_big t = *a;
    if (t.len == 0) {
        digits[count++] = '0';
    }
    while (t.len != 0) {
        uint64_t rem = 0;
        for (size_t i = t.len; i-- > 0;) {
            mh_u128 current = ((mh_u128)rem << 64) | t.limb[i];
            t.limb[i] = (uint64_t)(current / chunk);
            rem = (uint64_t)(current % chunk);
        }
        normalize(&t);
        for (int d = 0; d < 19; d++) {
            if (t.len == 0 && rem == 0 && d > 0) {
                break;
            }
            digits[count++] = (char)('0' + rem % 10);
            rem /= 10;
        }
    }
    if (count + 1 > size) {
        return 0;
    }
    for (size_t i = 0; i < count; i++) {
        buffer[i] = digits[count - 1 - i];
    }
    buffer[count] = '\0';
    return count;
}

void mh_frac_set_parts(mh_frac *r, bool negative, const mh_big *num, const mh_big *den) {
    if (den->len == 0) {
        arith_failed = true;
        r->negative = false;
        r->num.len = 0;
        mh_big_set_u64(&r->den, 1);
        return;
    }
    if (num->len == 0) {
        r->negative = false;
        r->num.len = 0;
        mh_big_set_u64(&r->den, 1);
        return;
    }
    mh_big g;
    mh_big rem;
    mh_big n;
    mh_big d;
    mh_big_gcd(&g, num, den);
    mh_big_divmod(&n, &rem, num, &g);
    mh_big_divmod(&d, &rem, den, &g);
    if (d.len == 0) {
        mh_big_set_u64(&d, 1);
        n.len = 0;
    }
    r->negative = negative && n.len != 0;
    r->num = n;
    r->den = d;
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

void mh_frac_add(mh_frac *r, const mh_frac *a, const mh_frac *b) {
    mh_big x;
    mh_big y;
    mh_big den;
    mh_big num;
    bool negative;
    mh_big_mul(&x, &a->num, &b->den);
    mh_big_mul(&y, &b->num, &a->den);
    mh_big_mul(&den, &a->den, &b->den);
    if (a->negative == b->negative) {
        mh_big_add(&num, &x, &y);
        negative = a->negative;
    } else if (mh_big_cmp(&x, &y) >= 0) {
        mh_big_sub(&num, &x, &y);
        negative = a->negative;
    } else {
        mh_big_sub(&num, &y, &x);
        negative = b->negative;
    }
    mh_frac_set_parts(r, negative, &num, &den);
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

void mh_frac_mul(mh_frac *r, const mh_frac *a, const mh_frac *b) {
    mh_big num;
    mh_big den;
    mh_big_mul(&num, &a->num, &b->num);
    mh_big_mul(&den, &a->den, &b->den);
    mh_frac_set_parts(r, a->negative != b->negative, &num, &den);
}

void mh_frac_div(mh_frac *r, const mh_frac *a, const mh_frac *b) {
    mh_big num;
    mh_big den;
    mh_big_mul(&num, &a->num, &b->den);
    mh_big_mul(&den, &a->den, &b->num);
    mh_frac_set_parts(r, a->negative != b->negative, &num, &den);
}

int mh_frac_sign(const mh_frac *a) {
    if (a->num.len == 0) {
        return 0;
    }
    return a->negative ? -1 : 1;
}

bool mh_frac_is_zero(const mh_frac *a) { return a->num.len == 0; }

int mh_frac_cmp(const mh_frac *a, const mh_frac *b) {
    mh_frac difference;
    mh_frac_sub(&difference, a, b);
    return mh_frac_sign(&difference);
}

void mh_frac_floor(mh_frac *r, const mh_frac *a) {
    mh_big q;
    mh_big rem;
    mh_big one;
    mh_big_divmod(&q, &rem, &a->num, &a->den);
    if (a->negative && rem.len != 0) {
        mh_big_set_u64(&one, 1);
        mh_big_add(&q, &q, &one);
    }
    mh_big_set_u64(&one, 1);
    mh_frac_set_parts(r, a->negative, &q, &one);
}

bool mh_frac_parse(mh_frac *r, const char *text) {
    size_t length = strlen(text);
    const char *slash = memchr(text, '/', length);
    bool num_negative;
    bool den_negative = false;
    mh_big num;
    mh_big den;
    if (slash == NULL) {
        if (!mh_parse_integer(text, length, &num_negative, &num)) {
            return false;
        }
        mh_big_set_u64(&den, 1);
    } else {
        size_t head = (size_t)(slash - text);
        if (!mh_parse_integer(text, head, &num_negative, &num) ||
            !mh_parse_integer(slash + 1, length - head - 1, &den_negative, &den)) {
            return false;
        }
    }
    if (den.len == 0) {
        return false;
    }
    mh_frac_set_parts(r, num_negative != den_negative, &num, &den);
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
