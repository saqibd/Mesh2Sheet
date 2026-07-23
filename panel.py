from __future__ import annotations

import bpy

from .constants import PANEL_ID, PANEL_LABEL
from .pipeline import PipelineManager


class MESH2SHEET_PT_main_panel(bpy.types.Panel):
    """Single sidebar panel for the Mesh2Sheet add-on."""

    bl_idname = PANEL_ID
    bl_label = PANEL_LABEL
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Mesh2Sheet"

    def draw(self, context: bpy.types.Context) -> None:
        layout = self.layout
        box = layout.box()
        box.label(text="Selected Object:")

        obj = context.active_object
        if obj is None:
            box.label(text="None")
        else:
            box.label(text=obj.name)

        analysis_box = box.box()
        analysis_box.label(text="Analysis")
        analysis_row = analysis_box.row()
        analysis_row.operator("mesh2sheet.analyze_mesh")

        pipeline = PipelineManager.get(context)
        has_panel_detection = pipeline.has_panel_detection()
        has_panel_refinement = pipeline.has_panel_refinement()

        refine_row = analysis_box.row()
        refine_row.enabled = has_panel_detection
        refine_row.operator("mesh2sheet.refine_panels")

        graph_row = analysis_box.row()
        graph_row.enabled = has_panel_detection or has_panel_refinement
        graph_row.operator("mesh2sheet.build_panel_graph")

        visualize_row = analysis_box.row()
        visualize_row.enabled = has_panel_detection
        visualize_row.operator("mesh2sheet.visualize_panels")

        future_box = box.box()
        future_box.label(text="Future")
        unfold_row = future_box.row()
        unfold_row.enabled = False
        unfold_row.label(text="Unfold")

        optimize_row = future_box.row()
        optimize_row.enabled = False
        optimize_row.label(text="Optimize")

        export_row = future_box.row()
        export_row.enabled = False
        export_row.label(text="Export")
