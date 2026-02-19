"""
DarkPause - Web Block Section (Freedom-style).

Session-based website blocking: the user picks which platforms
to block, sets a duration, and starts a blocking session.
When the session ends, the platforms are automatically unblocked.

Inspired by the Freedom app's model: select → set time → block.
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk

from core.config import ALL_PLATFORMS, APP_DATA_DIR, Platform
from core.permanent_blocks import (
    PRESETS,
    add_block,
    load_user_blocks,
    remove_block,
)
from ui.theme import (
    COLOR_DANGER,
    COLOR_PRIMARY,
    COLOR_PRIMARY_HOVER,
    COLOR_SURFACE,
    COLOR_TEXT_MUTED,
    FONT_BODY,
    FONT_MONO,
    FONT_SMALL,
    PAD_INNER,
)

logger = logging.getLogger(__name__)

_STATE_FILE: Path = APP_DATA_DIR / "web_block_state.json"


class WebBlockSection(ctk.CTkFrame):
    """
    UI section for Freedom-style session web blocking.

    Lets the user select which platforms to block, set a duration,
    and start a blocking session. Automatically unblocks when
    the session ends.

    Args:
        parent: Parent widget to pack into.
        lock_var: Shared BooleanVar for lock mode state.
    """

    def __init__(
        self,
        parent: ctk.CTkFrame,
        lock_var: ctk.BooleanVar,
    ) -> None:
        super().__init__(parent, fg_color="transparent")
        self.pack(fill="x")

        self._lock_var: ctk.BooleanVar = lock_var
        self._platform_vars: dict[str, ctk.BooleanVar] = {}
        self._session_active: bool = False
        self._session_locked: bool = False
        self._session_end: datetime | None = None
        self._timer_id: str | None = None
        self._blocked_platforms: list[Platform] = []

        self._build_ui()
        self._restore_session()
        self._refresh_status()

    def _build_ui(self) -> None:
        """Construct the web blocking section widgets."""
        self._build_platform_list()
        self._build_duration_row()
        self._build_action_button()
        self._build_status_bar()
        self._build_permanent_blocks()

    def _build_platform_list(self) -> None:
        """Build checkboxes for each configured platform."""
        platforms_frame = ctk.CTkFrame(self, fg_color="transparent")
        platforms_frame.pack(fill="x", padx=PAD_INNER, pady=(0, 5))

        for platform in ALL_PLATFORMS:
            var = ctk.BooleanVar(value=True)
            self._platform_vars[platform.id] = var
            ctk.CTkCheckBox(
                platforms_frame,
                text=f"{platform.icon_emoji} {platform.display_name}",
                variable=var,
                font=FONT_BODY,
            ).pack(anchor="w", pady=2)

    def _build_duration_row(self) -> None:
        """Build the duration input row."""
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=PAD_INNER, pady=(5, 5))

        ctk.CTkLabel(
            row, text="Duración:", font=FONT_BODY, text_color="gray",
        ).pack(side="left", padx=(0, 8))

        # Quick presets
        for mins, label in [(30, "30m"), (60, "1h"), (120, "2h")]:
            ctk.CTkButton(
                row, text=label, width=50, height=30,
                font=FONT_SMALL, fg_color=COLOR_SURFACE,
                command=lambda m=mins: self._set_duration(m),
            ).pack(side="left", padx=2)

        # Custom input
        self._duration_entry = ctk.CTkEntry(
            row, width=60, justify="center",
            placeholder_text="min", font=FONT_BODY,
        )
        self._duration_entry.pack(side="left", padx=(8, 4))
        self._duration_entry.insert(0, "60")

        ctk.CTkLabel(row, text="min", font=FONT_SMALL).pack(side="left")

    def _build_action_button(self) -> None:
        """Build the main block/unblock button."""
        self._action_btn = ctk.CTkButton(
            self, text="🚫  BLOQUEAR WEBS",
            command=self._toggle_session,
            fg_color=COLOR_PRIMARY, hover_color=COLOR_PRIMARY_HOVER,
            height=40, font=("Segoe UI", 14, "bold"), corner_radius=10,
        )
        self._action_btn.pack(fill="x", padx=20, pady=(5, 5))

    def _build_status_bar(self) -> None:
        """Build the session status indicator."""
        self._status_label = ctk.CTkLabel(
            self, text="",
            font=FONT_MONO, text_color=COLOR_TEXT_MUTED,
        )
        self._status_label.pack(pady=(0, 10))

    # ─── Duration Presets ───

    def _set_duration(self, minutes: int) -> None:
        """
        Set the duration entry to a preset value.

        Args:
            minutes: Duration in minutes.
        """
        self._duration_entry.delete(0, "end")
        self._duration_entry.insert(0, str(minutes))

    # ─── Session Toggle ───

    def _toggle_session(self) -> None:
        """Start or stop a web blocking session."""
        if self._session_active:
            self._stop_session()
        else:
            self._start_session()

    def _start_session(self) -> None:
        """
        Start a web blocking session.

        Validates inputs, blocks selected platforms via hosts file,
        and starts a countdown timer to auto-unblock.
        """
        from core import hosts_manager

        # Validate duration
        try:
            duration: int = int(self._duration_entry.get())
            if duration <= 0:
                raise ValueError("Duration must be positive")
        except (ValueError, TypeError):
            messagebox.showerror(
                "Error", "Introduce una duración válida en minutos.",
            )
            return

        # Get selected platforms
        selected: list[Platform] = [
            p for p in ALL_PLATFORMS
            if self._platform_vars.get(p.id, ctk.BooleanVar(value=False)).get()
        ]

        if not selected:
            messagebox.showwarning(
                "Aviso", "Selecciona al menos una web para bloquear.",
            )
            return

        # Lock mode confirmation
        locked: bool = self._lock_var.get()
        if locked:
            confirmed: bool = messagebox.askyesno(
                "⚠️ Lock Mode",
                "🔒 Lock Mode está activado.\n\n"
                "Una vez iniciado, NO podrás desbloquear las webs\n"
                "hasta que se agote el tiempo.\n\n"
                "¿Estás seguro?",
                icon="warning",
            )
            if not confirmed:
                return

        # Block platforms
        blocked_count: int = 0
        for platform in selected:
            if hosts_manager.block_platform(platform):
                blocked_count += 1
                logger.info(
                    f"🚫 Blocked {platform.display_name} for {duration}m"
                )

        if blocked_count == 0:
            messagebox.showerror(
                "Error", "No se pudo bloquear ninguna web. Comprueba permisos.",
            )
            return

        # Start session
        self._session_active = True
        self._session_locked = locked
        self._blocked_platforms = selected
        self._session_end = datetime.now() + timedelta(minutes=duration)

        # Persist for crash recovery
        self._save_state()

        # Update UI
        self._action_btn.configure(
            text="🔓  DESBLOQUEAR" if not locked else "🔒  BLOQUEADO",
            fg_color=COLOR_DANGER,
        )
        if locked:
            self._action_btn.configure(state="disabled")

        # Disable platform checkboxes during session
        for widget in self.winfo_children():
            self._disable_checkboxes_recursive(widget)

        self._duration_entry.configure(state="disabled")

        # Start countdown timer
        self._tick_timer()

        logger.info(
            f"🚫 Web block session started: {blocked_count} platforms, "
            f"{duration}m {'(locked)' if locked else ''}"
        )

    def _stop_session(self, force: bool = False) -> None:
        """
        Stop the current web blocking session and unblock platforms.

        Args:
            force: If True, bypass lock check (used by timer expiry).
        """
        from core import hosts_manager

        # Enforce lock: refuse manual stop if session was locked
        if self._session_locked and not force:
            if self._session_end and datetime.now() < self._session_end:
                return

        # Cancel timer
        if self._timer_id is not None:
            try:
                self.after_cancel(self._timer_id)
            except Exception:
                pass
            self._timer_id = None

        # Unblock platforms
        for platform in self._blocked_platforms:
            try:
                hosts_manager.unblock_platform(platform)
                logger.info(f"✅ Unblocked {platform.display_name}")
            except Exception as e:
                logger.error(f"Failed to unblock {platform.display_name}: {e}")

        # Reset state
        self._session_active = False
        self._session_locked = False
        self._blocked_platforms = []
        self._session_end = None

        # Clear persisted state
        self._clear_state()

        # Restore UI
        self._action_btn.configure(
            text="🚫  BLOQUEAR WEBS",
            fg_color=COLOR_PRIMARY,
            state="normal",
        )
        self._status_label.configure(text="")
        self._duration_entry.configure(state="normal")

        # Re-enable checkboxes
        for widget in self.winfo_children():
            self._enable_checkboxes_recursive(widget)

        logger.info("✅ Web block session ended.")

    # ─── Timer ───

    def _tick_timer(self) -> None:
        """
        Update the countdown display every second.

        Auto-stops the session when time is up.
        """
        if not self._session_active or self._session_end is None:
            return

        now: datetime = datetime.now()
        remaining: timedelta = self._session_end - now

        if remaining.total_seconds() <= 0:
            self._stop_session(force=True)
            return

        # Format remaining time
        total_secs: int = int(remaining.total_seconds())
        hours: int = total_secs // 3600
        minutes: int = (total_secs % 3600) // 60
        seconds: int = total_secs % 60

        if hours > 0:
            time_str: str = f"{hours}h {minutes:02d}m {seconds:02d}s"
        else:
            time_str = f"{minutes:02d}m {seconds:02d}s"

        platforms_str: str = ", ".join(
            p.display_name for p in self._blocked_platforms
        )
        self._status_label.configure(
            text=f"🔴 {platforms_str} → {time_str}",
            text_color=COLOR_DANGER,
        )

        self._timer_id = self.after(1000, self._tick_timer)

    # ─── Status Check ───

    def _refresh_status(self) -> None:
        """Check if any platforms are currently blocked and update UI."""
        from core import hosts_manager

        blocked: list[str] = []
        for platform in ALL_PLATFORMS:
            if hosts_manager.is_blocked(platform):
                blocked.append(platform.icon_emoji)

        if blocked and not self._session_active:
            self._status_label.configure(
                text=f"{'  '.join(blocked)} actualmente bloqueados",
                text_color=COLOR_TEXT_MUTED,
            )

    # ─── Helpers ───

    def _disable_checkboxes_recursive(self, widget: ctk.CTkBaseClass) -> None:
        """Recursively disable all checkboxes within a widget."""
        if isinstance(widget, ctk.CTkCheckBox):
            widget.configure(state="disabled")
        for child in widget.winfo_children():
            self._disable_checkboxes_recursive(child)

    def _enable_checkboxes_recursive(self, widget: ctk.CTkBaseClass) -> None:
        """Recursively enable all checkboxes within a widget."""
        if isinstance(widget, ctk.CTkCheckBox):
            widget.configure(state="normal")
        for child in widget.winfo_children():
            self._enable_checkboxes_recursive(child)

    # ─── Persistence ───

    def _save_state(self) -> None:
        """
        Save session state to disk for crash recovery.

        Writes platform IDs, end time, and lock status to JSON.
        """
        if self._session_end is None:
            return
        try:
            APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
            data: dict = {
                "end_iso": self._session_end.isoformat(),
                "platform_ids": [p.id for p in self._blocked_platforms],
                "locked": self._session_locked,
            }
            _STATE_FILE.write_text(json.dumps(data), encoding="utf-8")
            logger.debug(f"Web block state saved: {data}")
        except Exception as e:
            logger.warning(f"Failed to save web block state: {e}")

    def _clear_state(self) -> None:
        """Remove persisted web block state file."""
        try:
            _STATE_FILE.unlink(missing_ok=True)
        except Exception:
            pass

    def _restore_session(self) -> None:
        """
        Restore a persisted session from a previous crash.

        If the session hasn't expired, resumes the countdown timer.
        If it has expired, auto-unblocks the platforms.
        """
        from core import hosts_manager

        try:
            if not _STATE_FILE.exists():
                return

            raw: str = _STATE_FILE.read_text(encoding="utf-8")
            data: dict = json.loads(raw)

            end_time: datetime = datetime.fromisoformat(data["end_iso"])
            platform_ids: list[str] = data.get("platform_ids", [])
            locked: bool = data.get("locked", False)

            # Resolve platform objects from IDs
            id_to_platform: dict[str, Platform] = {
                p.id: p for p in ALL_PLATFORMS
            }
            platforms: list[Platform] = [
                id_to_platform[pid]
                for pid in platform_ids
                if pid in id_to_platform
            ]

            if not platforms:
                self._clear_state()
                return

            remaining: float = (end_time - datetime.now()).total_seconds()

            if remaining <= 0:
                # Session expired while app was down — unblock now
                for p in platforms:
                    try:
                        hosts_manager.unblock_platform(p)
                    except Exception as e:
                        logger.error(f"Failed to unblock {p.display_name}: {e}")
                self._clear_state()
                logger.info("✅ Recovered expired web block session — unblocked.")
                return

            # Session still active — resume countdown
            self._session_active = True
            self._session_locked = locked
            self._session_end = end_time
            self._blocked_platforms = platforms

            # Update UI to reflect active session
            self._action_btn.configure(
                text="🔓  DESBLOQUEAR" if not locked else "🔒  BLOQUEADO",
                fg_color=COLOR_DANGER,
            )
            if locked:
                self._action_btn.configure(state="disabled")

            for widget in self.winfo_children():
                self._disable_checkboxes_recursive(widget)
            self._duration_entry.configure(state="disabled")

            # Resume timer
            self._tick_timer()
            logger.info(
                f"🔄 Restored web block session: {len(platforms)} platforms, "
                f"{int(remaining // 60)}m remaining {'(locked)' if locked else ''}"
            )

        except Exception as e:
            logger.warning(f"Failed to restore web block session: {e}")
            self._clear_state()

    # ─── Permanent Blocks UI ───

    def _build_permanent_blocks(self) -> None:
        """Build the permanent blocks management sub-section."""
        # Separator
        ctk.CTkFrame(self, height=1, fg_color=COLOR_SURFACE).pack(
            fill="x", padx=10, pady=(15, 5),
        )

        # Header
        ctk.CTkLabel(
            self, text="🔒  Bloqueos permanentes", font=FONT_BODY,
        ).pack(anchor="w", padx=10, pady=(5, 2))

        ctk.CTkLabel(
            self,
            text="Siempre bloqueados. Sin temporizador.",
            font=FONT_SMALL,
            text_color=COLOR_TEXT_MUTED,
        ).pack(anchor="w", padx=10, pady=(0, 5))

        # Scrollable list of active blocks
        self._perm_list_frame = ctk.CTkScrollableFrame(
            self, height=90, fg_color=COLOR_SURFACE, corner_radius=6,
        )
        self._perm_list_frame.pack(fill="x", padx=10, pady=(0, 5))
        self._refresh_permanent_list()

        # Quick-add preset row
        preset_frame = ctk.CTkFrame(self, fg_color="transparent")
        preset_frame.pack(fill="x", padx=10, pady=(0, 5))

        ctk.CTkLabel(
            preset_frame, text="Añadir:", font=FONT_SMALL,
            text_color=COLOR_TEXT_MUTED,
        ).pack(side="left", padx=(0, 5))

        existing_labels: set[str] = {
            b.get("label", "") for b in load_user_blocks()
        }
        for preset in PRESETS:
            label: str = preset["label"]
            domains: list[str] = preset["domains"]
            btn = ctk.CTkButton(
                preset_frame,
                text=label,
                width=70,
                height=24,
                font=FONT_SMALL,
                fg_color=COLOR_SURFACE,
                hover_color=COLOR_PRIMARY_HOVER,
                command=lambda l=label, d=domains: self._add_permanent(l, d),
            )
            btn.pack(side="left", padx=2)

        # Custom domain input row
        custom_frame = ctk.CTkFrame(self, fg_color="transparent")
        custom_frame.pack(fill="x", padx=10, pady=(0, 5))

        self._custom_label_entry = ctk.CTkEntry(
            custom_frame, placeholder_text="Nombre",
            width=80, height=28, font=FONT_SMALL,
        )
        self._custom_label_entry.pack(side="left", padx=(0, 5))

        self._custom_domain_entry = ctk.CTkEntry(
            custom_frame, placeholder_text="dominio.com, otro.com",
            width=170, height=28, font=FONT_SMALL,
        )
        self._custom_domain_entry.pack(side="left", padx=(0, 5), expand=True, fill="x")

        ctk.CTkButton(
            custom_frame,
            text="+ Añadir",
            width=70,
            height=28,
            font=FONT_SMALL,
            fg_color=COLOR_PRIMARY,
            hover_color=COLOR_PRIMARY_HOVER,
            command=self._add_custom_permanent,
        ).pack(side="left")

    def _refresh_permanent_list(self) -> None:
        """Refresh the scrollable list of active permanent blocks."""
        for widget in self._perm_list_frame.winfo_children():
            widget.destroy()

        user_blocks: list[dict] = load_user_blocks()

        if not user_blocks:
            ctk.CTkLabel(
                self._perm_list_frame,
                text="No hay bloqueos permanentes personalizados.",
                font=FONT_SMALL,
                text_color=COLOR_TEXT_MUTED,
            ).pack(anchor="w", padx=5, pady=2)
            return

        for block in user_blocks:
            label: str = block.get("label", "?")
            domains: list[str] = block.get("domains", [])

            row = ctk.CTkFrame(self._perm_list_frame, fg_color="transparent")
            row.pack(fill="x", pady=1)

            ctk.CTkLabel(
                row,
                text=f"🔒 {label}",
                font=FONT_SMALL,
                anchor="w",
            ).pack(side="left", padx=(5, 5))

            ctk.CTkLabel(
                row,
                text=f"({len(domains)} dominios)",
                font=FONT_SMALL,
                text_color=COLOR_TEXT_MUTED,
            ).pack(side="left")

            ctk.CTkButton(
                row,
                text="❌",
                width=28,
                height=22,
                font=FONT_SMALL,
                fg_color=COLOR_DANGER,
                hover_color="#C0392B",
                command=lambda l=label: self._remove_permanent(l),
            ).pack(side="right", padx=5)

    def _add_permanent(self, label: str, domains: list[str]) -> None:
        """
        Add a permanent block and refresh the hosts file.

        Args:
            label: Human-readable name.
            domains: List of domains to block.
        """
        from core import hosts_manager

        # Avoid duplicates
        existing: set[str] = {b.get("label", "") for b in load_user_blocks()}
        if label in existing:
            messagebox.showinfo("Info", f"{label} ya está bloqueado.")
            return

        add_block(label, domains)
        hosts_manager.block_permanent_domains()
        self._refresh_permanent_list()
        logger.info(f"🔒 Permanent block added from UI: {label}")

    def _remove_permanent(self, label: str) -> None:
        """
        Remove a permanent block and refresh the hosts file.

        Args:
            label: The label of the block to remove.
        """
        from core import hosts_manager

        remove_block(label)
        hosts_manager.block_permanent_domains()
        self._refresh_permanent_list()
        logger.info(f"🔓 Permanent block removed from UI: {label}")

    def _add_custom_permanent(self) -> None:
        """Add a custom permanent block from the input fields."""
        label: str = self._custom_label_entry.get().strip()
        raw_domains: str = self._custom_domain_entry.get().strip()

        if not label:
            messagebox.showwarning("Atención", "Introduce un nombre.")
            return
        if not raw_domains:
            messagebox.showwarning("Atención", "Introduce al menos un dominio.")
            return

        domains: list[str] = [
            d.strip() for d in raw_domains.replace(" ", ",").split(",")
            if d.strip()
        ]

        self._add_permanent(label, domains)
        self._custom_label_entry.delete(0, "end")
        self._custom_domain_entry.delete(0, "end")
