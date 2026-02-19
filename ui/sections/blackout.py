"""
DarkPause - Blackout Section.

The primary action section: lets the user start a screen blackout
with duration presets, optional delay, lock mode, and break timer.
Replaces the old Quick Focus + Shortcuts sections with a single,
clear interface.
"""

import logging
from datetime import datetime, timedelta
from typing import Callable

import customtkinter as ctk

from ui.theme import (
    COLOR_DANGER,
    COLOR_PRESET_25,
    COLOR_PRESET_25_DIM,
    COLOR_PRESET_50,
    COLOR_PRESET_50_DIM,
    COLOR_PRIMARY,
    COLOR_PRIMARY_HOVER,
    COLOR_TEXT_MUTED,
    FONT_BODY,
    FONT_SECTION,
    FONT_SMALL,
    PAD_INNER,
    PAD_SECTION_X,
)

logger = logging.getLogger(__name__)


class BlackoutSection(ctk.CTkFrame):
    """
    UI section for starting a screen blackout session.

    Provides duration presets (25m/50m), a custom duration input,
    optional delay, lock mode, and automatic break scheduling.

    Args:
        parent: Parent widget to pack into.
        lock_var: Shared BooleanVar for lock mode state.
        confirm_lock: Callback that returns True if lock mode is confirmed.
        on_add_tasks: Callback to register new tasks in the main panel.
    """

    def __init__(
        self,
        parent: ctk.CTkFrame,
        lock_var: ctk.BooleanVar,
        confirm_lock: Callable[[], bool],
        on_add_tasks: Callable[[list[dict]], None],
    ) -> None:
        super().__init__(parent, fg_color="transparent")
        self.pack(fill="x")

        self._lock_var: ctk.BooleanVar = lock_var
        self._confirm_lock: Callable[[], bool] = confirm_lock
        self._on_add_tasks: Callable[[list[dict]], None] = on_add_tasks
        self._selected_preset: int | None = 25
        self._preset_buttons: dict[int, ctk.CTkButton] = {}

        self._build_ui()

    def _build_ui(self) -> None:
        """Construct the blackout section widgets."""
        self._build_duration_row()
        self._build_options()
        self._build_action_button()

    # ─── Duration Row ───

    def _build_duration_row(self) -> None:
        """Build the duration presets and custom input."""
        ctk.CTkLabel(
            self, text="Duración:",
            font=FONT_BODY, text_color="gray",
        ).pack(anchor="w", padx=PAD_INNER, pady=(0, 4))

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=PAD_INNER, pady=(0, 8))

        # Preset: 25 min
        btn_25 = ctk.CTkButton(
            row, text="25 min",
            command=lambda: self._select_preset(25, 5),
            fg_color=COLOR_PRESET_25, hover_color=COLOR_PRESET_25,
            width=80, height=36, font=FONT_BODY,
        )
        btn_25.pack(side="left", padx=(0, 8))
        self._preset_buttons[25] = btn_25

        # Preset: 50 min
        btn_50 = ctk.CTkButton(
            row, text="50 min",
            command=lambda: self._select_preset(50, 10),
            fg_color=COLOR_PRESET_50_DIM, hover_color=COLOR_PRESET_50,
            width=80, height=36, font=FONT_BODY,
        )
        btn_50.pack(side="left", padx=(0, 12))
        self._preset_buttons[50] = btn_50

        # Custom duration input
        self._duration_entry = ctk.CTkEntry(
            row, width=70, justify="center",
            placeholder_text="min", font=FONT_BODY,
        )
        self._duration_entry.pack(side="left", padx=(0, 4))
        self._duration_entry.insert(0, "25")
        self._duration_entry.bind("<Key>", lambda _: self._deselect_presets())

        ctk.CTkLabel(row, text="min", font=FONT_SMALL).pack(side="left")

    # ─── Options ───

    def _build_options(self) -> None:
        """Build optional checkboxes: delay, lock mode, break."""
        options = ctk.CTkFrame(self, fg_color="transparent")
        options.pack(fill="x", padx=PAD_INNER, pady=(0, 4))

        # Delay option
        delay_row = ctk.CTkFrame(options, fg_color="transparent")
        delay_row.pack(fill="x", pady=2)

        self._delay_enabled = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            delay_row, text="⏱ Empezar en",
            variable=self._delay_enabled, font=FONT_BODY, width=130,
            command=self._toggle_delay,
        ).pack(side="left")

        self._delay_entry = ctk.CTkEntry(
            delay_row, width=50, justify="center",
            font=FONT_BODY, state="disabled",
        )
        self._delay_entry.pack(side="left", padx=(4, 4))
        ctk.CTkLabel(
            delay_row, text="min",
            font=FONT_SMALL, text_color=COLOR_TEXT_MUTED,
        ).pack(side="left")

        # Lock mode
        lock_row = ctk.CTkFrame(options, fg_color="transparent")
        lock_row.pack(fill="x", pady=2)
        ctk.CTkCheckBox(
            lock_row, text="🔒 No se puede cancelar una vez empiece",
            variable=self._lock_var, font=FONT_BODY,
            text_color=COLOR_DANGER, hover_color="#b71c1c",
            fg_color=COLOR_DANGER,
        ).pack(anchor="w")

        # Break (Pomodoro) option
        break_row = ctk.CTkFrame(options, fg_color="transparent")
        break_row.pack(fill="x", pady=2)

        self._break_enabled = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            break_row, text="🍅 Al terminar, descanso de",
            variable=self._break_enabled, font=FONT_BODY,
            command=self._toggle_break,
        ).pack(side="left")

        self._break_entry = ctk.CTkEntry(
            break_row, width=50, justify="center",
            font=FONT_BODY, state="disabled",
        )
        self._break_entry.pack(side="left", padx=(4, 4))
        ctk.CTkLabel(
            break_row, text="min",
            font=FONT_SMALL, text_color=COLOR_TEXT_MUTED,
        ).pack(side="left")

    # ─── Action Button ───

    def _build_action_button(self) -> None:
        """Build the main BLOQUEAR button."""
        ctk.CTkButton(
            self, text="🌌  BLOQUEAR",
            command=self._execute,
            fg_color=COLOR_PRIMARY, hover_color=COLOR_PRIMARY_HOVER,
            height=44, font=("Segoe UI", 16, "bold"), corner_radius=10,
        ).pack(fill="x", padx=20, pady=(8, 14))

    # ─── Preset Logic ───

    def _select_preset(self, duration: int, break_duration: int) -> None:
        """
        Select a duration preset and update UI fields.

        Args:
            duration: Blackout duration in minutes.
            break_duration: Suggested break duration for Pomodoro.
        """
        self._duration_entry.delete(0, "end")
        self._duration_entry.insert(0, str(duration))

        self._break_entry.configure(state="normal")
        self._break_entry.delete(0, "end")
        self._break_entry.insert(0, str(break_duration))
        if not self._break_enabled.get():
            self._break_entry.configure(state="disabled")

        self._selected_preset = duration
        self._update_preset_highlights()

    def _deselect_presets(self) -> None:
        """Clear preset selection when user types a custom duration."""
        self._selected_preset = None
        self._update_preset_highlights()

    def _update_preset_highlights(self) -> None:
        """Update preset button colors based on selection state."""
        colors: dict[int, tuple[str, str]] = {
            25: (COLOR_PRESET_25, COLOR_PRESET_25_DIM),
            50: (COLOR_PRESET_50, COLOR_PRESET_50_DIM),
        }
        for dur, btn in self._preset_buttons.items():
            active, dim = colors[dur]
            btn.configure(fg_color=active if dur == self._selected_preset else dim)

    # ─── Toggle Helpers ───

    def _toggle_delay(self) -> None:
        """Enable/disable delay entry based on checkbox."""
        if self._delay_enabled.get():
            self._delay_entry.configure(state="normal")
            if not self._delay_entry.get():
                self._delay_entry.insert(0, "5")
        else:
            self._delay_entry.delete(0, "end")
            self._delay_entry.configure(state="disabled")

    def _toggle_break(self) -> None:
        """Enable/disable break entry based on checkbox."""
        if self._break_enabled.get():
            self._break_entry.configure(state="normal")
            if not self._break_entry.get():
                self._break_entry.insert(0, "5")
        else:
            self._break_entry.configure(state="disabled")

    # ─── Execute ───

    def _execute(self) -> None:
        """
        Execute the blackout action.

        Validates inputs, confirms lock mode if enabled, then creates
        task(s) via the on_add_tasks callback.
        """
        from tkinter import messagebox

        # Validate duration
        try:
            duration: int = int(self._duration_entry.get())
            if duration <= 0:
                raise ValueError("Duration must be positive")
        except (ValueError, TypeError):
            messagebox.showerror("Error", "Introduce una duración válida en minutos.")
            return

        # Validate delay
        wait: int = 0
        if self._delay_enabled.get():
            try:
                wait = int(self._delay_entry.get())
                if wait < 0:
                    raise ValueError("Delay must be non-negative")
            except (ValueError, TypeError):
                messagebox.showerror("Error", "Introduce un retraso válido en minutos.")
                return

        # Lock mode confirmation (after validation)
        locked: bool = self._lock_var.get()
        if locked and not self._confirm_lock():
            return

        now: datetime = datetime.now()
        trigger_ts: float = (now + timedelta(minutes=wait)).timestamp()
        trigger_label: str = (now + timedelta(minutes=wait)).strftime("%H:%M")

        tasks: list[dict] = []

        # Main blackout task
        label: str = f"🌌 Ahora" if wait == 0 else f"⏳ {trigger_label}"
        tasks.append({
            "type": "timer",
            "trigger_ts": trigger_ts,
            "duration": duration,
            "locked": locked,
            "active": True,
            "label": f"{label} → {duration}m",
        })

        # Optional break task (never locked)
        if self._break_enabled.get():
            try:
                break_dur: int = int(self._break_entry.get())
                if break_dur > 0:
                    break_ts: float = (
                        now + timedelta(minutes=wait + duration)
                    ).timestamp()
                    tasks.append({
                        "type": "timer",
                        "trigger_ts": break_ts,
                        "duration": break_dur,
                        "locked": False,
                        "active": True,
                        "label": f"☕ Descanso → {break_dur}m",
                    })
            except (ValueError, TypeError):
                pass  # Skip invalid break gracefully

        self._on_add_tasks(tasks)
        logger.info(
            f"🌌 Blackout: {duration}m "
            f"{'(locked) ' if locked else ''}"
            f"{'in ' + str(wait) + 'm' if wait > 0 else 'now'}"
        )
