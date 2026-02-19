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
import os
import tkinter as tk

from core import usage_tracker
from core.config import ALL_PLATFORMS
from datetime import datetime, timedelta
from tkinter import messagebox
from typing import TYPE_CHECKING, Callable, Optional

if TYPE_CHECKING:
    from core.scheduler import ScheduleManager

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
        on_start_blackout: Callback to start a blackout session (receives minutes: int, locked: bool).
        scheduler: Optional ScheduleManager for recurring schedule management.
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
        self._monitor_id: str | None = None  # FIX-5: Track monitor after() ID
        self._platform_refresh_id: str | None = None  # Track platform refresh loop
        self._platform_widgets: dict[str, dict] = {}  # Populated by _create_platform_section
        self._loops_active: bool = False  # Guard against double resume

        # Window config
        self.title("darkpause")
        self.geometry("500x850+100+100")
        self.minsize(500, 750)
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
        self.after(200, lambda: self.wm_attributes('-toolwindow', False))

        self._create_ui()
        self._start_task_monitor()
        self._loops_active = True

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

        # ─── Platform Status Section ───
        self._create_platform_section()

        # ─── Schedule Section ───
        self._create_schedule_section()

        # ─── Quick Focus Section ───
        self._create_quick_focus_section()

        # ─── Shortcuts Section ───
        self._create_shortcuts_section()

        # ─── Allowlist Mode Section ───
        self._create_allowlist_section()

        # ─── Recurring Schedules Section ───
        if self._scheduler is not None:
            self._create_recurring_schedule_section()

        # ─── Task Queue ───
        self._create_task_list()

        # Footer
        ctk.CTkLabel(
            self,
            text="⚠️ NO ESCAPE. NO MERCY.",
            font=("Segoe UI", 10, "bold"),
            text_color="#d63031",
        ).pack(side="bottom", pady=15)

    def _create_platform_section(self) -> None:
        """Create the 'Platforms' section showing usage per platform with progress bars."""
        frame = ctk.CTkFrame(self)
        frame.pack(fill="x", padx=20, pady=8)

        ctk.CTkLabel(
            frame, text="🔒 Plataformas",
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor="w", padx=15, pady=(10, 5))

        self._platform_widgets = {}

        for platform in ALL_PLATFORMS:
            row = ctk.CTkFrame(frame, fg_color="transparent")
            row.pack(fill="x", padx=15, pady=(2, 4))

            # Emoji + Name label (left)
            name_label = ctk.CTkLabel(
                row,
                text=f"{platform.icon_emoji} {platform.display_name}",
                font=("Segoe UI", 11),
                width=120,
                anchor="w",
            )
            name_label.pack(side="left")

            # Usage text label (right of name)
            usage_label = ctk.CTkLabel(
                row,
                text="--:-- / --m",
                font=("Consolas", 10),
                text_color="gray",
                width=100,
                anchor="e",
            )
            usage_label.pack(side="right", padx=(5, 0))

            # Progress bar (center, fills available space)
            progress = ctk.CTkProgressBar(
                row,
                height=12,
                corner_radius=6,
                progress_color="#2ECC71",
            )
            progress.pack(side="left", fill="x", expand=True, padx=(10, 10))
            progress.set(0.0)

            self._platform_widgets[platform.id] = {
                "label": usage_label,
                "progress": progress,
                "platform": platform,
            }

        # Bottom padding
        ctk.CTkFrame(frame, fg_color="transparent", height=5).pack()

        # Start refresh loop
        self._refresh_platforms()

    def _refresh_platforms(self) -> None:
        """Update platform usage data every 2 seconds."""
        try:
            for pid, widgets in self._platform_widgets.items():
                platform = widgets["platform"]
                limit_seconds: float = platform.daily_limit_minutes * 60
                used_seconds: float = usage_tracker.get_used_seconds(platform)

                # Calculate progress (0.0 = no usage, 1.0 = limit reached)
                progress_value: float = min(1.0, used_seconds / limit_seconds) if limit_seconds > 0 else 0.0

                # Format text: "MM:SS / Xm"
                used_fmt: str = usage_tracker.get_formatted_used(platform)
                widgets["label"].configure(
                    text=f"{used_fmt} / {platform.daily_limit_minutes}m",
                )

                # Color based on usage percentage
                if progress_value < 0.5:
                    color = "#2ECC71"  # Green
                elif progress_value < 0.8:
                    color = "#F39C12"  # Yellow/Orange
                else:
                    color = "#E74C3C"  # Red

                widgets["progress"].configure(progress_color=color)
                widgets["progress"].set(progress_value)
        except Exception as e:
            logger.warning(f"Platform refresh error: {e}")
        finally:
            # Always reschedule — even if this tick failed
            self._platform_refresh_id = self.after(2000, self._refresh_platforms)

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

        # Lock Mode checkbox
        lock_row = ctk.CTkFrame(frame, fg_color="transparent")
        lock_row.pack(fill="x", padx=10, pady=(0, 10))

        self._lock_var = ctk.BooleanVar(value=False)
        self._lock_checkbox = ctk.CTkCheckBox(
            lock_row,
            text="🔒 Lock Mode (irreversible)",
            variable=self._lock_var,
            font=("Segoe UI", 11),
            text_color="#d63031",
            hover_color="#b71c1c",
            fg_color="#d63031",
        )
        self._lock_checkbox.pack(anchor="w", padx=5)

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

    def _create_allowlist_section(self) -> None:
        """Create the 'Allowlist / Deep Work' toggle section."""
        frame = ctk.CTkFrame(self)
        frame.pack(fill="x", padx=20, pady=8)
        ctk.CTkLabel(
            frame, text="🌐 Deep Work Mode",
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor="w", padx=15, pady=(10, 5))

        ctk.CTkLabel(
            frame,
            text="Bloquea TODO internet excepto dominios esenciales de trabajo.",
            font=("Segoe UI", 10),
            text_color="gray",
        ).pack(anchor="w", padx=15, pady=(0, 5))

        self._allowlist_btn = ctk.CTkButton(
            frame,
            text="🌐 Activar Deep Work",
            command=self._toggle_allowlist,
            fg_color="#6C5CE7",
            width=200,
        )
        self._allowlist_btn.pack(pady=(0, 10))

    def _toggle_allowlist(self) -> None:
        """Toggle Allowlist / Deep Work mode on/off."""
        from core.firewall_manager import (
            enable_allowlist_mode,
            disable_allowlist_mode,
            is_allowlist_active,
        )

        if is_allowlist_active():
            disable_allowlist_mode()
            self._allowlist_btn.configure(
                text="🌐 Activar Deep Work",
                fg_color="#6C5CE7",
            )
            logger.info("🔓 Deep Work mode disabled via panel.")
        else:
            if enable_allowlist_mode():
                self._allowlist_btn.configure(
                    text="🔓 Desactivar Deep Work",
                    fg_color="#d63031",
                )
                logger.info("🌐 Deep Work mode enabled via panel.")
            else:
                messagebox.showerror(
                    "Error",
                    "No se pudo activar el modo Deep Work. Comprueba permisos.",
                )

    def _create_recurring_schedule_section(self) -> None:
        """Create the 'Recurring Schedules' section for weekly auto-blackout."""
        frame = ctk.CTkFrame(self)
        frame.pack(fill="x", padx=20, pady=8)
        ctk.CTkLabel(
            frame, text="⏰ Schedules Recurrentes",
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor="w", padx=15, pady=(10, 5))

        ctk.CTkLabel(
            frame,
            text="Bloqueos automáticos semanales.",
            font=("Segoe UI", 10),
            text_color="gray",
        ).pack(anchor="w", padx=15, pady=(0, 5))

        # Day checkboxes
        days_row = ctk.CTkFrame(frame, fg_color="transparent")
        days_row.pack(fill="x", padx=10, pady=(0, 5))

        self._day_vars: list[ctk.BooleanVar] = []
        day_labels: list[str] = ["L", "M", "X", "J", "V", "S", "D"]
        for i, label in enumerate(day_labels):
            var = ctk.BooleanVar(value=i < 5)  # Mon-Fri checked by default
            self._day_vars.append(var)
            ctk.CTkCheckBox(
                days_row,
                text=label,
                variable=var,
                width=40,
                font=("Segoe UI", 10),
            ).pack(side="left", padx=2)

        # Time entries
        time_row = ctk.CTkFrame(frame, fg_color="transparent")
        time_row.pack(fill="x", padx=10, pady=(0, 5))

        ctk.CTkLabel(time_row, text="De", font=("Segoe UI", 10)).pack(side="left", padx=2)
        self._sched_start = ctk.CTkEntry(
            time_row, placeholder_text="09:00", width=70, justify="center",
        )
        self._sched_start.pack(side="left", padx=2)
        self._sched_start.insert(0, "09:00")

        ctk.CTkLabel(time_row, text="a", font=("Segoe UI", 10)).pack(side="left", padx=5)
        self._sched_end = ctk.CTkEntry(
            time_row, placeholder_text="17:00", width=70, justify="center",
        )
        self._sched_end.pack(side="left", padx=2)
        self._sched_end.insert(0, "17:00")

        # Name entry
        ctk.CTkLabel(time_row, text="Nombre:", font=("Segoe UI", 10)).pack(side="left", padx=(10, 2))
        self._sched_name = ctk.CTkEntry(
            time_row, placeholder_text="Work", width=80, justify="center",
        )
        self._sched_name.pack(side="left", padx=2)
        self._sched_name.insert(0, "Work Mode")

        # Add button
        ctk.CTkButton(
            frame, text="➕ Añadir Schedule",
            command=self._add_recurring_schedule,
            fg_color="#fdcb6e", text_color="black",
            width=160,
        ).pack(pady=(5, 5))

        # Schedule list
        self._schedule_frame = ctk.CTkScrollableFrame(
            frame,
            height=60,
            fg_color="#2d3436",
            corner_radius=8,
        )
        self._schedule_frame.pack(fill="x", padx=10, pady=(0, 10))
        self._refresh_schedule_list()

    def _add_recurring_schedule(self) -> None:
        """Add a new recurring schedule from the UI inputs."""
        from core.scheduler import Schedule

        try:
            name: str = self._sched_name.get().strip() or "Schedule"
            start: str = self._sched_start.get().strip()
            end: str = self._sched_end.get().strip()

            # Validate time format
            datetime.strptime(start, "%H:%M")
            datetime.strptime(end, "%H:%M")

            # Collect selected days
            days: list[int] = [i for i, var in enumerate(self._day_vars) if var.get()]
            if not days:
                messagebox.showerror("Error", "Selecciona al menos un día.")
                return

            schedule = Schedule(
                name=name,
                days=days,
                start=start,
                end=end,
            )

            if self._scheduler:
                self._scheduler.add_schedule(schedule)
                self._refresh_schedule_list()
                logger.info(f"📅 Schedule '{name}' added: {start}-{end}")
        except ValueError:
            messagebox.showerror("Error", "Formato de hora inválido. Usa HH:MM.")

    def _refresh_schedule_list(self) -> None:
        """Refresh the recurring schedule list."""
        for widget in self._schedule_frame.winfo_children():
            widget.destroy()

        if not self._scheduler or not self._scheduler.schedules:
            ctk.CTkLabel(
                self._schedule_frame,
                text="Sin schedules",
                font=("Segoe UI", 9),
                text_color="#636e72",
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
                text=f"{status} {sched.name} | {days_str} | {sched.start}-{sched.end}",
                font=("Consolas", 9),
                text_color="white" if sched.enabled else "#636e72",
                anchor="w",
            ).pack(fill="x", padx=5, pady=1)

    def _create_task_list(self) -> None:
        """Create the task queue display using CTkScrollableFrame."""
        ctk.CTkLabel(
            self, text="Cola de Ejecución:",
            font=("Segoe UI", 11, "bold"), text_color="gray",
        ).pack(anchor="w", padx=25, pady=(15, 0))

        self._task_frame = ctk.CTkScrollableFrame(
            self,
            height=100,
            fg_color="#2d3436",
            corner_radius=8,
        )
        self._task_frame.pack(fill="x", padx=20, pady=5)

    # ─── Task Management ───

    def _confirm_lock_mode(self) -> bool:
        """
        Check if Lock Mode is enabled and confirm with the user.

        Returns:
            bool: True if the user confirms (or lock is off), False to cancel.
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

    def _add_fixed_task(self) -> None:
        """Add a scheduled task at a fixed time."""
        try:
            time_str: str = self._hour_entry.get()
            duration: int = int(self._hour_duration.get())
            # Validate format
            parsed: datetime = datetime.strptime(time_str, "%H:%M")
        except (ValueError, TypeError):
            messagebox.showerror("Error", "Formato inválido. Usa HH:MM y minutos.")
            return

        # Confirm Lock Mode AFTER validating inputs
        if not self._confirm_lock_mode():
            return

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
            "locked": self._lock_var.get(),
            "active": True,
            "label": f"⏰ {time_str}",
        })
        self._update_task_list()

    def _add_timer_task(self) -> None:
        """Add a quick focus task (start in X minutes, run for Y minutes)."""
        try:
            wait: int = int(self._wait_min.get())
            duration: int = int(self._wait_dur.get())
        except (ValueError, TypeError):
            messagebox.showerror("Error", "Introduce números válidos.")
            return

        # Confirm Lock Mode AFTER validating inputs
        if not self._confirm_lock_mode():
            return

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
            "locked": self._lock_var.get(),
            "active": True,
            "label": f"⏳ {trigger_label}",
        })
        self._update_task_list()

    def _add_preset(self, work_minutes: int, break_minutes: int) -> None:
        """
        Add a Pomodoro preset: work session, then automatic break.

        FIX-9: break_minutes is now actually used — schedules a second
        blackout after the work period ends.

        Args:
            work_minutes: Duration of the work (blackout) session.
            break_minutes: Duration of the break after work ends.
        """
        if not self._confirm_lock_mode():
            return
        now: datetime = datetime.now()
        # Work starts immediately
        work_trigger: float = now.timestamp()
        locked: bool = self._lock_var.get()
        self._scheduled_tasks.append({
            "type": "timer",
            "trigger_ts": work_trigger,
            "duration": work_minutes,
            "locked": locked,
            "active": True,
            "label": f"🍅 Work {work_minutes}m",
        })
        # Break starts after work ends
        # NOTE: Break intentionally omits "locked" — breaks should never
        # be irreversible, even if the work session was locked.
        if break_minutes > 0:
            break_trigger: float = (now + timedelta(minutes=work_minutes)).timestamp()
            self._scheduled_tasks.append({
                "type": "timer",
                "trigger_ts": break_trigger,
                "duration": break_minutes,
                "locked": False,
                "active": True,
                "label": f"☕ Break {break_minutes}m",
            })
        self._update_task_list()
        logger.info(f"🍅 Pomodoro {work_minutes}/{break_minutes} scheduled.")

    def _update_task_list(self) -> None:
        """Refresh the task queue display."""
        # Clear existing widgets
        for widget in self._task_frame.winfo_children():
            widget.destroy()

        if not self._scheduled_tasks:
            ctk.CTkLabel(
                self._task_frame,
                text="Sin tareas pendientes",
                font=("Segoe UI", 10),
                text_color="#636e72",
            ).pack(pady=5)
            return

        for task in self._scheduled_tasks:
            label: str = task.get("label", "Task")
            lock_icon: str = " 🔒" if task.get("locked") else ""
            status: str = " ✓" if not task["active"] else ""
            ctk.CTkLabel(
                self._task_frame,
                text=f"{label} → {task['duration']}m{lock_icon}{status}",
                font=("Consolas", 10),
                text_color="white" if task["active"] else "#636e72",
                anchor="w",
            ).pack(fill="x", padx=5, pady=1)

    def _start_task_monitor(self) -> None:
        """
        Background loop that triggers tasks when their time is reached.

        FIX-2: Uses timestamp comparison (>=) instead of fragile exact
        string matching that could miss triggers on CPU spikes.
        FIX-5: Only runs when the panel is visible.
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
            self._update_task_list()

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

        IMPORTANT: This method uses withdraw() — the panel disappears
        from the taskbar entirely. Use _minimize_to_taskbar() instead
        if you want the user to be able to restore it from the taskbar.

        FIX-5: Stops the task monitor loop to save CPU
        when the panel is not visible — BUT only if there are
        no active tasks pending. Otherwise the monitor must keep
        running to trigger scheduled blackouts.
        """
        self._pause_loops()
        self.withdraw()

    def _resume_loops(self) -> None:
        """Resume background loops (task monitor + platform refresh)."""
        if self._loops_active:
            return  # Already running — avoid double-start
        self._loops_active = True
        if self._monitor_id is None:
            self._start_task_monitor()
        if self._platform_refresh_id is None:
            self._refresh_platforms()

    def _pause_loops(self) -> None:
        """Pause background loops to save CPU when not visible."""
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

        # Stop platform refresh when hidden/minimized
        if self._platform_refresh_id is not None:
            try:
                self.after_cancel(self._platform_refresh_id)
            except Exception:
                pass
            self._platform_refresh_id = None
