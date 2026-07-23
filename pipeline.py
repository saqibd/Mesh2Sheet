from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import bpy


@dataclass
class Mesh2SheetPipeline:
    """Store cached processing results for the Mesh2Sheet workflow."""

    mesh_analysis: Any = None
    face_classification: Any = None
    edge_classification: Any = None
    panel_detection: Any = None
    panel_refinement: Any = None
    panel_graph: Any = None

    def clear(self) -> None:
        self.mesh_analysis = None
        self.face_classification = None
        self.edge_classification = None
        self.panel_detection = None
        self.panel_refinement = None
        self.panel_graph = None

    def clear_from(self, stage_name: str) -> None:
        stage_map = {
            "mesh_analysis": "mesh_analysis",
            "face_classification": "face_classification",
            "edge_classification": "edge_classification",
            "panel_detection": "panel_detection",
            "panel_refinement": "panel_refinement",
            "panel_graph": "panel_graph",
        }
        if stage_name not in stage_map:
            return

        setattr(self, stage_map[stage_name], None)

    def has_mesh_analysis(self) -> bool:
        return self.mesh_analysis is not None

    def has_face_classification(self) -> bool:
        return self.face_classification is not None

    def has_edge_classification(self) -> bool:
        return self.edge_classification is not None

    def has_panel_detection(self) -> bool:
        return self.panel_detection is not None

    def has_panel_refinement(self) -> bool:
        return self.panel_refinement is not None

    def has_panel_graph(self) -> bool:
        return self.panel_graph is not None


_pipeline = Mesh2SheetPipeline()


class PipelineManager:
    """Manage the processing pipeline using in-memory module state."""

    @classmethod
    def get(cls, context: bpy.types.Context) -> Mesh2SheetPipeline:
        return _pipeline

    @classmethod
    def reset(cls, context: bpy.types.Context) -> None:
        _pipeline.clear()
