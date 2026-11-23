"""Read the nodal blocks LoadCAD requests from an ASCII CalculiX FRD file.

CalculiX writes each value in a 12-character field. A leading minus sign
consumes the separator, so negative values are glued to the previous field.
Component names come from the -5 headers, not from a guessed order.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

_FLOAT = re.compile(r"[+-]?(?:\d+\.\d+|\d+)(?:[Ee][+-]?\d+)?")


@dataclass
class FrdField:
    name: str
    components: list[str]
    values: dict[int, np.ndarray] = field(default_factory=dict)


@dataclass
class FrdResults:
    blocks: dict[str, FrdField]

    def require(self, name: str) -> FrdField:
        if name not in self.blocks or not self.blocks[name].values:
            known = ", ".join(sorted(self.blocks)) or "none"
            raise ValueError(f"FRD block {name} is missing (found {known})")
        return self.blocks[name]


def _component_vector(field: FrdField, node_id: int, names: tuple[str, ...]) -> np.ndarray:
    values = field.values[node_id]
    indexes = []
    upper = [component.upper() for component in field.components]
    for name in names:
        if name not in upper:
            raise ValueError(f"FRD block {field.name} has no component {name} ({field.components})")
        indexes.append(upper.index(name))
    return np.array([float(values[index]) for index in indexes], dtype=float)


def displacements(results: FrdResults) -> dict[int, np.ndarray]:
    field = results.require("DISP")
    return {node: _component_vector(field, node, ("D1", "D2", "D3")) for node in field.values}


def reactions(results: FrdResults) -> dict[int, np.ndarray]:
    # *NODE FILE RF is stored as FORC with components F1, F2, F3.
    if "RF" in results.blocks:
        field = results.require("RF")
        names = ("RF1", "RF2", "RF3")
    else:
        field = results.require("FORC")
        names = ("F1", "F2", "F3")
    return {node: _component_vector(field, node, names) for node in field.values}


def stress_components(results: FrdResults) -> dict[int, np.ndarray]:
    field = results.require("STRESS")
    names = ("SXX", "SYY", "SZZ", "SXY", "SYZ", "SZX")
    return {node: _component_vector(field, node, names) for node in field.values}


def _header(line: str) -> tuple[str, list[str]] | None:
    stripped = line.strip()
    if not stripped.startswith("-"):
        return None
    parts = stripped.split()
    if parts[0] not in {"-1", "-2", "-3", "-4", "-5"}:
        return None
    return parts[0], parts[1:]


def _node_and_values(rest: str) -> tuple[int, list[float]]:
    match = re.match(r"(\d+)(.*)", rest)
    if match is None:
        raise ValueError(f"FRD data line has no node id: {rest!r}")
    values = [float(token) for token in _FLOAT.findall(match.group(2))]
    return int(match.group(1)), values


def parse_frd(path: Path) -> FrdResults:
    blocks: dict[str, FrdField] = {}
    current: FrdField | None = None
    node_id: int | None = None
    pending: list[float] = []

    def flush_node() -> None:
        nonlocal node_id, pending
        if current is not None and node_id is not None:
            current.values[node_id] = np.array(pending, dtype=float)
        node_id = None
        pending = []

    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        header = _header(raw)
        if header is None:
            continue
        key, parts = header
        if key == "-4" and parts:
            flush_node()
            current = FrdField(name=parts[0].upper(), components=[])
            blocks[current.name] = current
        elif key == "-5" and current is not None and parts:
            name = parts[0].upper()
            if name != "ALL":
                current.components.append(name)
        elif key == "-1" and current is not None and parts:
            flush_node()
            rest = raw.strip().split(maxsplit=1)[1]
            node_id, pending = _node_and_values(rest)
        elif key == "-2" and node_id is not None:
            pieces = raw.strip().split(maxsplit=1)
            body = pieces[1] if len(pieces) > 1 else ""
            pending.extend(float(token) for token in _FLOAT.findall(body))
        elif key == "-3":
            flush_node()
            current = None
    flush_node()
    return FrdResults(blocks=blocks)
