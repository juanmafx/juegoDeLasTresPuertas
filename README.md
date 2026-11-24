# juegoDeLasTresPuertas

Exact and reproducible Monte Carlo analysis of the Monty Hall problem and its generalization to
any number of doors. The repository name is Spanish for "the game of the three doors".

## Purpose

The Monty Hall problem is a standard example of how conditioning on information changes a
probability. A car is hidden behind one of three doors. You pick a door, the host opens a
different door showing a goat, and you may switch. Switching wins 2/3 of the time, which many
people find counterintuitive.

## Why this project exists

The project started as a short script demonstrating that switching helps. This version turns that
demonstration into a small, verifiable study: every simulated result can be checked against an
exact fraction, and the assumption that makes switching work, a host who knows where the car is,
can be turned off to watch the advantage disappear.

## What it does

- Computes exact win probabilities as rational numbers, by closed form or by walking the full game
  tree.
- Simulates the game with an explicit host, for 3 to 1024 doors and any valid number of opened
  doors.
- Compares two host models: `informed` (classic Monty Hall) and `random` (the "Monty Fall"
  variant, where games in which the host reveals the car are discarded).
- Reports Wilson confidence intervals and z-scores against the exact value.
- Records the seed of every run so it can be repeated.
- Optionally stores runs in SQLite.

| Doors | Opened | Host | Stay | Switch |
| ---: | ---: | --- | ---: | ---: |
| 3 | 1 | informed | 1/3 | 2/3 |
| 3 | 1 | random | 1/2 | 1/2 |
| 5 | 1 | informed | 1/5 | 4/15 |
| 100 | 98 | informed | 1/100 | 99/100 |

## Architecture

```text
src/monty_hall/
  domain/       Game rules, validated configuration, and a single game
  analysis/     Exact solvers and interval statistics
  simulation/   Seeded runner and report builder
  persistence/  Optional SQLite repository
  cli/          Command-line interface
db/schema.sql   Optional database schema
tests/          Unit, property-based, statistical, and integration suites
tools/          Test report generator
```

This is a command-line library with no client or server, so there is no frontend/backend split.
See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the derivations, complexity analysis, and
design decisions.

## Quick start

Requires Python 3.13 or newer and [uv](https://docs.astral.sh/uv/). There are no runtime
dependencies.

```bash
git clone https://github.com/juanmafx/juegoDeLasTresPuertas.git
cd juegoDeLasTresPuertas
uv sync --locked
uv run monty-hall exact
uv run monty-hall simulate --trials 1000000 --seed 42
```

Output of that simulation on Python 3.14:

```text
doors=3 opened=1 host=informed seed=42 trials=1000000 valid_games=1000000
stay    wins=333948 rate=0.333948 exact=0.333333 95% CI=[0.333024, 0.334873] z=+1.304
switch  wins=666052 rate=0.666052 exact=0.666667 95% CI=[0.665127, 0.666976] z=-1.304
```

## Usage guide

```bash
uv run monty-hall exact --doors 5 --opened 1
uv run monty-hall exact --host random --enumerate --format json
uv run monty-hall simulate --host random --trials 500000 --seed 7
uv run monty-hall simulate --doors 10 --opened 8 --confidence 0.99 --format json
uv run monty-hall simulate --trials 100000 --seed 1 --db runs.sqlite3
uv run monty-hall history --db runs.sqlite3 --limit 10
```

Invalid input exits with code 2 and a message on standard error.

## Configuration

The tool reads no environment variables or configuration files. Everything is a flag.

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

## Database

Persistence is **optional**. The game has no natural need for storage, so
[db/schema.sql](db/schema.sql) provides a small schema for keeping run results. It is applied
automatically when `--db` is used with `simulate`. `history` opens the file read-only.

## Testing

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run python tools/generate_test_report.py
```

The suite covers input validation, property-based game invariants, agreement between the closed
form and full enumeration, statistical convergence with fixed seeds, the database constraints, and
the CLI. The latest recorded run is in [reports/tests/test-report.md](reports/tests/test-report.md).

## Reproducibility

The same seed, configuration, and Python version produce the same result. Python only guarantees
stable sequences across versions for `random.random()`, so results from the integer sampling used
here could change in a future Python release. Statistical tests use fixed seeds, and property tests
run derandomized.

## Security

The tool makes no network calls, has no runtime dependencies, uses parameterized SQL, and validates
all input. The `random` module is used deliberately because this is a simulation and nothing here
is a security token. See [SECURITY.md](SECURITY.md) and
[docs/SECURITY_AUDIT.md](docs/SECURITY_AUDIT.md).

## Project history

Originally created in 2019 by Juan Manuel Ramallo as a single Python script. Modernized in 2026.
The Monty Hall problem itself is not original to this project: it was posed by Steve Selvin in 1975
and popularized by Marilyn vos Savant. The "Monty Fall" name comes from Jeffrey S. Rosenthal.

## License

No license has been published for this repository, so default copyright applies.
