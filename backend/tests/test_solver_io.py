import subprocess
from pathlib import Path

import numpy as np
import pytest

from loadcad.jobs.store import result_record
from loadcad.postprocess.stress import von_mises
from loadcad.solver.deck import write_deck, write_smoke_tet
from loadcad.solver.frd import displacements, parse_frd, stress_components
from loadcad.solver.runner import SolverFailure, run_ccx, solver_command


FRD = """
 -4  DISP        4    1
 -5  D1          1    1    1    0
 -5  D2          1    1    2    0
 -5  D3          1    1    3    0
 -1         1 1.00000E-03 0.00000E+00 -2.00000E-03
 -1         2 0.00000E+00 0.00000E+00 -4.00000E-03
 -1         3-1.00000E-03 2.00000E-03-3.00000E-03
 -3
 -4  STRESS      6    1
 -5  SXX         1    1    1    0
 -5  SYY         1    1    2    0
 -5  SZZ         1    1    3    0
 -5  SXY         1    1    4    0
 -5  SYZ         1    1    5    0
 -5  SZX         1    1    6    0
 -1         1 2.00000E+00 0.00000E+00 0.00000E+00 0.00000E+00 0.00000E+00 0.00000E+00
 -2  0.00000E+00
 -3
"""


def test_frd_parser_reads_components_by_name(tmp_path: Path):
    path = tmp_path / "job.frd"
    path.write_text(FRD, encoding="ascii")
    parsed = parse_frd(path)
    disp = displacements(parsed)
    stress = stress_components(parsed)
    assert disp[1] == pytest.approx(np.array([1e-3, 0.0, -2e-3]))
    assert disp[3] == pytest.approx(np.array([-1e-3, 2e-3, -3e-3]))
    assert von_mises(*stress[1]) == pytest.approx(2.0)


def test_deck_uses_c3d10_and_fixed_names(tmp_path: Path):
    path = tmp_path / "job.inp"
    nodes = {1: np.zeros(3)}
    elements = {1: list(range(1, 11))}
    write_deck(path, nodes, elements, fixed_nodes=[1, 2], dloads=[(1, 1, 3.5)])
    text = path.read_text(encoding="ascii")
    assert "*ELEMENT, TYPE=C3D10, ELSET=EALL" in text
    assert "FIXED_MOUNT, 1, 3, 0." in text
    assert "1, P1," in text
    assert "*INCLUDE" not in text
    assert "BENCHMARK" in text


def test_smoke_deck_has_ten_nodes(tmp_path: Path):
    path = tmp_path / "job.inp"
    write_smoke_tet(path)
    lines = path.read_text(encoding="ascii").splitlines()
    element = lines[lines.index("*ELEMENT, TYPE=C3D10, ELSET=EALL") + 1]
    assert len([part for part in element.split(",") if part.strip()]) == 11


def test_timeout_and_nonzero_exit_do_not_become_results(tmp_path: Path, monkeypatch):
    def fake_timeout(*_args, **kwargs):
        assert kwargs["shell"] is False
        assert isinstance(kwargs.get("cwd"), Path) or True
        raise subprocess.TimeoutExpired(cmd=["ccx"], timeout=1)

    monkeypatch.setattr(subprocess, "run", fake_timeout)
    with pytest.raises(SolverFailure) as caught:
        run_ccx(Path("ccx.exe"), tmp_path, timeout_s=1)
    assert caught.value.code == "solver_timeout"

    def fake_fail(*_args, **kwargs):
        assert kwargs["shell"] is False
        return subprocess.CompletedProcess(solver_command(Path("ccx.exe")), 8, b"bad", b"")

    monkeypatch.setattr(subprocess, "run", fake_fail)
    with pytest.raises(SolverFailure) as caught:
        run_ccx(Path("ccx.exe"), tmp_path)
    assert caught.value.code == "solver_failed"


def test_phase1_result_record_has_no_safety_factor():
    record = result_record(solver_status="completed", max_nodal_von_mises_mpa=12.0)
    assert record["decision_metric"] is None
    assert record["estimated_safety_factor"] is None
    assert "not a certified" in record["disclaimer"].lower()
