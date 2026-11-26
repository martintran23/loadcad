"""Decision metric for the Phase 2 bracket study.

The name is the unfiltered nodal peak. A stress convergence band is not set:
the stored refinement still moves that peak, so mesh_converged stays false.
"""

from __future__ import annotations

from loadcad.jobs.store import result_record
from loadcad.materials.cards import MaterialCard
from loadcad.postprocess.safety import safety_fields

DECISION_METRIC = "max_nodal_von_mises"
# None until a later refinement shows this stress sample flattening.
# The 5% figure in CONTEXT is the beam-displacement candidate, not a stress band.
STRESS_RELATIVE_BAND: float | None = None


def last_step_relative_change(rows: list[dict[str, object]], key: str) -> float:
    """Change from the second-finest stored size to the finest, divided by the coarser value."""
    ordered = sorted(rows, key=lambda row: float(row["element_size_mm"]))
    if len(ordered) < 2:
        raise ValueError("a refinement comparison needs two sizes")
    current = float(ordered[0][key])
    previous = float(ordered[1][key])
    if previous == 0.0:
        raise ValueError(f"{key} is zero on the coarser of the two finest meshes")
    return (current - previous) / previous


def mesh_converged(change: float) -> bool:
    if STRESS_RELATIVE_BAND is None:
        return False
    return abs(change) <= STRESS_RELATIVE_BAND


def bracket_safety_record(rows: list[dict[str, object]], card: MaterialCard) -> dict[str, object]:
    """Safety-factor record for the finest row. mesh_converged follows the unset band."""
    ordered = sorted(rows, key=lambda row: float(row["element_size_mm"]))
    finest = ordered[0]
    change = last_step_relative_change(ordered, "max_nodal_von_mises_mpa")
    decision = float(finest["max_nodal_von_mises_mpa"])
    fields = safety_fields(
        card,
        DECISION_METRIC,
        decision,
        decision,
        mesh_converged(change),
        "encastre_mounting_face",
        "normal_pressure",
    )
    return result_record(
        **fields,
        element_size_mm=finest["element_size_mm"],
        node_count=finest["node_count"],
        element_count=finest["element_count"],
        last_step_relative_change=change,
        stress_relative_band=STRESS_RELATIVE_BAND,
        mesh_convergence_note=(
            "No stress convergence band is adopted. mesh_converged is false "
            "until a band is set from a study whose decision metric has flattened."
        ),
    )
