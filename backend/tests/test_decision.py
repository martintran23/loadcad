import json
from pathlib import Path

from loadcad.materials.cards import get_card
from loadcad.postprocess.decision import STRESS_RELATIVE_BAND, mesh_converged
from loadcad.study import beam_summary, bracket_summary

STUDIES = Path(__file__).resolve().parents[1] / "studies"
REQUIRED = (
    "allowable_stress_mpa",
    "allowable_basis",
    "decision_metric",
    "decision_von_mises_mpa",
    "max_nodal_von_mises_mpa",
    "estimated_safety_factor",
    "elastic_assumption_exceeded",
    "mesh_converged",
    "restraint",
    "load_model",
    "disclaimer",
)


def _load(name: str) -> dict:
    return json.loads((STUDIES / name).read_text(encoding="utf-8"))


def test_stored_bracket_study_matches_the_safety_record():
    card = get_card("aluminum_6061_t6")
    stored = _load("phase2_bracket.json")
    built = bracket_summary(stored["rows"], card)
    safety = stored["safety"]
    assert safety == built["safety"]
    assert stored["last_step_relative_change"] == built["last_step_relative_change"]
    for key in REQUIRED:
        assert key in safety
    assert safety["decision_metric"] == "max_nodal_von_mises"
    assert safety["allowable_basis"] == "tensile_yield"
    assert safety["allowable_stress_mpa"] == 276.0
    assert safety["decision_von_mises_mpa"] == safety["max_nodal_von_mises_mpa"]
    assert safety["estimated_safety_factor"] == 276.0 / safety["decision_von_mises_mpa"]
    assert safety["elastic_assumption_exceeded"] is False
    assert safety["mesh_converged"] is False
    assert safety["restraint"] == "encastre_mounting_face"
    assert safety["load_model"] == "normal_pressure"
    assert "not a certified" in safety["disclaimer"].lower()
    assert STRESS_RELATIVE_BAND is None
    assert mesh_converged(0.0) is False
    assert stored["last_step_relative_change"]["max_nodal_von_mises_mpa"] > 0.05


def test_beam_study_has_no_safety_factor():
    stored = _load("phase2_beam.json")
    assert stored == beam_summary(stored["rows"])
    assert stored["decision_metric"] is None
    assert stored["estimated_safety_factor"] is None
    finest = min(stored["rows"], key=lambda row: row["element_size_mm"])
    assert abs(finest["error_vs_timoshenko"]) < 0.05


def test_near_hole_peak_stays_on_the_hole_wall():
    stored = _load("phase2_near_hole.json")
    rows = {row["element_size_mm"]: row for row in stored["rows"]}
    finest = rows[1.25]
    coarse = rows[2.5]
    assert finest["peak_node_hole_wall_distance_mm"] < 1e-9
    assert finest["max_nodal_von_mises_mpa"] == finest["excluded_nodal_von_mises_mpa"]
    assert finest["max_integration_point_von_mises_mpa"] == finest["excluded_integration_point_von_mises_mpa"]
    assert coarse["max_nodal_von_mises_mpa"] > coarse["excluded_nodal_von_mises_mpa"]
    assert coarse["peak_node_hole_wall_distance_mm"] < 1e-9
