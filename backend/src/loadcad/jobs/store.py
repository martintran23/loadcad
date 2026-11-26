"""Write a job folder. A safety factor is stored only with a named decision metric."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

DISCLAIMER = (
    "Simulated linear-elastic candidate under the stated assumptions. "
    "Not a certified, physically tested, or guaranteed-safe design."
)


def prepare_job(root: Path) -> dict[str, Path]:
    root.mkdir(parents=True, exist_ok=True)
    paths = {"root": root}
    for name in ("logs", "geometry", "mesh", "solver", "results"):
        path = root / name
        path.mkdir(exist_ok=True)
        paths[name] = path
    return paths


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def result_record(**fields: object) -> dict[str, object]:
    """Build a result record. A safety factor is kept only with a named metric."""
    record = dict(fields)
    if not record.get("decision_metric"):
        record["decision_metric"] = None
        record["estimated_safety_factor"] = None
    record["disclaimer"] = DISCLAIMER
    return record
