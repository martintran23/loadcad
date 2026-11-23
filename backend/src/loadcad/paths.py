"""Local paths for the Phase 1 toolchain.

The CalculiX binary is downloaded outside the Git tree. See CONTEXT.md.
"""

from __future__ import annotations

import os
from pathlib import Path

CCX_DOWNLOAD_URL = "https://www.dhondt.de/calculix_2.22_4win.zip"
# SHA-256 of the zip downloaded during Phase 1. Confirmed against the local file.
CCX_ZIP_SHA256 = "a1f91281944c96d6cd914cc020421e8ae65973b3e15d055dc63a3e3e3066d281"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def calculix_dir() -> Path:
    return repo_root() / "tools" / "calculix" / "dist" / "calculix_2.22_4win"


def calculix_zip() -> Path:
    return repo_root() / "tools" / "calculix" / "calculix_2.22_4win.zip"


def ccx_executable() -> Path | None:
    """Return the configured solver, or None when this machine has no binary."""
    override = os.environ.get("LOADCAD_CCX")
    if override:
        path = Path(override)
        if path.is_file():
            return path
    # The static build links SPOOLES and PaStiX and does not need mkl_rt.
    candidate = calculix_dir() / "ccx_static.exe"
    if candidate.is_file():
        return candidate
    return None
