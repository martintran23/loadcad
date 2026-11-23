"""Unit conversions for the millimetre–newton–second system.

CalculiX does not read units. Geometry in this project is millimetres and
stress is megapascals. Density, when stored, is tonne/mm^3 because
1 N = 1 tonne·mm/s^2.
"""

from __future__ import annotations


def gpa_to_mpa(gpa: float) -> float:
    return float(gpa) * 1_000.0


def kg_per_m3_to_tonne_per_mm3(density_kg_per_m3: float) -> float:
    """2700 kg/m^3 becomes 2.7e-9 tonne/mm^3."""
    return float(density_kg_per_m3) * 1e-12
