from __future__ import annotations

import bpy


class Mesh2SheetSettings(bpy.types.PropertyGroup):
    """Placeholder property group for future add-on settings."""

    pass


classes = (Mesh2SheetSettings,)


def register_properties() -> None:
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister_properties() -> None:
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
