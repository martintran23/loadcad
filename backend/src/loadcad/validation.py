"""Closed checks for the one Phase 1 load direction."""

from __future__ import annotations

import numpy as np


def require_phase1_force_direction(direction: tuple[float, float, float]) -> np.ndarray:
    """Accept only a unit load parallel to negative Z.

    Positive pressure on the horizontal top face is the verified bracket load.
    Other directions are rejected until a traction method is tested.
    """
    vector = np.array(direction, dtype=float)
    if vector.shape != (3,) or not np.all(np.isfinite(vector)):
        raise ValueError("force direction must be three finite components")
    length = float(np.linalg.norm(vector))
    if length == 0.0:
        raise ValueError("force direction must be non-zero")
    unit = vector / length
    if float(np.dot(unit, np.array([0.0, 0.0, -1.0]))) < 0.999:
        raise ValueError(
            "Phase 1 only accepts a downward force normal to the horizontal top face"
        )
    return unit
