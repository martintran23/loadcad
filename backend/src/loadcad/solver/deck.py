"""Write a CalculiX input deck from mesh tables.

Set names and material names are fixed by this module. Request text is never
copied into the deck.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

MATERIAL_NAME = "BENCHMARK"
ELEMENT_SET = "EALL"
FIXED_SET = "FIXED_MOUNT"


def _fmt(value: float) -> str:
    return f"{value:.10e}"


def _wrap_ids(ids: list[int], per_line: int = 8) -> list[str]:
    lines = []
    for start in range(0, len(ids), per_line):
        lines.append(", ".join(str(value) for value in ids[start : start + per_line]))
    return lines


def write_deck(
    path: Path,
    nodes: dict[int, np.ndarray],
    elements: dict[int, list[int]],
    fixed_nodes: list[int],
    dloads: list[tuple[int, int, float]] | None = None,
    cloads: dict[int, np.ndarray] | None = None,
    youngs_modulus_mpa: float = 210_000.0,
    poissons_ratio: float = 0.3,
    restrain: bool = True,
    integration_point_stress: bool = True,
) -> None:
    lines = [
        "*HEADING",
        "LoadCAD Phase 1 generated deck",
        "*NODE",
    ]
    for node_id in sorted(nodes):
        x, y, z = nodes[node_id]
        lines.append(f"{node_id}, {_fmt(float(x))}, {_fmt(float(y))}, {_fmt(float(z))}")
    lines.append(f"*ELEMENT, TYPE=C3D10, ELSET={ELEMENT_SET}")
    for element_id in sorted(elements):
        connectivity = ", ".join(str(node_id) for node_id in elements[element_id])
        lines.append(f"{element_id}, {connectivity}")
    if restrain:
        lines.append(f"*NSET, NSET={FIXED_SET}")
        lines.extend(_wrap_ids(sorted(set(fixed_nodes))))
    lines.extend(
        [
            f"*MATERIAL, NAME={MATERIAL_NAME}",
            "*ELASTIC",
            f"{_fmt(youngs_modulus_mpa)}, {_fmt(poissons_ratio)}",
            f"*SOLID SECTION, ELSET={ELEMENT_SET}, MATERIAL={MATERIAL_NAME}",
            "*STEP",
            "*STATIC",
        ]
    )
    if restrain:
        lines.extend(
            [
                "*BOUNDARY",
                f"{FIXED_SET}, 1, 3, 0.",
            ]
        )
    if dloads:
        lines.append("*DLOAD")
        for element_id, face, pressure in dloads:
            if face not in {1, 2, 3, 4}:
                raise ValueError(f"invalid C3D10 face {face}")
            lines.append(f"{element_id}, P{face}, {_fmt(pressure)}")
    if cloads:
        lines.append("*CLOAD")
        for node_id in sorted(cloads):
            force = np.asarray(cloads[node_id], dtype=float)
            for dof, component in enumerate(force, start=1):
                if abs(float(component)) > 1e-12:
                    lines.append(f"{node_id}, {dof}, {_fmt(float(component))}")
    lines.extend(
        [
            "*NODE FILE",
            "U, RF",
            "*EL FILE",
            "S",
        ]
    )
    if integration_point_stress:
        lines.extend(
            [
                "*EL PRINT, ELSET=" + ELEMENT_SET,
                "S",
            ]
        )
    if restrain:
        lines.extend(
            [
                "*NODE PRINT, NSET=" + FIXED_SET,
                "RF",
            ]
        )
    lines.extend(
        [
            "*END STEP",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="ascii")


def write_smoke_tet(path: Path) -> None:
    """One restrained tetrahedron, used only to probe the solver process."""
    corners = {
        1: np.array([0.0, 0.0, 0.0]),
        2: np.array([1.0, 0.0, 0.0]),
        3: np.array([0.0, 1.0, 0.0]),
        4: np.array([0.0, 0.0, 1.0]),
    }
    pairs = ((1, 2), (2, 3), (3, 1), (1, 4), (2, 4), (3, 4))
    nodes = dict(corners)
    for offset, (first, second) in enumerate(pairs, start=5):
        nodes[offset] = 0.5 * (corners[first] + corners[second])
    elements = {1: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]}
    # Face 1 is the triangle at z = 0. A downward load on the apex checks the process.
    write_deck(
        path,
        nodes,
        elements,
        fixed_nodes=[1, 2, 3, 5, 6, 7],
        cloads={4: np.array([0.0, 0.0, -1.0])},
        youngs_modulus_mpa=1_000.0,
        poissons_ratio=0.3,
    )
