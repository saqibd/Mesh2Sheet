from __future__ import annotations

from dataclasses import dataclass

import bmesh
import bpy


@dataclass
class MeshAnalysisResult:
    vertex_count: int
    edge_count: int
    face_count: int
    boundary_edge_count: int
    non_manifold_edge_count: int
    loose_vertex_count: int
    bounding_box_width: float
    bounding_box_depth: float
    bounding_box_height: float
    surface_area: float
    average_face_area: float
    average_edge_length: float
    is_watertight: bool
    warnings: list[str]


class MeshAnalyzer:
    """Analyze a mesh object and return a structured analysis result."""

    def analyze(self, obj: bpy.types.Object | None) -> MeshAnalysisResult:
        if obj is None or obj.type != "MESH" or obj.data is None:
            return MeshAnalysisResult(
                vertex_count=0,
                edge_count=0,
                face_count=0,
                boundary_edge_count=0,
                non_manifold_edge_count=0,
                loose_vertex_count=0,
                bounding_box_width=0.0,
                bounding_box_depth=0.0,
                bounding_box_height=0.0,
                surface_area=0.0,
                average_face_area=0.0,
                average_edge_length=0.0,
                is_watertight=False,
                warnings=["No valid mesh object provided."],
            )

        mesh = obj.data
        bm = bmesh.new()
        try:
            bm.from_mesh(mesh)

            vertex_count = len(bm.verts)
            edge_count = len(bm.edges)
            face_count = len(bm.faces)

            boundary_edge_count = 0
            non_manifold_edge_count = 0
            loose_vertex_count = 0
            total_face_area = 0.0
            total_edge_length = 0.0

            for face in bm.faces:
                total_face_area += face.calc_area()

            for edge in bm.edges:
                if edge.is_boundary:
                    boundary_edge_count += 1
                if self._is_non_manifold_edge(edge):
                    non_manifold_edge_count += 1
                total_edge_length += edge.calc_length()

            for vert in bm.verts:
                if len(vert.link_faces) == 0:
                    loose_vertex_count += 1

            min_x = min_y = min_z = None
            max_x = max_y = max_z = None
            for vert in bm.verts:
                world_co = obj.matrix_world @ vert.co
                if min_x is None:
                    min_x = max_x = world_co.x
                    min_y = max_y = world_co.y
                    min_z = max_z = world_co.z
                else:
                    min_x = min(min_x, world_co.x)
                    max_x = max(max_x, world_co.x)
                    min_y = min(min_y, world_co.y)
                    max_y = max(max_y, world_co.y)
                    min_z = min(min_z, world_co.z)
                    max_z = max(max_z, world_co.z)

            if min_x is None:
                bounding_box_width = 0.0
                bounding_box_depth = 0.0
                bounding_box_height = 0.0
            else:
                bounding_box_width = max_x - min_x
                bounding_box_depth = max_y - min_y
                bounding_box_height = max_z - min_z

            average_face_area = total_face_area / face_count if face_count else 0.0
            average_edge_length = total_edge_length / edge_count if edge_count else 0.0
            is_watertight = (
                face_count > 0
                and boundary_edge_count == 0
                and non_manifold_edge_count == 0
                and loose_vertex_count == 0
            )

            warnings: list[str] = []
            if boundary_edge_count > 0:
                warnings.append("Mesh has boundary edges.")
            if non_manifold_edge_count > 0:
                warnings.append("Mesh contains non-manifold edges.")
            if loose_vertex_count > 0:
                warnings.append("Mesh contains loose vertices.")
            if face_count == 0:
                warnings.append("Mesh contains no faces.")
            elif total_face_area == 0.0:
                warnings.append("Mesh surface area is zero.")

            return MeshAnalysisResult(
                vertex_count=vertex_count,
                edge_count=edge_count,
                face_count=face_count,
                boundary_edge_count=boundary_edge_count,
                non_manifold_edge_count=non_manifold_edge_count,
                loose_vertex_count=loose_vertex_count,
                bounding_box_width=bounding_box_width,
                bounding_box_depth=bounding_box_depth,
                bounding_box_height=bounding_box_height,
                surface_area=total_face_area,
                average_face_area=average_face_area,
                average_edge_length=average_edge_length,
                is_watertight=is_watertight,
                warnings=warnings,
            )
        finally:
            bm.free()

    @staticmethod
    def _is_non_manifold_edge(edge: bmesh.types.BMEdge) -> bool:
        non_manifold_attr = getattr(edge, "is_non_manifold", None)
        if non_manifold_attr is not None:
            return bool(non_manifold_attr)

        manifold_attr = getattr(edge, "is_manifold", None)
        if manifold_attr is not None:
            return not bool(manifold_attr)

        return len(edge.link_faces) != 2


def analyze_mesh(obj: bpy.types.Object | None) -> MeshAnalysisResult:
    """Backward-compatible wrapper for mesh analysis."""
    return MeshAnalyzer().analyze(obj)
