from __future__ import annotations

import time

import bpy

from .constants import (
    GRAPH_OPERATOR_ID,
    GRAPH_OPERATOR_LABEL,
    OPERATOR_ID,
    OPERATOR_LABEL,
    REFINE_OPERATOR_ID,
    REFINE_OPERATOR_LABEL,
    VISUALIZE_OPERATOR_ID,
    VISUALIZE_OPERATOR_LABEL,
)
from .edge_classifier import EdgeClassifier
from .face_classifier import FaceClassifier, FaceType
from .mesh_analyzer import MeshAnalyzer
from .panel_detector import PanelDetector
from .panel_graph import PanelGraph
from .panel_refiner import PanelRefiner
from .panel_visualizer import PanelVisualizer
from .pipeline import PipelineManager
from .utils import get_active_mesh_object


class MESH2SHEET_OT_analyze_mesh(bpy.types.Operator):
    """Run the core mesh analysis pipeline and cache each stage result."""

    bl_idname = OPERATOR_ID
    bl_label = OPERATOR_LABEL

    def execute(self, context: bpy.types.Context) -> set[str]:
        obj = get_active_mesh_object(context)
        if obj is None:
            self.report({"ERROR"}, "No active mesh object selected")
            return {"CANCELLED"}

        pipeline = PipelineManager.get(context)
        pipeline.clear()

        start = time.perf_counter()
        print("----------------------------")
        print("Running Mesh Analysis")
        result = MeshAnalyzer().analyze(obj)
        pipeline.mesh_analysis = result
        print("Completed Mesh Analysis")
        print(f"Execution Time: {time.perf_counter() - start:.3f} ms")
        print("----------------------------")

        start = time.perf_counter()
        print("Running Face Classification")
        classifications = FaceClassifier().classify(obj, result)
        pipeline.face_classification = classifications
        print("Completed Face Classification")
        print(f"Execution Time: {time.perf_counter() - start:.3f} ms")
        print("----------------------------")

        start = time.perf_counter()
        print("Running Edge Classification")
        edge_classifications = EdgeClassifier().classify(obj)
        pipeline.edge_classification = edge_classifications
        print("Completed Edge Classification")
        print(f"Execution Time: {time.perf_counter() - start:.3f} ms")
        print("----------------------------")

        start = time.perf_counter()
        print("Running Panel Detection")
        panel_result = PanelDetector().detect(obj, classifications)
        pipeline.panel_detection = panel_result
        print("Completed Panel Detection")
        print(f"Execution Time: {time.perf_counter() - start:.3f} ms")
        print("----------------------------")

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
        print("Watertight:")
        print("Yes" if result.is_watertight else "No")

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

        self.report({"INFO"}, f"Analyzed {obj.name}")
        return {"FINISHED"}


class MESH2SHEET_OT_refine_panels(bpy.types.Operator):
    """Refine the cached panel detection result and store it in the pipeline."""

    bl_idname = REFINE_OPERATOR_ID
    bl_label = REFINE_OPERATOR_LABEL

    def execute(self, context: bpy.types.Context) -> set[str]:
        pipeline = PipelineManager.get(context)
        if pipeline.panel_detection is None:
            self.report({"ERROR"}, "Run Analyze Mesh first")
            return {"CANCELLED"}

        obj = get_active_mesh_object(context)
        if obj is None:
            self.report({"ERROR"}, "No active mesh object selected")
            return {"CANCELLED"}

        start = time.perf_counter()
        print("----------------------------")
        print("Running Panel Refinement")
        refined_result = PanelRefiner().refine(pipeline.panel_detection, obj.data, pipeline.face_classification)
        pipeline.panel_refinement = refined_result
        print("Completed Panel Refinement")
        print(f"Execution Time: {time.perf_counter() - start:.3f} ms")
        print("----------------------------")
        print("Panel Refinement Complete")
        return {"FINISHED"}


class MESH2SHEET_OT_build_panel_graph(bpy.types.Operator):
    """Build the panel graph from the refined panels when available."""

    bl_idname = GRAPH_OPERATOR_ID
    bl_label = GRAPH_OPERATOR_LABEL

    def execute(self, context: bpy.types.Context) -> set[str]:
        pipeline = PipelineManager.get(context)
        if pipeline.panel_detection is None:
            self.report({"ERROR"}, "Run Analyze Mesh first")
            return {"CANCELLED"}

        obj = get_active_mesh_object(context)
        if obj is None:
            self.report({"ERROR"}, "No active mesh object selected")
            return {"CANCELLED"}

        start = time.perf_counter()
        print("----------------------------")
        print("Running Panel Graph")
        panel_source = pipeline.panel_refinement or pipeline.panel_detection
        graph_result = PanelGraph().build(obj, panel_source)
        pipeline.panel_graph = graph_result
        print("Completed Panel Graph")
        print(f"Execution Time: {time.perf_counter() - start:.3f} ms")
        print("----------------------------")
        print("Panel Graph Complete")
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

        pipeline = PipelineManager.get(context)
        panel_result = pipeline.panel_detection or PanelDetector().detect(obj, classifications)
        PanelVisualizer().visualize(obj, panel_result)

        print("Panel Visualization")
        print("")
        print("Panels Colored:")
        print(panel_result.panel_count)
        print("")
        print("Visualization Complete")

        self.report({"INFO"}, f"Visualized {panel_result.panel_count} panels")
        return {"FINISHED"}
