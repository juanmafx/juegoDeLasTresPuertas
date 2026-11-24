# C Test Report

- Generated (UTC): 2026-11-24T13:08:50Z
- Compiler: gcc (Ubuntu 15.2.0-16ubuntu1) 15.2.0
- Python running tools/conformance.py: Python 3.14.4
- Operating system: Linux x86_64
- Command: `make report` (runs `tools/report.sh`)

| Run | Exit code | Summary |
| --- | ---: | --- |
| Unit tests, plain build | 0 | 27 tests, 27 passed, 0 failed |
| Unit tests, AddressSanitizer + UBSan | 0 | 27 tests, 27 passed, 0 failed |
| Conformance, plain CLI | 0 | see below |
| Conformance, sanitized CLI | 0 | see below |

## Unit tests, plain build

```text
PASS fraction_parse_and_format
PASS fraction_arithmetic
PASS fraction_floor
PASS big_integers_beyond_64_bits
PASS overflow_is_detected
PASS parse_i64_bounds
PASS splitmix_and_words
PASS bounded_vectors
PASS weighted_and_shuffle_vectors
PASS scenario_validation
PASS exact_classic_hosts
PASS exact_biased_observed
PASS exact_weighted_prior
PASS exact_enumeration_limit
PASS exact_sixty_four_doors
PASS optimum_five_doors
PASS optimum_sixty_four_doors
PASS optimum_linear_and_short_curves
PASS simulation_matches_reference
PASS simulation_rejects_bad_runs
PASS wilson_interval
PASS cli_exact_output
PASS cli_simulate_and_prng
PASS cli_optimum_output
PASS cli_rejects_invalid_input
PASS cli_help_and_version
PASS json_double_format
27 tests, 27 passed, 0 failed
```

## Unit tests, AddressSanitizer + UBSan

```text
PASS fraction_parse_and_format
PASS fraction_arithmetic
PASS fraction_floor
PASS big_integers_beyond_64_bits
PASS overflow_is_detected
PASS parse_i64_bounds
PASS splitmix_and_words
PASS bounded_vectors
PASS weighted_and_shuffle_vectors
PASS scenario_validation
PASS exact_classic_hosts
PASS exact_biased_observed
PASS exact_weighted_prior
PASS exact_enumeration_limit
PASS exact_sixty_four_doors
PASS optimum_five_doors
PASS optimum_sixty_four_doors
PASS optimum_linear_and_short_curves
PASS simulation_matches_reference
PASS simulation_rejects_bad_runs
PASS wilson_interval
PASS cli_exact_output
PASS cli_simulate_and_prng
PASS cli_optimum_output
PASS cli_rejects_invalid_input
PASS cli_help_and_version
PASS json_double_format
27 tests, 27 passed, 0 failed
```

## tools/conformance.py against build/monty-lab

```text
PASS prng: 105 passed, 0 failed
PASS exact: 147 passed, 0 failed
PASS optimum: 54 passed, 0 failed
PASS simulation_identical: 26 passed, 0 failed
PASS simulation_statistical: 180 passed, 0 failed
PASS errors: 20 passed, 0 failed
INFO 6 of 101 Wilson 95% intervals exclude the exact value (allowed 13): classic-adversarial:decision z=+2.23; no-reveal-four-doors:stay z=+2.87; pick-middle-random-observed:switch z=+2.12; prior-skewed-toward-observed:stay z=+3.38; prior-skewed-toward-observed:switch z=-3.38; two-prizes-random:switch z=+2.30
```

The JSON report of this run is in `conformance.json`.

## tools/conformance.py against build/monty-lab-sanitize

```text
PASS prng: 105 passed, 0 failed
PASS exact: 147 passed, 0 failed
PASS optimum: 54 passed, 0 failed
PASS simulation_identical: 26 passed, 0 failed
PASS simulation_statistical: 180 passed, 0 failed
PASS errors: 20 passed, 0 failed
INFO 6 of 101 Wilson 95% intervals exclude the exact value (allowed 13): classic-adversarial:decision z=+2.23; no-reveal-four-doors:stay z=+2.87; pick-middle-random-observed:switch z=+2.12; prior-skewed-toward-observed:stay z=+3.38; prior-skewed-toward-observed:switch z=-3.38; two-prizes-random:switch z=+2.30
```
