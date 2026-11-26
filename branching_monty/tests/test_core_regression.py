# Regression targets from Context A of the Branching Monty prompt, plus derived closed forms.
from itertools import pairwise

import numpy as np
import pytest
from branching_monty.core.grover import density, grover_states, grover_success
from branching_monty.core.holevo import guess_probability, holevo_chi
from branching_monty.core.host import decision_mask, host_joint, success_given_goat
from branching_monty.core.leverage import conditional_min_entropy, leverage, mutual_information
from branching_monty.core.wigner import mana, wigner

TAU = 2 * np.pi
Q_GRID = [0.0, 0.25, 0.5, 0.75, 1.0]


def oracle_states(phi: float) -> list[np.ndarray]:
    return [grover_states(phi, phi, 3, t)[1] for t in range(3)]


@pytest.mark.parametrize(
    ("q", "expected"), [(0.0, 1 / 2), (0.25, 5 / 9), (0.5, 3 / 5), (0.75, 7 / 11), (1.0, 2 / 3)]
)
def test_switch_win_given_goat_matches_closed_form(q: float, expected: float) -> None:
    assert success_given_goat(host_joint(q, 3)) == pytest.approx(expected, abs=1e-12)
    assert expected == pytest.approx((1 + q) / (2 + q), abs=1e-12)


@pytest.mark.parametrize("q", [0.0, 0.3, 0.6, 0.9])
def test_derivative_matches_closed_form(q: float) -> None:
    h = 1e-6
    slope = (success_given_goat(host_joint(q + h, 3)) - success_given_goat(host_joint(q, 3))) / h
    assert slope == pytest.approx(1 / (2 + q) ** 2, abs=1e-5)


def test_mutual_information_endpoints() -> None:
    assert mutual_information(host_joint(0.0, 3).probs) == pytest.approx(np.log2(3) - 2 / 3)
    assert mutual_information(host_joint(0.0, 3).probs) == pytest.approx(0.918, abs=5e-4)
    assert mutual_information(host_joint(1.0, 3).probs) == pytest.approx(2 / 3)


def test_mutual_information_falls_monotonically_with_q() -> None:
    values = [mutual_information(host_joint(q, 3).probs) for q in np.linspace(0, 1, 21)]
    assert all(a > b for a, b in pairwise(values))


@pytest.mark.parametrize("q", Q_GRID)
def test_unconditional_value_claim_convention_is_two_thirds(q: float) -> None:
    joint = host_joint(q, 3)
    assert leverage(joint.probs, decision_mask(joint, "claim")).value == pytest.approx(2 / 3)


@pytest.mark.parametrize("q", Q_GRID)
def test_unconditional_value_loss_convention(q: float) -> None:
    joint = host_joint(q, 3)
    result = leverage(joint.probs, decision_mask(joint, "loss"))
    assert result.value == pytest.approx((1 + q) / 3)
    assert result.lam == pytest.approx(np.log2(1 + q))


@pytest.mark.parametrize("q", Q_GRID)
def test_leverage_equals_log_n_minus_min_entropy_when_all_actions_allowed(q: float) -> None:
    joint = host_joint(q, 3)
    expected = np.log2(3) - conditional_min_entropy(joint.probs)
    assert leverage(joint.probs).lam == pytest.approx(expected)


def test_one_query_standard_grover() -> None:
    assert grover_success(np.pi, np.pi, 3, 0) == pytest.approx(25 / 27)


@pytest.mark.parametrize("phase", [TAU / 3, 2 * TAU / 3])
def test_one_query_phase_matched_grover_is_exact(phase: float) -> None:
    for target in range(3):
        assert grover_success(phase, phase, 3, target) == pytest.approx(1.0)


def test_mismatched_phases_lose_the_advantage() -> None:
    assert grover_success(TAU / 3, 2 * TAU / 3, 3, 0) == pytest.approx(1 / 3)


def test_wigner_is_normalised() -> None:
    for state in grover_states(np.pi, np.pi, 3, 1):
        assert wigner(density(state), 3).sum() == pytest.approx(1.0)


def test_exact_circuit_stays_wigner_non_negative() -> None:
    for state in grover_states(TAU / 3, TAU / 3, 3, 0):
        values = wigner(density(state), 3)
        assert values.min() == pytest.approx(0.0, abs=1e-12)
        assert mana(density(state), 3) == pytest.approx(0.0, abs=1e-12)


def test_pi_oracle_creates_negativity_and_mana() -> None:
    initial, marked, _ = grover_states(np.pi, np.pi, 3, 0)
    assert wigner(density(initial), 3).min() == pytest.approx(0.0, abs=1e-12)
    assert wigner(density(marked), 3).min() == pytest.approx(-1 / 9)
    assert mana(density(marked), 3) == pytest.approx(np.log2(13 / 9))


def test_wigner_rejects_non_prime_dimension() -> None:
    with pytest.raises(ValueError, match="odd prime"):
        wigner(np.eye(9) / 9, 9)


def test_holevo_chi_after_one_oracle() -> None:
    priors = [1 / 3] * 3
    assert holevo_chi(oracle_states(np.pi), priors) == pytest.approx(1.392, abs=5e-4)
    assert holevo_chi(oracle_states(TAU / 3), priors) == pytest.approx(np.log2(3))


@pytest.mark.parametrize("method", ["srm", "sdp"])
def test_optimal_guessing_after_one_oracle(method: str) -> None:
    priors = [1 / 3] * 3
    tolerance = 1e-12 if method == "srm" else 1e-6
    pi_guess = guess_probability(oracle_states(np.pi), priors, method=method)
    exact_guess = guess_probability(oracle_states(TAU / 3), priors, method=method)
    assert pi_guess == pytest.approx(25 / 27, abs=tolerance)
    assert exact_guess == pytest.approx(1.0, abs=tolerance)


@pytest.mark.parametrize("phi", [np.pi, TAU / 3])
def test_diffusion_is_the_optimal_discriminator(phi: float) -> None:
    priors = [1 / 3] * 3
    optimum = guess_probability(oracle_states(phi), priors, method="sdp")
    assert grover_success(phi, phi, 3, 0) == pytest.approx(optimum, abs=1e-6)


def test_host_joint_is_a_distribution() -> None:
    for n in (3, 4, 7):
        for q in Q_GRID:
            joint = host_joint(q, n)
            assert joint.probs.sum() == pytest.approx(1.0)
            assert joint.probs.sum(axis=1) == pytest.approx(np.full(n, 1 / n))


def test_host_joint_rejects_invalid_input() -> None:
    with pytest.raises(ValueError, match="q must"):
        host_joint(1.5, 3)
    with pytest.raises(ValueError, match="n_doors"):
        host_joint(0.5, 2)
