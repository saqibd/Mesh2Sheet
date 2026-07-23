from __future__ import annotations

import colorsys

import bpy
import bmesh

from .panel_detector import PanelDetectionResult


class PanelVisualizer:
    """Apply panel colors to a mesh via a Blender color attribute."""

    def visualize(self, obj: bpy.types.Object | None, panel_result: PanelDetectionResult) -> None:
        if obj is None or obj.type != "MESH" or obj.data is None:
            return

        self.clear_visualization(obj)

        mesh = obj.data
        if not panel_result.panels:
            return

        bm = bmesh.new()
        try:
            bm.from_mesh(mesh)
            bm.verts.index_update()
            bm.edges.index_update()
            bm.faces.index_update()
            bm.verts.ensure_lookup_table()
            bm.edges.ensure_lookup_table()
            bm.faces.ensure_lookup_table()

            color_layer = mesh.color_attributes.get("panel_colors")
            if color_layer is None:
                color_layer = mesh.color_attributes.new(
                    name="panel_colors",
                    type="FLOAT_COLOR",
                    domain="CORNER",
                )

            if not isinstance(color_layer, bpy.types.FloatColorAttribute):
                color_layer = mesh.color_attributes.new(
                    name="panel_colors",
                    type="FLOAT_COLOR",
                    domain="CORNER",
                )

            for panel in panel_result.panels:
                color = self._panel_color(panel.panel_id, len(panel_result.panels))
                rgba_color = (color[0], color[1], color[2], 1.0)
                for face_index in panel.face_indices:
                    face = bm.faces[face_index]
                    for loop in face.loops:
                        color_layer.data[loop.index].color = rgba_color

            bm.to_mesh(mesh)
            mesh.update()
        finally:
            bm.free()

    def clear_visualization(self, obj: bpy.types.Object | None) -> None:
        if obj is None or obj.type != "MESH" or obj.data is None:
            return

        mesh = obj.data
        color_layer = mesh.color_attributes.get("panel_colors")
        if color_layer is None:
            return

        mesh.color_attributes.remove(color_layer)

    @staticmethod
    def _panel_color(panel_id: int, panel_count: int) -> tuple[float, float, float]:
        if panel_count <= 1:
            return (1.0, 1.0, 1.0)

        hue = panel_id / max(panel_count, 1)
        r, g, b = colorsys.hsv_to_rgb(hue, 0.85, 0.95)
        return (r, g, b)
