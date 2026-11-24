# monty-lab in C

A C17 implementation of the shared Monty Hall decision lab described in [`../spec/`](../spec/).
It has no third-party dependencies. The Python package in [`../python/`](../python/) is the
reference implementation.

## Layout

| Path | Contents |
| --- | --- |
| `src/rational.c` | Exact fractions over fixed-capacity unsigned integers |
| `src/prng.c` | SplitMix64, xoshiro256**, Lemire bounded draws, weighted choice, Fisher-Yates |
| `src/model.c` | Scenario limits and validation |
| `src/solver.c` | Exact solver: closed forms, plus enumeration for weighted priors and observed reveals |
| `src/optimum.c` | Value curve `V(K) = P(win) - c*K`, discrete optimum, least-squares parabola |
| `src/simulator.c` | Seeded Monte Carlo simulator and the Wilson 95% interval |
| `src/json.c`, `src/cli.c`, `src/main.c` | JSON output and the `monty-lab` command line |
| `tests/test_main.c` | Self-contained unit test runner |
| `tools/report.sh` | Writes `reports/` from a real run |

## Exact arithmetic

Fractions are reduced and use 64-bit limbs, with `unsigned __int128` for intermediate products.
Each integer holds at most 64 limbs (4096 bits). The specification needs more than 64 bits: the
64-door optimum curve has numerators and denominators of about 190 bits. Every addition,
multiplication and shift checks the capacity. If a result would exceed it, the command exits
with code 2 and prints `error: exact arithmetic exceeds the 4096-bit integer capacity`, and
nothing goes to standard output. No scenario in `spec/scenarios.json` comes close to the
capacity. A `--mixed` or `--cost` fraction with numbers of about a thousand digits can reach it,
and the Python reference, which has unbounded integers, would still answer that input.

## Build and test

Requires GCC (or another C17 compiler that supports `unsigned __int128`), make, and Python 3 for
the conformance suite.

```bash
make                       # build/monty-lab
make test                  # unit tests, plain build and AddressSanitizer + UBSan build
make conformance           # ../tools/conformance.py against build/monty-lab
make conformance-sanitize  # the same against the sanitized binary
make report                # all of the above, written to reports/test-report.md
```

All builds use `-std=c17 -Wall -Wextra -Werror -pedantic -Wshadow -Wconversion
-Wsign-conversion`.

## Usage

The command line follows [`../spec/cli.md`](../spec/cli.md): subcommands `exact`, `simulate`,
`optimum` and `prng`, and JSON on standard output.

```bash
./build/monty-lab exact --doors 3 --host informed
./build/monty-lab exact --doors 5 --prizes 2 --reveals 2 --host biased \
    --host-weights 1,2,3,4,5 --observed 1,2
./build/monty-lab simulate --host random --seed 1 --trials 1000
./build/monty-lab optimum --doors 5 --strategy switch --cost 1/20
./build/monty-lab prng --seed 0 --kind words --count 4
```

`optimum` reports two things about exploration. One is the exact best number of reveals `K*`.
The other is the least-squares parabola fitted to `V(K)`, the "hypothetical optimum parabola".
For the fit it gives the vertex, the vertex's offset from `K*`, the rounded vertex with its
regret, and the `K` the parabola would choose. With `--doors 5 --strategy switch --cost 1/20`,
the fit is convex. Its vertex at `K = 16/25` is a minimum, and rounding it would lose `13/30` of
a prize. The parabola's highest feasible point is still the exact optimum, `K* = 3`.

Exit codes: 0 for success, 2 for invalid input or exceeded arithmetic capacity, 141 when
standard output closes early.
