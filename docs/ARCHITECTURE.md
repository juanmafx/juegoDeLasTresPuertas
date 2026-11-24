# Architecture

## Design goals

1. Every simulated number can be checked against an exact one.
2. Game rules live in one place and have no dependency on input, output, or storage.
3. Runs are reproducible from their recorded seed, in every language for `monty-lab`.
4. The runtime has no third-party dependencies.
5. Expected values come from code that shares nothing with the implementations they check.

## Repository structure

`spec/` is the language-neutral contract, `tools/` holds the independent enumerator and the
conformance runner, and `python/` is the reference implementation. Further implementations are
meant to live in sibling directories and pass `tools/conformance.py`.

## Module structure

```text
python/src/monty_hall/
  lab/
    model.py        Scenario, Host, Strategy, fraction parsing and validation
    prng.py         SplitMix64, xoshiro256**, bounded, weighted and shuffle draws
    solver.py       Closed forms and enumeration over prize sets for observed reveals
    simulator.py    Deterministic simulation following spec/prng.md
    optimum.py      V(K) curve, exact optimum, exact least-squares parabola
    cli.py          The monty-lab command-line contract
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
lab.cli -> lab.optimum -> lab.solver -> lab.model
lab.cli -> lab.simulator -> lab.prng
lab.cli -> analysis.intervals
```

The original `domain`, `analysis`, `simulation`, `persistence` and `cli` packages are unchanged
and still back `monty-hall`. `lab` reuses only the Wilson interval from them.

`domain` imports nothing from the other packages. A test asserts that the packaged schema is
identical to `python/db/schema.sql`, so the two copies cannot drift.

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

## The generalized model (monty-lab)

The full contract is in `spec/cli.md`. With `N` doors, `M` prizes, `K` reveals, the pick `d`
and `pi = P(d holds a prize)` under the prior, the closed forms used by `lab/solver.py` are:

```text
informed, biased:  stay = pi                 switch = (M - pi) / (N - 1 - K)
adversarial:       decision = pi             stay = 1, switch = (M - 1) / (N - 1 - K)
random:            a = C(N - M, K) / C(N - 1, K), b = C(N - 1 - M, K) / C(N - 1, K)
                   decision = pi * a + (1 - pi) * b
                   stay = pi * a / decision
                   switch = (pi * a * (M - 1) + (1 - pi) * b * M) / ((N - 1 - K) * decision)
```

The informed and biased forms hold because a host that never opens a prize door leaves every
prize except the pick's among the `N - 1 - K` closed doors, whatever its preferences. Host
preferences matter only once you condition on which doors were opened, so observed reveals are
solved by enumerating prize sets: the prior over sets is built by dynamic programming over
subsets, and the probability that a biased host opens a given set is summed over its orderings
the same way. Enumeration is limited to 10 doors. For a uniform prior `pi = M / N`; for weights
it comes from the same subset dynamic programme.

The optimum curve evaluates `V(K) = P(win | strategy, K) - c*K` for every feasible `K` and fits
`a K^2 + b K + c` by solving the 3 by 3 normal equations exactly with Cramer's rule.

## Algorithms and complexity

| Operation | Time | Memory |
| --- | --- | --- |
| `closed_form` | O(1) arithmetic operations | O(1) |
| `play_game` | O(n) | O(n) |
| `run_simulation` | O(T * n) | O(n) |
| `enumerate_game_tree` | O(n^3 * k * C(n - 1, k)) operations, upper bound | O(k * C(n - 1, k)) |
| `wilson_interval`, `z_score` | O(1) | O(1) |
| `lab.solver.solve`, uniform prior, no observation | O(K) big-integer operations | O(1) |
| `lab.solver.solve`, weighted prior or observation | O(M * N^2 * 2^N) plus O(K^2 * 2^K) per prize set, upper bound | O(2^N) |
| `lab.simulator.simulate` | O(T * N * (M + K)) | O(N) |
| `lab.optimum.optimum_curve` | `N - M` solves plus O(N) for the fit | O(N) |

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
| `tests/lab` | Examples, Hypothesis, fixed-seed z tests | PRNG values, validation, anchors, observations average back to the unconditional result, corner optima for uniform priors, least-squares minimality, convergence |
| `tests/spec` | Spec files, JSON Schema, subprocess | Every scenario equals the independent enumerator, outputs match the schema, generated spec data is current |
| `tools/conformance.py` | Black-box CLI runs | Exact equality, bit-identical counts, interval coverage, error handling |

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
- Implement the contract in Java, PHP and C and run `tools/conformance.py` against each.
- Lift the 10-door enumeration limit for weighted priors with a faster inclusion-probability
  method, if one that stays exact proves practical.
