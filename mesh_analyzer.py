from __future__ import annotations

from typing import Dict

import bpy


def analyze_mesh(obj: bpy.types.Object | None) -> dict:
    """Return a lightweight mesh summary without modifying geometry."""
    if obj is None or obj.type != "MESH" or obj.data is None:
        return {
            "name": "",
            "vertex_count": 0,
            "edge_count": 0,
            "face_count": 0,
        }

    mesh = obj.data
    return {
        "name": obj.name,
        "vertex_count": len(mesh.vertices),
        "edge_count": len(mesh.edges),
        "face_count": len(mesh.polygons),
    }
