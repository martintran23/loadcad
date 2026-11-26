"""Mesh-refinement runs. The bracket summary names the decision metric and leaves mesh_converged false."""

from __future__ import annotations

import json
from pathlib import Path

from loadcad.geometry.beam import BeamSpec
from loadcad.materials.cards import MaterialCard, get_card
from loadcad.postprocess.decision import bracket_safety_record, last_step_relative_change
from loadcad.proof import PHASE1_BRACKET, run_beam, run_bracket

BEAM_SIZES_MM = (5.0, 2.5, 1.25)
BRACKET_SIZES_MM = (5.0, 2.5, 1.25)

BEAM_KEYS = (
    "element_size_mm",
    "node_count",
    "element_count",
    "tip_downward_deflection_mm",
    "euler_bernoulli_tip_mm",
    "timoshenko_tip_mm",
    "error_vs_euler_bernoulli",
    "error_vs_timoshenko",
    "max_nodal_von_mises_mpa",
    "max_integration_point_von_mises_mpa",
    "excluded_nodal_von_mises_mpa",
    "excluded_integration_point_von_mises_mpa",
    "relative_balance_error",
    "min_sicn",
)

BRACKET_KEYS = BEAM_KEYS + (
    "youngs_modulus_mpa",
    "poissons_ratio",
    "material_id",
    "pressure_mpa",
    "loaded_area_mm2",
    "corner_triangle_area_mm2",
    "max_displacement_mm",
    "peak_node_hole_wall_distance_mm",
    "excluded_peak_hole_wall_distance_mm",
    "excluded_element_count",
    "reaction_sum_n",
)


def _row(record: dict[str, object], keys: tuple[str, ...]) -> dict[str, object]:
    return {key: record[key] for key in keys if key in record}


def _changes(rows: list[dict[str, object]], keys: tuple[str, ...]) -> dict[str, float]:
    return {key: last_step_relative_change(rows, key) for key in keys if key in rows[-1]}


def beam_summary(rows: list[dict[str, object]]) -> dict[str, object]:
    return {
        "model": "rectangular_cantilever",
        "material_id": "benchmark_placeholder",
        "decision_metric": None,
        "estimated_safety_factor": None,
        "rows": rows,
        "last_step_relative_change": _changes(
            rows,
            (
                "tip_downward_deflection_mm",
                "max_nodal_von_mises_mpa",
                "max_integration_point_von_mises_mpa",
                "excluded_nodal_von_mises_mpa",
                "excluded_integration_point_von_mises_mpa",
            ),
        ),
    }


def bracket_summary(rows: list[dict[str, object]], card: MaterialCard) -> dict[str, object]:
    return {
        "model": "l_bracket",
        "material_id": card.material_id,
        "material_version": card.version,
        "rows": rows,
        "last_step_relative_change": _changes(
            rows,
            (
                "max_displacement_mm",
                "max_nodal_von_mises_mpa",
                "max_integration_point_von_mises_mpa",
                "excluded_nodal_von_mises_mpa",
                "excluded_integration_point_von_mises_mpa",
            ),
        ),
        "safety": bracket_safety_record(rows, card),
    }


def run_beam_refinement(root: Path, sizes: tuple[float, ...] = BEAM_SIZES_MM) -> list[dict[str, object]]:
    rows = []
    for size in sizes:
        record = run_beam(root / f"size-{size:g}", BeamSpec(element_size_mm=size))
        rows.append(_row(record, BEAM_KEYS))
    _write(root / "summary.json", beam_summary(rows))
    return rows


def run_bracket_refinement(
    root: Path,
    sizes: tuple[float, ...] = BRACKET_SIZES_MM,
    material_id: str = "aluminum_6061_t6",
) -> list[dict[str, object]]:
    card = get_card(material_id)
    card.require_solvable()
    rows = []
    for size in sizes:
        record = run_bracket(
            root / f"size-{size:g}",
            PHASE1_BRACKET,
            element_size_mm=size,
            youngs_modulus_mpa=card.youngs_modulus_mpa,
            poissons_ratio=float(card.poissons_ratio),
            material_id=card.material_id,
            material_note=card.limitations,
        )
        rows.append(_row(record, BRACKET_KEYS))
    _write(root / "summary.json", bracket_summary(rows, card))
    return rows


def _write(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
