"""
DarkPause - Control Panel (CustomTkinter).

The control panel is the main user-facing window that opens on demand
(via tray menu or Ctrl+Alt+D). It orchestrates four UI sections:

  1. 🌌 Bloquear Pantalla  — Start a blackout session
  2. ⏰ Programar           — Schedule one-time or recurring blackouts
  3. 🌐 Deep Work           — Toggle internet allowlist mode
  4. 📋 Pendiente           — View queued tasks

This module is the orchestrator: it creates sections, manages the
task monitor loop, and handles window lifecycle (show/hide/minimize).
Each section is implemented in its own module under ui/sections/.

This window does NOT own the main loop — it's a Toplevel that
can be opened and closed without killing the application.
"""

import logging
import os
import tkinter as tk
from datetime import datetime
from tkinter import messagebox
from typing import TYPE_CHECKING, Callable, Optional

if TYPE_CHECKING:
    from core.scheduler import ScheduleManager

import customtkinter as ctk

from ui.sections import (
    AllowlistSection,
    BlackoutSection,
    ScheduleSection,
    TaskQueueSection,
    WebBlockSection,
)
from ui.theme import COLOR_DANGER, COLOR_PRIMARY, FONT_SMALL, FONT_SUBTITLE, FONT_TITLE

logger = logging.getLogger(__name__)

# CTk appearance
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")


class ControlPanel(ctk.CTkToplevel):
    """
    DarkPause control panel — orchestrates all UI sections.

    Opened as a Toplevel window — closing it minimizes to the taskbar
    without terminating the application.

    Args:
        master: The parent Tkinter root.
        on_start_blackout: Callback to start a blackout (minutes, locked).
        scheduler: Optional ScheduleManager for recurring schedules.
    """

    def __init__(
        self,
        master: tk.Tk,
        on_start_blackout: Callable[[int, bool], None],
        scheduler: Optional["ScheduleManager"] = None,
    ) -> None:
        super().__init__(master)

        self._on_start_blackout: Callable[[int, bool], None] = on_start_blackout
        self._scheduler: Optional["ScheduleManager"] = scheduler
        self._scheduled_tasks: list[dict] = []
        self._monitor_id: str | None = None
        self._loops_active: bool = False

        # Shared state
        self._lock_var: ctk.BooleanVar = ctk.BooleanVar(value=False)

        # Window config
        self.title("darkpause")
        self.geometry("520x780+100+100")
        self.minsize(520, 600)
        self.resizable(False, True)

        # Icon
        try:
            icon_path: str = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "assets", "icon.ico",
            )
            if os.path.exists(icon_path):
                self.iconbitmap(icon_path)
        except Exception:
            pass

        # Intercept close → minimize to taskbar (don't kill or hide)
        self.protocol("WM_DELETE_WINDOW", self._minimize_to_taskbar)

        # Detect minimize/restore by OS (Win+D, Win+M, taskbar click)
        self.bind("<Map>", self._on_restore)
        self.bind("<Unmap>", self._on_minimize)

        # Force taskbar presence — CTkToplevel with a withdrawn root
        # may be treated as a tool window and not appear in the taskbar.
        self.after(200, lambda: self.wm_attributes("-toolwindow", False))

        self._create_ui()
        self._start_task_monitor()
        self._loops_active = True

    # ─── UI Construction ───

    def _create_ui(self) -> None:
        """Build the control panel UI from section modules."""
        from ui.widgets import CollapsibleFrame

        self._create_header()

        # Footer (packed first with side="bottom" so it stays pinned)
        ctk.CTkLabel(
            self,
            text="⚠️ NO ESCAPE. NO MERCY.",
            font=(FONT_SMALL[0], FONT_SMALL[1], "bold"),
            text_color=COLOR_DANGER,
        ).pack(side="bottom", pady=10)

        # Scrollable container for all sections
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=0, pady=0)

        # § 1 — Screen blackout (expanded by default)
        c1 = CollapsibleFrame(
            scroll,
            title="🌌 Bloquear Pantalla",
            subtitle="Pantalla negra de concentración",
            expanded=True,
        )
        self._blackout = BlackoutSection(
            parent=c1.content,
            lock_var=self._lock_var,
            confirm_lock=self._confirm_lock_mode,
            on_add_tasks=self._add_tasks,
        )

        # § 2 — Web blocking (expanded — primary action)
        c2 = CollapsibleFrame(
            scroll,
            title="🚫 Bloquear Webs",
            subtitle="Estilo Freedom",
            expanded=True,
        )
        self._web_block = WebBlockSection(
            parent=c2.content,
            lock_var=self._lock_var,
        )

        # § 3 — Scheduling (collapsed by default)
        c3 = CollapsibleFrame(
            scroll,
            title="⏰ Programar",
            subtitle="Bloqueos automáticos",
            expanded=False,
        )
        self._schedule = ScheduleSection(
            parent=c3.content,
            lock_var=self._lock_var,
            confirm_lock=self._confirm_lock_mode,
            on_add_tasks=self._add_tasks,
            scheduler=self._scheduler,
        )

        # § 4 — Deep Work (collapsed by default)
        c4 = CollapsibleFrame(
            scroll,
            title="🌐 Deep Work",
            subtitle="Solo webs de trabajo",
            expanded=False,
        )
        self._allowlist = AllowlistSection(parent=c4.content)

        # § 5 — Task queue (collapsed by default)
        c5 = CollapsibleFrame(
            scroll,
            title="📋 Pendiente",
            subtitle="Cola de tareas",
            expanded=False,
        )
        self._task_queue = TaskQueueSection(parent=c5.content)

    def _create_header(self) -> None:
        """Create the app header with title and subtitle."""
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(pady=(25, 20), fill="x", padx=20)

        ctk.CTkLabel(
            header, text="darkpause",
            font=FONT_TITLE, text_color=COLOR_PRIMARY,
        ).pack()
        ctk.CTkLabel(
            header, text="Distraction Freedom Protocol",
            font=FONT_SUBTITLE, text_color="gray",
        ).pack()

    # ─── Shared Logic ───

    def _confirm_lock_mode(self) -> bool:
        """
        Check if Lock Mode is enabled and confirm with the user.

        Returns:
            True if the user confirms (or lock is off), False to cancel.
        """
        if not self._lock_var.get():
            return True
        return messagebox.askyesno(
            "⚠️ Lock Mode",
            "🔒 Lock Mode está activado.\n\n"
            "Una vez iniciado, NO podrás cancelar el blackout.\n"
            "Solo terminará cuando se agote el tiempo.\n\n"
            "¿Estás seguro?",
            icon="warning",
        )

    def _add_tasks(self, tasks: list[dict]) -> None:
        """
        Register new tasks and refresh the queue display.

        Called by section modules when the user creates tasks.

        Args:
            tasks: List of task dicts to add to the queue.
        """
        self._scheduled_tasks.extend(tasks)
        self._task_queue.refresh(self._scheduled_tasks)

    # ─── Task Monitor ───

    def _start_task_monitor(self) -> None:
        """
        Background loop that triggers tasks when their time is reached.

        Uses timestamp comparison (>=) instead of fragile exact
        string matching. Only runs when the panel is visible (unless
        there are active tasks pending).
        """
        now_ts: float = datetime.now().timestamp()
        any_triggered: bool = False

        for task in self._scheduled_tasks:
            if not task["active"]:
                continue
            trigger_ts: float = task.get("trigger_ts", 0)
            if now_ts >= trigger_ts:
                task["active"] = False
                duration: int = task["duration"]
                locked: bool = task.get("locked", False)
                self._on_start_blackout(duration, locked)
                any_triggered = True
                logger.info(f"🌌 Task triggered: {duration}m blackout.")

        if any_triggered:
            self._task_queue.refresh(self._scheduled_tasks)

        # Purge completed tasks
        self._scheduled_tasks = [
            t for t in self._scheduled_tasks if t["active"]
        ]

        # Schedule next check
        self._monitor_id = self.after(1000, self._start_task_monitor)

    # ─── Visibility ───

    def show(self) -> None:
        """Show the control panel window."""
        self.deiconify()
        self.lift()
        self.focus_force()
        self._resume_loops()

    def _minimize_to_taskbar(self) -> None:
        """
        Minimize the panel to the Windows taskbar instead of hiding.

        Unlike withdraw(), iconify() keeps the window visible in the
        taskbar so the user can restore it with a click, and AHK's
        WinExist() can still find the window for Ctrl+Alt+D toggle.
        """
        self._pause_loops()
        self.iconify()

    def _on_restore(self, event: tk.Event = None) -> None:
        """Called when the window is restored/mapped (by OS or user)."""
        if self.state() == "normal" and not self._loops_active:
            self._resume_loops()

    def _on_minimize(self, event: tk.Event = None) -> None:
        """Called when the window is minimized by the OS (Win+D, Win+M)."""
        if self.state() == "iconic":
            self._pause_loops()

    def hide(self) -> None:
        """
        Hide the control panel completely (without destroying it).

        Uses withdraw() — the panel disappears from the taskbar entirely.
        Use _minimize_to_taskbar() if you want it restorable from taskbar.
        """
        self._pause_loops()
        self.withdraw()

    def _resume_loops(self) -> None:
        """Resume the task monitor loop."""
        if self._loops_active:
            return  # Already running — avoid double-start
        self._loops_active = True
        if self._monitor_id is None:
            self._start_task_monitor()

    def _pause_loops(self) -> None:
        """Pause the task monitor to save CPU when not visible."""
        self._loops_active = False
        has_active_tasks: bool = any(
            t["active"] for t in self._scheduled_tasks
        )

        # Only stop monitor if no pending tasks
        if not has_active_tasks and self._monitor_id is not None:
            try:
                self.after_cancel(self._monitor_id)
            except Exception:
                pass
            self._monitor_id = None
