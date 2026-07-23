from __future__ import annotations

import time
from typing import Optional

import bpy


class ProgressManager:
    """Manage Blender progress UI and console timing for pipeline stages."""

    def __init__(self, context: bpy.types.Context | None = None) -> None:
        self.context = context
        self.task_name: Optional[str] = None
        self.total_steps = 0
        self.current_step = 0
        self.started_at: Optional[float] = None
        self.last_message: Optional[str] = None

    def begin(self, task_name: str, total_steps: int) -> None:
        self.task_name = task_name
        self.total_steps = max(total_steps, 1)
        self.current_step = 0
        self.started_at = time.perf_counter()
        self.last_message = None
        if self.context is not None:
            window_manager = self.context.window_manager
            if hasattr(window_manager, "progress_begin"):
                window_manager.progress_begin(0, self.total_steps)

    def update(self, step: int, message: str) -> None:
        self.current_step = max(step, 0)
        self.last_message = message
        if self.context is not None:
            window_manager = self.context.window_manager
            if hasattr(window_manager, "progress_update"):
                window_manager.progress_update(self.current_step)
        print(f"------------------------------------")
        print(f"{self.task_name or 'Stage'}")
        print(f"Progress {self.current_step}/{self.total_steps}")
        if message:
            print(message)
        if self.started_at is not None:
            elapsed = time.perf_counter() - self.started_at
            print(f"Elapsed {elapsed:.2f} sec")
        print(f"------------------------------------")

    def finish(self) -> None:
        if self.context is not None:
            window_manager = self.context.window_manager
            if hasattr(window_manager, "progress_end"):
                window_manager.progress_end()
        self.current_step = self.total_steps
        self.last_message = None

    def set_status(self, message: str) -> None:
        if self.context is not None:
            self.context.workspace.status_text_set(message)

    def clear_status(self) -> None:
        if self.context is not None:
            self.context.workspace.status_text_set("")
