from __future__ import annotations

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


class PanelDetector:
    """Group connected planar faces into manufacturable panels."""

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
            face_lookup = {
                face_index: classification for face_index, classification in enumerate(classifications)
            }
            faces = list(bm.faces)
            face_index_lookup = {id(face): face_index for face_index, face in enumerate(faces)}
            visited: set[int] = set()
            panel_groups: list[list[int]] = []

            for face_index in range(len(faces)):
                if face_index in visited:
                    continue

                classification = face_lookup.get(face_index)
                if classification is None or classification.classification is not FaceType.PLANAR:
                    visited.add(face_index)
                    continue

                queue: deque[int] = deque([face_index])
                component: list[int] = []
                visited.add(face_index)

                while queue:
                    current_index = queue.popleft()
                    component.append(current_index)
                    current_face = faces[current_index]
                    for edge in current_face.edges:
                        for linked_face in edge.link_faces:
                            linked_index = face_index_lookup.get(id(linked_face))
                            if linked_index is None or linked_index in visited:
                                continue
                            linked_classification = face_lookup.get(linked_index)
                            if linked_classification is None:
                                continue
                            if linked_classification.classification is FaceType.PLANAR:
                                visited.add(linked_index)
                                queue.append(linked_index)

                panel_groups.append(component)

            panels = [
                PanelResult(panel_id=panel_id, face_indices=group)
                for panel_id, group in enumerate(panel_groups)
                if group
            ]

            panel_sizes = [len(panel.face_indices) for panel in panels]
            panel_count = len(panels)
            largest_panel_size = max(panel_sizes) if panel_sizes else 0
            smallest_panel_size = min(panel_sizes) if panel_sizes else 0
            average_panel_size = (
                sum(panel_sizes) / panel_count if panel_count else 0.0
            )

            print(f"Panels Created: {panel_count}")
            print(f"Visited Faces: {len(visited)}")
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


def detect_panels(
    obj: bpy.types.Object | None, classifications: list[FaceClassificationResult]
) -> PanelDetectionResult:
    """Backward-compatible wrapper for panel detection."""
    return PanelDetector().detect(obj, classifications)
