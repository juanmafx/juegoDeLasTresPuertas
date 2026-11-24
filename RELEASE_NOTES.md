# Release Notes: 2.0.0

Status: prepared, not tagged or published.

Version 2.0.0 rebuilds the 2019 Monty Hall script as a small tested package for studying the
problem. It now simulates the host, generalizes to many doors, and checks each result against an
exact fraction.

## Highlights

- Exact results by closed form and by full game-tree enumeration.
- Reproducible seeded simulation with Wilson confidence intervals.
- A random-host mode showing that the advantage depends on the host's knowledge.
- Optional SQLite storage of run results.
- Automated tests, with the recorded run in `reports/tests/`.

## Breaking changes

`MontyHall.py` was removed. Use:

```bash
uv run monty-hall simulate --trials 1000 --seed 42
```

## Requirements

Python 3.13 or newer. No runtime dependencies.
