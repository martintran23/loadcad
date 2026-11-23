"""Match Gmsh surfaces to CAD face fingerprints.

A role may own several coplanar fragments when a hole splits a face.
The match fails when the combined area or centroid does not agree, and when
one surface is claimed by two roles.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from loadcad.geometry.faces import FaceFingerprint


class FaceMatchError(Exception):
    def __init__(self, message: str, surfaces: list[dict[str, object]] | None = None) -> None:
        super().__init__(message)
        self.code = "face_match_failed"
        self.surfaces = surfaces or []


@dataclass(frozen=True)
class SurfaceRecord:
    tag: int
    centroid_mm: tuple[float, float, float]
    normal: tuple[float, float, float]
    area_mm2: float

    def as_dict(self) -> dict[str, object]:
        return {
            "tag": self.tag,
            "centroid_mm": list(self.centroid_mm),
            "normal": list(self.normal),
            "area_mm2": self.area_mm2,
        }


def _diagonal(bbox: tuple[float, float, float, float, float, float]) -> float:
    span = np.array(bbox[3:], dtype=float) - np.array(bbox[:3], dtype=float)
    return float(np.linalg.norm(span))


def match_roles(
    fingerprints: dict[str, FaceFingerprint],
    surfaces: list[SurfaceRecord],
    bbox_mm: tuple[float, float, float, float, float, float],
) -> dict[str, list[SurfaceRecord]]:
    tolerance = max(0.05, 0.001 * _diagonal(bbox_mm))
    claimed: dict[int, str] = {}
    matched: dict[str, list[SurfaceRecord]] = {}
    dump = [surface.as_dict() for surface in surfaces]
    for role, fingerprint in fingerprints.items():
        target_normal = np.array(fingerprint.normal, dtype=float)
        target_centroid = np.array(fingerprint.centroid_mm, dtype=float)
        chosen: list[SurfaceRecord] = []
        for surface in surfaces:
            normal = np.array(surface.normal, dtype=float)
            if abs(float(np.dot(normal, target_normal))) < 0.999:
                continue
            centroid = np.array(surface.centroid_mm, dtype=float)
            plane_distance = abs(float(np.dot(centroid - target_centroid, target_normal)))
            if plane_distance > tolerance:
                continue
            chosen.append(surface)
        if not chosen:
            raise FaceMatchError(f"no Gmsh surface matched role {role}", dump)
        area = float(sum(surface.area_mm2 for surface in chosen))
        if fingerprint.area_mm2 <= 0.0 or abs(area - fingerprint.area_mm2) / fingerprint.area_mm2 > 0.01:
            raise FaceMatchError(
                f"role {role} area {area:.6g} mm^2 disagrees with CAD {fingerprint.area_mm2:.6g} mm^2",
                dump,
            )
        weighted = sum(
            np.array(surface.centroid_mm) * surface.area_mm2 for surface in chosen
        ) / area
        if float(np.linalg.norm(weighted - target_centroid)) > tolerance:
            raise FaceMatchError(f"role {role} centroid does not match the CAD fingerprint", dump)
        for surface in chosen:
            previous = claimed.get(surface.tag)
            if previous is not None:
                raise FaceMatchError(
                    f"Gmsh surface {surface.tag} matched both {previous} and {role}",
                    dump,
                )
            claimed[surface.tag] = role
        matched[role] = chosen
    return matched
