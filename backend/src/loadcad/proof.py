"""Headless Phase 1 proofs: a cantilever benchmark and one filleted bracket.

Neither result includes a safety factor. decision_metric stays null.
"""

from __future__ import annotations

import importlib.metadata
import platform
import traceback
from pathlib import Path

import numpy as np

from loadcad.geometry.beam import BeamSpec, build_beam
from loadcad.geometry.bracket import BracketSpec, Hole, build_bracket
from loadcad.geometry.bracket import export_solid
from loadcad.jobs.store import prepare_job, result_record, sha256_file, write_json
from loadcad.meshing.gmsh_mesh import mesh_step
from loadcad.paths import CCX_DOWNLOAD_URL, CCX_ZIP_SHA256, ccx_executable
from loadcad.postprocess.beam_theory import (
    bending_stress_mpa,
    euler_bernoulli_tip_deflection_mm,
    timoshenko_tip_deflection_mm,
)
from loadcad.postprocess.loads import consistent_nodal_forces, total_force, triangle_area
from loadcad.postprocess.stress import von_mises
from loadcad.solver.deck import write_deck
from loadcad.solver.frd import displacements, parse_frd, reactions, stress_components
from loadcad.solver.runner import SolverFailure, run_ccx
from loadcad.validation import require_phase1_force_direction

PHASE1_BRACKET = BracketSpec(
    length_mm=60.0,
    height_mm=60.0,
    width_mm=30.0,
    thickness_mm=5.0,
    fillet_radius_mm=3.0,
    holes=(
        Hole("vertical", 5.0, 15.0, 40.0),
        Hole("horizontal", 5.0, 15.0, 40.0),
    ),
)
BRACKET_FORCE_N = 100.0
BRACKET_DIRECTION = (0.0, 0.0, -1.0)
BRACKET_ELEMENT_SIZE_MM = 2.5
# Benchmark constants, not an approved material card.
BENCHMARK_E_MPA = 210_000.0
BENCHMARK_NU = 0.3


def _versions() -> dict[str, str]:
    versions = {}
    for package in ("build123d", "gmsh", "meshio", "numpy"):
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = "not-installed"
    versions["python"] = platform.python_version()
    return versions


def _ccx_version(dat_path: Path, stdout: str = "") -> str | None:
    """Prefer the .dat banner. This Windows build prints it only on stdout."""
    texts = []
    if dat_path.is_file():
        texts.append(dat_path.read_text(encoding="utf-8", errors="replace"))
    texts.append(stdout)
    for text in texts:
        for line in text.splitlines():
            if "CalculiX" in line and "Version" in line:
                return line.strip()
    return None


def _geometry_log(paths: dict[str, Path], lines: list[str]) -> None:
    (paths["logs"] / "geometry.log").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _mark_completed(paths: dict[str, Path]) -> None:
    stale = paths["logs"] / "failure.log"
    if stale.is_file():
        stale.unlink()
    write_json(paths["root"] / "status.json", {"status": "completed", "failure_code": None})


def _fail(paths: dict[str, Path], code: str, message: str) -> None:
    write_json(
        paths["root"] / "status.json",
        {"status": "failed", "stage": "failed", "failure_code": code, "message": message},
    )
    (paths["logs"] / "failure.log").write_text(message, encoding="utf-8")


def _sample_bending(
    spec: BeamSpec,
    nodes: dict[int, np.ndarray],
    stress: dict[int, np.ndarray],
) -> dict[str, float | int | None]:
    """Mean axial stress near midspan, away from the root and the tip load."""
    theory = bending_stress_mpa(
        spec.force_n, spec.length_mm / 2.0, spec.width_mm, spec.height_mm
    )
    top: list[float] = []
    bottom: list[float] = []
    for node_id, point in nodes.items():
        if node_id not in stress:
            continue
        if abs(float(point[0]) - spec.length_mm / 2.0) > spec.element_size_mm:
            continue
        if abs(float(point[1])) > spec.element_size_mm:
            continue
        if float(point[2]) >= 0.35 * spec.height_mm:
            top.append(float(stress[node_id][0]))
        elif float(point[2]) <= -0.35 * spec.height_mm:
            bottom.append(float(stress[node_id][0]))
    return {
        "sample_x_mm": spec.length_mm / 2.0,
        "beam_theory_sxx_mpa": theory,
        "mean_top_sxx_mpa": float(np.mean(top)) if top else None,
        "mean_bottom_sxx_mpa": float(np.mean(bottom)) if bottom else None,
        "top_sample_count": len(top),
        "bottom_sample_count": len(bottom),
    }


def _reaction_check(
    reaction_sum: np.ndarray, applied: np.ndarray
) -> dict[str, object]:
    plus = reaction_sum + applied
    minus = reaction_sum - applied
    scale = max(float(np.linalg.norm(applied)), 1.0)
    return {
        "reaction_sum_n": [float(value) for value in reaction_sum],
        "applied_force_n": [float(value) for value in applied],
        "reaction_plus_applied_n": [float(value) for value in plus],
        "reaction_minus_applied_n": [float(value) for value in minus],
        "relative_balance_error": float(min(np.linalg.norm(plus), np.linalg.norm(minus)) / scale),
    }


def run_beam(root: Path, spec: BeamSpec | None = None) -> dict[str, object]:
    spec = spec or BeamSpec()
    paths = prepare_job(root)
    ccx = ccx_executable()
    if ccx is None:
        _fail(paths, "solver_failed", "ccx_static.exe is not available")
        raise SolverFailure("solver_failed", "ccx_static.exe is not available")
    try:
        solid = build_beam(spec)
        step = paths["geometry"] / "beam.step"
        stl = paths["geometry"] / "beam.stl"
        export_solid(solid.shape, str(step), str(stl))
        write_json(
            paths["geometry"] / "face_map.json",
            {role: fp.as_dict() for role, fp in solid.fingerprints.items()},
        )
        _geometry_log(
            paths,
            [
                "model=rectangular_cantilever",
                f"bbox_mm={list(solid.bbox_mm)}",
                f"volume_mm3={solid.volume_mm3}",
                f"step={step.name}",
                f"stl={stl.name}",
            ],
        )
        mesh = mesh_step(
            step,
            solid.fingerprints,
            solid.bbox_mm,
            spec.element_size_mm,
            paths["mesh"] / "beam.msh",
        )
        (paths["logs"] / "gmsh.log").write_text(mesh.log, encoding="utf-8")
        area = sum(
            triangle_area(*(mesh.nodes[nid] for nid in tri.corners))
            for tri in mesh.role_triangles["tip_face"]
        )
        traction = np.array([0.0, 0.0, -spec.force_n / area])
        forces = consistent_nodal_forces(mesh.role_triangles["tip_face"], mesh.nodes, traction)
        applied = total_force(forces)
        if float(np.linalg.norm(applied - np.array([0.0, 0.0, -spec.force_n]))) > 1e-6 * spec.force_n:
            raise RuntimeError(f"assembled tip load {applied} does not equal the requested force")
        deck = paths["solver"] / "job.inp"
        write_deck(
            deck,
            mesh.nodes,
            mesh.elements,
            mesh.role_nodes["fixed_root"],
            cloads=forces,
            youngs_modulus_mpa=spec.youngs_modulus_mpa,
            poissons_ratio=spec.poissons_ratio,
        )
        try:
            solved = run_ccx(ccx, paths["solver"], timeout_s=600)
        except SolverFailure as exc:
            (paths["logs"] / "ccx.log").write_text(str(exc), encoding="utf-8")
            raise
        (paths["logs"] / "ccx.log").write_text(solved.stdout + "\n" + solved.stderr, encoding="utf-8")
        parsed = parse_frd(solved.frd_path)
        disp = displacements(parsed)
        stress = stress_components(parsed)
        reaction = reactions(parsed)
        magnitudes = {node: float(np.linalg.norm(value)) for node, value in disp.items()}
        peak_node = max(magnitudes, key=magnitudes.get)
        mises = {node: von_mises(*stress[node]) for node in stress}
        peak_mises_node = max(mises, key=mises.get)
        tip_target = np.array([spec.length_mm, 0.0, 0.0])
        tip_node = min(
            mesh.role_nodes["tip_face"],
            key=lambda node: float(np.linalg.norm(mesh.nodes[node] - tip_target)),
        )
        tip_uz = float(disp[tip_node][2])
        downward = -tip_uz
        euler = euler_bernoulli_tip_deflection_mm(
            spec.force_n,
            spec.length_mm,
            spec.youngs_modulus_mpa,
            spec.width_mm,
            spec.height_mm,
        )
        timoshenko = timoshenko_tip_deflection_mm(
            spec.force_n,
            spec.length_mm,
            spec.youngs_modulus_mpa,
            spec.poissons_ratio,
            spec.width_mm,
            spec.height_mm,
        )
        reaction_sum = np.zeros(3)
        for node in mesh.role_nodes["fixed_root"]:
            if node in reaction:
                reaction_sum = reaction_sum + reaction[node]
        record = result_record(
            solver_status="completed",
            model="rectangular_cantilever",
            load_model=(
                "uniform tangential traction in -Z on the tip face, "
                "as consistent C3D10 nodal forces"
            ),
            youngs_modulus_mpa=spec.youngs_modulus_mpa,
            poissons_ratio=spec.poissons_ratio,
            length_mm=spec.length_mm,
            width_mm=spec.width_mm,
            height_mm=spec.height_mm,
            force_n=spec.force_n,
            element_size_mm=spec.element_size_mm,
            node_count=len(mesh.nodes),
            element_count=len(mesh.elements),
            min_sicn=mesh.min_quality,
            c3d10_raw_gmsh_order_matches=mesh.raw_order_matches,
            max_displacement_mm=magnitudes[peak_node],
            max_displacement_node=int(peak_node),
            tip_node=int(tip_node),
            tip_uz_mm=tip_uz,
            tip_downward_deflection_mm=downward,
            euler_bernoulli_tip_mm=euler,
            timoshenko_tip_mm=timoshenko,
            error_vs_euler_bernoulli=(downward - euler) / euler,
            error_vs_timoshenko=(downward - timoshenko) / timoshenko,
            max_nodal_von_mises_mpa=mises[peak_mises_node],
            max_nodal_von_mises_node=int(peak_mises_node),
            midspan_bending=_sample_bending(spec, mesh.nodes, stress),
            **_reaction_check(reaction_sum, np.array([0.0, 0.0, -spec.force_n])),
            ccx_version=_ccx_version(solved.dat_path, solved.stdout),
            material_note="Benchmark modulus only. Not an approved material card.",
        )
        write_json(paths["results"] / "results.json", record)
        write_json(
            paths["mesh"] / "metadata.json",
            {
                "gmsh_version": mesh.gmsh_version,
                "element_type": "C3D10",
                "element_order": 2,
                "target_size_mm": spec.element_size_mm,
                "node_count": len(mesh.nodes),
                "element_count": len(mesh.elements),
                "min_quality_sicn": mesh.min_quality,
                "raw_gmsh_order_matches_c3d10": mesh.raw_order_matches,
                "c3d10_node_order": mesh.node_order,
                "matched_tags": mesh.matched_tags,
                "bounding_box_mm": list(mesh.bbox_mm),
            },
        )
        write_json(
            paths["root"] / "provenance.json",
            {
                "versions": _versions(),
                "gmsh_version_api": mesh.gmsh_version,
                "ccx_path": str(ccx),
                "ccx_sha256": sha256_file(ccx),
                "ccx_download_url": CCX_DOWNLOAD_URL,
                "ccx_zip_sha256": CCX_ZIP_SHA256,
                "ccx_version": record["ccx_version"],
                "omp_num_threads": "1",
                "step_sha256": sha256_file(step),
                "inp_sha256": sha256_file(deck),
                "platform": platform.platform(),
            },
        )
        write_json(paths["root"] / "request.json", spec.__dict__)
        _mark_completed(paths)
        return record
    except Exception as exc:
        code = getattr(exc, "code", "solver_failed")
        _fail(paths, str(code), traceback.format_exc())
        raise


def run_bracket(
    root: Path,
    spec: BracketSpec | None = None,
    force_n: float = BRACKET_FORCE_N,
    direction: tuple[float, float, float] = BRACKET_DIRECTION,
    element_size_mm: float = BRACKET_ELEMENT_SIZE_MM,
) -> dict[str, object]:
    spec = spec or PHASE1_BRACKET
    paths = prepare_job(root)
    ccx = ccx_executable()
    if ccx is None:
        _fail(paths, "solver_failed", "ccx_static.exe is not available")
        raise SolverFailure("solver_failed", "ccx_static.exe is not available")
    try:
        require_phase1_force_direction(direction)
        if force_n <= 0.0:
            raise ValueError("force magnitude must be positive")
        solid = build_bracket(spec)
        step = paths["geometry"] / "bracket.step"
        stl = paths["geometry"] / "bracket.stl"
        export_solid(solid.shape, str(step), str(stl))
        write_json(
            paths["geometry"] / "face_map.json",
            {
                "planar": {role: fp.as_dict() for role, fp in solid.fingerprints.items()},
                "cylinders": [fp.as_dict() for fp in solid.cylinders],
                "volume_mm3": solid.volume_mm3,
            },
        )
        _geometry_log(
            paths,
            [
                "model=l_bracket",
                f"bbox_mm={list(solid.bbox_mm)}",
                f"volume_mm3={solid.volume_mm3}",
                f"step={step.name}",
                f"stl={stl.name}",
            ],
        )
        mesh = mesh_step(
            step,
            solid.fingerprints,
            solid.bbox_mm,
            element_size_mm,
            paths["mesh"] / "bracket.msh",
        )
        (paths["logs"] / "gmsh.log").write_text(mesh.log, encoding="utf-8")
        area = sum(
            triangle_area(*(mesh.nodes[nid] for nid in tri.corners))
            for tri in mesh.role_triangles["horizontal_top"]
        )
        pressure = force_n / area
        dloads = [
            (element_id, face, pressure) for element_id, face in mesh.role_dloads["horizontal_top"]
        ]
        deck = paths["solver"] / "job.inp"
        write_deck(
            deck,
            mesh.nodes,
            mesh.elements,
            mesh.role_nodes["mounting_outer"],
            dloads=dloads,
            youngs_modulus_mpa=BENCHMARK_E_MPA,
            poissons_ratio=BENCHMARK_NU,
        )
        try:
            solved = run_ccx(ccx, paths["solver"], timeout_s=900)
        except SolverFailure as exc:
            (paths["logs"] / "ccx.log").write_text(str(exc), encoding="utf-8")
            raise
        (paths["logs"] / "ccx.log").write_text(solved.stdout + "\n" + solved.stderr, encoding="utf-8")
        parsed = parse_frd(solved.frd_path)
        disp = displacements(parsed)
        stress = stress_components(parsed)
        reaction = reactions(parsed)
        magnitudes = {node: float(np.linalg.norm(value)) for node, value in disp.items()}
        peak_node = max(magnitudes, key=magnitudes.get)
        mises = {node: von_mises(*stress[node]) for node in stress}
        peak_mises_node = max(mises, key=mises.get)
        reaction_sum = np.zeros(3)
        for node in mesh.role_nodes["mounting_outer"]:
            if node in reaction:
                reaction_sum = reaction_sum + reaction[node]
        record = result_record(
            solver_status="completed",
            model="l_bracket",
            load_model="positive pressure on horizontal_top, resultant force in -Z",
            restraint="encastre_mounting_face",
            material_id="benchmark_placeholder",
            material_note=(
                "E and nu are benchmark placeholders so the solver can run. "
                "They are not an approved material card and no allowable stress is defined."
            ),
            youngs_modulus_mpa=BENCHMARK_E_MPA,
            poissons_ratio=BENCHMARK_NU,
            allowable_stress_mpa=None,
            force_n=force_n,
            direction=[0.0, 0.0, -1.0],
            pressure_mpa=pressure,
            loaded_area_mm2=area,
            element_size_mm=element_size_mm,
            node_count=len(mesh.nodes),
            element_count=len(mesh.elements),
            min_sicn=mesh.min_quality,
            c3d10_raw_gmsh_order_matches=mesh.raw_order_matches,
            volume_mm3=solid.volume_mm3,
            max_displacement_mm=magnitudes[peak_node],
            max_displacement_node=int(peak_node),
            max_nodal_von_mises_mpa=mises[peak_mises_node],
            max_nodal_von_mises_node=int(peak_mises_node),
            **_reaction_check(reaction_sum, np.array([0.0, 0.0, -force_n])),
            ccx_version=_ccx_version(solved.dat_path, solved.stdout),
        )
        write_json(paths["results"] / "results.json", record)
        write_json(
            paths["mesh"] / "metadata.json",
            {
                "gmsh_version": mesh.gmsh_version,
                "element_type": "C3D10",
                "element_order": 2,
                "target_size_mm": element_size_mm,
                "node_count": len(mesh.nodes),
                "element_count": len(mesh.elements),
                "min_quality_sicn": mesh.min_quality,
                "raw_gmsh_order_matches_c3d10": mesh.raw_order_matches,
                "c3d10_node_order": mesh.node_order,
                "matched_tags": mesh.matched_tags,
                "bounding_box_mm": list(mesh.bbox_mm),
            },
        )
        write_json(
            paths["root"] / "provenance.json",
            {
                "versions": _versions(),
                "gmsh_version_api": mesh.gmsh_version,
                "ccx_path": str(ccx),
                "ccx_sha256": sha256_file(ccx),
                "ccx_download_url": CCX_DOWNLOAD_URL,
                "ccx_zip_sha256": CCX_ZIP_SHA256,
                "ccx_version": record["ccx_version"],
                "omp_num_threads": "1",
                "step_sha256": sha256_file(step),
                "inp_sha256": sha256_file(deck),
                "platform": platform.platform(),
            },
        )
        write_json(
            paths["root"] / "request.json",
            {
                "schema_version": 1,
                "part_family": "l_bracket",
                "geometry": {
                    "length_mm": spec.length_mm,
                    "height_mm": spec.height_mm,
                    "width_mm": spec.width_mm,
                    "thickness_mm": spec.thickness_mm,
                    "fillet_radius_mm": spec.fillet_radius_mm,
                    "holes": [hole.__dict__ for hole in spec.holes],
                },
                "material_id": "benchmark_placeholder",
                "load_case": {
                    "type": "normal_pressure_on_face",
                    "face_role": "horizontal_top",
                    "force_n": force_n,
                    "direction": [0.0, 0.0, -1.0],
                    "gravity": False,
                },
                "boundary_condition": {
                    "type": "encastre_mounting_face",
                    "face_role": "mounting_outer",
                    "dofs": [1, 2, 3],
                },
                "target_safety_factor": None,
            },
        )
        _mark_completed(paths)
        return record
    except Exception as exc:
        code = getattr(exc, "code", "solver_failed")
        _fail(paths, str(code), traceback.format_exc())
        raise
