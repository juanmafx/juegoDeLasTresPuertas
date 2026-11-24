# Changelog

This project follows [Semantic Versioning](https://semver.org/). The original script had no version
number and is treated as 1.0.0.

## [3.0.0] - Unreleased

Prepared, not tagged. See [RELEASE_NOTES.md](RELEASE_NOTES.md).

### Breaking changes

- The Python project moved from the repository root into `python/`: `pyproject.toml`, `uv.lock`,
  `src/`, `tests/`, `tools/` and `reports/`. Run `uv` commands from `python/`, and install from a
  Git URL with `#subdirectory=python`.
- `db/schema.sql` at the repository root is now the cross-language `monty-lab` results schema.
  The `monty-hall` run schema moved, unchanged, to `python/db/schema.sql`; databases created by
  2.0.0 keep working with `monty-hall`.

### Added

- `spec/`: the cross-language `monty-lab` contract (`cli.md`), the exact random stream
  (`prng.md`), JSON Schemas for scenarios and output, 49 scenarios with exact expectations,
  105 PRNG vectors, and reference simulation counts.
- `monty_hall.lab` and the `monty-lab` command: `N` up to 64 doors, `M` prizes, uniform or
  weighted priors, informed, random, biased and adversarial hosts, stay, switch and mixed
  strategies, results conditional on an observed reveal, a deterministic SplitMix64 and
  xoshiro256** simulator, and the exploration-cost curve with its exact optimum and least-squares
  parabola.
- Java 17 (`java/`), PHP 8.4 (`php/`) and C17 (`c/`) implementations of `monty-lab`, each with
  its own test suite, recorded report and CI workflow. All four pass `tools/conformance.py` and
  produce identical JSON.
- `tools/enumerate.py`, an independent brute-force oracle for the scenario expectations.
- `tools/conformance.py`, which checks any language's CLI against `spec/`.
- `tools/crosscheck.py` and the `Conformance` workflow, which compare the four CLIs with each
  other on seeded random invocations.
- `docs/THEORY.md`, an essay from three doors to deciding with partial information, with exact
  derivations, the critical-cost results and an analysis of the hypothetical optimum parabola.
- `docs/DECISION_GUIDE.md`, practical questions derived from the model, marked as interpretation.
- `tools/make_figures.py`, which generates the SVG charts and `results.json` in `docs/figures/`
  from CLI output and checks that the committed files are current; CI runs the check.
- `db/schema.sql` and `tools/record_run.py` for storing `exact`, `simulate` and `optimum` output
  from any implementation, with a view that lists simulations whose counts disagree.
- `jsonschema` 4.26.0 as a Python development dependency for schema tests.

### Changed

- Version 3.0.0 in every implementation: Python `__version__`, the Maven project, PHP
  `Cli::VERSION` and C `MH_VERSION`. `monty-lab --version` prints `monty-lab 3.0.0` in all four.
- CI runs the Python checks from `python/` and also checks `tools/`, the scenario expectations,
  conformance and the figures.
- `SECURITY.md` covers the four implementations, the PHP runtime dependency and the new loader;
  3.x is the supported line.

### Fixed

- The 95% Wilson interval now uses the specification's `z = 1.959963984540054` in Python, the
  value the other implementations use, instead of `NormalDist().inv_cdf(0.975)`, which differs in
  the last bits. This also changes `monty-hall`'s 95% bounds in the last bits.

## [2.0.0] - 2026-11-23

### Added

- Installable `monty_hall` package with a `monty-hall` command.
- Explicit host simulation for 3 to 1024 doors and any valid number of opened doors.
- `informed` and `random` host policies.
- Exact solvers: closed form and full game-tree enumeration.
- Wilson confidence intervals, z-scores, and recorded seeds.
- Optional SQLite persistence with `db/schema.sql` (now `python/db/schema.sql`).
- Unit, property-based, statistical, and integration tests with a committed report.
- CI with least-privilege permissions and pinned actions and dependencies.
- Architecture, security, and release documentation.

### Changed

- All code, output, and documentation are now in English.
- The README now states the switching result correctly. The earlier text said the player always
  wins under a condition that was worded incorrectly.

### Security

- `simulate` and `history` refuse SQLite files whose run tables, views, indexes, or triggers differ
  from the packaged schema, and stored rows are type-checked when read.

### Fixed

- Text output no longer rounds confidence levels such as 0.999 up to `100%`.
- An unusable `--db` path now fails before the simulation runs.
- A closed output pipe now exits with code 141 instead of printing a Python error.

### Removed

- **Breaking:** `MontyHall.py`, replaced by the `monty-hall` command. It remains in Git history.

## [1.0.0] - 2019-09-25

- Original script. It compared the first pick with the car position and inferred the switching
  result without modeling the host.
