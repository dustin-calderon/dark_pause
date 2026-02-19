"""
DarkPause - Schedule Section.

Groups all scheduling functionality under one clear section:
- One-time: "Block today at 16:00 for 60 minutes"
- Recurring: "Mon-Fri 09:00-17:00 every week"
"""

import logging
from datetime import datetime, timedelta
from tkinter import messagebox
from typing import TYPE_CHECKING, Callable, Optional

import customtkinter as ctk

from ui.theme import (
    COLOR_SURFACE,
    COLOR_TEXT_MUTED,
    FONT_BODY,
    FONT_MONO,
    FONT_SMALL,
    PAD_INNER,
)

if TYPE_CHECKING:
    from core.scheduler import ScheduleManager

logger = logging.getLogger(__name__)


class ScheduleSection(ctk.CTkFrame):
    """
    UI section for scheduling blackout sessions.

    Combines one-time scheduled tasks ("at 16:00 for 60 min")
    and recurring weekly schedules into one organized section.

    Args:
        parent: Parent widget to pack into.
        lock_var: Shared BooleanVar for lock mode state.
        confirm_lock: Callback that returns True if lock mode is confirmed.
        on_add_tasks: Callback to register new tasks in the main panel.
        scheduler: Optional ScheduleManager for recurring schedules.
    """

    def __init__(
        self,
        parent: ctk.CTkFrame,
        lock_var: ctk.BooleanVar,
        confirm_lock: Callable[[], bool],
        on_add_tasks: Callable[[list[dict]], None],
        scheduler: Optional["ScheduleManager"] = None,
    ) -> None:
        super().__init__(parent, fg_color="transparent")
        self.pack(fill="x")

        self._lock_var: ctk.BooleanVar = lock_var
        self._confirm_lock: Callable[[], bool] = confirm_lock
        self._on_add_tasks: Callable[[list[dict]], None] = on_add_tasks
        self._scheduler: Optional["ScheduleManager"] = scheduler

        self._build_ui()

    def _build_ui(self) -> None:
        """Construct the schedule section widgets."""
        self._build_one_time()

        if self._scheduler is not None:
            self._build_separator()
            self._build_recurring()

        # Bottom padding
        ctk.CTkFrame(self, fg_color="transparent", height=5).pack()

    # ─── One-Time Schedule ───

    def _build_one_time(self) -> None:
        """Build the one-time schedule sub-section."""
        ctk.CTkLabel(
            self, text="Una vez",
            font=FONT_BODY, text_color="gray",
        ).pack(anchor="w", padx=PAD_INNER, pady=(0, 4))

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=PAD_INNER, pady=(0, 8))

        ctk.CTkLabel(row, text="Hoy a las", font=FONT_SMALL).pack(
            side="left", padx=(0, 4),
        )
        self._hour_entry = ctk.CTkEntry(
            row, placeholder_text="16:00", width=80,
            justify="center", font=FONT_BODY,
        )
        self._hour_entry.pack(side="left", padx=(0, 8))
        self._hour_entry.insert(0, "16:00")

        ctk.CTkLabel(row, text="durante", font=FONT_SMALL).pack(
            side="left", padx=(0, 4),
        )
        self._hour_duration = ctk.CTkEntry(
            row, placeholder_text="60", width=60,
            justify="center", font=FONT_BODY,
        )
        self._hour_duration.pack(side="left", padx=(0, 4))
        self._hour_duration.insert(0, "60")

        ctk.CTkLabel(row, text="min", font=FONT_SMALL).pack(
            side="left", padx=(0, 8),
        )

        ctk.CTkButton(
            row, text="Programar", width=100,
            command=self._add_fixed_task,
            fg_color=COLOR_SURFACE, font=FONT_BODY,
        ).pack(side="right")

    # ─── Recurring Schedules ───

    def _build_separator(self) -> None:
        """Add a visual separator between sub-sections."""
        ctk.CTkFrame(self, height=1, fg_color=COLOR_TEXT_MUTED).pack(
            fill="x", padx=PAD_INNER, pady=8,
        )

    def _build_recurring(self) -> None:
        """Build the recurring weekly schedule sub-section."""
        ctk.CTkLabel(
            self, text="Cada semana",
            font=FONT_BODY, text_color="gray",
        ).pack(anchor="w", padx=PAD_INNER, pady=(0, 4))

        # Day checkboxes
        days_row = ctk.CTkFrame(self, fg_color="transparent")
        days_row.pack(fill="x", padx=PAD_INNER, pady=(0, 5))

        self._day_vars: list[ctk.BooleanVar] = []
        day_labels: list[str] = ["L", "M", "X", "J", "V", "S", "D"]
        for i, label in enumerate(day_labels):
            var = ctk.BooleanVar(value=i < 5)  # Mon-Fri by default
            self._day_vars.append(var)
            ctk.CTkCheckBox(
                days_row, text=label, variable=var,
                width=40, font=FONT_SMALL,
            ).pack(side="left", padx=2)

        # Time range + name
        time_row = ctk.CTkFrame(self, fg_color="transparent")
        time_row.pack(fill="x", padx=PAD_INNER, pady=(0, 5))

        ctk.CTkLabel(time_row, text="De", font=FONT_SMALL).pack(
            side="left", padx=2,
        )
        self._sched_start = ctk.CTkEntry(
            time_row, placeholder_text="09:00", width=70,
            justify="center", font=FONT_BODY,
        )
        self._sched_start.pack(side="left", padx=2)
        self._sched_start.insert(0, "09:00")

        ctk.CTkLabel(time_row, text="a", font=FONT_SMALL).pack(
            side="left", padx=5,
        )
        self._sched_end = ctk.CTkEntry(
            time_row, placeholder_text="17:00", width=70,
            justify="center", font=FONT_BODY,
        )
        self._sched_end.pack(side="left", padx=2)
        self._sched_end.insert(0, "17:00")

        ctk.CTkLabel(time_row, text="Nombre:", font=FONT_SMALL).pack(
            side="left", padx=(10, 2),
        )
        self._sched_name = ctk.CTkEntry(
            time_row, placeholder_text="Work", width=80,
            justify="center", font=FONT_BODY,
        )
        self._sched_name.pack(side="left", padx=2)
        self._sched_name.insert(0, "Work Mode")

        # Add button
        ctk.CTkButton(
            self, text="➕ Añadir",
            command=self._add_recurring,
            fg_color="#fdcb6e", text_color="black",
            width=120, font=FONT_BODY,
        ).pack(pady=(5, 5))

        # Existing schedules list
        self._schedule_frame = ctk.CTkScrollableFrame(
            self, height=50, fg_color=COLOR_SURFACE, corner_radius=8,
        )
        self._schedule_frame.pack(fill="x", padx=PAD_INNER, pady=(0, 10))
        self._refresh_list()

    # ─── One-Time Logic ───

    def _add_fixed_task(self) -> None:
        """
        Schedule a one-time blackout at a specific time today.

        Validates the time format (HH:MM) and duration, confirms lock mode,
        then creates a scheduled task. If the time has already passed today,
        schedules for tomorrow.
        """
        try:
            time_str: str = self._hour_entry.get()
            duration: int = int(self._hour_duration.get())
            parsed: datetime = datetime.strptime(time_str, "%H:%M")
        except (ValueError, TypeError):
            messagebox.showerror("Error", "Formato inválido. Usa HH:MM y minutos.")
            return

        if self._lock_var.get() and not self._confirm_lock():
            return

        now: datetime = datetime.now()
        trigger_dt: datetime = now.replace(
            hour=parsed.hour, minute=parsed.minute, second=0, microsecond=0,
        )
        if trigger_dt < now:
            trigger_dt += timedelta(days=1)

        self._on_add_tasks([{
            "type": "fixed",
            "trigger_ts": trigger_dt.timestamp(),
            "duration": duration,
            "locked": self._lock_var.get(),
            "active": True,
            "label": f"⏰ {time_str} → {duration}m",
        }])
        logger.info(f"⏰ Scheduled: {time_str} for {duration}m")

    # ─── Recurring Logic ───

    def _add_recurring(self) -> None:
        """Add a new recurring weekly schedule from the UI inputs."""
        from core.scheduler import Schedule

        try:
            name: str = self._sched_name.get().strip() or "Schedule"
            start: str = self._sched_start.get().strip()
            end: str = self._sched_end.get().strip()

            # Validate time format
            datetime.strptime(start, "%H:%M")
            datetime.strptime(end, "%H:%M")

            days: list[int] = [
                i for i, var in enumerate(self._day_vars) if var.get()
            ]
            if not days:
                messagebox.showerror("Error", "Selecciona al menos un día.")
                return

            schedule = Schedule(name=name, days=days, start=start, end=end)

            if self._scheduler:
                self._scheduler.add_schedule(schedule)
                self._refresh_list()
                logger.info(f"📅 Schedule '{name}' added: {start}-{end}")
        except ValueError:
            messagebox.showerror("Error", "Formato de hora inválido. Usa HH:MM.")

    def _refresh_list(self) -> None:
        """Refresh the recurring schedule display list."""
        for widget in self._schedule_frame.winfo_children():
            widget.destroy()

        if not self._scheduler or not self._scheduler.schedules:
            ctk.CTkLabel(
                self._schedule_frame,
                text="Sin schedules",
                font=("Segoe UI", 9),
                text_color=COLOR_TEXT_MUTED,
            ).pack(pady=3)
            return

        day_names: list[str] = ["L", "M", "X", "J", "V", "S", "D"]
        for sched in self._scheduler.schedules:
            days_str: str = "".join(
                day_names[d] for d in sched.days if d < len(day_names)
            )
            status: str = "✓" if sched.enabled else "✗"
            ctk.CTkLabel(
                self._schedule_frame,
                text=f"{status} {sched.name} · {days_str} · {sched.start}-{sched.end}",
                font=FONT_MONO,
                text_color="white" if sched.enabled else COLOR_TEXT_MUTED,
                anchor="w",
            ).pack(fill="x", padx=5, pady=1)
