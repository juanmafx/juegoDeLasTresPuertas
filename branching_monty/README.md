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

Requires Python 3.13 or newer and [uv](https://docs.astral.sh/uv/). Qiskit is an optional
dependency group that `uv sync` installs by default; `uv sync --no-group qiskit` leaves it out,
and its single test is then skipped.

```bash
cd branching_monty
uv sync
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

Experiments run from the repository root so that the package resolves. Each writes JSON to
standard output, or to `--out`, and takes `--help`:

```bash
P="uv run --project branching_monty python -m branching_monty.experiments"
D=branching_monty/reports/data
$P.branch_trace --doors 5 --reveals 2 --q 1/2 --out $D/branch_trace.json
$P.signalling_design --out $D/signalling_design.json
$P.reflexivity_sweep --out $D/reflexivity_sweep.json
$P.latency_sweep --out $D/latency_sweep.json
$P.phase_grid --out $D/phase_grid.json
$P.partial_oracle --out $D/partial_oracle.json
$P.decoherence --out $D/decoherence.json
$P.five_doors --out $D/five_doors.json
$P.qiskit_n4 --out $D/qiskit_n4.json
$P.make_figures
```

| Experiment | Module | What it measures |
| --- | --- | --- |
| `branch_trace` | 2 | One seeded world through the branch engine, with the full branch warehouse |
| `signalling_design` | 3 | Uniform Monty against the best and worst committed goat-only host |
| `reflexivity_sweep` | 3 | Lambda against feedback strength r for three feedback modes |
| `latency_sweep` | 3 | Lambda from causal pruning over jitter, timing gap and latency floor |
| `phase_grid` | 4 | 721 x 721 oracle and diffusion phases, mana and the Spekkens residual |
| `partial_oracle` | 4 | A partially informed oracle across classical and quantum black boxes |
| `decoherence` | 4 | Dephasing between oracle and diffusion; gamma* closed form and numeric |
| `five_doors` | 4 | Five doors: quantum against Spekkens, and whether the gap tracks mana |
| `qiskit_n4` | 4 | Optional N = 4 qubit run with `CPhaseGate(phi)` |
| `make_figures` | 5 | Every PNG in `reports/figures/` |

Monte Carlo experiments use fixed seeds and report standard errors. The findings are written up
in [reports/branching_monty_report.md](reports/branching_monty_report.md).
