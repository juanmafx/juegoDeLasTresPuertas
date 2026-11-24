# Changelog

This project follows [Semantic Versioning](https://semver.org/). The original script had no version
number and is treated as 1.0.0.

## [2.0.0] - Unreleased

### Added

- Installable `monty_hall` package with a `monty-hall` command.
- Explicit host simulation for 3 to 1024 doors and any valid number of opened doors.
- `informed` and `random` host policies.
- Exact solvers: closed form and full game-tree enumeration.
- Wilson confidence intervals, z-scores, and recorded seeds.
- Optional SQLite persistence with `db/schema.sql`.
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
