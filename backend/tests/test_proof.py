import json
from pathlib import Path

import pytest

from loadcad.paths import ccx_executable, repo_root
from loadcad.proof import run_beam, run_bracket
from loadcad.toolchain import probe_paths

ccx = pytest.mark.skipif(ccx_executable() is None, reason="CalculiX ccx_static.exe is not available")


@ccx
def test_path_probe_and_beam_and_bracket_solves():
    root = repo_root() / "artifacts" / "phase1"
    report = probe_paths(root / "path-with-space", Path(r"C:\Temp\loadcad-phase1\path-nospace"))
    (root / "path_probe.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    for label in ("with_spaces", "without_spaces"):
        assert report[label]["gmsh"]["ok"]
        assert report[label]["ccx"]["ok"]
    beam = run_beam(root / "beam")
    bracket = run_bracket(root / "bracket")
    for record, folder in ((beam, root / "beam"), (bracket, root / "bracket")):
        assert record["estimated_safety_factor"] is None
        assert record["decision_metric"] is None
        assert record["max_nodal_von_mises_mpa"] > 0
        assert (folder / "solver" / "job.frd").is_file()
        assert (folder / "solver" / "job.inp").is_file()
        assert (folder / "results" / "results.json").is_file()
    assert (root / "bracket" / "geometry" / "bracket.step").is_file()
    assert (root / "bracket" / "geometry" / "bracket.stl").is_file()
    assert (root / "bracket" / "mesh" / "bracket.msh").is_file()
    assert beam["tip_downward_deflection_mm"] > 0
    # Equilibrium is a load check, not a stress-accuracy band.
    assert beam["relative_balance_error"] < 0.01
    assert bracket["relative_balance_error"] < 0.01
