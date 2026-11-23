import math

import numpy as np
import pytest

from loadcad.postprocess.beam_theory import (
    bending_stress_mpa,
    euler_bernoulli_tip_deflection_mm,
    second_moment_of_area,
    timoshenko_tip_deflection_mm,
)
from loadcad.postprocess.loads import FaceTriangle, consistent_nodal_forces, total_force, triangle_area
from loadcad.postprocess.stress import von_mises
from loadcad.units import gpa_to_mpa, kg_per_m3_to_tonne_per_mm3
from loadcad.validation import require_phase1_force_direction


def test_density_and_modulus_conversions():
    assert gpa_to_mpa(210.0) == 210_000.0
    assert kg_per_m3_to_tonne_per_mm3(2700.0) == pytest.approx(2.7e-9)


def test_beam_formulas_match_hand_calculation():
    inertia = second_moment_of_area(10.0, 10.0)
    assert inertia == pytest.approx(10.0 * 1000.0 / 12.0)
    tip = euler_bernoulli_tip_deflection_mm(100.0, 200.0, 210_000.0, 10.0, 10.0)
    assert tip == pytest.approx(100.0 * 200.0**3 / (3.0 * 210_000.0 * inertia))
    shear = timoshenko_tip_deflection_mm(100.0, 200.0, 210_000.0, 0.3, 10.0, 10.0)
    assert shear > tip
    stress = bending_stress_mpa(100.0, 200.0, 10.0, 10.0)
    assert stress == pytest.approx(100.0 * 200.0 * 5.0 / inertia)


def test_von_mises_uniaxial_and_zero():
    assert von_mises(12.0, 0, 0, 0, 0, 0) == pytest.approx(12.0)
    assert von_mises(-7.5, 0, 0, 0, 0, 0) == pytest.approx(7.5)
    assert von_mises(0, 0, 0, 0, 0, 0) == pytest.approx(0.0)


def test_consistent_traction_sums_to_the_face_force():
    nodes = {
        1: np.array([0.0, 0.0, 0.0]),
        2: np.array([2.0, 0.0, 0.0]),
        3: np.array([0.0, 2.0, 0.0]),
        4: np.array([1.0, 0.0, 0.0]),
        5: np.array([1.0, 1.0, 0.0]),
        6: np.array([0.0, 1.0, 0.0]),
    }
    tri = FaceTriangle(corners=(1, 2, 3), midsides=(4, 5, 6))
    area = triangle_area(nodes[1], nodes[2], nodes[3])
    traction = np.array([0.0, 0.0, -10.0 / area])
    forces = consistent_nodal_forces([tri], nodes, traction)
    assert forces[1].shape == (3,) if 1 in forces else True
    assert 1 not in forces
    summed = total_force(forces)
    assert summed == pytest.approx(np.array([0.0, 0.0, -10.0]))


def test_phase1_direction_rejects_a_skew_force():
    assert require_phase1_force_direction((0.0, 0.0, -2.0))[2] == pytest.approx(-1.0)
    with pytest.raises(ValueError):
        require_phase1_force_direction((1.0, 0.0, -1.0))


def test_math_is_available_for_beam_ratio():
    assert math.isfinite(timoshenko_tip_deflection_mm(1, 100, 1000, 0.3, 10, 10))
