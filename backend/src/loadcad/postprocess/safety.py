"""Safety-factor record. Emitted only for a named decision metric."""

from __future__ import annotations

from loadcad.materials.cards import MaterialCard


def safety_fields(
    card: MaterialCard,
    decision_metric: str,
    decision_von_mises_mpa: float,
    max_nodal_von_mises_mpa: float,
    mesh_converged: bool,
    restraint: str,
    load_model: str,
) -> dict[str, object]:
    card.require_solvable()
    if not decision_metric:
        raise ValueError("a safety factor requires a named decision metric")
    if decision_von_mises_mpa <= 0.0:
        raise ValueError("decision stress must be positive")
    return {
        "material_id": card.material_id,
        "material_version": card.version,
        "allowable_stress_mpa": card.allowable_stress_mpa,
        "allowable_basis": card.allowable_basis,
        "decision_metric": decision_metric,
        "decision_von_mises_mpa": float(decision_von_mises_mpa),
        "max_nodal_von_mises_mpa": float(max_nodal_von_mises_mpa),
        "estimated_safety_factor": card.allowable_stress_mpa / float(decision_von_mises_mpa),
        "elastic_assumption_exceeded": float(decision_von_mises_mpa) > card.allowable_stress_mpa,
        "mesh_converged": bool(mesh_converged),
        "restraint": restraint,
        "load_model": load_model,
        "material_limitations": card.limitations,
    }
