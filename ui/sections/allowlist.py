"""
DarkPause - Allowlist (Deep Work) Section.

Toggle that blocks ALL internet traffic except a curated allowlist
of work-essential domains (Google Docs, GitHub, StackOverflow, etc.)
using Windows Firewall rules.
"""

import logging
from tkinter import messagebox

import customtkinter as ctk

from ui.theme import (
    COLOR_DANGER,
    COLOR_PRIMARY,
    FONT_BODY,
)

logger = logging.getLogger(__name__)


class AllowlistSection(ctk.CTkFrame):
    """
    UI section for the Deep Work (allowlist) mode toggle.

    When activated, blocks all outbound internet traffic except
    pre-configured work domains via Windows Firewall rules.

    Args:
        parent: Parent widget to pack into.
    """

    def __init__(self, parent: ctk.CTkFrame) -> None:
        super().__init__(parent, fg_color="transparent")
        self.pack(fill="x")
        self._build_ui()

    def _build_ui(self) -> None:
        """Construct the allowlist section widgets."""
        self._btn = ctk.CTkButton(
            self, text="🌐 Activar Deep Work",
            command=self._toggle,
            fg_color=COLOR_PRIMARY, width=200, font=FONT_BODY,
        )
        self._btn.pack(pady=(5, 10))

    def _toggle(self) -> None:
        """Toggle Allowlist / Deep Work mode on/off."""
        from core.firewall_manager import (
            disable_allowlist_mode,
            enable_allowlist_mode,
            is_allowlist_active,
        )

        if is_allowlist_active():
            disable_allowlist_mode()
            self._btn.configure(
                text="🌐 Activar Deep Work",
                fg_color=COLOR_PRIMARY,
            )
            logger.info("🔓 Deep Work mode disabled via panel.")
        else:
            if enable_allowlist_mode():
                self._btn.configure(
                    text="🔓 Desactivar Deep Work",
                    fg_color=COLOR_DANGER,
                )
                logger.info("🌐 Deep Work mode enabled via panel.")
            else:
                messagebox.showerror(
                    "Error",
                    "No se pudo activar el modo Deep Work. Comprueba permisos.",
                )
