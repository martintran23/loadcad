import numpy as np
import pytest

from loadcad.jobs.store import result_record
from loadcad.materials.cards import PRUSAMENT_PLA, get_card
from loadcad.postprocess.metrics import integration_peak, nodal_peak
from loadcad.postprocess.safety import safety_fields
from loadcad.solver.dat_stress import parse_integration_stress


def test_aluminum_card_uses_cited_typical_values():
    card = get_card("aluminum_6061_t6")
    card.require_solvable()
    assert card.youngs_modulus_mpa == pytest.approx(68900.0)
    assert card.poissons_ratio == pytest.approx(0.33)
    assert card.allowable_stress_mpa == pytest.approx(276.0)
    assert card.allowable_basis == "tensile_yield"
    assert card.density_tonne_per_mm3 == pytest.approx(2.7e-9)
    assert "not for design" in card.limitations.lower()


def test_printed_cards_have_no_cited_poisson_ratio():
    for material_id in ("prusament_pla", "prusament_petg"):
        card = get_card(material_id)
        assert card.allowable_basis == "specified_allowable"
        assert card.poissons_ratio is None
        with pytest.raises(Exception) as caught:
            card.require_solvable()
        assert caught.value.code == "request_invalid"
    assert PRUSAMENT_PLA.allowable_stress_mpa == pytest.approx(17.0)
    assert get_card("prusament_petg").allowable_stress_mpa == pytest.approx(18.0)


def test_dat_parser_reorders_sxz_and_syz(tmp_path):
    path = tmp_path / "job.dat"
    path.write_text(
        "\n".join(
            [
                " stresses (elem, integ.pnt.,sxx,syy,szz,sxy,sxz,syz) for set EALL and time  1",
                "         4   1  1.0  0.0  0.0  0.0  3.0  2.0",
                "",
            ]
        ),
        encoding="ascii",
    )
    parsed = parse_integration_stress(path)
    assert parsed[4][0] == pytest.approx(np.array([1.0, 0.0, 0.0, 0.0, 2.0, 3.0]))


def test_exclusion_removes_the_loaded_element():
    elements = {1: [1, 2, 3, 4], 2: [5, 6, 7, 8]}
    nodal = {1: 1.0, 2: 9.0, 5: 3.0}
    value, node = nodal_peak(nodal, elements, {1})
    assert (value, node) == (3.0, 5)
    integration = {1: [np.array([10.0, 0, 0, 0, 0, 0])], 2: [np.array([4.0, 0, 0, 0, 0, 0])]}
    peak, element, point = integration_peak(integration, {1})
    assert (peak, element, point) == (4.0, 2, 1)


def test_safety_fields_require_a_metric():
    card = get_card("aluminum_6061_t6")
    fields = safety_fields(
        card,
        "excluded_integration_point_von_mises",
        100.0,
        120.0,
        False,
        "encastre_mounting_face",
        "normal_pressure",
    )
    assert fields["estimated_safety_factor"] == pytest.approx(2.76)
    assert fields["elastic_assumption_exceeded"] is False
    assert fields["mesh_converged"] is False
    record = result_record(**fields)
    assert record["decision_metric"] == "excluded_integration_point_von_mises"
    assert record["estimated_safety_factor"] == pytest.approx(2.76)
