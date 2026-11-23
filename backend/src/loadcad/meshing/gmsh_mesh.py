"""Import a millimetre STEP file and mesh it with second-order tetrahedra."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from loadcad.geometry.faces import FaceFingerprint
from loadcad.meshing.c3d10 import (
    FACE_CORNERS,
    MeshError,
    apply_permutation,
    confirmed_permutation,
    enforce_element_cap,
)
from loadcad.meshing.match import FaceMatchError, SurfaceRecord, match_roles
from loadcad.postprocess.loads import FaceTriangle


@dataclass
class VolumeMesh:
    nodes: dict[int, np.ndarray]
    elements: dict[int, list[int]]
    raw_order_matches: bool
    node_order: str
    role_nodes: dict[str, list[int]]
    role_triangles: dict[str, list[FaceTriangle]]
    role_dloads: dict[str, list[tuple[int, int]]]
    bbox_mm: tuple[float, float, float, float, float, float]
    min_quality: float | None
    gmsh_version: str
    log: str
    matched_tags: dict[str, list[int]]


@contextmanager
def _gmsh_session():
    import gmsh

    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.logger.start()
        yield gmsh
    finally:
        try:
            gmsh.logger.stop()
        except Exception:
            pass
        gmsh.finalize()


def _log(gmsh: object) -> str:
    try:
        return "\n".join(gmsh.logger.get())  # type: ignore[attr-defined]
    except Exception:
        return ""


def _set_millimetres(gmsh: object) -> None:
    # Do not set this option to metres. Material cards are in MPa.
    try:
        gmsh.option.setString("Geometry.OCCTargetUnit", "MM")  # type: ignore[attr-defined]
    except Exception:
        pass


def _flatten_normal(raw: object) -> np.ndarray | None:
    values = np.array(raw, dtype=float).reshape(-1)
    if values.size < 3:
        return None
    normal = values[:3]
    length = float(np.linalg.norm(normal))
    if length == 0.0:
        return None
    return normal / length


def _parameter_midpoint(bounds: object) -> tuple[float, float]:
    # Gmsh 4.15 returns ((umin, vmin), (umax, vmax)).
    if isinstance(bounds, tuple) and len(bounds) == 2 and len(bounds[0]) == 2 and len(bounds[1]) == 2:
        u = 0.5 * (float(bounds[0][0]) + float(bounds[1][0]))
        v = 0.5 * (float(bounds[0][1]) + float(bounds[1][1]))
        return u, v
    flat = np.array(bounds, dtype=float).reshape(-1)
    if flat.size < 4:
        raise MeshError("mesh_quality_failed", "surface parameter bounds are incomplete")
    return 0.5 * (float(flat[0]) + float(flat[1])), 0.5 * (float(flat[2]) + float(flat[3]))


def _surface_normal(gmsh: object, tag: int) -> np.ndarray:
    u, v = _parameter_midpoint(gmsh.model.getParametrizationBounds(2, tag))  # type: ignore[attr-defined]
    normal = _flatten_normal(gmsh.model.getNormal(tag, [u, v]))  # type: ignore[attr-defined]
    if normal is None:
        raise MeshError("mesh_quality_failed", f"surface {tag} normal is undefined")
    return normal


def _surfaces(gmsh: object) -> list[SurfaceRecord]:
    records = []
    for _dim, tag in gmsh.model.getEntities(2):  # type: ignore[attr-defined]
        centroid = gmsh.model.occ.getCenterOfMass(2, tag)  # type: ignore[attr-defined]
        area = float(gmsh.model.occ.getMass(2, tag))  # type: ignore[attr-defined]
        normal = _surface_normal(gmsh, int(tag))
        records.append(
            SurfaceRecord(
                tag=int(tag),
                centroid_mm=(float(centroid[0]), float(centroid[1]), float(centroid[2])),
                normal=(float(normal[0]), float(normal[1]), float(normal[2])),
                area_mm2=area,
            )
        )
    return records


def _bbox_of_volumes(gmsh: object) -> tuple[float, float, float, float, float, float]:
    volumes = list(gmsh.model.getEntities(3))  # type: ignore[attr-defined]
    if len(volumes) != 1:
        raise MeshError("geometry_failed", f"expected one imported volume, found {len(volumes)}")
    bounds = gmsh.model.getBoundingBox(3, volumes[0][1])  # type: ignore[attr-defined]
    return tuple(float(value) for value in bounds)  # type: ignore[return-value]


def assert_same_scale(
    cad_bbox: tuple[float, float, float, float, float, float],
    mesh_bbox: tuple[float, float, float, float, float, float],
) -> None:
    for cad, mesh in zip(cad_bbox, mesh_bbox, strict=True):
        limit = max(0.05, 0.001 * max(abs(cad), 1.0))
        if abs(cad - mesh) > limit:
            raise MeshError(
                "geometry_failed",
                f"imported bounding box {mesh_bbox} disagrees with CAD {cad_bbox}",
            )


def _classify_triangle(node_ids: list[int]) -> FaceTriangle:
    """Gmsh triangle type 9: corners, then midsides of edges 1-2, 2-3, and 3-1."""
    if len(node_ids) != 6:
        raise MeshError("mesh_quality_failed", "load surface element is not a 6-node triangle")
    return FaceTriangle(
        corners=(node_ids[0], node_ids[1], node_ids[2]),
        midsides=(node_ids[3], node_ids[4], node_ids[5]),
    )


def _triangle_is_straight(tri: FaceTriangle, nodes: dict[int, np.ndarray]) -> bool:
    pairs = ((0, 1), (1, 2), (2, 0))
    points = [nodes[nid] for nid in tri.corners]
    span = max(float(np.linalg.norm(points[i] - points[j])) for i, j in pairs)
    tolerance = max(1e-4, 1e-4 * span)
    for (first, second), mid in zip(pairs, tri.midsides, strict=True):
        expected = 0.5 * (nodes[tri.corners[first]] + nodes[tri.corners[second]])
        if float(np.linalg.norm(nodes[mid] - expected)) > tolerance:
            return False
    return True


def _triangles_for_surfaces(
    gmsh: object,
    tags: list[int],
    nodes: dict[int, np.ndarray],
) -> tuple[list[int], list[FaceTriangle]]:
    node_ids: set[int] = set()
    triangles: list[FaceTriangle] = []
    for tag in tags:
        types, _element_tags, connectivity = gmsh.model.mesh.getElements(2, tag)  # type: ignore[attr-defined]
        for element_type, blob in zip(types, connectivity, strict=True):
            per_element = int(gmsh.model.mesh.getElementProperties(element_type)[3])  # type: ignore[attr-defined]
            if per_element != 6:
                raise MeshError(
                    "mesh_quality_failed",
                    f"surface {tag} produced {per_element}-node elements, expected 6",
                )
            flat = [int(value) for value in blob]
            for start in range(0, len(flat), 6):
                tri = _classify_triangle(flat[start : start + 6])
                triangles.append(tri)
                node_ids.update(tri.corners)
                node_ids.update(tri.midsides)
    return sorted(node_ids), triangles


def mesh_step(
    step_path: Path,
    fingerprints: dict[str, FaceFingerprint],
    cad_bbox: tuple[float, float, float, float, float, float],
    element_size_mm: float,
    msh_path: Path,
) -> VolumeMesh:
    with _gmsh_session() as gmsh:
        gmsh.model.add("loadcad")
        _set_millimetres(gmsh)
        gmsh.model.occ.importShapes(str(step_path))
        gmsh.model.occ.synchronize()
        mesh_bbox = _bbox_of_volumes(gmsh)
        assert_same_scale(cad_bbox, mesh_bbox)
        surfaces = _surfaces(gmsh)
        try:
            matched = match_roles(fingerprints, surfaces, cad_bbox)
        except FaceMatchError:
            (msh_path.parent / "surface_dump.log").write_text(_log(gmsh), encoding="utf-8")
            raise
        for role, records in matched.items():
            gmsh.model.addPhysicalGroup(2, [record.tag for record in records], name=role)
        volume_tag = int(gmsh.model.getEntities(3)[0][1])
        gmsh.model.addPhysicalGroup(3, [volume_tag], name="EALL")
        points = gmsh.model.getEntities(0)
        gmsh.model.mesh.setSize(points, float(element_size_mm))
        gmsh.option.setNumber("Mesh.ElementOrder", 2)
        for name, value in (
            ("Mesh.MeshSizeMin", float(element_size_mm) * 0.5),
            ("Mesh.MeshSizeMax", float(element_size_mm)),
            ("Mesh.Optimize", 1),
            ("Mesh.HighOrderOptimize", 1),
            ("Mesh.RandomFactor", 1e-9),
        ):
            try:
                gmsh.option.setNumber(name, value)
            except Exception:
                pass
        gmsh.model.mesh.generate(3)
        try:
            gmsh.model.mesh.optimize("HighOrder")
        except Exception:
            pass
        node_tags, coordinates, _ = gmsh.model.mesh.getNodes()
        coords = np.array(coordinates, dtype=float).reshape(-1, 3)
        nodes = {int(tag): coords[index] for index, tag in enumerate(node_tags)}
        types, element_tags, connectivity = gmsh.model.mesh.getElements(3)
        raw_elements: dict[int, list[int]] = {}
        for element_type, tags, blob in zip(types, element_tags, connectivity, strict=True):
            per_element = int(gmsh.model.mesh.getElementProperties(element_type)[3])
            if per_element != 10:
                raise MeshError(
                    "mesh_quality_failed",
                    f"volume element type {element_type} has {per_element} nodes, expected 10",
                )
            flat = [int(value) for value in blob]
            tags_int = [int(value) for value in tags]
            for index, tag in enumerate(tags_int):
                raw_elements[tag] = flat[index * 10 : (index + 1) * 10]
        permutation_name, permutation = confirmed_permutation(list(raw_elements.values()), nodes)
        elements = {
            tag: apply_permutation(raw, permutation) for tag, raw in raw_elements.items()
        }
        raw_matches = permutation_name == "identity"
        enforce_element_cap(len(elements))
        min_quality = _min_quality(gmsh, list(elements))
        if min_quality is not None and min_quality <= 0.0:
            raise MeshError("mesh_quality_failed", f"minimum SICN quality is {min_quality}")
        role_nodes: dict[str, list[int]] = {}
        role_triangles: dict[str, list[FaceTriangle]] = {}
        role_dloads: dict[str, list[tuple[int, int]]] = {}
        boundary_faces: dict[frozenset[int], tuple[int, int]] = {}
        internal_faces: set[frozenset[int]] = set()
        for element_id, element_nodes in elements.items():
            for number, indices in FACE_CORNERS.items():
                key = frozenset(element_nodes[index] for index in indices)
                if key in internal_faces:
                    continue
                if key in boundary_faces:
                    del boundary_faces[key]
                    internal_faces.add(key)
                else:
                    boundary_faces[key] = (element_id, number)
        for role, records in matched.items():
            role_nodes[role], role_triangles[role] = _triangles_for_surfaces(
                gmsh, [record.tag for record in records], nodes
            )
            dloads = []
            for tri in role_triangles[role]:
                key = frozenset(tri.corners)
                if key not in boundary_faces:
                    raise MeshError(
                        "mesh_quality_failed",
                        f"surface triangle on {role} did not map to one boundary volume face",
                    )
                dloads.append(boundary_faces[key])
            role_dloads[role] = dloads
        straight = [
            tri
            for triangles in role_triangles.values()
            for tri in triangles
            if _triangle_is_straight(tri, nodes)
        ]
        if not straight:
            raise MeshError(
                "mesh_quality_failed",
                "no straight face triangle confirmed the Gmsh 6-node order",
            )
        version = str(gmsh.option.getString("General.Version"))
        log = _log(gmsh)
        msh_path.parent.mkdir(parents=True, exist_ok=True)
        # meshio 5.3.5 rejects Gmsh 4.1 files that mix many cell blocks with
        # fewer physical-tag blocks. Version 2.2 is the debug artifact.
        gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
        gmsh.option.setNumber("Mesh.SaveAll", 1)
        gmsh.write(str(msh_path))
        return VolumeMesh(
            nodes=nodes,
            elements=elements,
            raw_order_matches=raw_matches,
            node_order=permutation_name,
            role_nodes=role_nodes,
            role_triangles=role_triangles,
            role_dloads=role_dloads,
            bbox_mm=mesh_bbox,
            min_quality=min_quality,
            gmsh_version=version,
            log=log,
            matched_tags={role: [record.tag for record in records] for role, records in matched.items()},
        )


def _min_quality(gmsh: object, element_ids: list[int]) -> float | None:
    if not element_ids:
        return None
    try:
        values = gmsh.model.mesh.getElementQualities(element_ids, "minSICN")  # type: ignore[attr-defined]
    except Exception:
        return None
    if len(values) == 0:
        return None
    return float(min(values))


def inspect_bbox(step_path: Path) -> tuple[float, float, float, float, float, float]:
    with _gmsh_session() as gmsh:
        gmsh.model.add("inspect")
        _set_millimetres(gmsh)
        gmsh.model.occ.importShapes(str(step_path))
        gmsh.model.occ.synchronize()
        return _bbox_of_volumes(gmsh)
