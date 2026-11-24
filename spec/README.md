# Shared specification

Every language implementation follows these files. Nothing here depends on a particular language.

| File | Contents | Produced by |
| --- | --- | --- |
| [cli.md](cli.md) | The model, flags, validation, output and exit codes | Written by hand |
| [prng.md](prng.md) | SplitMix64, xoshiro256**, Lemire bounded draws, weighted choice, shuffle, one simulated game | Written by hand |
| [scenario.schema.json](scenario.schema.json) | JSON Schema for a scenario and for `scenarios.json` | Written by hand |
| [cli-output.schema.json](cli-output.schema.json) | JSON Schema for the output of every subcommand | Written by hand |
| [scenarios.json](scenarios.json) | 49 scenarios with exact expected fractions and value curves | Inputs by hand, `expected` by `tools/enumerate.py --write` |
| [prng-vectors.json](prng-vectors.json) | 105 golden generator outputs over five seeds | `python/tools/write_spec_data.py` |
| [simulation-reference.json](simulation-reference.json) | Win counts of the Python reference for every scenario with a `simulation` block | `python/tools/write_spec_data.py` |

## Where the expected values come from

`tools/enumerate.py` is a standalone script that imports nothing from any implementation. It walks
the game's probability tree directly: every ordered prize draw, every ordered host draw and every
switch target, each with its exact probability, and adds up wins with Python's `Fraction`. That is
the `brute_force` method, used when the tree has at most 400,000 leaves.

Larger games, up to 64 doors, need a uniform prior and no observed reveal. They use the
`class_enumeration` method: it conditions on whether the pick holds a prize, enumerates the
hypergeometric number of prizes a random host reveals, and counts prizes among the closed doors.
It is still exact, but it relies on the exchangeability of a uniform prior instead of listing
every door. Each scenario records which method produced it in `expected.exact_method`.

The least-squares parabola in the enumerator is solved by Gaussian elimination, while the Python
reference uses Cramer's rule, so the two fits are computed independently.

Check the file with:

```bash
python3 -I tools/enumerate.py spec/scenarios.json --check
```

The PRNG vectors were cross-checked once, outside the repository, against a separate C
transcription of the algorithms in `prng.md`; all 105 agreed.
