from __future__ import annotations

import bpy

from .constants import PANEL_ID, PANEL_LABEL


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

        box.operator("mesh2sheet.analyze_mesh")
