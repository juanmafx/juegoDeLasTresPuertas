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

### Removed

- **Breaking:** `MontyHall.py`, replaced by the `monty-hall` command. It remains in Git history.

## [1.0.0] - 2019-09-25

- Original script. It compared the first pick with the car position and inferred the switching
  result without modeling the host.
