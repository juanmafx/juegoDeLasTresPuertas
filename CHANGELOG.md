# Changelog

This project follows [Semantic Versioning](https://semver.org/). The original script had no version
number and is treated as 1.0.0.

## [3.0.1] - 2026-11-24

Documentation corrections only. No change in code behaviour.

### Changed

- The changelog, release notes and security audit now reflect the published 3.0.0 release and
  the 2026-11-24 history rewrite.

## [3.0.0] - 2026-11-24

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
- `docs/SECURITY_AUDIT.md` records an audit of the decision lab. Dependabot also watches the Maven
  and Composer manifests, and the Java and PHP workflows run their remaining Docker steps without
  network access.
- `docs/THEORY.md` and `docs/DECISION_GUIDE.md` were corrected where they overstated results: the
  adversarial host's switch probability does rise with reveals when there are several prizes, the
  unproven random-host case covers mixing as well as switching, and the parabola's failures and
  curvature are described only as far as the recorded sweep supports.

### Fixed

- The input syntax is now part of `spec/cli.md` and is the same in every implementation: flag
  names must be written in full, the argument after a flag is always its value, `-h` and `--help`
  win over other errors, integers are ASCII decimal digits with an optional sign and surrounding
  ASCII whitespace, and each written part of a `--mixed` or `--cost` fraction must lie within
  2^63 - 1. Before, the four implementations disagreed on flag prefixes, `1_000`, non-ASCII digits
  and whitespace, leading zeros, values starting with `-`, help after an invalid value, and very
  long or very large fractions, and Python 3.13 and 3.14 disagreed with each other on values such
  as `-1/-2`. `tools/conformance.py` has a new `syntax` section for these rules.
- The C implementation used integers of at most 4,096 bits and rejected valid ten-door games with
  large prior weights, such as five prizes with weights near 1,000,000. It now uses
  arbitrary-precision integers, and `tools/conformance.py` has a new `large_values` section with a
  game whose exact values are wider than 4,096 bits.
- The Python reference failed with exit code 2 when an exact value had more than 4,300 digits,
  Python's default limit for converting integers to text. It now prints such values.
- PHP fraction arithmetic cancels common factors before multiplying, and `optimum` computes the
  prior probability of the pick once instead of once per reveal count. A ten-door optimum that
  took about 160 seconds on the development machine now takes about 32 without GMP or BCMath.
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

- **Breaking:** `MontyHall.py`, replaced by the `monty-hall` command.

## [1.0.0] - 2019-09-25

- Original script. It compared the first pick with the car position and inferred the switching
  result without modeling the host.
