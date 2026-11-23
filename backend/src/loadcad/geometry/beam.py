"""Rectangular cantilever used as the analytical benchmark.

The section is centered on Y = 0 and Z = 0. X runs from the fixed root at 0
to the tip at length_mm. This is a benchmark solid, not the L-bracket.
"""

from __future__ import annotations

from dataclasses import dataclass

from loadcad.geometry.errors import GeometryError
from loadcad.geometry.faces import FaceFingerprint, planar_role


@dataclass(frozen=True)
class BeamSpec:
    length_mm: float = 200.0
    width_mm: float = 10.0
    height_mm: float = 10.0
    youngs_modulus_mpa: float = 210_000.0
    poissons_ratio: float = 0.3
    force_n: float = 100.0
    element_size_mm: float = 5.0


@dataclass
class BeamSolid:
    shape: object
    fingerprints: dict[str, FaceFingerprint]
    volume_mm3: float
    bbox_mm: tuple[float, float, float, float, float, float]
    spec: BeamSpec


def build_beam(spec: BeamSpec) -> BeamSolid:
    from build123d import Box, Pos

    shape = Pos(spec.length_mm / 2.0, 0.0, 0.0) * Box(
        spec.length_mm, spec.width_mm, spec.height_mm
    )
    solids = list(shape.solids())
    if len(solids) != 1:
        raise GeometryError("geometry_failed", f"expected one beam solid, found {len(solids)}")
    box = shape.bounding_box()
    bbox = (
        float(box.min.X),
        float(box.min.Y),
        float(box.min.Z),
        float(box.max.X),
        float(box.max.Y),
        float(box.max.Z),
    )
    fingerprints = {
        "fixed_root": planar_role(shape, "fixed_root", (-1.0, 0.0, 0.0), 0.0, 0),
        "tip_face": planar_role(shape, "tip_face", (1.0, 0.0, 0.0), spec.length_mm, 0),
    }
    return BeamSolid(
        shape=shape,
        fingerprints=fingerprints,
        volume_mm3=float(shape.volume),
        bbox_mm=bbox,
        spec=spec,
    )
