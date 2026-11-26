# Module 4: Spekkens, quantum and Bayesian tiers on the same marked-door black boxes.
from fractions import Fraction

import numpy as np
import pytest
from branching_monty.core.grover import (
    density,
    diffusion,
    grover_states,
    grover_success,
    oracle,
    uniform_state,
)
from branching_monty.core.holevo import guess_probability
from branching_monty.core.wigner import mana, wigner
from branching_monty.tiers.bayesian import bit_query_value, mark_reveal_value, monty_partial_host
from branching_monty.tiers.quantum import (
    best_one_query_closed_form,
    best_phases,
    chirp_oracle,
    chirp_protocol,
    dephased_success,
    gamma_star_closed_form,
    gamma_star_numeric,
    partial_oracle_grover,
    partial_oracle_optimum,
    post_oracle_mana,
    success_grid,
)
from branching_monty.tiers.spekkens import (
    NotRepresentable,
    collapse_position,
    evolve,
    is_clifford,
    is_line_state,
    lines,
    measure_position,
    momentum_eigenstate,
    represent,
    symplectic_group,
)

TAU = 2 * np.pi
Q_GRID = [0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0]


def test_phase_space_structure() -> None:
    assert len(lines(3)) == 12
    assert len(lines(5)) == 30
    assert len(symplectic_group(3)) == 24
    assert len(symplectic_group(5)) == 120


@pytest.mark.parametrize("d", [3, 5])
def test_uniform_state_is_the_zero_momentum_line(d: int) -> None:
    s = uniform_state(d)
    assert np.allclose(wigner(density(s), d), momentum_eigenstate(0, d))


@pytest.mark.parametrize("phase", [TAU / 3, 2 * TAU / 3])
@pytest.mark.parametrize("target", range(3))
def test_spekkens_reproduces_exact_search(phase: float, target: int) -> None:
    maps = [represent(oracle(phase, 3, target), 3), represent(diffusion(phase, 3), 3)]
    toy = evolve(momentum_eigenstate(0, 3), maps)
    quantum = grover_states(phase, phase, 3, target)
    for epistemic, state in zip(toy, quantum, strict=True):
        assert np.allclose(epistemic, wigner(density(state), 3), atol=1e-12)
        assert is_line_state(epistemic, 3)
    assert np.allclose(measure_position(toy[-1]), np.eye(3)[target])


@pytest.mark.parametrize("d", [3, 5])
def test_spekkens_reproduces_chirp_search(d: int) -> None:
    outcomes = set()
    for target in range(d):
        gates = [chirp_oracle(d, target), *chirp_protocol(d)]
        toy = evolve(momentum_eigenstate(0, d), [represent(g, d) for g in gates])
        state = uniform_state(d)
        for step, gate in enumerate(gates, start=1):
            state = gate @ state
            assert np.allclose(wigner(density(state), d), toy[step], atol=1e-9)
        probs = measure_position(toy[-1])
        assert probs.max() == pytest.approx(1.0)
        outcomes.add(int(np.argmax(probs)))
    assert outcomes == set(range(d))


def test_spekkens_cannot_implement_pi_phase_gates() -> None:
    with pytest.raises(NotRepresentable):
        represent(oracle(np.pi, 3, 0), 3)
    assert not is_clifford(diffusion(np.pi, 3), 3)


def test_only_stabilizer_phases_are_clifford_at_three_doors() -> None:
    clifford = [k for k in range(36) if is_clifford(oracle(TAU * k / 36, 3, 0), 3)]
    assert clifford == [0, 12, 24]


def test_no_nontrivial_marking_oracle_is_clifford_at_five_doors() -> None:
    assert is_clifford(oracle(0.0, 5, 0), 5)
    for k in range(1, 5):
        assert not is_clifford(oracle(TAU * k / 5, 5, 0), 5)
    assert not is_clifford(oracle(np.pi, 5, 0), 5)


def test_measurement_collapses_to_a_line() -> None:
    final = evolve(momentum_eigenstate(0, 3), [represent(oracle(TAU / 3, 3, 1), 3)])[-1]
    post = collapse_position(final, 2)
    assert is_line_state(post, 3)
    assert np.allclose(post.sum(axis=1), np.eye(3)[2])


def test_success_grid_matches_state_vector() -> None:
    rng = np.random.default_rng(7)
    phis, thetas = rng.uniform(0, TAU, 9), rng.uniform(0, TAU, 9)
    grid = success_grid(3, phis, thetas)
    for i, phi in enumerate(phis):
        for j, theta in enumerate(thetas):
            assert grid[i, j] == pytest.approx(grover_success(phi, theta, 3, 0), abs=1e-12)


def test_coarse_grid_peaks_only_at_matched_stabilizer_phases() -> None:
    axis = np.linspace(0, TAU, 37)
    grid = success_grid(3, axis, axis)
    peaks = {(i % 36, j % 36) for i, j in zip(*np.where(grid > 1 - 1e-12), strict=True)}
    assert peaks == {(12, 12), (24, 24)}


def test_residual_is_not_a_function_of_mana() -> None:
    axis = np.linspace(0, TAU, 361)
    zero_phase = success_grid(3, np.array([0.0]), axis).max()
    exact_phase = success_grid(3, np.array([TAU / 3]), axis).max()
    assert post_oracle_mana(0.0, 3) == pytest.approx(0.0, abs=1e-12)
    assert post_oracle_mana(TAU / 3, 3) == pytest.approx(0.0, abs=1e-12)
    assert zero_phase == pytest.approx(1 / 3)
    assert exact_phase == pytest.approx(1.0)


@pytest.mark.parametrize("q", Q_GRID)
def test_partial_quantum_oracle_equals_classical_mark_reveal(q: float) -> None:
    phi, theta = best_phases(3)
    expected = max(q, (1 - q) / 2)
    assert partial_oracle_grover(phi, theta, 3, q) == pytest.approx(expected, abs=1e-12)
    assert partial_oracle_optimum(phi, 3, q) == pytest.approx(expected, abs=1e-6)
    assert float(mark_reveal_value(3, Fraction(q).limit_denominator(100))) == pytest.approx(
        expected
    )


GOLDEN = (np.sqrt(5) - 1) / 2


@pytest.mark.parametrize("q", [0.1, 0.25, 0.5, 0.6, 0.65, 0.75, 0.9])
def test_monty_and_partial_quantum_oracle_cross_at_inverse_golden_ratio(q: float) -> None:
    phi, theta = best_phases(3)
    monty = (1 + q) / (2 + q)
    quantum = partial_oracle_grover(phi, theta, 3, q)
    if q < GOLDEN:
        assert monty > quantum + 1e-6
    else:
        assert quantum > monty + 1e-6


def test_crossing_point_is_exact() -> None:
    phi, theta = best_phases(3)
    assert partial_oracle_grover(phi, theta, 3, GOLDEN) == pytest.approx(
        (1 + GOLDEN) / (2 + GOLDEN), abs=1e-12
    )
    assert float(monty_partial_host(Fraction(1, 2))) == pytest.approx(3 / 5)


def test_bit_query_baseline() -> None:
    for n in (3, 4, 5):
        assert bit_query_value(n, Fraction(1)) == Fraction(2, n)


@pytest.mark.parametrize("n", range(3, 8))
def test_best_one_query_closed_form(n: int) -> None:
    phi, theta = best_phases(n)
    best = best_one_query_closed_form(n)
    assert grover_success(phi, theta, n, 0) == pytest.approx(best, abs=1e-12)
    axis = np.linspace(0, TAU, 145)
    assert success_grid(n, axis, axis).max() <= best + 1e-9


@pytest.mark.parametrize("n", [3, 4, 5])
def test_dephasing_is_affine_in_gamma(n: int) -> None:
    phi, theta = best_phases(n)
    best = best_one_query_closed_form(n)
    for gamma in (0.0, 0.2, 0.55, 1.0):
        expected = (1 - gamma) * best + gamma / n
        assert dephased_success(phi, theta, n, gamma) == pytest.approx(expected, abs=1e-12)


@pytest.mark.parametrize(
    ("n", "threshold", "expected"),
    [
        (3, 2 / 3, Fraction(1, 2)),
        (4, 2 / 3, Fraction(4, 9)),
        (5, 2 / 3, Fraction(113, 288)),
        (3, 2 / 3, Fraction(1, 2)),
        (4, 1 / 2, Fraction(2, 3)),
        (5, 2 / 5, Fraction(71, 96)),
    ],
)
def test_gamma_star(n: int, threshold: float, expected: Fraction) -> None:
    assert gamma_star_closed_form(n, threshold) == pytest.approx(float(expected), abs=1e-12)
    assert gamma_star_numeric(n, threshold) == pytest.approx(float(expected), abs=1e-10)


def test_five_door_wigner() -> None:
    s = uniform_state(5)
    assert wigner(density(s), 5).sum() == pytest.approx(1.0)
    assert mana(density(s), 5) == pytest.approx(0.0, abs=1e-12)
    assert wigner(density(oracle(np.pi, 5, 0) @ s), 5).min() < -1e-3


def test_five_door_strict_gap_where_three_doors_show_none() -> None:
    quantum_five = guess_probability(
        [oracle(np.pi, 5, t) @ uniform_state(5) for t in range(5)], [1 / 5] * 5
    )
    assert quantum_five == pytest.approx(121 / 125, abs=1e-6)
    assert grover_success(np.pi, np.pi, 5, 0) == pytest.approx(121 / 125, abs=1e-12)
    spekkens_five = float(bit_query_value(5, Fraction(1)))
    assert quantum_five - spekkens_five == pytest.approx(121 / 125 - 2 / 5, abs=1e-6)
    quantum_three = grover_success(TAU / 3, TAU / 3, 3, 0)
    assert quantum_three - 1.0 == pytest.approx(0.0, abs=1e-12)


def test_five_door_gap_does_not_track_mana() -> None:
    def optimum(phi: float) -> float:
        return guess_probability(
            [oracle(phi, 5, t) @ uniform_state(5) for t in range(5)], [1 / 5] * 5
        )

    low, high = TAU / 5, 2 * TAU / 5
    assert post_oracle_mana(low, 5) == pytest.approx(post_oracle_mana(high, 5), abs=1e-12)
    assert optimum(low) == pytest.approx(0.6647, abs=5e-4)
    assert optimum(high) == pytest.approx(0.9423, abs=5e-4)


def test_qiskit_n4_matches_numpy() -> None:
    pytest.importorskip("qiskit")
    from branching_monty.experiments.qiskit_n4 import oracle_is_clifford, qiskit_success

    for phi in np.linspace(0, TAU, 13):
        assert qiskit_success(phi) == pytest.approx(grover_success(phi, np.pi, 4, 3), abs=1e-12)
    assert qiskit_success(np.pi) == pytest.approx(1.0)
    assert oracle_is_clifford(np.pi)
    assert not oracle_is_clifford(np.pi / 3)
