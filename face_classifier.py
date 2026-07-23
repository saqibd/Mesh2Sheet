from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import bmesh
import bpy
from mathutils import Vector

from .mesh_analyzer import MeshAnalysisResult


class FaceType(Enum):
    PLANAR = "PLANAR"
    CURVED = "CURVED"
    BOUNDARY = "BOUNDARY"
    SMALL_FEATURE = "SMALL_FEATURE"
    UNKNOWN = "UNKNOWN"


@dataclass
class FaceClassificationResult:
    face_index: int
    classification: FaceType
    normal: Vector
    area: float
    center: Vector
    neighbors: list[int]


class FaceClassifier:
    """Classify mesh faces into a conservative set of geometric categories."""

    SMALL_FEATURE_AREA_RATIO = 0.10
    PLANAR_ALIGNMENT_THRESHOLD = 0.98
    CURVED_ALIGNMENT_THRESHOLD = 0.95

    def classify(
        self, obj: bpy.types.Object | None, analysis: MeshAnalysisResult | None
    ) -> list[FaceClassificationResult]:
        if obj is None or obj.type != "MESH" or obj.data is None or analysis is None:
            return []

        bm = bmesh.new()
        try:
            bm.from_mesh(obj.data)
            faces = list(bm.faces)
            if not faces:
                return []

            face_index_map = {id(face): index for index, face in enumerate(faces)}
            average_face_area = analysis.average_face_area
            threshold_area = average_face_area * self.SMALL_FEATURE_AREA_RATIO

            results: list[FaceClassificationResult] = []
            for face_index, face in enumerate(faces):
                classification = self._classify_face(face, threshold_area)
                normal = self._transform_normal_to_world(obj, face.normal)
                center = self._transform_point_to_world(obj, face.calc_center_median())
                neighbors = self._collect_neighbor_indices(face, face_index_map)

                results.append(
                    FaceClassificationResult(
                        face_index=face_index,
                        classification=classification,
                        normal=normal,
                        area=face.calc_area(),
                        center=center,
                        neighbors=neighbors,
                    )
                )

            return results
        finally:
            bm.free()

    def _classify_face(self, face: bmesh.types.BMFace, threshold_area: float) -> FaceType:
        if any(edge.is_boundary for edge in face.edges):
            return FaceType.BOUNDARY

        area = face.calc_area()
        if threshold_area > 0.0 and area < threshold_area:
            return FaceType.SMALL_FEATURE

        neighbor_faces = self._collect_neighbor_faces(face)
        if not neighbor_faces:
            return FaceType.UNKNOWN

        neighbor_normals = [neighbor.normal for neighbor in neighbor_faces]
        if not neighbor_normals:
            return FaceType.UNKNOWN

        average_alignment = sum(face.normal.dot(normal) for normal in neighbor_normals) / len(
            neighbor_normals
        )
        if average_alignment >= self.PLANAR_ALIGNMENT_THRESHOLD:
            return FaceType.PLANAR
        if average_alignment <= self.CURVED_ALIGNMENT_THRESHOLD:
            return FaceType.CURVED
        return FaceType.UNKNOWN

    @staticmethod
    def _collect_neighbor_faces(face: bmesh.types.BMFace) -> list[bmesh.types.BMFace]:
        neighbors: set[bmesh.types.BMFace] = set()
        for edge in face.edges:
            for linked_face in edge.link_faces:
                if linked_face != face:
                    neighbors.add(linked_face)
        return list(neighbors)

    @classmethod
    def _collect_neighbor_indices(
        cls, face: bmesh.types.BMFace, face_index_map: dict[int, int]
    ) -> list[int]:
        neighbors: list[int] = []
        for edge in face.edges:
            for linked_face in edge.link_faces:
                if linked_face != face and id(linked_face) in face_index_map:
                    neighbor_index = face_index_map[id(linked_face)]
                    if neighbor_index not in neighbors:
                        neighbors.append(neighbor_index)
        return neighbors

    @staticmethod
    def _transform_normal_to_world(obj: bpy.types.Object, normal: Vector) -> Vector:
        matrix = obj.matrix_world.to_3x3().inverted().transposed()
        return matrix @ normal

    @staticmethod
    def _transform_point_to_world(obj: bpy.types.Object, point: Vector) -> Vector:
        return obj.matrix_world @ point


def classify_faces(
    obj: bpy.types.Object | None, analysis: MeshAnalysisResult | None
) -> list[FaceClassificationResult]:
    """Backward-compatible wrapper for face classification."""
    return FaceClassifier().classify(obj, analysis)
