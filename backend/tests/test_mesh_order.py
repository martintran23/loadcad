import numpy as np
import pytest

from loadcad.geometry.faces import FaceFingerprint
from loadcad.meshing.c3d10 import (
    enforce_element_cap,
    face_number,
    raw_c3d10_order,
    reorder_c3d10,
)
from loadcad.meshing.c3d10 import MeshError
from loadcad.meshing.match import FaceMatchError, SurfaceRecord, match_roles


def _points():
    corners = {
        1: np.array([0.0, 0.0, 0.0]),
        2: np.array([1.0, 0.0, 0.0]),
        3: np.array([0.0, 1.0, 0.0]),
        4: np.array([0.0, 0.0, 1.0]),
    }
    pairs = ((1, 2), (2, 3), (3, 1), (1, 4), (2, 4), (3, 4))
    points = dict(corners)
    ordered = [1, 2, 3, 4]
    for first, second in pairs:
        nid = len(points) + 1
        points[nid] = 0.5 * (corners[first] + corners[second])
        ordered.append(nid)
    return points, ordered


def test_raw_c3d10_order_accepts_the_calculix_pattern():
    points, ordered = _points()
    assert raw_c3d10_order(ordered, points)
    swapped = ordered[:]
    swapped[4], swapped[5] = swapped[5], swapped[4]
    assert not raw_c3d10_order(swapped, points)
    repaired, matched = reorder_c3d10(swapped, points)
    assert matched is False
    assert raw_c3d10_order(repaired, points)


def test_face_numbers_follow_the_manual():
    _points_map, ordered = _points()
    assert face_number((ordered[0], ordered[1], ordered[2]), ordered) == 1
    assert face_number((ordered[0], ordered[3], ordered[1]), ordered) == 2
    assert face_number((ordered[1], ordered[3], ordered[2]), ordered) == 3
    assert face_number((ordered[2], ordered[3], ordered[0]), ordered) == 4


def test_element_cap_refuses_a_huge_mesh_before_the_solver():
    enforce_element_cap(10)
    with pytest.raises(MeshError) as caught:
        enforce_element_cap(200_001)
    assert caught.value.code == "mesh_quality_failed"


def test_split_faces_match_and_a_bad_fingerprint_fails():
    fingerprint = FaceFingerprint("mounting_outer", (0.0, 5.0, 5.0), (-1.0, 0.0, 0.0), 100.0)
    surfaces = [
        SurfaceRecord(1, (0.0, 2.0, 5.0), (-1.0, 0.0, 0.0), 40.0),
        SurfaceRecord(2, (0.0, 7.0, 5.0), (-1.0, 0.0, 0.0), 60.0),
    ]
    matched = match_roles({"mounting_outer": fingerprint}, surfaces, (0, 0, 0, 60, 30, 60))
    assert [item.tag for item in matched["mounting_outer"]] == [1, 2]
    bad = FaceFingerprint("mounting_outer", (20.0, 0.0, 0.0), (-1.0, 0.0, 0.0), 100.0)
    with pytest.raises(FaceMatchError) as caught:
        match_roles({"mounting_outer": bad}, surfaces, (0, 0, 0, 60, 30, 60))
    assert caught.value.code == "face_match_failed"


def test_one_surface_cannot_fill_two_roles():
    fingerprint = FaceFingerprint("a", (0.0, 0.0, 0.0), (-1.0, 0.0, 0.0), 10.0)
    other = FaceFingerprint("b", (0.0, 0.0, 0.0), (-1.0, 0.0, 0.0), 10.0)
    surface = SurfaceRecord(7, (0.0, 0.0, 0.0), (-1.0, 0.0, 0.0), 10.0)
    with pytest.raises(FaceMatchError):
        match_roles({"a": fingerprint, "b": other}, [surface], (0, 0, 0, 10, 10, 10))
