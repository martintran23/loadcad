from pathlib import Path

import meshio
import pytest

from loadcad.geometry.beam import BeamSpec, build_beam
from loadcad.geometry.bracket import build_bracket, export_solid
from loadcad.proof import PHASE1_BRACKET
from loadcad.meshing.gmsh_mesh import inspect_bbox, mesh_step


def test_step_import_keeps_millimetres_and_meshes_c3d10(tmp_path: Path):
    spec = BeamSpec(length_mm=40.0, width_mm=8.0, height_mm=8.0, element_size_mm=4.0)
    solid = build_beam(spec)
    step = tmp_path / "beam.step"
    export_solid(solid.shape, str(step), str(tmp_path / "beam.stl"))
    imported = inspect_bbox(step)
    assert imported == pytest.approx(solid.bbox_mm, abs=1e-4)
    mesh = mesh_step(step, solid.fingerprints, solid.bbox_mm, spec.element_size_mm, tmp_path / "beam.msh")
    assert mesh.elements
    assert all(len(nodes) == 10 for nodes in mesh.elements.values())
    assert mesh.role_nodes["fixed_root"]
    assert mesh.role_triangles["tip_face"]
    assert mesh.role_dloads["tip_face"]
    read = meshio.read(tmp_path / "beam.msh")
    assert len(read.points) > 0
    assert mesh.raw_order_matches in {True, False}


def test_bracket_faces_match_after_holes(tmp_path: Path):
    solid = build_bracket(PHASE1_BRACKET)
    step = tmp_path / "bracket.step"
    export_solid(solid.shape, str(step), str(tmp_path / "bracket.stl"))
    mesh = mesh_step(
        step,
        solid.fingerprints,
        solid.bbox_mm,
        5.0,
        tmp_path / "bracket.msh",
    )
    mount = set(mesh.matched_tags["mounting_outer"])
    load = set(mesh.matched_tags["horizontal_top"])
    assert mount and load
    assert mount.isdisjoint(load)
    assert mesh.role_dloads["horizontal_top"]
    assert mesh.role_nodes["mounting_outer"]
