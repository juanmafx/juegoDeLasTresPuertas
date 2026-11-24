# Deterministic random stream

Every implementation must produce the same 64-bit words, the same bounded draws and the same game
outcomes for the same seed. All arithmetic below is on unsigned 64-bit integers and wraps modulo
2^64 unless stated otherwise. `>>` is a logical shift, `^` is exclusive or, and
`rotl(x, k) = (x << k) | (x >> (64 - k))`.

Golden outputs are in [prng-vectors.json](prng-vectors.json). They were produced by the Python
reference and cross-checked against a separate C transcription of the algorithms below; all 105
vectors agreed.

## Seed range

The command-line contract accepts seeds from 0 to 2^63 - 1 so that every language can parse them
as a signed 64-bit integer. Internally the seed is treated as an unsigned 64-bit value.

## SplitMix64 (seed expansion)

State `x` starts at the seed. Each call:

```text
x = x + 0x9E3779B97F4A7C15
z = x
z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9
z = (z ^ (z >> 27)) * 0x94D049BB133111EB
return z ^ (z >> 31)
```

For seed 0 the first output is `0xE220A8397B1DCDAF` (16294208416658607535).

## xoshiro256** (generation)

The state `s[0..3]` is filled by four consecutive SplitMix64 calls from the seed, in order
`s[0], s[1], s[2], s[3]`. Each call to `next_u64`:

```text
result = rotl(s[1] * 5, 7) * 9
t = s[1] << 17
s[2] = s[2] ^ s[0]
s[3] = s[3] ^ s[1]
s[1] = s[1] ^ s[2]
s[0] = s[0] ^ s[3]
s[2] = s[2] ^ t
s[3] = rotl(s[3], 45)
return result
```

## Bounded integers (Lemire's multiply-and-reject method)

`bounded(n)` returns an integer uniform in `[0, n)` for `1 <= n <= 2^64 - 1`. The product `x * n`
is the full 128-bit product.

```text
x = next_u64()
m = x * n                       (128-bit)
low = m mod 2^64
if low < n:
    threshold = (2^64 - n) mod n
    while low < threshold:
        x = next_u64()
        m = x * n
        low = m mod 2^64
return m >> 64                  (the high 64 bits)
```

The number of words consumed is therefore one, plus one per rejection.

## Weighted choice

`weighted_index(w)` takes non-negative integer weights with a positive total `W`.

```text
r = bounded(W)
c = 0
for i in 0 .. len(w) - 1:
    c = c + w[i]
    if r < c: return i
```

Zero-weight entries are never returned. With all weights equal to 1 the result is exactly
`bounded(len(w))`.

## Weighted sample without replacement

`weighted_sample(items, w, k)` repeats `k` times: `i = weighted_index(current weights)`, append
`items[i]`, then remove position `i` from both lists while keeping the remaining order. Uniform
sampling is this procedure with every weight equal to 1. `k = 0` consumes nothing.

## Shuffle (Fisher-Yates, last index down)

```text
for i from len(a) - 1 down to 1:
    j = bounded(i + 1)
    swap a[i], a[j]
```

The game does not shuffle; the shuffle is part of the contract so implementations can be checked
on it.

## One simulated game

Doors are the integers `0 .. N - 1`, and every candidate list below is in ascending door order.
For each trial, with one generator for the whole run:

1. `prizes = weighted_sample(doors, prior, M)`. A uniform prior is all weights 1.
2. Adversarial host and the pick holds no prize: count `no_offer`, end the trial.
3. Host candidates: random host, all doors except the pick; any other host, all doors that are
   neither the pick nor a prize. Weights: the host weights of those doors for the biased host,
   otherwise 1. `opened = weighted_sample(candidates, weights, K)`.
4. Random host and `opened` contains a prize: count `void`, end the trial.
5. Count `decision`. `remaining` is every door that is neither the pick nor opened.
   `target = remaining[bounded(len(remaining))]`.
6. `switching = bounded(q_den) < q_num`, where `q = q_num / q_den` is the mixed probability in
   lowest terms. This draw happens on every decision trial, whatever the strategies of interest.
7. If an observed reveal is set and `opened` differs from it as a set, end the trial. Otherwise
   count `observed` when an observation is set, and record:
   stay wins when the pick is a prize, switch wins when `target` is a prize, and mixed wins as
   switch when `switching` is true, otherwise as stay.

Steps 5 and 6 draw before step 7 filters, so the stream does not depend on the observation.
