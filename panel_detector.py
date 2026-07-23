from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass

import bmesh
import bpy

from .face_classifier import FaceClassificationResult, FaceType


@dataclass
class PanelResult:
    panel_id: int
    face_indices: list[int]


@dataclass
class PanelDetectionResult:
    panels: list[PanelResult]
    panel_count: int
    largest_panel_size: int
    smallest_panel_size: int
    average_panel_size: float
    median_panel_size: float = 0.0
    panel_size_histogram: dict[int, int] | None = None


class PanelDetector:
    """Group mesh faces into manufacturing-relevant panels using geometry-aware rules."""

    ANGLE_THRESHOLD_DEGREES = 8.0

    def detect(
        self, obj: bpy.types.Object | None, classifications: list[FaceClassificationResult]
    ) -> PanelDetectionResult:
        print("PanelDetector.detect() entered.")
        if obj is None or obj.type != "MESH" or obj.data is None:
            print("PanelDetector.detect() exiting.")
            return PanelDetectionResult([], 0, 0, 0, 0.0)

        bm = bmesh.new()
        try:
            bm.from_mesh(obj.data)
            faces = list(bm.faces)
            face_lookup = {
                face_index: classification for face_index, classification in enumerate(classifications)
            }
            face_index_lookup = {id(face): face_index for face_index, face in enumerate(faces)}
            visited: set[int] = set()
            panel_groups: list[list[int]] = []

            for face_index in range(len(faces)):
                if face_index in visited:
                    continue

                queue: deque[int] = deque([face_index])
                component: list[int] = []
                visited.add(face_index)

                while queue:
                    current_index = queue.popleft()
                    component.append(current_index)
                    for neighbor_index in self._collect_neighbors(current_index, faces, face_index_lookup):
                        if neighbor_index in visited:
                            continue

                        current_classification = face_lookup.get(current_index)
                        neighbor_classification = face_lookup.get(neighbor_index)
                        if not self.should_merge(current_classification, neighbor_classification):
                            continue

                        visited.add(neighbor_index)
                        queue.append(neighbor_index)

                panel_groups.append(component)

            panels = [
                PanelResult(panel_id=panel_id, face_indices=group)
                for panel_id, group in enumerate(panel_groups)
                if group
            ]

            total_panel_face_assignments = sum(len(panel.face_indices) for panel in panels)
            assigned_face_set: set[int] = set()
            for panel in panels:
                for face_index in panel.face_indices:
                    assigned_face_set.add(face_index)

            panel_sizes = [len(panel.face_indices) for panel in panels]
            panel_count = len(panels)
            largest_panel_size = max(panel_sizes) if panel_sizes else 0
            smallest_panel_size = min(panel_sizes) if panel_sizes else 0
            average_panel_size = sum(panel_sizes) / panel_count if panel_count else 0.0

            print("Panel Segmentation Diagnostics")
            print("")
            print("Angle Threshold:")
            print(f"{self.ANGLE_THRESHOLD_DEGREES:.2f} degrees")
            print("")
            print("Faces Assigned:")
            print(len(assigned_face_set))
            print("")
            print("Panels Created:")
            print(panel_count)
            print("")
            print("Largest Panel:")
            print(largest_panel_size)
            print("")
            print("Smallest Panel:")
            print(smallest_panel_size)
            print("")
            print("Average Panel Size:")
            print(f"{average_panel_size:.2f}")
            print("")
            print(f"Total panel face assignments: {total_panel_face_assignments}")
            print(f"Faces represented in panels: {len(assigned_face_set)}")
            print(f"Unassigned faces: {len(faces) - len(assigned_face_set)}")
            print("PanelDetector.detect() exiting.")
            return PanelDetectionResult(
                panels=panels,
                panel_count=panel_count,
                largest_panel_size=largest_panel_size,
                smallest_panel_size=smallest_panel_size,
                average_panel_size=average_panel_size,
            )
        finally:
            bm.free()
            print("PanelDetector.detect() exiting.")

    @staticmethod
    def compute_face_angle(face_a: FaceClassificationResult | None, face_b: FaceClassificationResult | None) -> float:
        """Calculate the angle between two face normals in radians."""
        if face_a is None or face_b is None:
            return math.pi

        normal_a = face_a.normal
        normal_b = face_b.normal
        if normal_a.length == 0.0 or normal_b.length == 0.0:
            return math.pi

        dot_product = normal_a.normalized().dot(normal_b.normalized())
        dot_product = max(-1.0, min(1.0, dot_product))
        return math.acos(dot_product)

    def should_merge(
        self, face_a: FaceClassificationResult | None, face_b: FaceClassificationResult | None
    ) -> bool:
        """Decide whether two adjacent faces should remain in the same manufacturing panel."""
        if face_a is None or face_b is None:
            return False

        # Unknown faces are intentionally isolated so later sprints can classify them more carefully.
        if face_a.classification is FaceType.UNKNOWN or face_b.classification is FaceType.UNKNOWN:
            return False

        # Boundary faces should not be merged across the cut edge created by the mesh boundary.
        if face_a.classification is FaceType.BOUNDARY or face_b.classification is FaceType.BOUNDARY:
            return False

        angle = self.compute_face_angle(face_a, face_b)
        if angle > math.radians(self.ANGLE_THRESHOLD_DEGREES):
            return False

        # Planar and small-feature regions are usually treated as one manufacturing patch.
        if (
            face_a.classification in {FaceType.PLANAR, FaceType.SMALL_FEATURE}
            and face_b.classification in {FaceType.PLANAR, FaceType.SMALL_FEATURE}
        ):
            return True

        # Curved regions stay together only with other curved regions.
        if face_a.classification is FaceType.CURVED and face_b.classification is FaceType.CURVED:
            return True

        # TODO Feature edge detection
        return False

    @staticmethod
    def _collect_neighbors(
        face_index: int,
        faces: list[bmesh.types.BMFace],
        face_index_lookup: dict[int, int],
    ) -> list[int]:
        """Return breadth-first neighbor face indices for the given face index."""
        current_face = faces[face_index]
        neighbors: list[int] = []
        for edge in current_face.edges:
            for linked_face in edge.link_faces:
                linked_index = face_index_lookup.get(id(linked_face))
                if linked_index is None or linked_index == face_index:
                    continue
                if linked_index not in neighbors:
                    neighbors.append(linked_index)
        return neighbors


def detect_panels(
    obj: bpy.types.Object | None, classifications: list[FaceClassificationResult]
) -> PanelDetectionResult:
    """Backward-compatible wrapper for panel detection."""
    return PanelDetector().detect(obj, classifications)
