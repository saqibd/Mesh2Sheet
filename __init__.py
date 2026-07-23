import bpy

bl_info = {
    "name": "Mesh2Sheet",
    "author": "OpenAI",
    "version": (0, 1, 0),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > Mesh2Sheet",
    "description": "A modular Blender add-on foundation for mesh analysis and future sheet unfolding workflows.",
    "category": "Object",
}

from .constants import ADDON_NAME, PANEL_ID, PANEL_LABEL
from .operators import (
    MESH2SHEET_OT_analyze_mesh,
    MESH2SHEET_OT_build_panel_graph,
    MESH2SHEET_OT_refine_panels,
    MESH2SHEET_OT_visualize_panels,
)
from .panel import MESH2SHEET_PT_main_panel
from .properties import register_properties, unregister_properties

__all__ = [
    "MESH2SHEET_OT_analyze_mesh",
    "MESH2SHEET_OT_build_panel_graph",
    "MESH2SHEET_OT_refine_panels",
    "MESH2SHEET_OT_visualize_panels",
    "MESH2SHEET_PT_main_panel",
]

classes = (
    MESH2SHEET_OT_analyze_mesh,
    MESH2SHEET_OT_refine_panels,
    MESH2SHEET_OT_build_panel_graph,
    MESH2SHEET_OT_visualize_panels,
    MESH2SHEET_PT_main_panel,
)


def register() -> None:
    register_properties()
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister() -> None:
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    unregister_properties()
