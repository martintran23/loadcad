"""Candidate von Mises samples. None of these is the decision metric by itself."""

from __future__ import annotations

import math

import numpy as np

from loadcad.geometry.bracket import BracketSpec
from loadcad.postprocess.stress import von_mises


def elements_touching(elements: dict[int, list[int]], node_ids: list[int]) -> set[int]:
    faces = set(node_ids)
    return {
        element_id
        for element_id, connectivity in elements.items()
        if faces.intersection(connectivity)
    }


def _peak(values: dict[int, float]) -> tuple[float, int]:
    if not values:
        raise ValueError("stress sample is empty")
    node_id = max(values, key=values.get)
    return float(values[node_id]), int(node_id)


def nodal_peak(
    nodal_von_mises: dict[int, float],
    elements: dict[int, list[int]],
    excluded_elements: set[int],
) -> tuple[float, int]:
    kept: set[int] = set()
    for element_id, connectivity in elements.items():
        if element_id not in excluded_elements:
            kept.update(connectivity)
    sample = {node_id: nodal_von_mises[node_id] for node_id in kept if node_id in nodal_von_mises}
    return _peak(sample)


def integration_peak(
    integration_stress: dict[int, list[np.ndarray]],
    excluded_elements: set[int],
) -> tuple[float, int, int]:
    best_value = -1.0
    best_element = 0
    best_point = 0
    seen = False
    for element_id, points in integration_stress.items():
        if element_id in excluded_elements:
            continue
        for point_index, components in enumerate(points, start=1):
            value = von_mises(*components)
            seen = True
            if value > best_value:
                best_value = value
                best_element = element_id
                best_point = point_index
    if not seen:
        raise ValueError("integration-point sample is empty")
    return best_value, best_element, best_point


def hole_wall_distance_mm(point: np.ndarray, spec: BracketSpec) -> float | None:
    """Smallest distance from a point to a hole wall, when the point is beside that hole."""
    distances: list[float] = []
    for hole in spec.holes:
        radius = hole.diameter_mm / 2.0
        if hole.leg == "vertical":
            if point[0] < -radius or point[0] > spec.thickness_mm + radius:
                continue
            radial = math.hypot(
                float(point[1]) - hole.center_across_width_mm,
                float(point[2]) - hole.center_along_leg_mm,
            )
        else:
            if point[2] < -radius or point[2] > spec.thickness_mm + radius:
                continue
            radial = math.hypot(
                float(point[0]) - hole.center_along_leg_mm,
                float(point[1]) - hole.center_across_width_mm,
            )
        distances.append(abs(radial - radius))
    if not distances:
        return None
    return float(min(distances))
