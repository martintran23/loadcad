import json
from pathlib import Path

import numpy as np
import pytest

from loadcad.geometry.bracket import BracketSpec
from loadcad.geometry.errors import GeometryError
from loadcad.paths import ccx_executable
from loadcad.proof import run_bracket
from loadcad.solver.deck import write_deck
from loadcad.solver.frd import displacements, parse_frd
from loadcad.solver.runner import SolverFailure, require_bounded_displacement, run_ccx

ccx = pytest.mark.skipif(ccx_executable() is None, reason="CalculiX ccx_static.exe is not available")


def test_zero_fillet_job_fails_without_a_safety_factor(tmp_path: Path):
    spec = BracketSpec(60, 60, 30, 5, 0)
    with pytest.raises(GeometryError) as caught:
        run_bracket(tmp_path, spec)
    assert caught.value.code == "request_invalid"
    status = json.loads((tmp_path / "status.json").read_text(encoding="utf-8"))
    assert status["status"] == "failed"
    assert status["failure_code"] == "request_invalid"
    assert not (tmp_path / "results" / "results.json").exists()


@ccx
def test_unrestrained_solid_fails_without_a_safety_factor(tmp_path: Path):
    nodes = {
        1: np.array([0.0, 0.0, 0.0]),
        2: np.array([1.0, 0.0, 0.0]),
        3: np.array([0.0, 1.0, 0.0]),
        4: np.array([0.0, 0.0, 1.0]),
    }
    for offset, (first, second) in enumerate(((1, 2), (2, 3), (3, 1), (1, 4), (2, 4), (3, 4)), start=5):
        nodes[offset] = 0.5 * (nodes[first] + nodes[second])
    write_deck(
        tmp_path / "job.inp",
        nodes,
        {1: list(range(1, 11))},
        fixed_nodes=[],
        cloads={4: np.array([0.0, 0.0, -1.0])},
        restrain=False,
        integration_point_stress=False,
    )
    solved = run_ccx(ccx_executable(), tmp_path, timeout_s=60)
    assert solved.returncode == 0
    disp = displacements(parse_frd(solved.frd_path))
    peak = max(float(np.linalg.norm(value)) for value in disp.values())
    with pytest.raises(SolverFailure) as caught:
        require_bounded_displacement(peak, 1.0)
    assert caught.value.code == "solver_failed"
    text = (tmp_path / "job.inp").read_text(encoding="ascii")
    assert "*BOUNDARY" not in text
    assert "estimated_safety_factor" not in text
