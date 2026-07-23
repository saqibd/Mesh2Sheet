from __future__ import annotations

import math
from collections import Counter, defaultdict
from typing import Optional

import bmesh
import bpy

from .face_classifier import FaceClassificationResult, FaceType
from .panel_detector import PanelDetectionResult, PanelResult


class PanelRefiner:
    """Refine initial panel segmentation with conservative manufacturing-oriented merges."""

    TINY_PANEL_SIZE = 5
    COPLANAR_ANGLE_THRESHOLD_DEGREES = 5.0

    def refine(
        self,
        panel_result: PanelDetectionResult,
        mesh: bpy.types.Mesh | None,
        classifications: list[FaceClassificationResult] | None = None,
    ) -> PanelDetectionResult:
        if mesh is None:
            return self._build_result([], 0)

        initial_panels = [
            PanelResult(panel_id=index, face_indices=list(panel.face_indices))
            for index, panel in enumerate(panel_result.panels)
            if panel.face_indices
        ]
        initial_panel_count = len(initial_panels)

        if not initial_panels:
            return self._build_result([], 0)

        bm = bmesh.new()
        try:
            bm.from_mesh(mesh)
            face_index_lookup = {id(face): face_index for face_index, face in enumerate(list(bm.faces))}
            panel_sets = [set(panel.face_indices) for panel in initial_panels]

            panel_sets = self.merge_small_panels(panel_sets, bm, face_index_lookup)
            panels_after_tiny_merge = len(panel_sets)

            panel_sets = self.merge_coplanar_panels(panel_sets, bm, face_index_lookup, classifications)
            panels_after_coplanar_merge = len(panel_sets)

            panel_sets = self.cleanup_islands(panel_sets, bm, face_index_lookup)
            panels_after_cleanup = len(panel_sets)

            panel_sets = self._ensure_full_face_coverage(panel_sets, len(bm.faces))
            refined_panels = self._normalize_panels(panel_sets)
            stats = self.compute_panel_statistics(refined_panels)

            faces_reassigned = self._count_faces_reassigned(initial_panels, refined_panels)

            print("Panel Refinement")
            print("")
            print("Initial Panels:")
            print(initial_panel_count)
            print("")
            print("Panels After Tiny Merge:")
            print(panels_after_tiny_merge)
            print("")
            print("Panels After Coplanar Merge:")
            print(panels_after_coplanar_merge)
            print("")
            print("Panels After Cleanup:")
            print(panels_after_cleanup)
            print("")
            print("Largest Panel:")
            print(stats["largest_panel_size"])
            print("")
            print("Smallest Panel:")
            print(stats["smallest_panel_size"])
            print("")
            print("Median Panel Size:")
            print(stats["median_panel_size"])
            print("")
            print("Average Panel Size:")
            print(f"{stats['average_panel_size']:.2f}")
            print("")
            print("Faces Reassigned:")
            print(faces_reassigned)
            print("")
            print("Panel refinement complete")

            return self._build_result(refined_panels, len(bm.faces), stats)
        finally:
            bm.free()

    def merge_small_panels(
        self,
        panels: list[set[int]],
        bm: bmesh.types.BMesh,
        face_index_lookup: dict[int, int],
    ) -> list[set[int]]:
        """Merge panels smaller than the tiny-panel threshold into the best neighboring panel."""
        current_panels = [set(panel_faces) for panel_faces in panels]
        while True:
            tiny_panel_indices = [index for index, panel in enumerate(current_panels) if len(panel) < self.TINY_PANEL_SIZE]
            if not tiny_panel_indices:
                break

            changed = False
            for panel_index in tiny_panel_indices:
                tiny_panel = current_panels[panel_index]
                if not tiny_panel:
                    continue

                best_target_index = self._best_neighbor_for_small_panel(panel_index, current_panels, bm, face_index_lookup)
                if best_target_index is None:
                    continue

                current_panels[best_target_index].update(tiny_panel)
                current_panels[panel_index] = set()
                changed = True

            if not changed:
                break

        return [panel for panel in current_panels if panel]

    def merge_coplanar_panels(
        self,
        panels: list[set[int]],
        bm: bmesh.types.BMesh,
        face_index_lookup: dict[int, int],
        classifications: list[FaceClassificationResult] | None,
    ) -> list[set[int]]:
        """Merge neighboring panels whose average normals are nearly coplanar."""
        current_panels = [set(panel_faces) for panel_faces in panels]
        if len(current_panels) < 2:
            return current_panels

        adjacency = self._build_panel_adjacency(current_panels, bm, face_index_lookup)
        for first_index in range(len(current_panels)):
            for second_index in range(first_index + 1, len(current_panels)):
                if not adjacency[first_index].get(second_index):
                    continue

                first_panel = current_panels[first_index]
                second_panel = current_panels[second_index]
                if not first_panel or not second_panel:
                    continue

                if self._panel_contains_only_curved_faces(first_panel, classifications) or self._panel_contains_only_curved_faces(second_panel, classifications):
                    continue

                normal_a = self._average_panel_normal(first_panel, bm, face_index_lookup)
                normal_b = self._average_panel_normal(second_panel, bm, face_index_lookup)
                if not normal_a or not normal_b:
                    continue

                angle = self._angle_between_normals(normal_a, normal_b)
                if angle < math.radians(self.COPLANAR_ANGLE_THRESHOLD_DEGREES):
                    current_panels[first_index].update(second_panel)
                    current_panels[second_index] = set()

        return [panel for panel in current_panels if panel]

    def cleanup_islands(
        self,
        panels: list[set[int]],
        bm: bmesh.types.BMesh,
        face_index_lookup: dict[int, int],
    ) -> list[set[int]]:
        """Merge tiny panel islands that are completely surrounded by a larger neighboring panel."""
        current_panels = [set(panel_faces) for panel_faces in panels]
        if len(current_panels) < 2:
            return current_panels

        adjacency = self._build_panel_adjacency(current_panels, bm, face_index_lookup)
        for panel_index, panel_faces in enumerate(current_panels):
            if len(panel_faces) < self.TINY_PANEL_SIZE:
                continue

            surrounding_neighbors = [
                neighbor_index
                for neighbor_index, shared_count in adjacency[panel_index].items()
                if shared_count > 0 and len(current_panels[neighbor_index]) > len(panel_faces)
            ]
            if not surrounding_neighbors:
                continue

            dominant_neighbor = max(
                surrounding_neighbors,
                key=lambda neighbor_index: (adjacency[panel_index][neighbor_index], len(current_panels[neighbor_index])),
            )
            current_panels[dominant_neighbor].update(panel_faces)
            current_panels[panel_index] = set()

        return [panel for panel in current_panels if panel]

    def compute_panel_statistics(self, panels: list[PanelResult]) -> dict[str, object]:
        """Compute panel size statistics after refinement."""
        sizes = [len(panel.face_indices) for panel in panels]
        if not sizes:
            return {
                "largest_panel_size": 0,
                "smallest_panel_size": 0,
                "average_panel_size": 0.0,
                "median_panel_size": 0.0,
                "panel_size_histogram": {},
            }

        histogram = Counter(sizes)
        sorted_histogram = {size: histogram[size] for size in sorted(histogram)}
        return {
            "largest_panel_size": max(sizes),
            "smallest_panel_size": min(sizes),
            "average_panel_size": sum(sizes) / len(sizes),
            "median_panel_size": self._median(sizes),
            "panel_size_histogram": sorted_histogram,
        }

    def _build_result(
        self,
        panels: list[PanelResult],
        face_count: int,
        statistics: Optional[dict[str, object]] = None,
    ) -> PanelDetectionResult:
        if statistics is None:
            statistics = self.compute_panel_statistics(panels)

        return PanelDetectionResult(
            panels=panels,
            panel_count=len(panels),
            largest_panel_size=int(statistics["largest_panel_size"]),
            smallest_panel_size=int(statistics["smallest_panel_size"]),
            average_panel_size=float(statistics["average_panel_size"]),
            median_panel_size=float(statistics["median_panel_size"]),
            panel_size_histogram=dict(statistics["panel_size_histogram"]),
        )

    def _ensure_full_face_coverage(self, panels: list[set[int]], total_face_count: int) -> list[set[int]]:
        """Ensure every face is represented exactly once in the final panel sets."""
        covered_faces = set()
        for panel in panels:
            covered_faces.update(panel)

        if len(covered_faces) >= total_face_count:
            return panels

        missing_faces = set(range(total_face_count)) - covered_faces
        for face_index in sorted(missing_faces):
            panels.append({face_index})
        return panels

    def _normalize_panels(self, panel_sets: list[set[int]]) -> list[PanelResult]:
        normalized_panels: list[PanelResult] = []
        for panel_id, panel_faces in enumerate(panel_sets):
            if not panel_faces:
                continue
            normalized_panels.append(
                PanelResult(panel_id=panel_id, face_indices=sorted(panel_faces))
            )
        return normalized_panels

    def _best_neighbor_for_small_panel(
        self,
        panel_index: int,
        panels: list[set[int]],
        bm: bmesh.types.BMesh,
        face_index_lookup: dict[int, int],
    ) -> Optional[int]:
        best_index: Optional[int] = None
        best_score: tuple[int, float, int] | None = None

        for candidate_index, candidate_panel in enumerate(panels):
            if candidate_index == panel_index or not candidate_panel:
                continue
            shared_count = self._shared_edge_count(panel_index, candidate_index, panels, bm, face_index_lookup)
            if shared_count <= 0:
                continue

            average_angle = self._average_panel_angle(panel_index, candidate_index, panels, bm, face_index_lookup)
            score = (-shared_count, average_angle, -len(candidate_panel))
            if best_score is None or score < best_score:
                best_score = score
                best_index = candidate_index

        return best_index

    def _panel_contains_only_curved_faces(
        self,
        panel_faces: set[int],
        classifications: list[FaceClassificationResult] | None,
    ) -> bool:
        if not classifications:
            return False
        if not panel_faces:
            return False
        return all(
            classifications[face_index].classification is FaceType.CURVED for face_index in panel_faces if face_index < len(classifications)
        )

    def _build_panel_adjacency(
        self,
        panels: list[set[int]],
        bm: bmesh.types.BMesh,
        face_index_lookup: dict[int, int],
    ) -> list[dict[int, int]]:
        adjacency: list[dict[int, int]] = [defaultdict(int) for _ in panels]
        face_to_panel: dict[int, int] = {}
        for panel_id, panel_faces in enumerate(panels):
            for face_index in panel_faces:
                face_to_panel[face_index] = panel_id

        for edge in bm.edges:
            if len(edge.link_faces) != 2:
                continue

            face_a = face_index_lookup.get(id(edge.link_faces[0]))
            face_b = face_index_lookup.get(id(edge.link_faces[1]))
            if face_a is None or face_b is None:
                continue

            panel_a = face_to_panel.get(face_a)
            panel_b = face_to_panel.get(face_b)
            if panel_a is None or panel_b is None or panel_a == panel_b:
                continue

            adjacency[panel_a][panel_b] += 1
            adjacency[panel_b][panel_a] += 1

        return adjacency

    def _shared_edge_count(
        self,
        panel_a_index: int,
        panel_b_index: int,
        panels: list[set[int]],
        bm: bmesh.types.BMesh,
        face_index_lookup: dict[int, int],
    ) -> int:
        face_to_panel: dict[int, int] = {}
        for panel_id, panel_faces in enumerate(panels):
            for face_index in panel_faces:
                face_to_panel[face_index] = panel_id

        count = 0
        for edge in bm.edges:
            if len(edge.link_faces) != 2:
                continue
            face_a = face_index_lookup.get(id(edge.link_faces[0]))
            face_b = face_index_lookup.get(id(edge.link_faces[1]))
            if face_a is None or face_b is None:
                continue
            if face_to_panel.get(face_a) == panel_a_index and face_to_panel.get(face_b) == panel_b_index:
                count += 1
            elif face_to_panel.get(face_a) == panel_b_index and face_to_panel.get(face_b) == panel_a_index:
                count += 1
        return count

    def _average_panel_angle(
        self,
        panel_a_index: int,
        panel_b_index: int,
        panels: list[set[int]],
        bm: bmesh.types.BMesh,
        face_index_lookup: dict[int, int],
    ) -> float:
        normal_a = self._average_panel_normal(panels[panel_a_index], bm, face_index_lookup)
        normal_b = self._average_panel_normal(panels[panel_b_index], bm, face_index_lookup)
        if not normal_a or not normal_b:
            return math.pi
        return self._angle_between_normals(normal_a, normal_b)

    def _average_panel_normal(
        self,
        panel_faces: set[int],
        bm: bmesh.types.BMesh,
        face_index_lookup: dict[int, int],
    ) -> Optional[tuple[float, float, float]]:
        faces = list(bm.faces)
        normals: list[tuple[float, float, float]] = []
        for face_index in panel_faces:
            if face_index < 0 or face_index >= len(faces):
                continue
            face = faces[face_index]
            normals.append((face.normal.x, face.normal.y, face.normal.z))

        if not normals:
            return None

        total_x = sum(normal[0] for normal in normals)
        total_y = sum(normal[1] for normal in normals)
        total_z = sum(normal[2] for normal in normals)
        length = math.sqrt(total_x * total_x + total_y * total_y + total_z * total_z)
        if length == 0.0:
            return None
        return (total_x / length, total_y / length, total_z / length)

    @staticmethod
    def _angle_between_normals(normal_a: tuple[float, float, float], normal_b: tuple[float, float, float]) -> float:
        dot_product = normal_a[0] * normal_b[0] + normal_a[1] * normal_b[1] + normal_a[2] * normal_b[2]
        dot_product = max(-1.0, min(1.0, dot_product))
        return math.acos(dot_product)

    @staticmethod
    def _median(values: list[int]) -> float:
        if not values:
            return 0.0
        ordered = sorted(values)
        middle = len(ordered) // 2
        if len(ordered) % 2 == 0:
            return (ordered[middle - 1] + ordered[middle]) / 2.0
        return float(ordered[middle])

    def _count_faces_reassigned(
        self,
        initial_panels: list[PanelResult],
        refined_panels: list[PanelResult],
    ) -> int:
        initial_mapping = {}
        for panel in initial_panels:
            for face_index in panel.face_indices:
                initial_mapping[face_index] = panel.panel_id

        refined_mapping = {}
        for panel in refined_panels:
            for face_index in panel.face_indices:
                refined_mapping[face_index] = panel.panel_id

        return sum(1 for face_index in initial_mapping if initial_mapping.get(face_index) != refined_mapping.get(face_index))
