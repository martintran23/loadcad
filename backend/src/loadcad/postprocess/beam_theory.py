"""Euler-Bernoulli and Timoshenko tip deflection for a rectangular cantilever.

The beam axis is X. The transverse load is in the negative Z direction.
The formulas return the positive downward deflection magnitude.
"""

from __future__ import annotations


def second_moment_of_area(width_mm: float, height_mm: float) -> float:
    """I = b h^3 / 12, about the axis that bends under a Z load."""
    return width_mm * height_mm**3 / 12.0


def shear_modulus(youngs_modulus_mpa: float, poissons_ratio: float) -> float:
    return youngs_modulus_mpa / (2.0 * (1.0 + poissons_ratio))


def euler_bernoulli_tip_deflection_mm(
    force_n: float,
    length_mm: float,
    youngs_modulus_mpa: float,
    width_mm: float,
    height_mm: float,
) -> float:
    inertia = second_moment_of_area(width_mm, height_mm)
    return force_n * length_mm**3 / (3.0 * youngs_modulus_mpa * inertia)


def timoshenko_tip_deflection_mm(
    force_n: float,
    length_mm: float,
    youngs_modulus_mpa: float,
    poissons_ratio: float,
    width_mm: float,
    height_mm: float,
) -> float:
    """Add the rectangular-section shear term (6/5) P L / (A G)."""
    bending = euler_bernoulli_tip_deflection_mm(
        force_n, length_mm, youngs_modulus_mpa, width_mm, height_mm
    )
    area = width_mm * height_mm
    modulus = shear_modulus(youngs_modulus_mpa, poissons_ratio)
    shear = (6.0 / 5.0) * force_n * length_mm / (area * modulus)
    return bending + shear


def bending_stress_mpa(
    force_n: float,
    moment_arm_mm: float,
    width_mm: float,
    height_mm: float,
) -> float:
    """Outer-fiber |sigma_x| = P * arm * (h/2) / I.

    At the root, moment_arm_mm is the full length. Away from the root, pass
    the remaining distance to the tip.
    """
    inertia = second_moment_of_area(width_mm, height_mm)
    return force_n * moment_arm_mm * (height_mm / 2.0) / inertia
