from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import bpy

from .progress import ProgressManager


@dataclass
class Mesh2SheetPipeline:
    """Store cached processing results for the Mesh2Sheet workflow."""

    mesh_analysis: Any = None
    face_classification: Any = None
    edge_classification: Any = None
    panel_detection: Any = None
    panel_refinement: Any = None
    panel_graph: Any = None
    cancelled: bool = False
    progress: ProgressManager | None = None
    timings: dict[str, float] = field(default_factory=dict)

    def clear(self) -> None:
        self.mesh_analysis = None
        self.face_classification = None
        self.edge_classification = None
        self.panel_detection = None
        self.panel_refinement = None
        self.panel_graph = None
        self.cancelled = False
        self.timings = {}

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

    def start_stage(self, context: bpy.types.Context, stage_name: str, total_steps: int = 1) -> ProgressManager:
        if self.progress is None:
            self.progress = ProgressManager(context)
        self.progress.begin(stage_name, total_steps)
        self.progress.set_status(stage_name)
        return self.progress

    def finish_stage(self, stage_name: str, elapsed_seconds: float) -> None:
        self.timings[stage_name] = elapsed_seconds
        if self.progress is not None:
            self.progress.clear_status()
            self.progress.finish()

    def print_summary(self) -> None:
        print("------------------------------------")
        print("Pipeline Summary")
        for stage_name, duration in self.timings.items():
            print(f"{stage_name}\n{duration:.2f} sec")
        total = sum(self.timings.values())
        print(f"Total\n{total:.2f} sec")
        print("------------------------------------")


_pipeline = Mesh2SheetPipeline()


class PipelineManager:
    """Manage the processing pipeline using in-memory module state."""

    @classmethod
    def get(cls, context: bpy.types.Context) -> Mesh2SheetPipeline:
        if _pipeline.progress is None and context is not None:
            _pipeline.progress = ProgressManager(context)
        return _pipeline

    @classmethod
    def reset(cls, context: bpy.types.Context) -> None:
        _pipeline.clear()
        if context is not None:
            _pipeline.progress = ProgressManager(context)
