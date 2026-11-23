"""Geometry failures that stop a job before meshing."""

from __future__ import annotations


class GeometryError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
