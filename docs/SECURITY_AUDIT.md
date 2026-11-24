# Security Audit

- Date: 2026-11-23
- Scope: all tracked files on branch `modernize/2026` and the full Git history
- Open findings: none in the code; accepted limitations are listed below
- The decision lab added later (`spec/`, `tools/`, `python/src/monty_hall/lab/`, `java/`, `php/`,
  `c/`) was audited separately on 2026-11-24; see [Decision lab audit](#decision-lab-audit). It
  adds a Ruff `S603` exception for `tools/conformance.py`, which runs the CLI command its user
  passes in.
- On 2026-11-24, after this audit, the public history was rewritten so that only the 2026
  modernization commits remain. Commits earlier than 2026 are no longer in any branch or tag,
  although GitHub may still serve them by direct commit hash until it purges unreferenced
  objects. Treat anything that was ever published in that history as compromised.

## Method

| Check | Result |
| --- | --- |
| Manual review of source, tests, tools, CI, and history | Findings below were fixed |
| `gitleaks` 8.30.1 with `--redact` on full history and working tree | No leaks found |
| Dependency audit with `pip-audit` 2.10.1 on the locked development dependencies | No known vulnerabilities at audit time |
| Static security rules with Ruff (`S` rules) | Passing; see the rule exceptions below |
| Strict type checking with mypy | Passing |
| Crafted SQLite files run against `history` and `simulate` | Refused with exit code 2 |

Ruff exceptions: `S311` (pseudo-random) in the two simulation modules and tests, `S101` (assert) in
tests, `S603` (subprocess without a shell) in tests and the report tool, and `S314` (XML parsing) in
the report tool, which only parses the JUnit file that pytest just wrote.

## Findings fixed

| Severity | Finding | Fix |
| --- | --- | --- |
| Medium | A crafted view could hang `history` indefinitely | Schema is compared before any query |
| Medium | A crafted trigger in an existing file could run during `simulate` | Schema is compared before any write |
| Low | A crafted row crashed `history` with a traceback | Rows are type-checked when read |

## Review by category

| Category | Status |
| --- | --- |
| SQL injection | All values are bound parameters; statements are constants |
| XSS and CSRF | Not applicable: there is no web interface |
| Authentication and 2FA | Not applicable: there are no accounts, logins, or contact forms |
| Cryptography | None implemented; `secrets` only generates the default simulation seed |
| Unsafe evaluation | No `eval`, `exec`, `pickle`, or shell invocation in the package |
| Weak hashing | Not applicable: no hashing |
| Hardcoded secrets | None |
| Output injection | `history` prints JSON, which escapes terminal control characters |
| Resource exhaustion | Doors, trials, seed, enumeration size, and history limit are bounded |
| Database integrity | `STRICT` tables, `CHECK` constraints, schema comparison; `history` is read-only |
| Supply chain | No runtime dependencies; locked development dependencies with hashes |
| CI | `contents: read` only, actions pinned to commit SHAs, credentials not persisted |

## Accepted limitations

- `random.Random` is not cryptographically secure. It is appropriate for simulation.
- `--trials` near its maximum with many doors can run for a long time. This only affects the local
  user who requested it.
- The schema comparison does not make a hostile SQLite file safe to parse. Only open files you trust.
- The `hatchling` build backend and the `pip-audit` tool are pinned by version, not by hash.
- The audit reflects advisories known on its date and is not a guarantee of absence of defects.

## Decision lab audit

- Date: 2026-11-24
- Scope: the commits from `e7064a4` to the audit commit on `modernize/2026`: the specification,
  the Python, Java, PHP and C implementations, the tools, the documents and the workflows
- Open findings: none in the code; accepted limitations are listed below

| Check | Result |
| --- | --- |
| A separate enumerator and closed forms written for the audit, outside the repository, against all 49 scenarios in `spec/scenarios.json` and their 18 optimum blocks | No differences |
| The same oracle against all four CLIs on 300 random games, `exact` and `optimum`, up to 64 doors, weighted priors with weights up to 1,000,000 | No differences after the fixes below; before them the C CLI rejected 2 of 200 valid games |
| A separate PRNG and simulator written from `spec/prng.md` | All 105 vectors and all 26 reference simulations matched; 60 further random simulations matched in all four CLIs |
| `tools/conformance.py`, `tools/crosscheck.py` and 1,500 fuzzed argument lists through all four CLIs | Passing; identical exit codes and JSON |
| C unit tests and conformance under AddressSanitizer and UndefinedBehaviorSanitizer, 4,000 fuzzed invocations of the sanitized binary, GCC 13.5 build with `-Werror` | No sanitizer reports, no crashes |
| `gitleaks` 8.30.1 with `--redact` over the lab commits | No leaks found |
| `pip-audit` 2.10.1, `composer audit` in the pinned Composer image, OSV query for the resolved Maven artifacts | No known vulnerabilities at audit time |
| Workflows | `contents: read`, credentials not persisted, actions pinned to commit SHAs, images pinned by digest |

| Severity | Finding | Fix |
| --- | --- | --- |
| Medium | The C implementation capped integers at 4,096 bits and exited with code 2 on valid ten-door games with large prior weights, sometimes with a misleading message | Arbitrary-precision integers; arithmetic failures are reported first |
| Medium | `--mixed` and `--cost` accepted fractions of any length in Java and PHP but not in Python and C, so input size was unbounded and the CLIs disagreed | Each written part is limited to 2^63 - 1 in every implementation |
| Medium | The CLIs disagreed on flag prefixes, `1_000`, non-ASCII digits and whitespace, leading zeros, values starting with `-`, and `-h` after an invalid value; Python 3.13 and 3.14 also disagreed | One input syntax in `spec/cli.md`, implemented in all four and checked by `tools/conformance.py` |
| Low | Python exited with code 2 when an exact value had more than 4,300 digits | Output formatting lifts the limit only while formatting |
| Low | PHP took about 160 seconds on a ten-door optimum without GMP or BCMath | About 32 seconds after cancelling factors before multiplying; documented |
| Low | Java and PHP ran some Docker steps in CI with network access they do not need | `--network none` |
| Low | `docs/THEORY.md` and `docs/DECISION_GUIDE.md` said reveals change nothing against the adversarial host, did not exclude mixing from the unproven random-host case, and described the parabola's failures and curvature more confidently than the sweep supports | Corrected to what is derived or recorded in `results.json` |

Accepted limitations of the decision lab:

- Without the GMP or BCMath extension, PHP can take tens of seconds or more on ten-door games with
  large prior weights; the output is still exact. With BCMath the measured case took under one
  second.
- None of the workflows has run on GitHub Actions for these commits; their steps were run locally.
- The C implementation stops with exit code 2 if one integer would exceed 4,194,304 bits or memory
  runs out. The widest integer seen in testing had 46,912 bits.
