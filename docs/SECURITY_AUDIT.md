# Security Audit

- Date: 2026-11-23
- Scope: all tracked files on branch `modernize/2026` and the two commits of prior history
- Open findings: none in the code

## Method

| Check | Result |
| --- | --- |
| Tracked files reviewed manually | Original script and README contained no secrets |
| History reviewed for secrets and private keys | None found in the two prior commits |
| Dependency audit with `pip-audit` 2.10.1 on the locked development dependencies | No known vulnerabilities at audit time |
| Static security rules with Ruff (`S` rules) | Passing; the pseudo-random rule is disabled only in the two simulation modules and in tests |
| Strict type checking with mypy | Passing |

## Review by category

| Category | Status |
| --- | --- |
| SQL injection | All values are bound parameters; statements are constants |
| XSS and CSRF | Not applicable: there is no web interface |
| Unsafe evaluation | No `eval`, `exec`, `pickle`, or shell invocation in the package |
| Weak hashing | Not applicable: no hashing |
| Hardcoded secrets | None |
| Resource exhaustion | Doors, trials, seed, enumeration size, and history limit are bounded |
| Database integrity | `STRICT` tables with `CHECK` constraints; `history` is read-only |
| Supply chain | No runtime dependencies; locked development dependencies with hashes |
| CI | `contents: read` only, actions pinned to commit SHAs, credentials not persisted |

## Accepted limitations

- `random.Random` is not cryptographically secure. It is appropriate for simulation.
- `--trials` near its maximum with many doors can run for a long time. This only affects the local
  user who requested it.
- The audit reflects advisories known on its date and is not a guarantee of absence of defects.
