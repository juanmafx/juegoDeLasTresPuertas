# Release Notes: 3.0.0

Status: prepared, not tagged or released.

Version 3.0.0 turns the Monty Hall study into a four-language decision lab. One specification in
`spec/` defines the model, the command line, the JSON output and an exact random stream, and
implementations in Python, Java, PHP and C must agree with it and with each other: exact results
as identical reduced fractions, and seeded simulations with bit-identical win counts.

## Highlights

- **The generalized model.** Up to 64 doors, several prizes, uniform or weighted priors, `K`
  reveals, four host policies (informed, random, biased, adversarial), and stay, switch and mixed
  strategies, with results conditional on the reveal actually observed.
- **Four implementations, one answer.** `monty-lab exact`, `simulate` and `optimum` behave
  identically in Python, Java, PHP and C, including how they parse their input and how large an
  exact value they can print. Each passes every section of `tools/conformance.py`, and
  `tools/crosscheck.py` compared them on 600 seeded random invocations with no difference in exit
  code or JSON.
- **The exploration-cost model.** `optimum` evaluates `V(K) = P(win) - c*K` exactly, reports the
  discrete optimum, and fits the "hypothetical optimum parabola", reporting its shape, vertex,
  distance from the optimum and the regret of acting on it.
- **Theory and guidance.** `docs/THEORY.md` derives every host's formulas, explains why the same
  opened door means different things under different hosts, proves that the optimum lies at a
  corner in the main cases with a critical cost such as `1/N`, and reports where the parabola
  works and where it fails. `docs/DECISION_GUIDE.md` offers practical questions, clearly marked
  as interpretation.
- **Reproducible figures.** Six SVG charts in `docs/figures/`, generated from CLI output by
  `tools/make_figures.py`, which can also check that they are current.
- **Results database for any language.** `db/schema.sql` and `tools/record_run.py` store CLI
  output with the implementation and version that produced it.

## Breaking changes

1. **The Python project lives in `python/`.** `pyproject.toml`, `uv.lock`, `src/`, `tests/`,
   `tools/` and `reports/` moved out of the repository root. Run commands from `python/`:

   ```bash
   cd python
   uv sync --locked
   uv run monty-hall simulate --trials 1000 --seed 42
   uv run monty-lab exact
   ```

   To install from Git, add `#subdirectory=python` to the URL.

2. **`db/schema.sql` changed meaning.** At the repository root it is now the `monty-lab` results
   schema for all languages. The `monty-hall` run schema is unchanged and moved to
   `python/db/schema.sql`; databases created with 2.0.0 keep working with `monty-hall`.

The `monty-hall` command keeps its flags, output and seeded results. Its 95% Wilson bounds can
differ from 2.0.0 in the last floating-point bits, because it now uses the specification's
`z = 1.959963984540054`.

## Requirements

| Implementation | Requirement |
| --- | --- |
| Python | Python 3.13 or newer and uv; no runtime dependencies |
| Java | Java 17; Maven 3.9 to build, or the pinned Maven Docker image |
| PHP | PHP 8.4 or newer and Composer; runtime dependency `brick/math` 1.0.0; `ext-bcmath` or `ext-gmp` recommended for ten-door games with large prior weights |
| C | A C17 compiler and make |

## Verification for this release

Recorded in the per-language report directories (`python/reports/`, `java/reports/`,
`php/reports/`, `c/reports/`). The figures were regenerated and checked with both the Python and
the C command lines. The CI workflows themselves have not yet run on GitHub Actions for this
version.
