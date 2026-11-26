# The branch engine must reproduce Module 1 and the existing decision lab exactly.
import random
from fractions import Fraction

import numpy as np
import pytest
from branching_monty.branches.engine import (
    BranchEngine,
    GameSpec,
    ensemble_leverage,
    exact_value,
    sample_world,
    tree_joint,
)
from branching_monty.core.host import decision_mask, host_joint
from branching_monty.core.leverage import leverage
from monty_hall.lab.model import Host, Scenario
from monty_hall.lab.solver import solve

Q_GRID = [Fraction(0), Fraction(1, 4), Fraction(1, 2), Fraction(3, 4), Fraction(1)]


@pytest.mark.parametrize("q", Q_GRID)
def test_one_reveal_tree_matches_host_joint(q: Fraction) -> None:
    histories, joint = tree_joint(GameSpec(3, 1, q), 1)
    reference = host_joint(float(q), 3)
    columns = {history[0]: [float(row[i]) for row in joint] for i, history in enumerate(histories)}
    for i, action in enumerate(reference.actions):
        assert columns[action] == pytest.approx(reference.probs[:, i].tolist(), abs=1e-15)


@pytest.mark.parametrize("q", Q_GRID)
@pytest.mark.parametrize("convention", ["claim", "loss"])
def test_ensemble_leverage_matches_module_one(q: Fraction, convention: str) -> None:
    reference = host_joint(float(q), 3)
    expected = leverage(reference.probs, decision_mask(reference, convention))
    result = ensemble_leverage(GameSpec(3, 1, q), 1, convention)
    assert result.value == pytest.approx(expected.value, abs=1e-15)
    assert result.info == pytest.approx(expected.info, abs=1e-12)
    assert result.lam == pytest.approx(expected.lam, abs=1e-12)


@pytest.mark.parametrize("q", Q_GRID)
def test_exact_values_are_closed_forms(q: Fraction) -> None:
    spec = GameSpec(3, 1, q)
    assert exact_value(spec, 1, "claim") == Fraction(2, 3)
    assert exact_value(spec, 1, "loss") == (1 + q) / 3


@pytest.mark.parametrize("q", Q_GRID)
def test_goat_reveal_posterior_is_exact(q: Fraction) -> None:
    engine = BranchEngine(GameSpec(3, 1, q))
    engine.observe((1, False))
    assert engine.posterior_car() == [1 / (2 + q), Fraction(0), (1 + q) / (2 + q)]
    door, value = engine.best_decision()
    assert value == (1 + q) / (2 + q)
    assert door == (0 if q == 0 else 2)


@pytest.mark.parametrize("doors", range(3, 8))
@pytest.mark.parametrize(("q", "host"), [(Fraction(1), Host.INFORMED), (Fraction(0), Host.RANDOM)])
def test_goat_histories_match_decision_lab(doors: int, q: Fraction, host: Host) -> None:
    for reveals in range(doors - 1):
        engine = BranchEngine(GameSpec(doors, reveals, q))
        for door in range(1, reveals + 1):
            engine.observe((door, False))
        lab = solve(Scenario(doors=doors, reveals=reveals, host=host))
        marginal = engine.posterior_car()
        assert marginal[0] == lab.stay
        assert all(marginal[d] == lab.switch for d in range(reveals + 1, doors))


def test_log_tracks_pruning() -> None:
    engine = BranchEngine(GameSpec(3, 1, Fraction(1, 2)))
    assert engine.log[0].live_branches == 6
    assert engine.log[0].posterior_entropy == pytest.approx(np.log2(3))
    assert engine.log[0].ensemble_lambda == pytest.approx(0.0, abs=1e-12)
    assert engine.log[0].ensemble_info == pytest.approx(0.0, abs=1e-12)
    entry = engine.observe((1, False))
    assert entry.live_branches == 4
    assert entry.min_entropy == pytest.approx(-np.log2(3 / 5))
    assert entry.ensemble_lambda == pytest.approx(1.0)


def test_warehouse_keeps_every_branch_and_normalised_weights() -> None:
    engine = BranchEngine(GameSpec(5, 3, Fraction(1, 3)))
    for door in (1, 2, 3):
        engine.observe((door, False))
    assert len(engine.warehouse) == 10
    for step in range(4):
        total = sum(record.weights[step] for record in engine.warehouse.values())
        assert total == 1
    assert len(engine.to_json()["log"]) == 4


def test_impossible_observation_is_rejected() -> None:
    engine = BranchEngine(GameSpec(4, 2, Fraction(1)))
    with pytest.raises(ValueError, match="impossible"):
        engine.observe((0, False))
    with pytest.raises(ValueError, match="impossible"):
        engine.observe((1, True))
    engine.observe((1, False))
    engine.observe((2, False))
    with pytest.raises(ValueError, match="no reveals left"):
        engine.observe((3, False))


def test_spec_validation() -> None:
    with pytest.raises(ValueError, match="reveals"):
        GameSpec(4, 3, Fraction(1))
    with pytest.raises(ValueError, match="q must"):
        GameSpec(4, 1, Fraction(3, 2))


@pytest.mark.parametrize("convention", ["claim", "loss"])
def test_monte_carlo_agrees_with_exact_value(convention: str) -> None:
    spec = GameSpec(4, 2, Fraction(1, 3))
    rng = random.Random(20191001)
    trials = 6000
    wins = 0
    for _ in range(trials):
        truth, history = sample_world(spec, rng)
        engine = BranchEngine(spec, convention)
        for obs in history:
            engine.observe(obs)
        door, _ = engine.best_decision()
        wins += door == truth.car
    exact = float(exact_value(spec, 2, convention))
    sigma = np.sqrt(exact * (1 - exact) / trials)
    assert abs(wins / trials - exact) < 4 * sigma
