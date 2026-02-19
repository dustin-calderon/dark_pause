"""
DarkPause - Task Queue Section.

Displays pending/completed blackout tasks and provides a monitor
loop that triggers tasks when their scheduled time is reached.
"""

import logging
from datetime import datetime

import customtkinter as ctk

from ui.theme import (
    COLOR_SURFACE,
    COLOR_TEXT_MUTED,
    FONT_MONO,
    FONT_SMALL,
)

logger = logging.getLogger(__name__)


class TaskQueueSection(ctk.CTkFrame):
    """
    UI section showing the pending task queue.

    Displays scheduled blackout tasks with their trigger time,
    duration, and lock status. The actual task monitoring loop
    is managed by the parent ControlPanel.

    Args:
        parent: Parent widget to pack into.
    """

    def __init__(self, parent: ctk.CTkFrame) -> None:
        super().__init__(parent, fg_color="transparent")
        self.pack(fill="x")
        self._build_ui()

    def _build_ui(self) -> None:
        """Construct the task queue display."""
        self._list_frame = ctk.CTkScrollableFrame(
            self, height=80, fg_color=COLOR_SURFACE, corner_radius=8,
        )
        self._list_frame.pack(fill="x", padx=5, pady=5)

        self._show_empty()

    def _show_empty(self) -> None:
        """Show placeholder text when no tasks are pending."""
        ctk.CTkLabel(
            self._list_frame,
            text="Sin tareas pendientes",
            font=FONT_SMALL,
            text_color=COLOR_TEXT_MUTED,
        ).pack(pady=5)

    def refresh(self, tasks: list[dict]) -> None:
        """
        Refresh the task queue display with current tasks.

        Args:
            tasks: List of task dictionaries with keys:
                   label, duration, locked, active.
        """
        for widget in self._list_frame.winfo_children():
            widget.destroy()

        active_tasks: list[dict] = [t for t in tasks if t.get("active")]

        if not active_tasks:
            self._show_empty()
            return

        for task in active_tasks:
            label: str = task.get("label", "Task")
            lock_icon: str = " 🔒" if task.get("locked") else ""
            ctk.CTkLabel(
                self._list_frame,
                text=f"{label}{lock_icon}",
                font=FONT_MONO,
                text_color="white",
                anchor="w",
            ).pack(fill="x", padx=5, pady=1)
