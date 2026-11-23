"""Probe whether ccx and Gmsh tolerate a path that contains spaces."""

from __future__ import annotations

import traceback
from pathlib import Path

from loadcad.paths import ccx_executable
from loadcad.solver.deck import write_smoke_tet
from loadcad.solver.runner import SolverFailure, run_ccx


def _gmsh_box(directory: Path) -> dict[str, object]:
    import gmsh

    directory.mkdir(parents=True, exist_ok=True)
    msh = directory / "box.msh"
    gmsh.initialize()
    try:
        gmsh.model.add("box")
        gmsh.model.occ.addBox(0, 0, 0, 10, 10, 10)
        gmsh.model.occ.synchronize()
        gmsh.option.setNumber("Mesh.MeshSizeMax", 5)
        gmsh.model.mesh.generate(3)
        gmsh.write(str(msh))
        version = str(gmsh.option.getString("General.Version"))
    finally:
        gmsh.finalize()
    return {"ok": msh.is_file() and msh.stat().st_size > 0, "msh": str(msh), "gmsh_version": version}


def _ccx_smoke(directory: Path) -> dict[str, object]:
    ccx = ccx_executable()
    solver = directory / "solver"
    solver.mkdir(parents=True, exist_ok=True)
    write_smoke_tet(solver / "job.inp")
    if ccx is None:
        return {"ok": False, "error": "ccx missing"}
    try:
        result = run_ccx(ccx, solver, timeout_s=120)
    except SolverFailure as exc:
        return {"ok": False, "error": str(exc), "code": exc.code}
    return {"ok": True, "returncode": result.returncode, "frd": str(result.frd_path)}


def probe_paths(with_spaces: Path, without_spaces: Path) -> dict[str, object]:
    report: dict[str, object] = {}
    for label, directory in (("with_spaces", with_spaces), ("without_spaces", without_spaces)):
        entry: dict[str, object] = {"directory": str(directory)}
        try:
            entry["gmsh"] = _gmsh_box(directory / "gmsh")
        except Exception:
            entry["gmsh"] = {"ok": False, "traceback": traceback.format_exc()}
        try:
            entry["ccx"] = _ccx_smoke(directory / "ccx")
        except Exception:
            entry["ccx"] = {"ok": False, "traceback": traceback.format_exc()}
        report[label] = entry
    return report
