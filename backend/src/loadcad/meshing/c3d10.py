"""C3D10 node order and face numbers.

CalculiX 2.22 *DLOAD numbers tetrahedron faces as:

- P1: corner nodes 1-2-3
- P2: 1-4-2
- P3: 2-4-3
- P4: 3-4-1

Midside nodes follow the corner nodes: 5 on 1-2, 6 on 2-3, 7 on 3-1,
8 on 1-4, 9 on 2-4, 10 on 3-4. A raw Gmsh element is kept only when its
ten coordinates satisfy that pattern and the corner volume is positive.
"""

from __future__ import annotations

import numpy as np

# Corner-index pairs for nodes 5 through 10.
MID_PAIRS = ((0, 1), (1, 2), (2, 0), (0, 3), (1, 3), (2, 3))
# Gmsh 4.15 tet-10 reference node 9 is the midpoint of vertices 3-4, and node 10
# is the midpoint of vertices 2-4. CalculiX C3D10 stores those two midsides
# in the opposite order. Identity is tried as well, in case a later Gmsh build
# changes the reference order.
GMSH_TET10_PERMUTATIONS = {
    "identity": (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
    "swap_last_two": (0, 1, 2, 3, 4, 5, 6, 7, 9, 8),
}
# Face number -> corner indices in the CalculiX convention.
FACE_CORNERS = {
    1: (0, 1, 2),
    2: (0, 3, 1),
    3: (1, 3, 2),
    4: (2, 3, 0),
}

MAX_VOLUME_ELEMENTS = 200_000


class MeshError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def signed_corner_volume(points: np.ndarray) -> float:
    return float(np.dot(np.cross(points[1] - points[0], points[2] - points[0]), points[3] - points[0])) / 6.0


def _midpoint_tolerance(points: np.ndarray) -> float:
    span = float(np.linalg.norm(points.max(axis=0) - points.min(axis=0)))
    return max(1e-6, 1e-8 * span)


def raw_c3d10_order(node_ids: list[int], points: dict[int, np.ndarray]) -> bool:
    if len(node_ids) != 10:
        return False
    coords = np.vstack([points[nid] for nid in node_ids])
    tolerance = _midpoint_tolerance(coords)
    for offset, (first, second) in enumerate(MID_PAIRS):
        expected = 0.5 * (coords[first] + coords[second])
        if float(np.linalg.norm(coords[4 + offset] - expected)) > tolerance:
            return False
    return signed_corner_volume(coords[:4]) > 0.0


def apply_permutation(node_ids: list[int], permutation: tuple[int, ...]) -> list[int]:
    if len(node_ids) != 10:
        raise MeshError("mesh_quality_failed", "expected a 10-node tetrahedron")
    return [node_ids[index] for index in permutation]


def confirmed_permutation(
    elements: list[list[int]], points: dict[int, np.ndarray]
) -> tuple[str, tuple[int, ...]]:
    """Pick the Gmsh-to-C3D10 map that straight elements actually satisfy.

    Curved edges do not put the midside node on the chord midpoint, so only
    straight elements can confirm the map. The same map is then used for the
    curved elements from that Gmsh version.
    """
    for name, permutation in GMSH_TET10_PERMUTATIONS.items():
        for element in elements:
            ordered = apply_permutation(element, permutation)
            if raw_c3d10_order(ordered, points):
                return name, permutation
    raise MeshError(
        "mesh_quality_failed",
        "no straight tetrahedron confirmed the Gmsh 10-node ordering",
    )


def reorder_c3d10(node_ids: list[int], points: dict[int, np.ndarray]) -> tuple[list[int], bool]:
    """Return connectivity in CalculiX order and whether Gmsh already used it."""
    if raw_c3d10_order(node_ids, points):
        return list(node_ids), True
    coords = np.vstack([points[nid] for nid in node_ids])
    tolerance = _midpoint_tolerance(coords)
    mids: dict[int, frozenset[int]] = {}
    for nid in node_ids:
        best_error = tolerance
        best_pair: tuple[int, int] | None = None
        for index, first in enumerate(node_ids):
            if first == nid:
                continue
            for second in node_ids[index + 1 :]:
                if second == nid:
                    continue
                error = float(np.linalg.norm(points[nid] - 0.5 * (points[first] + points[second])))
                if error < best_error:
                    best_error = error
                    best_pair = (first, second)
        if best_pair is not None:
            mids[nid] = frozenset(best_pair)
    corners = [nid for nid in node_ids if nid not in mids]
    if len(corners) != 4 or len(mids) != 6:
        raise MeshError(
            "mesh_quality_failed",
            f"could not identify 4 corners and 6 midsides in element nodes {node_ids}",
        )
    ordered = corners[:]
    corner_points = np.vstack([points[nid] for nid in ordered])
    if signed_corner_volume(corner_points) < 0.0:
        ordered[2], ordered[3] = ordered[3], ordered[2]
    pair_to_mid = {pair: nid for nid, pair in mids.items()}
    for first, second in MID_PAIRS:
        pair = frozenset((ordered[first], ordered[second]))
        if pair not in pair_to_mid:
            raise MeshError("mesh_quality_failed", f"missing midside for corners {tuple(pair)}")
        ordered.append(pair_to_mid[pair])
    if not raw_c3d10_order(ordered, points):
        raise MeshError("mesh_quality_failed", "reordered element still fails the C3D10 midpoint test")
    return ordered, False


def face_number(corner_ids: tuple[int, int, int], element_nodes: list[int]) -> int:
    target = frozenset(corner_ids)
    for number, indices in FACE_CORNERS.items():
        if frozenset(element_nodes[index] for index in indices) == target:
            return number
    raise MeshError("mesh_quality_failed", f"triangle {corner_ids} is not a face of the element")


def enforce_element_cap(element_count: int) -> None:
    if element_count > MAX_VOLUME_ELEMENTS:
        raise MeshError(
            "mesh_quality_failed",
            f"{element_count} volume elements exceeds the local cap of {MAX_VOLUME_ELEMENTS}",
        )
