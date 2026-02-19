"""
DarkPause - Reusable UI Widgets.

Custom widgets shared across sections, including
the CollapsibleFrame for toggle-able sections.
"""

import customtkinter as ctk

from ui.theme import (
    COLOR_TEXT_MUTED,
    FONT_SECTION,
    FONT_SMALL,
    PAD_INNER,
    PAD_SECTION_X,
)


class CollapsibleFrame(ctk.CTkFrame):
    """
    A frame with a clickable header that toggles content visibility.

    Clicking the header (title + arrow) expands or collapses the
    content area below it, keeping the UI compact.

    Args:
        parent: Parent widget.
        title: Section title displayed in the header.
        subtitle: Optional one-line description under the title.
        expanded: Whether the section starts expanded.
    """

    def __init__(
        self,
        parent: ctk.CTkBaseClass,
        title: str,
        subtitle: str = "",
        expanded: bool = True,
    ) -> None:
        super().__init__(parent)
        self.pack(fill="x", padx=PAD_SECTION_X, pady=(0, 6))

        self._title: str = title
        self._expanded: bool = expanded

        self._build_header(title, subtitle)

        # Content frame — sections pack their widgets inside this
        self._content = ctk.CTkFrame(self, fg_color="transparent")
        if expanded:
            self._content.pack(fill="x")

    @property
    def content(self) -> ctk.CTkFrame:
        """The content frame where child widgets should be packed."""
        return self._content

    def _build_header(self, title: str, subtitle: str) -> None:
        """Build the clickable header with arrow, title, and subtitle."""
        header = ctk.CTkFrame(self, fg_color="transparent", cursor="hand2")
        header.pack(fill="x", padx=PAD_INNER, pady=(10, 4))
        header.bind("<Button-1>", lambda _: self.toggle())

        # Arrow indicator
        arrow_text: str = "▼" if self._expanded else "▶"
        self._arrow = ctk.CTkLabel(
            header, text=arrow_text,
            font=("Segoe UI", 10), text_color=COLOR_TEXT_MUTED,
            width=16,
        )
        self._arrow.pack(side="left", padx=(0, 6))
        self._arrow.bind("<Button-1>", lambda _: self.toggle())

        # Title
        title_label = ctk.CTkLabel(header, text=title, font=FONT_SECTION)
        title_label.pack(side="left")
        title_label.bind("<Button-1>", lambda _: self.toggle())

        # Subtitle (on same row, right-aligned and muted)
        if subtitle:
            sub_label = ctk.CTkLabel(
                header, text=subtitle,
                font=FONT_SMALL, text_color=COLOR_TEXT_MUTED,
            )
            sub_label.pack(side="right", padx=(8, 0))
            sub_label.bind("<Button-1>", lambda _: self.toggle())

    def toggle(self) -> None:
        """Toggle the content frame visibility."""
        if self._expanded:
            self._content.pack_forget()
            self._arrow.configure(text="▶")
        else:
            self._content.pack(fill="x")
            self._arrow.configure(text="▼")
        self._expanded = not self._expanded
