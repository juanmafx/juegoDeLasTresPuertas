# juegoDeLasTresPuertas

Exact and reproducible analysis of the Monty Hall problem and its generalizations, built as a
decision lab with one shared specification and a Python reference implementation. The repository
name is Spanish for "the game of the three doors".

## Purpose

The Monty Hall problem is a standard example of how conditioning on information changes a
probability. A car is hidden behind one of three doors. You pick a door, the host opens a
different door showing a goat, and you may switch. Switching wins 2/3 of the time, which many
people find counterintuitive.

## Why this project exists

The project started as a short script demonstrating that switching helps. It is now a small,
verifiable lab for a more general question: when someone reveals information before you decide,
how much is that information worth, and what does it depend on? The answer depends on how the
host chooses what to reveal, so the host is an explicit, swappable policy, and every simulated
number can be checked against an exact fraction.

## What it does

- Models `N` doors (3 to 64), `M` prizes, a uniform or weighted prior over prize placement, the
  player's pick and `K` reveals.
- Four host policies: `informed` (classic), `random` (may reveal a prize; those games are void),
  `biased` (prefers some doors) and `adversarial` (offers a switch only when you are right).
- Three strategies: `stay`, `switch` and `mixed(q)`.
- Exact results as reduced fractions, including results conditional on which doors were opened.
- A deterministic simulator whose random stream is fully specified, so other languages can
  reproduce its win counts bit for bit.
- An exploration-cost model: with a cost `c` per reveal, `V(K) = P(win) - c*K`, its exact optimum
  over `K`, and a least-squares parabola fitted to `V(K)` (the "hypothetical optimum parabola").

| Doors | Reveals | Host | Stay | Switch |
| ---: | ---: | --- | ---: | ---: |
| 3 | 1 | informed | 1/3 | 2/3 |
| 3 | 1 | random, no prize revealed | 1/2 | 1/2 |
| 3 | 1 | adversarial, switch offered | 1/1 | 0/1 |
| 3 | 1 | biased, prefers door 1 with p = 3/4, door 1 opened | 3/7 | 4/7 (= 1/(1+p)) |
| 3 | 1 | biased, prefers door 1 with p = 3/4, door 2 opened | 1/5 | 4/5 (= 1/(2-p)) |
| 5 | 1 | informed | 1/5 | 4/15 |
| 64 | 62 | informed | 1/64 | 63/64 |

## The hypothetical optimum parabola

The idea was to treat reveals as exploration with a price and to approximate the trade-off by a
parabola whose vertex marks the best amount of exploration. The lab computes both the exact
discrete optimum and that parabola, and reports how far apart they are. The result so far is that,
in this model, the trade-off is not shaped like an inverted parabola.

For a uniform prior the switch probability has the form `A + B / (N - 1 - K)` (informed, biased
and adversarial hosts) or `M / (N - K)` (random host), and staying is constant or of the same
form. These are convex in `K`, so `V(K)` is convex and its maximum is always at `K = 0` or at the
largest feasible `K`: either do not explore or explore as much as possible. A property test
checks this on generated games. A one-off random search during development, over 2,925 games
with weighted priors and all four hosts, found no concave fit and no interior optimum either, but
that search is not committed and is not a proof for weighted priors.

So the fitted parabola is convex or linear in every case examined, and its vertex is a minimum.
The lab still reports the vertex, its distance from the exact optimum, the regret of acting on
the rounded vertex, and the choice the parabola itself would recommend. For ten doors with
`c = 1/100`, the exact optimum is `K* = 8` with `V = 41/50`; the parabola's vertex is at
`K = 241371/103790` (about 2.33), and rounding it to `K = 2` would lose `249/350` of a prize,
while the highest point of the fitted parabola over the feasible range is `K = 8`, the right
answer.

## Repository layout

```text
spec/              Shared specification: CLI contract, PRNG, JSON Schemas, scenarios, vectors
tools/
  enumerate.py     Independent brute-force oracle for spec/scenarios.json
  conformance.py   Checks any language's CLI against spec/
python/            Python reference implementation (package monty_hall)
  src/monty_hall/
    lab/           Decision lab: model, PRNG, exact solver, simulator, optimum, CLI contract
    domain/ analysis/ simulation/ persistence/ cli/
                   The original two-policy study tool with optional SQLite storage
  tests/           Unit, property-based, statistical, integration, and spec suites
  tools/           Test report generator, spec data generator
  db/schema.sql    Optional database schema
docs/              Architecture and security notes
```

There is no frontend or backend: these are command-line tools and a library. See
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and [spec/README.md](spec/README.md).

## Quick start

Requires Python 3.13 or newer and [uv](https://docs.astral.sh/uv/). There are no runtime
dependencies.

```bash
git clone https://github.com/juanmafx/juegoDeLasTresPuertas.git
cd juegoDeLasTresPuertas/python
uv sync --locked
uv run monty-lab exact
uv run monty-lab simulate --seed 42 --trials 100000
uv run monty-lab optimum --doors 10 --strategy switch --cost 1/100
```

## Usage guide

### monty-lab, the cross-language contract

```bash
uv run monty-lab exact --doors 5 --prizes 2 --reveals 2
uv run monty-lab exact --host biased --host-weights 1,3,1 --observed 1
uv run monty-lab exact --doors 4 --prior 3,1,1,1 --host random --reveals 2
uv run monty-lab simulate --host adversarial --seed 7 --trials 50000 --mixed 1/3
uv run monty-lab optimum --doors 6 --host random --strategy switch --cost 1/30
uv run monty-lab prng --seed 0 --kind words --count 4
```

Output is always JSON. The complete flag list, validation rules, output fields and exit codes are
in [spec/cli.md](spec/cli.md). Explicit priors and observed reveals use exact enumeration, which is
limited to 10 doors; simulation has no such limit.

### monty-hall, the original study tool

```bash
uv run monty-hall exact --doors 5 --opened 1
uv run monty-hall exact --host random --enumerate --format json
uv run monty-hall simulate --host random --trials 500000 --seed 7
uv run monty-hall simulate --trials 100000 --seed 1 --db runs.sqlite3
uv run monty-hall history --db runs.sqlite3 --limit 10
```

It supports the `informed` and `random` hosts with one prize, prints text or JSON, and can store
runs in SQLite. It uses Python's `random` module, so its streams are not part of the
cross-language contract.

| Flag | Commands | Default | Valid values |
| --- | --- | --- | --- |
| `--doors` | `simulate`, `exact` | `3` | 3 to 1024; `--enumerate` allows at most 9 |
| `--opened` | `simulate`, `exact` | `1` | 1 to doors - 2 |
| `--host` | `simulate`, `exact` | `informed` | `informed`, `random` |
| `--format` | `simulate`, `exact` | `text` | `text`, `json` |
| `--trials` | `simulate` | `100000` | 1 to 100,000,000 |
| `--seed` | `simulate` | generated and printed | 0 to 2^63 - 1 |
| `--confidence` | `simulate` | `0.95` | strictly between 0 and 1 |
| `--db` | `simulate`, `history` | none | SQLite file path |
| `--enumerate` | `exact` | off | flag |
| `--limit` | `history` | `20` | 1 to 1000 |

Both programs exit with code 2 and a message on standard error for invalid input, and with code
141 if the reader of standard output closes early. Neither reads environment variables or
configuration files.

## Database

Persistence is **optional** and belongs to `monty-hall`. [python/db/schema.sql](python/db/schema.sql)
is applied automatically when `--db` is used with `simulate`. `history` opens the file read-only.
Both commands refuse a file whose run tables, views, indexes, or triggers differ from that schema.

## Testing

From `python/`:

```bash
uv run pytest
uv run ruff check . ../tools
uv run ruff format --check . ../tools
uv run mypy
uv run mypy --strict ../tools
uv run python -I ../tools/enumerate.py ../spec/scenarios.json --check
uv run python tools/write_spec_data.py --check
uv run python -I ../tools/conformance.py --cli "python -m monty_hall.lab"
uv run python tools/generate_test_report.py
```

The suite covers input validation, PRNG vectors, property-based invariants (including that
averaging over every possible reveal recovers the unconditional result), agreement with the
independent enumerator on every scenario, statistical convergence with fixed seeds, JSON Schema
validation of every output, the database, and both CLIs. The latest recorded run is in
[python/reports/tests/test-report.md](python/reports/tests/test-report.md).

`tools/conformance.py` takes the command that runs any implementation's CLI. It checks exact
fractions for equality, simulation counts for bit-identical equality with
`spec/simulation-reference.json`, PRNG vectors, error handling, and whether the exact values fall
inside the Wilson 95% intervals. About one interval in twenty is expected to miss by chance, so it
fails only when misses exceed what a 0.1% binomial tail allows, or when any deviation reaches
five standard errors.

## Reproducibility

`monty-lab` uses SplitMix64, xoshiro256** and Lemire's bounded draws exactly as written in
[spec/prng.md](spec/prng.md), so a seed and scenario give the same counts in any language and any
Python version. `monty-hall` keeps its original behaviour: the same seed, configuration and Python
version produce the same result. Statistical tests use fixed seeds, and property tests run
derandomized.

## Security

The tools make no network calls, have no runtime dependencies, use parameterized SQL, bound their
numeric options, and refuse SQLite files whose run tables or views differ from the expected schema.
Neither random generator is cryptographically secure, and none needs to be. See
[SECURITY.md](SECURITY.md) and [docs/SECURITY_AUDIT.md](docs/SECURITY_AUDIT.md).

## Project history

Originally created in 2019 by Juan Manuel Ramallo as a single Python script. Modernized in 2026.
The Monty Hall problem itself is not original to this project: it was posed by Steve Selvin in 1975
and popularized by Marilyn vos Savant. The "Monty Fall" name comes from Jeffrey S. Rosenthal.

## License

No license has been published for this repository, so default copyright applies.
