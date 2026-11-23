"""Semantic face fingerprints taken from the finished solid.

build123d labels do not survive a later faces() query or a STEP face entity.
The fingerprint is the identity that Gmsh matching has to recover.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class FaceFingerprint:
    role: str
    centroid_mm: tuple[float, float, float]
    normal: tuple[float, float, float]
    area_mm2: float

    def as_dict(self) -> dict[str, object]:
        return {
            "role": self.role,
            "centroid_mm": list(self.centroid_mm),
            "normal": list(self.normal),
            "area_mm2": self.area_mm2,
        }


def _xyz(value: object) -> np.ndarray:
    return np.array([float(value.X), float(value.Y), float(value.Z)], dtype=float)  # type: ignore[attr-defined]


def _geom_name(shape: object) -> str:
    geom = shape.geom_type  # type: ignore[attr-defined]
    return str(getattr(geom, "name", geom)).upper()


def _normal(face: object) -> np.ndarray:
    try:
        raw = face.normal_at()  # type: ignore[attr-defined]
    except TypeError:
        raw = face.normal_at(face.center())  # type: ignore[attr-defined]
    vector = _xyz(raw)
    length = float(np.linalg.norm(vector))
    if length == 0.0:
        raise ValueError("face normal has zero length")
    return vector / length


def _group(role: str, faces: list[object]) -> FaceFingerprint:
    if not faces:
        raise ValueError(f"no faces for role {role}")
    areas = np.array([float(face.area) for face in faces], dtype=float)  # type: ignore[attr-defined]
    centroids = np.vstack([_xyz(face.center()) for face in faces])  # type: ignore[attr-defined]
    normals = np.vstack([_normal(face) for face in faces])
    area = float(areas.sum())
    centroid = (areas[:, None] * centroids).sum(axis=0) / area
    normal = normals.mean(axis=0)
    normal = normal / np.linalg.norm(normal)
    return FaceFingerprint(
        role=role,
        centroid_mm=(float(centroid[0]), float(centroid[1]), float(centroid[2])),
        normal=(float(normal[0]), float(normal[1]), float(normal[2])),
        area_mm2=area,
    )


def planar_role(
    part: object,
    role: str,
    normal: tuple[float, float, float],
    plane_offset_mm: float,
    offset_axis: int,
) -> FaceFingerprint:
    """Group planar faces whose normal and plane location match a role."""
    target = np.array(normal, dtype=float)
    chosen: list[object] = []
    for face in part.faces():  # type: ignore[attr-defined]
        if "PLANE" not in _geom_name(face):
            continue
        face_normal = _normal(face)
        if float(np.dot(face_normal, target)) < 0.999:
            continue
        center = _xyz(face.center())
        if abs(float(center[offset_axis]) - plane_offset_mm) > 1e-3:
            continue
        chosen.append(face)
    return _group(role, chosen)


def cylinder_fingerprints(part: object) -> list[FaceFingerprint]:
    """One fingerprint per cylindrical face, named hole_cylinder_N."""
    found: list[FaceFingerprint] = []
    index = 0
    for face in part.faces():  # type: ignore[attr-defined]
        if "CYLINDER" not in _geom_name(face):
            continue
        center = _xyz(face.center())
        # A cylinder has no single outward plane normal. Store the face
        # center and a zero normal so the record stays explicit.
        found.append(
            FaceFingerprint(
                role=f"hole_cylinder_{index}",
                centroid_mm=(float(center[0]), float(center[1]), float(center[2])),
                normal=(0.0, 0.0, 0.0),
                area_mm2=float(face.area),  # type: ignore[attr-defined]
            )
        )
        index += 1
    return found
