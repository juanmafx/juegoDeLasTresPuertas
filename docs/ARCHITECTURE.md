# Architecture

## Design goals

1. Every simulated number can be checked against an exact one.
2. Game rules live in one place and have no dependency on input, output, or storage.
3. Runs are reproducible from their recorded seed.
4. The runtime has no third-party dependencies.

## Module structure

```text
src/monty_hall/
  domain/
    models.py       GameConfig, HostPolicy, GameOutcome, validation
    game.py         play_game
  analysis/
    exact.py        closed_form, enumerate_game_tree
    intervals.py    wilson_interval, z_score
  simulation/
    runner.py       SimulationRequest, SimulationResult, run_simulation
    report.py       build_report
  persistence/
    repository.py   RunRepository
    schema.sql      Packaged copy of db/schema.sql
  cli/
    main.py         Argument parsing and command handlers
```

Dependencies point inward:

```text
cli -> persistence -> simulation -> domain
cli -> simulation -> analysis -> domain
```

`domain` imports nothing from the other packages. A test asserts that the packaged schema is
identical to `db/schema.sql`, so the two copies cannot drift.

## The model

Let `n` be the number of doors and `k` the number the host opens, with `1 <= k <= n - 2`. The car
and the first pick are independent and uniform. A switching player moves to a uniformly random
door among the `n - k - 1` that are neither picked nor opened.

### Informed host

The host never opens the picked door or the car door, and chooses uniformly among valid sets.

- Staying wins when the first pick was right: `P(stay) = 1 / n`.
- With probability `(n - 1) / n` the car is elsewhere. It is never revealed, so it is one of the
  `n - k - 1` remaining doors, and the switch finds it with probability `1 / (n - k - 1)`.

```text
P(switch) = (n - 1) / (n * (n - k - 1))
```

Since `n - 1 > n - k - 1`, switching is strictly better for every valid game. When `k = n - 2`
exactly one door remains, so `P(switch) = (n - 1) / n` and the two strategies sum to 1. For smaller
`k` they do not, because a switching player can move to another losing door.

### Random host (Monty Fall)

The host opens `k` of the other doors uniformly and may reveal the car. Those games are discarded.
The revealed set is a uniform `k`-subset of the `n - 1` other doors, so:

```text
P(valid game) = (n - k) / n
P(stay | valid) = P(switch | valid) = 1 / (n - k)
```

Given that the car was not revealed, it is uniform over the `n - k` closed doors, so switching has
no advantage. The advantage comes from the host's knowledge rather than from a door being opened.

## Algorithms and complexity

| Operation | Time | Memory |
| --- | --- | --- |
| `closed_form` | O(1) arithmetic operations | O(1) |
| `play_game` | O(n) | O(n) |
| `run_simulation` | O(T * n) | O(n) |
| `enumerate_game_tree` | O(n^3 * k * C(n - 1, k)) operations, upper bound | O(k * C(n - 1, k)) |
| `wilson_interval`, `z_score` | O(1) | O(1) |

`T` is the number of trials. Enumeration is exponential in `n` for mid-range `k`, so it is limited
to 9 doors. Its purpose is to verify the closed form independently, using exact rationals so that
no floating-point tolerance is involved.

## Statistical method

The standard error of an estimated rate is `sqrt(p * (1 - p) / T)`, so precision improves with the
square root of the trial count: 100 times more trials give one more decimal digit.

Intervals use the **Wilson score** method because, unlike the normal approximation, it stays inside
`[0, 1]` and behaves well for rates near 0 or 1, which occur with many doors. The reported z-score
measures the distance from the exact value in standard errors.

For the random host, rates are conditional on valid games, so `valid_games` rather than `trials` is
the denominator.

## Verification strategy

| Suite | Technique | What it establishes |
| --- | --- | --- |
| `tests/unit` | Example-based | Validation, known fractions, reference interval values |
| `tests/property` | Hypothesis, derandomized | Game invariants, closed form equals enumeration for 3 to 6 doors |
| `tests/statistical` | Fixed-seed z and chi-square tests | Simulation converges, sampling is unbiased |
| `tests/integration` | Real SQLite and CLI | Round trips, constraints, tampered schemas, exit codes |

## Persistence

SQLite was chosen because storage is optional and needs no server. Tables are `STRICT`, and `CHECK`
constraints reject impossible results such as more wins than valid games. All values are bound as
parameters. `history` connects in read-only mode, so it does not change the database file. For a
database in WAL mode, SQLite can still create `-wal` and `-shm` files next to it.

Before any query, the repository compares the objects attached to its table and view with those of
the packaged schema, and refuses a mismatch. This stops a crafted view from hanging `history` and a
crafted trigger from running during `simulate`. Rows are type-checked when read.

## Recommended extensions

- Replace per-game list building with an O(k) sparse sampler for very large door counts.
- Add a biased-host policy, which makes the conditional probability depend on the door opened.
- Move to a version-stable generator if results must match across Python releases.
