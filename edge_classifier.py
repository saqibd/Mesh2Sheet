from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

import bmesh
import bpy


class EdgeType(Enum):
    SMOOTH = "SMOOTH"
    SHARP = "SHARP"
    BOUNDARY = "BOUNDARY"
    FEATURE = "FEATURE"
    UNKNOWN = "UNKNOWN"


@dataclass
class EdgeClassificationResult:
    edge_index: int
    face_a: int | None
    face_b: int | None
    dihedral_angle: float
    classification: EdgeType


class EdgeClassifier:
    """Classify mesh edges into geometric edge categories."""

    SMOOTH_THRESHOLD_DEGREES = 15.0
    SHARP_THRESHOLD_DEGREES = 45.0

    def classify(self, obj: bpy.types.Object | None) -> list[EdgeClassificationResult]:
        if obj is None or obj.type != "MESH" or obj.data is None:
            return []

        bm = bmesh.new()
        try:
            bm.from_mesh(obj.data)
            faces = list(bm.faces)
            face_index_lookup = {id(face): face_index for face_index, face in enumerate(faces)}
            results: list[EdgeClassificationResult] = []

            for edge_index, edge in enumerate(bm.edges):
                results.append(self.classify_edge(edge, edge_index, face_index_lookup))

            self._print_diagnostics(results, len(bm.edges))
            return results
        finally:
            bm.free()

    def classify_edge(
        self,
        edge: bmesh.types.BMEdge,
        edge_index: int,
        face_index_lookup: dict[int, int],
    ) -> EdgeClassificationResult:
        linked_faces = list(edge.link_faces)
        if len(linked_faces) == 0:
            return EdgeClassificationResult(
                edge_index=edge_index,
                face_a=None,
                face_b=None,
                dihedral_angle=0.0,
                classification=EdgeType.BOUNDARY,
            )

        if len(linked_faces) == 1:
            face_a = face_index_lookup.get(id(linked_faces[0]))
            return EdgeClassificationResult(
                edge_index=edge_index,
                face_a=face_a,
                face_b=None,
                dihedral_angle=0.0,
                classification=EdgeType.BOUNDARY,
            )

        if len(linked_faces) > 2:
            face_a = face_index_lookup.get(id(linked_faces[0]))
            face_b = face_index_lookup.get(id(linked_faces[1]))
            return EdgeClassificationResult(
                edge_index=edge_index,
                face_a=face_a,
                face_b=face_b,
                dihedral_angle=0.0,
                classification=EdgeType.FEATURE,
            )

        face_a = face_index_lookup.get(id(linked_faces[0]))
        face_b = face_index_lookup.get(id(linked_faces[1]))
        angle = self.calculate_dihedral_angle(linked_faces[0], linked_faces[1])
        angle_degrees = math.degrees(angle)

        if angle_degrees < self.SMOOTH_THRESHOLD_DEGREES:
            classification = EdgeType.SMOOTH
        elif angle_degrees < self.SHARP_THRESHOLD_DEGREES:
            classification = EdgeType.SHARP
        else:
            classification = EdgeType.FEATURE

        return EdgeClassificationResult(
            edge_index=edge_index,
            face_a=face_a,
            face_b=face_b,
            dihedral_angle=angle_degrees,
            classification=classification,
        )

    def calculate_dihedral_angle(
        self,
        face_a: bmesh.types.BMFace,
        face_b: bmesh.types.BMFace,
    ) -> float:
        normal_a = face_a.normal.normalized()
        normal_b = face_b.normal.normalized()
        dot_product = max(-1.0, min(1.0, normal_a.dot(normal_b)))
        return math.acos(dot_product)

    def build_statistics(self, results: list[EdgeClassificationResult]) -> dict[str, float | int]:
        if not results:
            return {
                "total_edges": 0,
                "boundary": 0,
                "smooth": 0,
                "sharp": 0,
                "feature": 0,
                "unknown": 0,
                "average_dihedral_angle": 0.0,
                "maximum_dihedral_angle": 0.0,
                "minimum_dihedral_angle": 0.0,
            }

        classifications = [result.classification for result in results]
        angles = [result.dihedral_angle for result in results]
        return {
            "total_edges": len(results),
            "boundary": classifications.count(EdgeType.BOUNDARY),
            "smooth": classifications.count(EdgeType.SMOOTH),
            "sharp": classifications.count(EdgeType.SHARP),
            "feature": classifications.count(EdgeType.FEATURE),
            "unknown": classifications.count(EdgeType.UNKNOWN),
            "average_dihedral_angle": sum(angles) / len(angles),
            "maximum_dihedral_angle": max(angles),
            "minimum_dihedral_angle": min(angles),
        }

    def _print_diagnostics(self, results: list[EdgeClassificationResult], edge_count: int) -> None:
        statistics = self.build_statistics(results)
        print("Edge Classification")
        print("")
        print("Total Edges:")
        print(statistics["total_edges"])
        print("")
        print("Boundary:")
        print(statistics["boundary"])
        print("")
        print("Smooth:")
        print(statistics["smooth"])
        print("")
        print("Sharp:")
        print(statistics["sharp"])
        print("")
        print("Feature:")
        print(statistics["feature"])
        print("")
        print("Unknown:")
        print(statistics["unknown"])
        print("")
        print("Average Dihedral Angle:")
        print(f"{statistics['average_dihedral_angle']:.2f}")
        print("")
        print("Maximum Dihedral Angle:")
        print(f"{statistics['maximum_dihedral_angle']:.2f}")
        print("")
        print("Minimum Dihedral Angle:")
        print(f"{statistics['minimum_dihedral_angle']:.2f}")

        if edge_count != statistics["total_edges"]:
            print("Edge count mismatch detected during classification")


def classify_edges(obj: bpy.types.Object | None) -> list[EdgeClassificationResult]:
    """Backward-compatible wrapper for edge classification."""
    return EdgeClassifier().classify(obj)
