"""Run an unmodified ccx binary. User input never becomes part of the command."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path


class SolverFailure(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass
class SolverRun:
    command: list[str]
    returncode: int
    stdout: str
    stderr: str
    frd_path: Path
    dat_path: Path
    sta_path: Path


def solver_command(ccx_path: Path, job_name: str = "job") -> list[str]:
    return [str(ccx_path), "-i", job_name]


def run_ccx(
    ccx_path: Path,
    work_dir: Path,
    job_name: str = "job",
    timeout_s: float = 600.0,
) -> SolverRun:
    command = solver_command(ccx_path, job_name)
    env = os.environ.copy()
    env["OMP_NUM_THREADS"] = "1"
    work_dir.mkdir(parents=True, exist_ok=True)
    try:
        completed = subprocess.run(
            command,
            cwd=work_dir,
            shell=False,
            capture_output=True,
            timeout=timeout_s,
            env=env,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise SolverFailure("solver_timeout", f"ccx exceeded {timeout_s:.0f}s") from exc
    stdout = completed.stdout.decode("utf-8", errors="replace")
    stderr = completed.stderr.decode("utf-8", errors="replace")
    frd_path = work_dir / f"{job_name}.frd"
    dat_path = work_dir / f"{job_name}.dat"
    sta_path = work_dir / f"{job_name}.sta"
    if completed.returncode != 0:
        raise SolverFailure(
            "solver_failed",
            f"ccx exited {completed.returncode}\n{stdout}\n{stderr}",
        )
    if not frd_path.is_file():
        raise SolverFailure("result_unreadable", "ccx exited 0 without an FRD file")
    return SolverRun(
        command=command,
        returncode=completed.returncode,
        stdout=stdout,
        stderr=stderr,
        frd_path=frd_path,
        dat_path=dat_path,
        sta_path=sta_path,
    )
