"""
DarkPause - Control Panel (CustomTkinter).

The control panel is a secondary window that opens on demand
(via tray menu or Ctrl+Alt+D). It provides an interface for:
- Quick Focus: lock screen for X minutes
- Scheduled lock at a specific time
- Pomodoro shortcuts (25/5, 50/10)
- Task queue display

This window does NOT own the main loop — it's a Toplevel that
can be opened and closed without killing the application.
"""

import logging
import tkinter as tk
from datetime import datetime, timedelta
from tkinter import messagebox
from typing import Callable, Optional

import customtkinter as ctk

logger = logging.getLogger(__name__)

# CTk appearance
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")


class ControlPanel(ctk.CTkToplevel):
    """
    DarkPause control panel for managing focus sessions.

    Opened as a Toplevel window — closing it hides the panel
    without terminating the application.

    Args:
        master: The parent Tkinter root.
        on_start_blackout: Callback to start a blackout session (receives minutes: int).
    """

    def __init__(
        self,
        master: tk.Tk,
        on_start_blackout: Callable[[int], None],
    ) -> None:
        super().__init__(master)

        self._on_start_blackout: Callable[[int], None] = on_start_blackout
        self._scheduled_tasks: list[dict] = []
        self._monitor_id: str | None = None  # FIX-5: Track monitor after() ID

        # Window config
        self.title("darkpause")
        self.geometry("500x650+100+100")
        self.minsize(500, 600)
        self.resizable(False, False)

        # Icon
        try:
            import os
            icon_path: str = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "assets", "icon.ico",
            )
            if os.path.exists(icon_path):
                self.iconbitmap(icon_path)
        except Exception:
            pass

        # Intercept close → hide (don't kill)
        self.protocol("WM_DELETE_WINDOW", self.hide)

        self._create_ui()
        self._start_task_monitor()

    def _create_ui(self) -> None:
        """Build the control panel UI."""
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(pady=(25, 15), fill="x", padx=20)

        title_container = ctk.CTkFrame(header, fg_color="transparent")
        title_container.pack(expand=True, fill="x")

        ctk.CTkLabel(
            title_container,
            text="darkpause",
            font=("Segoe UI", 32, "bold"),
            text_color="#6C5CE7",
        ).pack()
        ctk.CTkLabel(
            title_container,
            text="Distraction Freedom Protocol",
            font=("Segoe UI", 12),
            text_color="gray",
        ).pack()

        # ─── Schedule Section ───
        self._create_schedule_section()

        # ─── Quick Focus Section ───
        self._create_quick_focus_section()

        # ─── Shortcuts Section ───
        self._create_shortcuts_section()

        # ─── Task Queue ───
        self._create_task_list()

        # Footer
        ctk.CTkLabel(
            self,
            text="⚠️ NO ESCAPE. NO MERCY.",
            font=("Segoe UI", 10, "bold"),
            text_color="#d63031",
        ).pack(side="bottom", pady=15)

    def _create_schedule_section(self) -> None:
        """Create the 'Schedule' section (block at specific time)."""
        frame = ctk.CTkFrame(self)
        frame.pack(fill="x", padx=20, pady=8)
        ctk.CTkLabel(
            frame, text="📅 Programar Hora",
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor="w", padx=15, pady=(10, 5))

        row = ctk.CTkFrame(frame, fg_color="transparent")
        row.pack(fill="x", padx=10, pady=(0, 10))

        self._hour_entry = ctk.CTkEntry(
            row, placeholder_text="16:00", width=100, justify="center",
        )
        self._hour_entry.pack(side="left", padx=5)
        self._hour_entry.insert(0, "16:00")

        self._hour_duration = ctk.CTkEntry(
            row, placeholder_text="60", width=60, justify="center",
        )
        self._hour_duration.pack(side="left", padx=5)
        self._hour_duration.insert(0, "60")

        ctk.CTkLabel(row, text="min", font=("Segoe UI", 10)).pack(side="left")

        ctk.CTkButton(
            row, text="Programar", width=100,
            command=self._add_fixed_task, fg_color="#2d3436",
        ).pack(side="right", padx=5)

    def _create_quick_focus_section(self) -> None:
        """Create the 'Quick Focus' section (block in X minutes for Y minutes)."""
        frame = ctk.CTkFrame(self)
        frame.pack(fill="x", padx=20, pady=8)
        ctk.CTkLabel(
            frame, text="⏳ Quick Focus",
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor="w", padx=15, pady=(10, 5))

        row = ctk.CTkFrame(frame, fg_color="transparent")
        row.pack(fill="x", padx=10, pady=(0, 10))

        ctk.CTkLabel(row, text="En").pack(side="left", padx=2)
        self._wait_min = ctk.CTkEntry(row, width=50, justify="center")
        self._wait_min.pack(side="left", padx=2)
        self._wait_min.insert(0, "0")

        ctk.CTkLabel(row, text="min, Por").pack(side="left", padx=5)
        self._wait_dur = ctk.CTkEntry(row, width=50, justify="center")
        self._wait_dur.pack(side="left", padx=2)
        self._wait_dur.insert(0, "25")
        ctk.CTkLabel(row, text="min").pack(side="left", padx=2)

        ctk.CTkButton(
            row, text="GO", width=60,
            command=self._add_timer_task,
            fg_color="#00b894", text_color="black",
        ).pack(side="right", padx=5)

    def _create_shortcuts_section(self) -> None:
        """Create Pomodoro shortcut buttons."""
        frame = ctk.CTkFrame(self)
        frame.pack(fill="x", padx=20, pady=8)
        ctk.CTkLabel(
            frame, text="⚡ Shortcuts",
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor="w", padx=15, pady=(10, 5))

        row = ctk.CTkFrame(frame, fg_color="transparent")
        row.pack(fill="x", padx=10, pady=(0, 10))

        ctk.CTkButton(
            row, text="🍅 Pomo 25",
            command=lambda: self._add_preset(25, 5),
            fg_color="#e17055", width=140,
        ).pack(side="left", padx=5, expand=True)

        ctk.CTkButton(
            row, text="🧘 Pomo 50",
            command=lambda: self._add_preset(50, 10),
            fg_color="#0984e3", width=140,
        ).pack(side="left", padx=5, expand=True)

    def _create_task_list(self) -> None:
        """Create the task queue display."""
        ctk.CTkLabel(
            self, text="Cola de Ejecución:",
            font=("Segoe UI", 11, "bold"), text_color="gray",
        ).pack(anchor="w", padx=25, pady=(15, 0))

        self._task_listbox = tk.Listbox(
            self,
            bg="#2d3436", fg="white", borderwidth=0,
            highlightthickness=0, font=("Consolas", 10), height=5,
        )
        self._task_listbox.pack(fill="x", padx=20, pady=5)

    # ─── Task Management ───

    def _add_fixed_task(self) -> None:
        """Add a scheduled task at a fixed time."""
        try:
            time_str: str = self._hour_entry.get()
            duration: int = int(self._hour_duration.get())
            # Validate format
            parsed: datetime = datetime.strptime(time_str, "%H:%M")
            # Build trigger timestamp for today at that time
            now: datetime = datetime.now()
            trigger_dt: datetime = now.replace(
                hour=parsed.hour, minute=parsed.minute, second=0, microsecond=0,
            )
            # If the time already passed today, schedule for tomorrow
            if trigger_dt < now:
                trigger_dt += timedelta(days=1)
            self._scheduled_tasks.append({
                "type": "fixed",
                "trigger_ts": trigger_dt.timestamp(),
                "duration": duration,
                "active": True,
                "label": f"⏰ {time_str}",
            })
            self._update_task_list()
        except (ValueError, TypeError):
            messagebox.showerror("Error", "Formato inválido. Usa HH:MM y minutos.")

    def _add_timer_task(self) -> None:
        """Add a quick focus task (start in X minutes, run for Y minutes)."""
        try:
            wait: int = int(self._wait_min.get())
            duration: int = int(self._wait_dur.get())
            trigger_ts: float = (
                datetime.now() + timedelta(minutes=wait)
            ).timestamp()
            trigger_label: str = (
                datetime.now() + timedelta(minutes=wait)
            ).strftime("%H:%M:%S")
            self._scheduled_tasks.append({
                "type": "timer",
                "trigger_ts": trigger_ts,
                "duration": duration,
                "active": True,
                "label": f"⏳ {trigger_label}",
            })
            self._update_task_list()
        except (ValueError, TypeError):
            messagebox.showerror("Error", "Introduce números válidos.")

    def _add_preset(self, work_minutes: int, break_minutes: int) -> None:
        """
        Add a Pomodoro preset: work session, then automatic break.

        FIX-9: break_minutes is now actually used — schedules a second
        blackout after the work period ends.

        Args:
            work_minutes: Duration of the work (blackout) session.
            break_minutes: Duration of the break after work ends.
        """
        now: datetime = datetime.now()
        # Work starts immediately
        work_trigger: float = now.timestamp()
        self._scheduled_tasks.append({
            "type": "timer",
            "trigger_ts": work_trigger,
            "duration": work_minutes,
            "active": True,
            "label": f"🍅 Work {work_minutes}m",
        })
        # Break starts after work ends
        if break_minutes > 0:
            break_trigger: float = (now + timedelta(minutes=work_minutes)).timestamp()
            self._scheduled_tasks.append({
                "type": "timer",
                "trigger_ts": break_trigger,
                "duration": break_minutes,
                "active": True,
                "label": f"☕ Break {break_minutes}m",
            })
        self._update_task_list()
        logger.info(f"🍅 Pomodoro {work_minutes}/{break_minutes} scheduled.")

    def _update_task_list(self) -> None:
        """Refresh the task queue display."""
        self._task_listbox.delete(0, tk.END)
        for task in self._scheduled_tasks:
            label: str = task.get("label", "Task")
            status: str = "✓" if not task["active"] else ""
            self._task_listbox.insert(
                tk.END,
                f"{label} → {task['duration']}m {status}",
            )

    def _start_task_monitor(self) -> None:
        """
        Background loop that triggers tasks when their time is reached.

        FIX-2: Uses timestamp comparison (>=) instead of fragile exact
        string matching that could miss triggers on CPU spikes.
        FIX-5: Only runs when the panel is visible.
        """
        now_ts: float = datetime.now().timestamp()

        for task in self._scheduled_tasks:
            if not task["active"]:
                continue

            trigger_ts: float = task.get("trigger_ts", 0)
            if now_ts >= trigger_ts:
                task["active"] = False
                duration: int = task["duration"]
                self._on_start_blackout(duration)
                self._update_task_list()
                logger.info(f"🌌 Task triggered: {duration}m blackout.")

        # Purge completed tasks to prevent unbounded list growth
        self._scheduled_tasks = [
            t for t in self._scheduled_tasks if t["active"]
        ]

        # Schedule next check in 1 second
        self._monitor_id = self.after(1000, self._start_task_monitor)

    # ─── Visibility ───

    def show(self) -> None:
        """Show the control panel window."""
        self.deiconify()
        self.lift()
        self.focus_force()
        # FIX-5: Resume task monitor when visible
        if self._monitor_id is None:
            self._start_task_monitor()

    def hide(self) -> None:
        """
        Hide the control panel (without destroying it).

        IMPORTANT: This method MUST use withdraw(), never destroy().
        The task monitor uses self.after() which requires the widget
        to still exist. Destroying the widget would silently kill
        pending task triggers.

        FIX-5: Stops the task monitor loop to save CPU
        when the panel is not visible — BUT only if there are
        no active tasks pending. Otherwise the monitor must keep
        running to trigger scheduled blackouts.
        """
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

        self.withdraw()
