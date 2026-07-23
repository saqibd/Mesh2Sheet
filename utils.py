from __future__ import annotations

from typing import Any

import bpy


def get_active_mesh_object(context: bpy.types.Context) -> bpy.types.Object | None:
    """Return the active mesh object when available."""
    if context is None:
        return None

    obj = context.active_object
    if obj is None or obj.type != "MESH":
        return None
    return obj


def format_object_summary(obj: bpy.types.Object | None) -> str:
    """Return a simple text summary for reporting."""
    if obj is None:
        return "No active mesh object"

    mesh = obj.data
    if mesh is None:
        return obj.name

    return (
        f"{obj.name} | verts={len(mesh.vertices)} | "
        f"edges={len(mesh.edges)} | faces={len(mesh.polygons)}"
    )
