"""Read C3D10 integration-point stresses from a CalculiX .dat file.

The .dat header for this 2.22 build lists components as
sxx, syy, szz, sxy, sxz, syz. The von Mises function expects
sxx, syy, szz, sxy, syz, szx, so sxz and syz are swapped here.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np


def parse_integration_stress(path: Path) -> dict[int, list[np.ndarray]]:
    stresses: dict[int, list[np.ndarray]] = {}
    reading = False
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        lower = raw.lower()
        if "integ.pnt" in lower and "sxx" in lower:
            reading = True
            continue
        if not reading:
            continue
        parts = raw.split()
        if len(parts) < 8:
            if parts:
                reading = False
            continue
        try:
            element_id = int(parts[0])
            values = [float(part) for part in parts[2:8]]
        except ValueError:
            reading = False
            continue
        sxx, syy, szz, sxy, sxz, syz = values
        stresses.setdefault(element_id, []).append(
            np.array([sxx, syy, szz, sxy, syz, sxz], dtype=float)
        )
    if not stresses:
        raise ValueError(f"no integration-point stress block in {path}")
    return stresses
