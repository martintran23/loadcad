"""Consistent nodal forces for a uniform traction on quadratic tet faces.

On a 6-node triangular face, a uniform traction integrates to zero at the
corner nodes and one third of the face force at each midside node.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class FaceTriangle:
    corners: tuple[int, int, int]
    midsides: tuple[int, int, int]


def triangle_area(p1: np.ndarray, p2: np.ndarray, p3: np.ndarray) -> float:
    return float(0.5 * np.linalg.norm(np.cross(p2 - p1, p3 - p1)))


def quadratic_triangle_area(tri: FaceTriangle, nodes: dict[int, np.ndarray]) -> float:
    """Area of the four flat triangles formed by corners and midside nodes."""
    c0, c1, c2 = (nodes[nid] for nid in tri.corners)
    m01, m12, m20 = (nodes[nid] for nid in tri.midsides)
    return (
        triangle_area(c0, m01, m20)
        + triangle_area(c1, m12, m01)
        + triangle_area(c2, m20, m12)
        + triangle_area(m01, m12, m20)
    )


def consistent_nodal_forces(
    triangles: list[FaceTriangle],
    nodes: dict[int, np.ndarray],
    traction: np.ndarray,
) -> dict[int, np.ndarray]:
    """Return nodal forces whose sum equals traction times the total face area."""
    forces: dict[int, np.ndarray] = {}
    for tri in triangles:
        area = triangle_area(*(nodes[nid] for nid in tri.corners))
        share = np.asarray(traction, dtype=float) * (area / 3.0)
        for nid in tri.midsides:
            forces[nid] = forces.get(nid, np.zeros(3)) + share
    return forces


def total_force(forces: dict[int, np.ndarray]) -> np.ndarray:
    total = np.zeros(3)
    for value in forces.values():
        total = total + value
    return total
