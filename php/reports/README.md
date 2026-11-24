# Recorded runs

Produced on 2026-11-24 from this directory's code, by the commands in [`../README.md`](../README.md).

| File | Run |
| --- | --- |
| `tests/junit.xml`, `tests/test-report.md` | PHPUnit 13.4.8 on PHP 8.4.28 in `php:8.4-cli@sha256:6b13a867…`: 550 tests, 2517 assertions, all passed |
| `static-analysis/phpstan.txt` | PHPStan 2.3.7, level 9, same image: no errors |
| `conformance/conformance-local-php85.*` | `tools/conformance.py --cli "php php/bin/monty-lab"` with the local PHP 8.5.4 and Python 3.14.4 |
| `conformance/conformance-docker-php84.*` | The same check with the CLI run in the PHP 8.4.28 image |

Both conformance runs passed every section: 105 PRNG vectors, 147 exact checks, 54 optimum checks,
26 bit-identical simulations, 180 statistical checks and 20 invalid invocations. Their statistics
block, 6 of 101 Wilson intervals excluding the exact value with 13 allowed, is identical to the
Python reference's, as expected from bit-identical win counts.
