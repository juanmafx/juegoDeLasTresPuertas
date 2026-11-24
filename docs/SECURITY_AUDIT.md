# Security Audit

- Date: 2026-11-23
- Scope: all tracked files on branch `modernize/2026` and the full Git history
- Open findings: none in the code; accepted limitations are listed below
- Not covered: the decision lab added later (`spec/`, `tools/`, `python/src/monty_hall/lab/`)
  has not been audited. It adds a Ruff `S603` exception for `tools/conformance.py`, which runs the
  CLI command its user passes in.

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
