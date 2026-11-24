# monty-lab command-line contract

Every implementation ships one program, called `monty-lab` here, with four subcommands. Flags,
defaults, validation, exit codes and JSON output are identical across languages. Output is one
JSON document on standard output, described by [cli-output.schema.json](cli-output.schema.json).
Whitespace and key order in the output are free; values are not.

The Python reference runs as `python -m monty_hall.lab` or `monty-lab` from the `python/`
project. `tools/conformance.py --cli "<command>"` checks any implementation against this file.

## The model

A game has `N` doors numbered `0 .. N - 1`, `M` prizes, a prior over prize placement, the
player's pick, `K` doors opened by the host, a host policy and a mixed-strategy probability `q`.

- **Prior.** Uniform, or one non-negative integer weight per door. Prizes are placed by drawing
  `M` doors one at a time without replacement, each draw proportional to the weights of the doors
  not yet drawn.
- **informed host.** Never opens the pick or a prize door; opens `K` doors uniformly among the
  rest.
- **random host.** Opens `K` doors uniformly among all doors except the pick, without knowing
  where the prizes are. Games where a prize is revealed are **void**.
- **biased host.** Like informed, but draws its `K` doors one at a time without replacement in
  proportion to positive integer host weights.
- **adversarial host.** When the pick holds no prize the game ends with **no offer**. Otherwise
  it opens `K` doors like the informed host and offers the switch.
- **Strategies.** `stay`; `switch`, uniformly to one of the `N - 1 - K` closed doors other than
  the pick; `mixed`, which switches with probability `q`.

### What the probabilities mean

- `outcomes.decision` is the probability that the player reaches the stay-or-switch decision:
  1 for informed and biased, the probability of no void for random, the probability of an offer
  for adversarial. `void` and `no_offer` complete it to 1.
- `win.*` are probabilities of winning **conditional on reaching the decision**. With an
  observed reveal they are also conditional on the host having opened exactly that set, and
  `outcomes.observed` is the joint probability of reaching the decision with that reveal.
- When the conditioning event has probability 0, the conditional values are `null`.
- `prize_at_pick` is the prior probability that the pick holds a prize.

For the random host this is the standard "conditional on no prize revealed" reading. For the
adversarial host it is "given that a switch was offered".

## Fractions

Exact values are strings `"numerator/denominator"` in lowest terms with a positive denominator,
always including the slash: `"0/1"`, `"1/1"`, `"-3/20"`. Flags that take a fraction accept
`a/b` or an integer `a`, as defined under [Input syntax](#input-syntax). Implementations need
arbitrary-precision integers for exact results: denominators exceed 64 bits for larger games, and
with ten doors and large prior weights an exact value can run to thousands of digits. Integers of
a fixed small width, such as 64 or 4,096 bits, are not enough.

## Input syntax

These rules are part of the contract; every implementation accepts and rejects the same inputs.

- **Arguments.** The subcommand comes first, and the arguments after it are read left to right.
  `-h` and `--help` ask for help. Any other argument that starts with `--` and contains no `=` is
  a flag name and takes the next argument as its value, even when that argument starts with `-`;
  `--name=value` is the same flag in one argument. If help was asked for anywhere, the usage text
  is printed and the exit code is 0 before anything else is checked. Names are written in full;
  abbreviations such as `--door` are invalid. A flag given more than once keeps its last value.
  `--version` is accepted only as the first argument.
- **Integers.** Optional surrounding ASCII whitespace (space, tab, line feed, vertical tab, form
  feed, carriage return), an optional `+` or `-`, then one or more ASCII digits `0-9`. Leading
  zeros are allowed. Nothing else is: no digit separators such as `1_000`, no non-ASCII digits or
  whitespace, no decimal point.
- **Integer lists.** Integers separated by commas. An empty or all-whitespace value is the empty
  list; an empty item, as in `1,,2` or `1,2,`, is invalid.
- **Fractions.** An integer, or two integers separated by one `/`, the second not zero. Each of the
  two integers, as written, must lie between `-(2^63 - 1)` and `2^63 - 1`. The value is then
  reduced, so `-1/-2` is `1/2` and `-0/5` is `0/1`.
- **Keywords.** `uniform`, host names, strategies and PRNG kinds are lowercase and matched
  exactly, without surrounding whitespace.

## Shared scenario flags (exact, simulate, optimum)

| Flag | Default | Meaning |
| --- | --- | --- |
| `--doors N` | `3` | 3 to 64 |
| `--prizes M` | `1` | 1 to `N - 2` |
| `--prior P` | `uniform` | `uniform` or `N` comma-separated integers from 0 to 1,000,000 |
| `--pick D` | `0` | 0 to `N - 1` |
| `--host H` | `informed` | `informed`, `random`, `biased`, `adversarial` |
| `--host-weights W` | none | `N` comma-separated integers from 1 to 1,000,000; required for, and only for, `biased` |
| `--mixed Q` | `1/2` | fraction from 0 to 1 |

`exact` and `simulate` also take:

| Flag | Default | Meaning |
| --- | --- | --- |
| `--reveals K` | `1` | 0 to `N - M - 1` |
| `--observed D,...` | none | exactly `K` distinct doors, none equal to the pick; empty string when `K = 0` |

### Validation

Any of the following exits with code 2, prints nothing on standard output and prints a message
on standard error (`error: ...` for validation errors):

- a value outside the ranges above, or an integer, list, fraction, keyword or flag that breaks
  the [input syntax](#input-syntax);
- a prior with fewer than `M` positive weights, or a weight list whose length is not `N`;
- host weights given without `--host biased`, or missing with it;
- `exact` or `optimum` with an explicit prior, or `exact` with `--observed`, when `N > 10`
  (the enumeration limit; `simulate` has no such limit);
- `optimum` when some feasible `K` has no decision (adversarial host and a pick with prior
  weight 0);
- `simulate` with `--trials` outside 1 to 100,000,000 or `--seed` outside 0 to 2^63 - 1.

`K <= N - M - 1` guarantees that the informed, biased and adversarial hosts always have `K`
valid doors and that at least `M` closed doors remain besides the pick.

## exact

```text
monty-lab exact [scenario flags] [--reveals K] [--observed D,...]
```

```json
{
  "command": "exact",
  "scenario": { "doors": 3, "prizes": 1, "prior": "uniform", "pick": 0, "reveals": 1,
                "host": "informed", "host_weights": null, "mixed": "1/2", "observed": null },
  "prize_at_pick": "1/3",
  "outcomes": { "decision": "1/1", "void": "0/1", "no_offer": "0/1", "observed": null },
  "win": { "stay": "1/3", "switch": "2/3", "mixed": "1/2" }
}
```

`scenario` echoes the normalized input: `observed` sorted ascending, `mixed` reduced.

## simulate

```text
monty-lab simulate [scenario flags] [--reveals K] [--observed D,...] --seed S [--trials T]
```

`--seed` is required; `--trials` defaults to 100,000. The run follows [prng.md](prng.md) exactly,
so `counts`, `sample_size` and every `wins` value must be bit-identical across languages.

```json
{
  "command": "simulate",
  "scenario": { "...": "as for exact" },
  "seed": 1,
  "trials": 1000,
  "counts": { "decision": 675, "void": 325, "no_offer": 0, "observed": null },
  "sample_size": 675,
  "strategies": {
    "stay":   { "wins": 343, "rate": 0.5081, "wilson95": [0.4705, 0.5457] },
    "switch": { "wins": 332, "rate": 0.4919, "wilson95": [0.4543, 0.5295] },
    "mixed":  { "wins": 346, "rate": 0.5126, "wilson95": [0.4749, 0.5501] }
  }
}
```

This is `simulate --host random --seed 1 --trials 1000` from the Python reference, with floats
shortened to four decimals here. `sample_size` is `counts.observed`
when an observation is set, otherwise `counts.decision`. `rate` is `wins / sample_size`.
`wilson95` is the Wilson score interval with `z = 1.959963984540054`; when `wins` is 0 the lower
bound is exactly 0, and when `wins` equals `sample_size` the upper bound is exactly 1. With an
empty sample, `rate` and `wilson95` are `null`. Floating-point fields are compared with a
tolerance of 1e-9.

## optimum

```text
monty-lab optimum [scenario flags] --strategy stay|switch|mixed [--cost C]
```

`--reveals` and `--observed` are not accepted. `--cost` is a non-negative fraction, default 0, in
units of the prize value. For every feasible `K = 0 .. N - M - 1`:

```text
V(K) = P(win | strategy, K) - C * K
```

where `P(win | ...)` is the decision-conditional probability that `exact` reports.

- `curve` lists `{reveals, win, value}` for each `K`.
- `optimum` is the exact discrete maximum `K*` and `V(K*)`; ties go to the smallest `K`.
- `parabola` is the least-squares quadratic `a K^2 + b K + c` fitted exactly (rational normal
  equations) to the points `(K, V(K))`, the **hypothetical optimum parabola**. It is `null` when
  there are fewer than three feasible `K`.
  - `shape` is `concave` (`a < 0`), `convex` (`a > 0`) or `linear` (`a = 0`).
  - `vertex` is `{reveals: -b / (2a), value: c - b^2 / (4a)}`, `null` when `a = 0`. For a convex
    fit the vertex is a minimum of the parabola, not a maximum.
  - `vertex_offset` is `vertex.reveals - K*` and `vertex_value_gap` is `vertex.value - V(K*)`.
  - `rounded_vertex` is the vertex rounded to `floor(vertex + 1/2)` and clamped to the feasible
    range, with its exact value and `regret = V(K*) - V(rounded)`.
  - `fitted_choice` is the feasible `K` where the fitted parabola is highest (smallest on ties),
    with its exact value and regret. This is the decision the parabola would recommend.
  - `residual_sum_of_squares` is the exact fit error.

```json
{
  "command": "optimum",
  "scenario": { "...": "as for exact, with reveals and observed null" },
  "strategy": "switch",
  "cost": "1/20",
  "curve": [ { "reveals": 0, "win": "1/5", "value": "1/5" } ],
  "optimum": { "reveals": 3, "value": "13/20" },
  "parabola": {
    "a": "1/12", "b": "-8/75", "c": "21/100", "shape": "convex",
    "residual_sum_of_squares": "1/500",
    "vertex": { "reveals": "16/25", "value": "1319/7500" },
    "vertex_offset": "-59/25", "vertex_value_gap": "-889/1875",
    "rounded_vertex": { "reveals": 1, "value": "13/60", "regret": "13/30" },
    "fitted_choice": { "reveals": 3, "value": "13/20", "regret": "0/1" }
  }
}
```

This is `optimum --doors 5 --strategy switch --cost 1/20` with `curve` shortened to its first
point. The fit is convex, so its vertex at `K = 16/25` is the parabola's minimum; the parabola
still recommends the right decision (`fitted_choice` is `K* = 3`), while rounding the vertex
would lose `13/30` of a prize.

## prng

```text
monty-lab prng --seed S --kind splitmix|words|bounded|weighted|shuffle
               [--count C] [--bound B] [--weights W] [--size Z]
```

| Kind | Extra flags | `values` |
| --- | --- | --- |
| `splitmix` | `--count` | the first `C` SplitMix64 outputs from the seed, decimal strings |
| `words` | `--count` | the first `C` xoshiro256** words, decimal strings |
| `bounded` | `--count`, `--bound` (1 to 2^63 - 1) | `C` draws of `bounded(B)` |
| `weighted` | `--count`, `--weights` | `C` draws of `weighted_index(W)` |
| `shuffle` | `--size` (1 to 10,000) | `0 .. Z - 1` after one Fisher-Yates shuffle |

`--count` is 1 to 100,000, default 1. `--weights` is a non-empty list of non-negative integers
whose total is from 1 to 2^63 - 1. The output also echoes `seed`, `kind` and the extra flag
that was used (`bound`, `weights` or `size`). Words are strings because they exceed the integer
range many JSON parsers handle exactly.

## Exit codes

| Code | Meaning |
| --- | --- |
| 0 | Success |
| 2 | Invalid input |
| 141 | Standard output closed early (Python reference; other languages should match where the runtime allows) |
