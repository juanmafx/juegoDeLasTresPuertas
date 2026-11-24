# monty-lab, Java implementation

Java 17 implementation of the `monty-lab` contract in [`../spec/`](../spec/README.md). It has the
same subcommands, flags, validation and JSON output as the Python reference in `../python/`, and
its simulations produce the same win counts for the same seed.

- Exact results use `BigInteger` fractions (`Fraction`), never floating point.
- `Solver` uses the closed forms for unobserved games and enumerates prize placements for weighted
  priors and observed reveals (up to 10 doors, as the contract requires).
- `SplitMix64` and `Xoshiro256StarStar` follow `spec/prng.md`, including Lemire's bounded draw on
  the full unsigned 64-bit range.
- `Optimum` builds the value curve `V(K) = P(win) - c*K`, its exact discrete optimum, and the
  least-squares parabola (the "hypothetical optimum parabola") solved exactly by Cramer's rule.
- `Simulator` reports win counts; the CLI adds rates and Wilson 95% intervals.

There are no runtime dependencies. JUnit 5 is the only test dependency.

## Build and test

Maven runs in a pinned Docker image, so no local Maven is needed. From the repository root:

```bash
docker run --rm -u "$(id -u):$(id -g)" \
  -v "$PWD:/work" -w /work/java \
  -v "$HOME/.m2:/var/maven/.m2" -e MAVEN_CONFIG=/var/maven/.m2 \
  maven:3.9.11-eclipse-temurin-17@sha256:e4a7ace3dc0d645ed97f8d9ad0b0d3f0b14fa8d150138f27f116d7105a639b82 \
  mvn -B -ntp -Duser.home=/var/maven verify
```

With a local JDK 17 you can use the committed Maven wrapper instead. It downloads Maven 3.9.11 and
checks it against the SHA-256 in `.mvn/wrapper/maven-wrapper.properties`:

```bash
cd java
./mvnw -B verify
```

Both build `target/monty-lab.jar` and run the JUnit suite. The tests read `../spec/` directly:
every PRNG vector, every scenario's exact and optimum expectations, and every reference simulation.

## Conformance

```bash
python3 -I tools/conformance.py --cli "java -jar java/target/monty-lab.jar"
```

`java/tools/test-report.sh` does the Docker build, copies the JUnit XML into `reports/tests/`,
runs the conformance check, and writes `reports/tests/test-report.md` and
`reports/conformance.json`. Set `MONTY_LAB_M2` to use a Maven cache other than `~/.m2`.

## Usage

```bash
java -jar java/target/monty-lab.jar exact
java -jar java/target/monty-lab.jar exact --doors 5 --prizes 2 --reveals 2 --host random
java -jar java/target/monty-lab.jar exact --host biased --host-weights 1,3,1 --observed 2
java -jar java/target/monty-lab.jar simulate --host random --seed 1 --trials 1000
java -jar java/target/monty-lab.jar optimum --doors 5 --strategy switch --cost 1/20
java -jar java/target/monty-lab.jar prng --seed 0 --kind words --count 4
```

Output is one JSON document on standard output. Invalid input exits with code 2 and prints
`error: ...` on standard error; a closed standard output exits with 141. See
[`../spec/cli.md`](../spec/cli.md) for every flag and field.

Like the Python reference's argparse parser, flags accept `--flag value` and `--flag=value`, and
a unique prefix of a flag name (`--rev 2`) is accepted.
