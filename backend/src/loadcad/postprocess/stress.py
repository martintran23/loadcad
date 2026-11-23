"""Von Mises stress from Cauchy components.

CalculiX writes stress components. It does not write von Mises stress.
Component order for callers is Sxx, Syy, Szz, Sxy, Syz, Szx.
"""

from __future__ import annotations

import math

import numpy as np


def von_mises(
    sxx: float,
    syy: float,
    szz: float,
    sxy: float,
    syz: float,
    szx: float,
) -> float:
    value = 0.5 * (
        (sxx - syy) ** 2 + (syy - szz) ** 2 + (szz - sxx) ** 2
    ) + 3.0 * (sxy**2 + syz**2 + szx**2)
    # Negative values are floating-point noise around a zero tensor.
    return float(math.sqrt(max(value, 0.0)))


def von_mises_array(components: np.ndarray) -> np.ndarray:
    """Compute von Mises for an array of shape (n, 6)."""
    sxx, syy, szz, sxy, syz, szx = (components[:, i] for i in range(6))
    value = 0.5 * (
        (sxx - syy) ** 2 + (syy - szz) ** 2 + (szz - sxx) ** 2
    ) + 3.0 * (sxy**2 + syz**2 + szx**2)
    return np.sqrt(np.maximum(value, 0.0))
