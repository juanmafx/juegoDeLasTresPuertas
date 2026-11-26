# Optional qubit run: N = 4 one-query Grover, oracle phase moved off Clifford via CPhaseGate.
import argparse
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit.library import CPhaseGate
from qiskit.quantum_info import Clifford, Statevector

from branching_monty.core.grover import grover_success
from branching_monty.experiments.output import emit


def oracle_circuit(phi: float) -> QuantumCircuit:
    qc = QuantumCircuit(2)
    qc.append(CPhaseGate(phi), [0, 1])
    return qc


def grover_circuit(phi: float) -> QuantumCircuit:
    qc = QuantumCircuit(2)
    qc.h([0, 1])
    qc.compose(oracle_circuit(phi), inplace=True)
    qc.h([0, 1])
    qc.x([0, 1])
    qc.cz(0, 1)
    qc.x([0, 1])
    qc.h([0, 1])
    return qc


def qiskit_success(phi: float) -> float:
    return float(Statevector(grover_circuit(phi)).probabilities()[3])


def oracle_is_clifford(phi: float) -> bool:
    try:
        Clifford(oracle_circuit(phi))
    except Exception:
        return False
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--points", type=int, default=73)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)
    rows = []
    for phi in np.linspace(0, 2 * np.pi, args.points):
        rows.append(
            {
                "phi": float(phi),
                "qiskit_success": qiskit_success(phi),
                "numpy_success": grover_success(phi, np.pi, 4, 3),
                "oracle_is_clifford": oracle_is_clifford(phi),
            }
        )
    emit(
        {
            "experiment": "qiskit_n4",
            "black_box": "one CPhaseGate(phi) call marking |11>; standard diffusion; statevector",
            "rows": rows,
        },
        args.out,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
