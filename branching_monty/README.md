# Branching Monty

An experimental layer beside the decision lab. It treats every Monty Hall variant as a
branching-and-pruning system and measures how much a constraint on an informed agent is worth,
across three tiers: Bayesian, epistemically restricted (Spekkens) and quantum.

The existing implementations in `python/`, `java/`, `php/` and `c/` are untouched.

## Layout

```text
core/          Generalized Grover, discrete Wigner function and mana, partially informed host,
               leverage metric, Holevo information and optimal discrimination
branches/      Branch engine: explicit hypothesis tree, Bayesian pruning, branch warehouse
agents/        Two agents exchanging messages: signalling policies, reflexivity, latency
tiers/         Bayesian, Spekkens and quantum tiers (Module 4)
experiments/   One script per experiment, fixed seeds, JSON output
tests/         pytest regression targets
reports/       Generated data, figures and the report
```

## The leverage metric

For a decision-maker who sees the host's action `O` and must name the car's door `C`:

- `V` is the Bayes-optimal probability of success.
- `Lambda = log2(N * V)` bits. With every decision allowed it equals `log2 N - H_min(C|O)`.
- `I = I(C;O)` classically, the Holevo quantity quantumly.
- `epsilon = Lambda / I`.

The convention for a revealed car matters and is always stated: `claim` lets the player take a
revealed car, `loss` counts it as a lost game.

## Usage

Requires Python 3.13 or newer and [uv](https://docs.astral.sh/uv/).

```bash
cd branching_monty
uv sync
uv run pytest
uv run ruff check .
```

Experiments run from the repository root so that the package resolves:

```bash
uv run --project branching_monty python -m branching_monty.experiments.<name> --help
```
