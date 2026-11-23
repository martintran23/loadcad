"""Parametric L-bracket.

Coordinates, millimetres, right-handed:

- Origin at the outer corner.
- +X along the horizontal leg, +Y across the width, +Z up the vertical leg.
- Both legs share one thickness.
- A simulation solid has a positive inside fillet.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from loadcad.geometry.errors import GeometryError
from loadcad.geometry.faces import FaceFingerprint, cylinder_fingerprints, planar_role

MAX_HOLES = 8


@dataclass(frozen=True)
class Hole:
    leg: str
    diameter_mm: float
    center_across_width_mm: float
    center_along_leg_mm: float


@dataclass(frozen=True)
class BracketSpec:
    length_mm: float
    height_mm: float
    width_mm: float
    thickness_mm: float
    fillet_radius_mm: float
    holes: tuple[Hole, ...] = ()


@dataclass
class BracketSolid:
    shape: object
    fingerprints: dict[str, FaceFingerprint]
    cylinders: list[FaceFingerprint]
    volume_mm3: float
    bbox_mm: tuple[float, float, float, float, float, float]


def _positive(name: str, value: float) -> None:
    if not math.isfinite(value) or value <= 0.0:
        raise GeometryError("request_invalid", f"{name} must be finite and positive")


def _hole_bounds(spec: BracketSpec, hole: Hole) -> None:
    if hole.leg not in {"vertical", "horizontal"}:
        raise GeometryError("request_invalid", f"unsupported hole leg {hole.leg!r}")
    _positive("hole diameter", hole.diameter_mm)
    radius = hole.diameter_mm / 2.0
    edge = 1.5 * hole.diameter_mm
    fillet_clearance = spec.thickness_mm + spec.fillet_radius_mm + radius
    y = hole.center_across_width_mm
    if y < edge or y > spec.width_mm - edge:
        raise GeometryError(
            "request_invalid",
            "hole wall must stay at least one diameter from the side edges",
        )
    along = hole.center_along_leg_mm
    if hole.leg == "horizontal":
        if along < fillet_clearance or along > spec.length_mm - edge:
            raise GeometryError(
                "request_invalid",
                "horizontal hole intersects the fillet or a free edge",
            )
    else:
        if along < fillet_clearance or along > spec.height_mm - edge:
            raise GeometryError(
                "request_invalid",
                "vertical hole intersects the fillet or the top edge",
            )


def _cylinders_overlap(spec: BracketSpec, first: Hole, second: Hole) -> bool:
    """Reject holes whose finite cylinders come within one diameter of wall."""
    required = first.diameter_mm / 2.0 + second.diameter_mm / 2.0 + max(
        first.diameter_mm, second.diameter_mm
    )
    if first.leg == second.leg:
        gap = math.hypot(
            first.center_across_width_mm - second.center_across_width_mm,
            first.center_along_leg_mm - second.center_along_leg_mm,
        )
        return gap < required
    vertical = first if first.leg == "vertical" else second
    horizontal = second if vertical is first else first
    # Axes are perpendicular. Compare the point on each finite axis.
    # Vertical axis spans x in [0, thickness] at (y, z).
    # Horizontal axis spans z in [0, thickness] at (x, y).
    y_gap = abs(vertical.center_across_width_mm - horizontal.center_across_width_mm)
    x_gap = _axis_gap(0.0, spec.thickness_mm, horizontal.center_along_leg_mm)
    z_gap = _axis_gap(0.0, spec.thickness_mm, vertical.center_along_leg_mm)
    return math.sqrt(x_gap**2 + y_gap**2 + z_gap**2) < required


def _axis_gap(start: float, end: float, value: float) -> float:
    if value < start:
        return start - value
    if value > end:
        return value - end
    return 0.0


def validate_bracket(spec: BracketSpec) -> None:
    _positive("length", spec.length_mm)
    _positive("height", spec.height_mm)
    _positive("width", spec.width_mm)
    _positive("thickness", spec.thickness_mm)
    if spec.fillet_radius_mm <= 0.0 or not math.isfinite(spec.fillet_radius_mm):
        raise GeometryError(
            "request_invalid",
            "simulation requires a positive inside fillet radius",
        )
    if spec.thickness_mm >= spec.length_mm or spec.thickness_mm >= spec.height_mm:
        raise GeometryError("request_invalid", "thickness must be smaller than both legs")
    if spec.fillet_radius_mm >= spec.length_mm - spec.thickness_mm:
        raise GeometryError("request_invalid", "fillet does not fit on the horizontal leg")
    if spec.fillet_radius_mm >= spec.height_mm - spec.thickness_mm:
        raise GeometryError("request_invalid", "fillet does not fit on the vertical leg")
    if len(spec.holes) > MAX_HOLES:
        raise GeometryError("request_invalid", f"at most {MAX_HOLES} holes")
    for hole in spec.holes:
        _hole_bounds(spec, hole)
    for index, first in enumerate(spec.holes):
        for second in spec.holes[index + 1 :]:
            if _cylinders_overlap(spec, first, second):
                raise GeometryError("request_invalid", "holes intersect or leave too little wall")


def _bbox(shape: object) -> tuple[float, float, float, float, float, float]:
    box = shape.bounding_box()  # type: ignore[attr-defined]
    return (
        float(box.min.X),
        float(box.min.Y),
        float(box.min.Z),
        float(box.max.X),
        float(box.max.Y),
        float(box.max.Z),
    )


def _placed_box(x0: float, y0: float, z0: float, sx: float, sy: float, sz: float) -> object:
    from build123d import Box, Pos

    return Pos(x0 + sx / 2.0, y0 + sy / 2.0, z0 + sz / 2.0) * Box(sx, sy, sz)


def _reentrant_edges(shape: object, thickness: float) -> list[object]:
    edges = []
    for edge in shape.edges():  # type: ignore[attr-defined]
        center = edge.center()
        if abs(float(center.X) - thickness) > 1e-5:
            continue
        if abs(float(center.Z) - thickness) > 1e-5:
            continue
        tangent = edge.tangent_at(0.5)
        if abs(float(tangent.X)) > 1e-3 or abs(abs(float(tangent.Y)) - 1.0) > 1e-3:
            continue
        edges.append(edge)
    return edges


def _cut_hole(shape: object, spec: BracketSpec, hole: Hole) -> object:
    from build123d import Cylinder, Pos, Rot

    radius = hole.diameter_mm / 2.0
    extra = 2.0
    if hole.leg == "vertical":
        tool = Pos(spec.thickness_mm / 2.0, hole.center_across_width_mm, hole.center_along_leg_mm)
        tool = tool * Rot(0, 90, 0) * Cylinder(radius, spec.thickness_mm + extra)
    else:
        tool = Pos(
            hole.center_along_leg_mm,
            hole.center_across_width_mm,
            spec.thickness_mm / 2.0,
        ) * Cylinder(radius, spec.thickness_mm + extra)
    return shape - tool


def build_bracket(spec: BracketSpec) -> BracketSolid:
    from build123d import fillet

    validate_bracket(spec)
    vertical = _placed_box(0.0, 0.0, 0.0, spec.thickness_mm, spec.width_mm, spec.height_mm)
    horizontal = _placed_box(0.0, 0.0, 0.0, spec.length_mm, spec.width_mm, spec.thickness_mm)
    shape = vertical + horizontal
    edges = _reentrant_edges(shape, spec.thickness_mm)
    if len(edges) != 1:
        raise GeometryError(
            "geometry_failed",
            f"expected one inside corner edge, found {len(edges)}",
        )
    shape = fillet(edges, radius=spec.fillet_radius_mm)
    for hole in spec.holes:
        shape = _cut_hole(shape, spec, hole)
    solids = list(shape.solids())
    if len(solids) != 1:
        raise GeometryError("geometry_failed", f"expected one solid, found {len(solids)}")
    bbox = _bbox(shape)
    expected = (0.0, 0.0, 0.0, spec.length_mm, spec.width_mm, spec.height_mm)
    for actual, target in zip(bbox, expected, strict=True):
        if abs(actual - target) > 1e-4:
            raise GeometryError(
                "geometry_failed",
                f"bounding box {bbox} does not match the requested envelope {expected}",
            )
    fingerprints = {
        "mounting_outer": planar_role(shape, "mounting_outer", (-1.0, 0.0, 0.0), 0.0, 0),
        "horizontal_top": planar_role(
            shape, "horizontal_top", (0.0, 0.0, 1.0), spec.thickness_mm, 2
        ),
    }
    return BracketSolid(
        shape=shape,
        fingerprints=fingerprints,
        cylinders=cylinder_fingerprints(shape),
        volume_mm3=float(shape.volume),
        bbox_mm=bbox,
    )


def export_solid(shape: object, step_path: str, stl_path: str) -> None:
    from pathlib import Path

    from build123d import Unit, export_step, export_stl

    export_step(shape, step_path, unit=Unit.MM)
    export_stl(shape, stl_path)
    if not Path(step_path).is_file() or not Path(stl_path).is_file():
        raise GeometryError("geometry_failed", "CAD export did not write both STEP and STL")
