import math
from pathlib import Path

import pytest

from loadcad.geometry.bracket import BracketSpec, Hole, build_bracket, export_solid
from loadcad.geometry.errors import GeometryError
from loadcad.proof import PHASE1_BRACKET


def _plain() -> BracketSpec:
    return BracketSpec(60, 60, 30, 5, 3)


def test_bracket_envelope_fillet_and_step_units(tmp_path: Path):
    solid = build_bracket(PHASE1_BRACKET)
    assert solid.bbox_mm == pytest.approx((0, 0, 0, 60, 30, 60))
    assert solid.volume_mm3 > 0
    assert "mounting_outer" in solid.fingerprints
    assert "horizontal_top" in solid.fingerprints
    assert len(solid.cylinders) >= 2
    step = tmp_path / "bracket.step"
    stl = tmp_path / "bracket.stl"
    export_solid(solid.shape, str(step), str(stl))
    text = step.read_text(encoding="utf-8", errors="ignore")
    assert "MILLI" in text and "METRE" in text
    assert stl.stat().st_size > 0


def test_hole_removes_about_two_cylinder_volumes():
    before = build_bracket(_plain()).volume_mm3
    after = build_bracket(PHASE1_BRACKET).volume_mm3
    expected = 2.0 * math.pi * (2.5**2) * 5.0
    assert (before - after) == pytest.approx(expected, rel=0.05)


def test_zero_fillet_and_intersecting_holes_are_rejected():
    with pytest.raises(GeometryError) as caught:
        build_bracket(BracketSpec(60, 60, 30, 5, 0))
    assert caught.value.code == "request_invalid"
    overlap = BracketSpec(
        60,
        60,
        30,
        5,
        3,
        holes=(
            Hole("horizontal", 5, 15, 40),
            Hole("horizontal", 5, 16, 41),
        ),
    )
    with pytest.raises(GeometryError) as caught:
        build_bracket(overlap)
    assert "intersect" in str(caught.value)
