# Samples one seeded world, runs the branch engine on it and writes the branch warehouse as JSON.
import argparse
import json
import random
import sys
from fractions import Fraction
from pathlib import Path

from branching_monty.branches.engine import BranchEngine, GameSpec, sample_world


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--doors", type=int, default=3)
    parser.add_argument("--reveals", type=int, default=1)
    parser.add_argument("--q", type=Fraction, default=Fraction(1))
    parser.add_argument("--convention", choices=["claim", "loss"], default="claim")
    parser.add_argument("--seed", type=int, default=20191001)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)

    spec = GameSpec(args.doors, args.reveals, args.q)
    truth, history = sample_world(spec, random.Random(args.seed))
    engine = BranchEngine(spec, args.convention)
    for obs in history:
        engine.observe(obs)
    door, value = engine.best_decision()
    document = engine.to_json()
    document["seed"] = args.seed
    document["truth"] = {"car": truth.car, "host_knows": truth.host_knows}
    document["decision"] = {"door": door, "posterior": str(value), "won": door == truth.car}

    text = json.dumps(document, indent=2)
    if args.out is None:
        sys.stdout.write(text + "\n")
    else:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
