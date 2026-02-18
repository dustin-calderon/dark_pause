"""
DarkPause - System Tray Icon Generator.

Creates dynamic PIL images for use as system tray icons.
Supports multiple states: blocked, active, warning, paused, focus.
"""

import logging
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

from .config import (
    COLOR_ACTIVE,
    COLOR_BLOCKED,
    COLOR_FOCUS,
    COLOR_PAUSED,
    COLOR_WARNING,
)

logger = logging.getLogger(__name__)

ICON_SIZE: int = 64
"""Size of the generated icon in pixels."""


def create_icon(
    state: str = "blocked",
    text: Optional[str] = None,
) -> Image.Image:
    """
    Create a system tray icon image.

    Args:
        state: One of "blocked", "active", "warning", "paused", "focus".
        text: Optional short text to overlay (e.g., "25").

    Returns:
        Image.Image: A PIL Image suitable for pystray.
    """
    color_map: dict[str, str] = {
        "blocked": COLOR_BLOCKED,
        "active": COLOR_ACTIVE,
        "warning": COLOR_WARNING,
        "paused": COLOR_PAUSED,
        "focus": COLOR_FOCUS,
    }
    bg_color: str = color_map.get(state, COLOR_BLOCKED)

    img: Image.Image = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), (0, 0, 0, 0))
    draw: ImageDraw.ImageDraw = ImageDraw.Draw(img)

    # Draw filled circle
    margin: int = 4
    draw.ellipse(
        [margin, margin, ICON_SIZE - margin, ICON_SIZE - margin],
        fill=bg_color,
    )

    # Draw optional text overlay
    if text:
        try:
            font: ImageFont.FreeTypeFont = ImageFont.truetype("arial.ttf", 20)
        except OSError:
            font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), text, font=font)
        text_width: int = bbox[2] - bbox[0]
        text_height: int = bbox[3] - bbox[1]
        text_x: float = (ICON_SIZE - text_width) / 2
        text_y: float = (ICON_SIZE - text_height) / 2 - 2

        draw.text(
            (text_x, text_y),
            text,
            fill="white",
            font=font,
        )

    return img
