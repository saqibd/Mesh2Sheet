from __future__ import annotations

import bpy

from .constants import (
    OPERATOR_ID,
    OPERATOR_LABEL,
    VISUALIZE_OPERATOR_ID,
    VISUALIZE_OPERATOR_LABEL,
)
from .face_classifier import FaceClassifier, FaceType
from .mesh_analyzer import MeshAnalyzer
from .panel_detector import PanelDetector
from .panel_visualizer import PanelVisualizer
from .utils import get_active_mesh_object


class MESH2SHEET_OT_analyze_mesh(bpy.types.Operator):
    """Analyze the active mesh object and report its structural statistics."""

    bl_idname = OPERATOR_ID
    bl_label = OPERATOR_LABEL

    def execute(self, context: bpy.types.Context) -> set[str]:
        obj = get_active_mesh_object(context)
        if obj is None:
            self.report({"ERROR"}, "No active mesh object selected")
            return {"CANCELLED"}

        result = MeshAnalyzer().analyze(obj)
        classifications = FaceClassifier().classify(obj, result)

        print("Mesh Analysis")
        print("")
        print("Vertices:")
        print(result.vertex_count)
        print("")
        print("Edges:")
        print(result.edge_count)
        print("")
        print("Faces:")
        print(result.face_count)
        print("")
        print("Boundary Edge Count:")
        print(result.boundary_edge_count)
        print("")
        print("Non-Manifold Edge Count:")
        print(result.non_manifold_edge_count)
        print("")
        print("Loose Vertex Count:")
        print(result.loose_vertex_count)
        print("")
        print("Bounding Box Width:")
        print(f"{result.bounding_box_width:.6f}")
        print("")
        print("Bounding Box Depth:")
        print(f"{result.bounding_box_depth:.6f}")
        print("")
        print("Bounding Box Height:")
        print(f"{result.bounding_box_height:.6f}")
        print("")
        print("Surface Area:")
        print(f"{result.surface_area:.6f}")
        print("")
        print("Average Face Area:")
        print(f"{result.average_face_area:.6f}")
        print("")
        print("Average Edge Length:")
        print(f"{result.average_edge_length:.6f}")
        print("")
        print("Watertight:")
        print("Yes" if result.is_watertight else "No")

        if result.warnings:
            print("")
            print("Warnings:")
            for warning in result.warnings:
                print(f"- {warning}")

        print("")
        print("Face Classification")
        print("")
        print("Planar:")
        print(sum(1 for item in classifications if item.classification is FaceType.PLANAR))
        print("")
        print("Curved:")
        print(sum(1 for item in classifications if item.classification is FaceType.CURVED))
        print("")
        print("Boundary:")
        print(sum(1 for item in classifications if item.classification is FaceType.BOUNDARY))
        print("")
        print("Small Features:")
        print(sum(1 for item in classifications if item.classification is FaceType.SMALL_FEATURE))
        print("")
        print("Unknown:")
        print(sum(1 for item in classifications if item.classification is FaceType.UNKNOWN))

        total_classified_faces = len(classifications)
        print("")
        print("Total Classified Faces:")
        print(total_classified_faces)

        if total_classified_faces != result.face_count:
            raise RuntimeError(
                f"Face classification count mismatch: expected {result.face_count}, got {total_classified_faces}"
            )

        print("Starting Panel Detection...")
        panel_result = PanelDetector().detect(obj, classifications)
        print("Panel Detection Complete.")
        print(f"Number of panels returned: {len(panel_result.panels)}")
        print("")
        print("Panel Detection")
        print("")
        print("Panels Found:")
        print(panel_result.panel_count)
        print("")
        print("Largest Panel:")
        print(panel_result.largest_panel_size)
        print("")
        print("Smallest Panel:")
        print(panel_result.smallest_panel_size)
        print("")
        print("Average Panel Size:")
        print(f"{panel_result.average_panel_size:.2f}")

        self.report({"INFO"}, f"Analyzed {obj.name}")
        return {"FINISHED"}


class MESH2SHEET_OT_visualize_panels(bpy.types.Operator):
    """Visualize detected panels by assigning a unique face color per panel."""

    bl_idname = VISUALIZE_OPERATOR_ID
    bl_label = VISUALIZE_OPERATOR_LABEL

    def execute(self, context: bpy.types.Context) -> set[str]:
        obj = get_active_mesh_object(context)
        if obj is None:
            self.report({"ERROR"}, "No active mesh object selected")
            return {"CANCELLED"}

        analysis = MeshAnalyzer().analyze(obj)
        classifications = FaceClassifier().classify(obj, analysis)
        panel_result = PanelDetector().detect(obj, classifications)

        PanelVisualizer().visualize(obj, panel_result)

        print("Panel Visualization")
        print("")
        print("Panels Colored:")
        print(panel_result.panel_count)
        print("")
        print("Visualization Complete")

        self.report({"INFO"}, f"Visualized {panel_result.panel_count} panels")
        return {"FINISHED"}
