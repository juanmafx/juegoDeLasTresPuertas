# Seeded Monte Carlo simulator whose random stream is fixed by spec/prng.md.
from dataclasses import dataclass

from monty_hall.lab.model import MAX_SEED, MAX_TRIALS, Host, Scenario, ScenarioError
from monty_hall.lab.prng import Xoshiro256StarStar


@dataclass(frozen=True, slots=True)
class SimulationCounts:
    trials: int
    seed: int
    decision: int
    void: int
    no_offer: int
    observed: int | None
    stay_wins: int
    switch_wins: int
    mixed_wins: int

    @property
    def sample_size(self) -> int:
        return self.decision if self.observed is None else self.observed


def simulate(scenario: Scenario, trials: int, seed: int) -> SimulationCounts:
    if isinstance(trials, bool) or not isinstance(trials, int) or not 1 <= trials <= MAX_TRIALS:
        raise ScenarioError(f"trials must be between 1 and {MAX_TRIALS}")
    if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed <= MAX_SEED:
        raise ScenarioError(f"seed must be between 0 and {MAX_SEED}")
    rng = Xoshiro256StarStar(seed)
    doors = list(range(scenario.doors))
    prior = list(scenario.prior_weights)
    pick = scenario.pick
    host = scenario.host
    host_weights = scenario.host_weights
    observed = None if scenario.observed is None else frozenset(scenario.observed)
    q_num, q_den = scenario.mixed.numerator, scenario.mixed.denominator
    decision = void = no_offer = observed_count = stay = switch = mixed = 0
    for _ in range(trials):
        prizes = frozenset(rng.weighted_sample(doors, prior, scenario.prizes))
        if host is Host.ADVERSARIAL and pick not in prizes:
            no_offer += 1
            continue
        if host is Host.RANDOM:
            candidates = [d for d in doors if d != pick]
        else:
            candidates = [d for d in doors if d != pick and d not in prizes]
        if host_weights is None:
            weights = [1] * len(candidates)
        else:
            weights = [host_weights[d] for d in candidates]
        opened = frozenset(rng.weighted_sample(candidates, weights, scenario.reveals))
        if host is Host.RANDOM and opened & prizes:
            void += 1
            continue
        decision += 1
        remaining = [d for d in doors if d != pick and d not in opened]
        target = remaining[rng.bounded(len(remaining))]
        switching = rng.bounded(q_den) < q_num
        if observed is not None:
            if opened != observed:
                continue
            observed_count += 1
        stay_win = pick in prizes
        switch_win = target in prizes
        stay += stay_win
        switch += switch_win
        mixed += switch_win if switching else stay_win
    return SimulationCounts(
        trials,
        seed,
        decision,
        void,
        no_offer,
        None if observed is None else observed_count,
        stay,
        switch,
        mixed,
    )
