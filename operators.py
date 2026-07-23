from __future__ import annotations

import bpy

from .constants import OPERATOR_ID, OPERATOR_LABEL
from .mesh_analyzer import analyze_mesh
from .utils import get_active_mesh_object


class MESH2SHEET_OT_analyze_mesh(bpy.types.Operator):
    """Analyze the active mesh object and report its basic statistics."""

    bl_idname = OPERATOR_ID
    bl_label = OPERATOR_LABEL

    def execute(self, context: bpy.types.Context) -> set[str]:
        obj = get_active_mesh_object(context)
        if obj is None:
            self.report({"ERROR"}, "No active mesh object selected")
            return {"CANCELLED"}

        result = analyze_mesh(obj)
        print(f"Object Name: {result['name']}")
        print(f"Vertex Count: {result['vertex_count']}")
        print(f"Edge Count: {result['edge_count']}")
        print(f"Face Count: {result['face_count']}")
        self.report({"INFO"}, f"Analyzed {result['name']}")
        return {"FINISHED"}
