# monty-lab in PHP

PHP implementation of the generalized Monty Hall decision lab. It follows the shared contract in
[`../spec/`](../spec/README.md) and is checked against it by
[`../tools/conformance.py`](../tools/conformance.py). The Python package in `../python/` is the
reference.

## What is here

| Path | Contents |
| --- | --- |
| `src/Fraction.php` | Exact rationals in lowest terms on `brick/math` arbitrary-precision integers |
| `src/Scenario.php` | Validated scenario: doors, prizes, prior, pick, reveals, host, host weights, mixed `q`, observation |
| `src/Solver.php` | Closed forms for unobserved games; enumeration of prize sets and host draws for weighted priors and observed reveals (at most 10 doors) |
| `src/Optimum.php` | Value curve `V(K) = P(win) - c*K`, exact optimum `K*`, and the least-squares parabola (Cramer's rule on exact normal equations) with vertex, rounded vertex and fitted choice |
| `src/Prng/` | SplitMix64, xoshiro256**, Lemire bounded draws, weighted choice, sampling and shuffle, on native 64-bit integers split into 32-bit and 16-bit limbs |
| `src/Simulator.php` | Deterministic Monte Carlo run following `spec/prng.md` step by step |
| `src/Wilson.php` | Wilson 95% score interval (the only floating-point output) |
| `src/Cli.php`, `bin/monty-lab` | The `exact`, `simulate`, `optimum` and `prng` subcommands of `spec/cli.md` |
| `tests/Unit/` | PHPUnit tests, including every scenario, PRNG vector and reference simulation in `spec/` |
| `reports/` | Output of the recorded test, static analysis and conformance runs |

No exact value goes through floating point. The PRNG never relies on integer overflow, which PHP
turns into floats; products are assembled from limbs that stay below 2^63.

## Requirements

- PHP 8.4 or newer. No extensions beyond the defaults are needed at run time: `brick/math` falls
  back to its pure-PHP calculator when GMP and BCMath are absent. That calculator is slow on the
  very large exact values that ten-door games with large prior weights produce: on the
  development machine, `optimum --doors 10 --prizes 3 --host random --strategy stay` with prior
  weights near 1,000,000 took about 32 seconds with the pure-PHP calculator and under one second in
  the same pinned image with the `bcmath` extension installed, with identical output. Install
  `ext-bcmath` or `ext-gmp` if you work with such games.
- Composer, for the pinned dependencies in `composer.lock`.
- PHPUnit needs the `dom` and `xml` extensions. Where the local PHP lacks them, run it in the
  pinned image below.

## Install

```bash
cd php
composer install --no-scripts --no-plugins
```

If the local PHP lacks `dom` or `xml`, either add
`--ignore-platform-req=ext-dom --ignore-platform-req=ext-xml --ignore-platform-req=ext-xmlwriter`
or install inside the pinned Composer image, as CI does:

```bash
docker run --rm -u "$(id -u):$(id -g)" -e COMPOSER_HOME=/tmp/composer -v "$PWD":/app -w /app \
  composer@sha256:698d3801b2a622ace460c4743c781282fcbcb733a4cbf8b31c44731e846585e8 \
  composer install --no-scripts --no-plugins --no-interaction
```

## Test

From the repository root, so the tests can read `spec/`:

```bash
PHP_IMAGE=php:8.4-cli@sha256:6b13a8678b38ca38e4e3950be57b664ed8c8706131a0586111f68792aede4c58
docker run --rm --network none -u "$(id -u):$(id -g)" -v "$PWD":/app -w /app/php "$PHP_IMAGE" vendor/bin/phpunit
docker run --rm -u "$(id -u):$(id -g)" -v "$PWD":/app -w /app/php "$PHP_IMAGE" vendor/bin/phpstan analyse
python3 -I tools/conformance.py --cli "php php/bin/monty-lab"
```

PHPStan runs at level 9 with one ignored identifier, `missingType.iterableValue`. Declaring array
value types needs PHPDoc, which this repository's no-docblock policy rules out, and level 10 then
fails on every untyped array read, so level 9 is the highest level the policy allows.

To refresh `reports/tests/`:

```bash
docker run --rm --network none -u "$(id -u):$(id -g)" -v "$PWD":/app -w /app/php "$PHP_IMAGE" \
  sh -c 'vendor/bin/phpunit --log-junit reports/tests/junit.xml; php tools/write-test-report.php'
```

## Usage

```bash
php/bin/monty-lab exact
php/bin/monty-lab exact --doors 5 --host biased --host-weights 1,1,1,4,2 --reveals 2 --observed 1,3
php/bin/monty-lab simulate --host random --seed 1 --trials 1000
php/bin/monty-lab optimum --doors 5 --strategy switch --cost 1/20
php/bin/monty-lab prng --seed 0 --kind words --count 4
```

Flags, validation, exit codes and the JSON output are those of [`../spec/cli.md`](../spec/cli.md).
`--flag value` and `--flag=value` are both accepted. Invalid input exits with code 2 and an
`error: ...` line on standard error. A closed standard output exits with 141.

`optimum` prints the exact value curve, the discrete optimum `K*` and the hypothetical optimum
parabola fitted to it, with how far its vertex lies from `K*` and what following the parabola
would cost.

## Differences from the Python reference

None are known. The input syntax in `spec/cli.md` now bounds every written part of a fraction to
2^63 - 1 and requires full flag names, so the earlier differences in mixed denominators and flag
prefixes no longer exist.
