# Security Policy

## Supported versions

| Version | Supported |
| --- | --- |
| 3.x | Yes |
| 2.x | No, upgrade to 3.x |
| Earlier, unversioned script | No |

## Reporting a vulnerability

Use the private vulnerability reporting option on the repository's GitHub Security tab if it is
available. Otherwise, open an issue asking for a private contact, without including exploit
details. This is a personal project, so responses are best effort and no response time is promised.

## Scope and threat model

The repository contains local command-line tools: `monty-lab` in Python, Java, PHP and C, the
original Python `monty-hall` tool, and the helper scripts in `tools/`. None of them makes network
calls, authenticates anyone, reads environment variables for configuration, or runs as a service.
Their inputs are command-line flags, JSON files and SQLite file paths chosen by the person running
them.

- **Input validation.** Every `monty-lab` implementation validates the same ranges and formats,
  defined in `spec/cli.md`, and exits with code 2 on invalid input. `tools/conformance.py` and
  `tools/crosscheck.py` include invalid invocations.
- **Resource limits.** Door counts, prize counts, trial counts and list lengths are bounded.
  Exact enumeration is limited to 10 doors. Very long `--mixed` or `--cost` fractions make exact
  arithmetic slower; the C implementation refuses results above its 4096-bit integer capacity
  with exit code 2, while the other implementations use unbounded integers.
- **Memory safety.** The C implementation is compiled with warnings as errors, and its unit tests
  and the conformance suite also run under AddressSanitizer and UndefinedBehaviorSanitizer.
- **Databases.** `monty-hall` refuses SQLite files whose run tables, views, indexes or triggers
  differ from its schema, but that check does not make a hostile file safe to parse.
  `tools/record_run.py` does not perform such a check. Use both only with database files you
  created or trust. All SQL uses bound parameters.
- **Dependencies.** Python, Java and C have no runtime dependencies. PHP uses `brick/math`,
  pinned in `php/composer.lock`. Development tools (pytest, Hypothesis, ruff, mypy, jsonschema,
  JUnit and Maven plugins, PHPUnit, PHPStan) are pinned by version and lock files. Composer is run
  with `--no-scripts --no-plugins` in CI, and the Docker images used for Java and PHP are pinned
  by digest.
- **CI.** Workflows request `contents: read` only, check out without persisting credentials, and
  pin third-party actions to commit SHAs.

## Randomness

Neither Python's `random` module (used by `monty-hall`) nor the SplitMix64 and xoshiro256**
generators (used by `monty-lab`) is cryptographically secure, and neither needs to be. Seeds are
not secrets. Do not reuse these generators for security purposes.
