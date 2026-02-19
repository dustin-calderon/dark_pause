"""
DarkPause - Configuration Constants.

Centralized configuration for the unified digital discipline app.
Includes: platform definitions, permanent block domains, global settings,
UI colors, and system paths.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path


# ─────────────────────────────────────────────
# Platform Definition
# ─────────────────────────────────────────────
@dataclass(frozen=True)
class Platform:
    """
    Configuration for a single platform to limit.

    Attributes:
        id: Unique identifier (e.g., "instagram", "youtube").
        display_name: Human-readable name for UI.
        daily_limit_minutes: Max daily usage in minutes.
        domains: List of domains to block via hosts file.
        process_names: List of Windows process names to kill.
        marker_tag: Unique tag used in hosts file markers.
        icon_emoji: Emoji for UI display.
    """
    id: str
    display_name: str
    daily_limit_minutes: int
    domains: list[str] = field(default_factory=list)
    process_names: list[str] = field(default_factory=list)
    marker_tag: str = ""
    icon_emoji: str = "🚫"

    @property
    def marker_start(self) -> str:
        """Start marker for this platform's block in the hosts file."""
        return f"# >>> DARKPAUSE-{self.marker_tag}-START <<<"

    @property
    def marker_end(self) -> str:
        """End marker for this platform's block in the hosts file."""
        return f"# >>> DARKPAUSE-{self.marker_tag}-END <<<"

    @property
    def usage_file_name(self) -> str:
        """Filename for this platform's usage data."""
        return f"usage_{self.id}.json"


# ─────────────────────────────────────────────
# Platform Definitions
# ─────────────────────────────────────────────
INSTAGRAM = Platform(
    id="instagram",
    display_name="Instagram",
    daily_limit_minutes=10,
    domains=[
        "instagram.com",
        "www.instagram.com",
        "api.instagram.com",
        "i.instagram.com",
        "graph.instagram.com",
        "l.instagram.com",
        "static.cdninstagram.com",
        "scontent.cdninstagram.com",
        "edge-chat.instagram.com",
        "scontent-mad1-1.cdninstagram.com",
        "scontent-mad2-1.cdninstagram.com",
    ],
    process_names=[
        "Instagram.exe",
        "InstagramApp.exe",
    ],
    marker_tag="INSTAGRAM",
    icon_emoji="📸",
)

YOUTUBE = Platform(
    id="youtube",
    display_name="YouTube",
    daily_limit_minutes=60,
    domains=[
        "youtube.com",
        "www.youtube.com",
        "m.youtube.com",
        "youtu.be",
        "youtube-nocookie.com",
        "www.youtube-nocookie.com",
        "youtubei.googleapis.com",
        "yt3.ggpht.com",
        "yt3.googleusercontent.com",
        "i.ytimg.com",
        "s.ytimg.com",
    ],
    process_names=[],
    marker_tag="YOUTUBE",
    icon_emoji="▶️",
)

ALL_PLATFORMS: list[Platform] = [INSTAGRAM, YOUTUBE]
"""List of all platforms managed by DarkPause."""


def get_platform_by_id(platform_id: str) -> Platform | None:
    """
    Look up a platform by its unique ID.

    Args:
        platform_id: The platform identifier (e.g., "instagram").

    Returns:
        Platform | None: The matching Platform, or None if not found.
    """
    for platform in ALL_PLATFORMS:
        if platform.id == platform_id:
            return platform
    return None


# ─────────────────────────────────────────────
# Global Settings
# ─────────────────────────────────────────────
RESET_HOUR: int = 4
"""Hour of the day (0-23) when all daily usage counters reset. Default: 4 AM."""

WARNING_STEPS: list[int] = [5, 1]
"""Minutes remaining at which to send warning notifications (descending)."""

WARNING_THRESHOLD_MINUTES: int = max(WARNING_STEPS)
"""Derived: earliest warning threshold (for tray icon state)."""

REDIRECT_IP: str = "127.0.0.1"
"""IP address to redirect blocked domains to."""

TIMER_TICK_SECONDS: int = 1
"""How often the timer updates (in seconds)."""

# ─────────────────────────────────────────────
# Windows Hosts File
# ─────────────────────────────────────────────
HOSTS_FILE_PATH: Path = Path(r"C:\Windows\System32\drivers\etc\hosts")
"""Path to the Windows hosts file."""

# ─────────────────────────────────────────────
# Storage
# ─────────────────────────────────────────────
_appdata_base: str = os.environ.get("APPDATA", "") or os.path.expanduser("~")
APP_DATA_DIR: Path = Path(_appdata_base) / "DarkPause"
"""Application data directory for persistent storage."""

# ─────────────────────────────────────────────
# UI
# ─────────────────────────────────────────────
APP_NAME: str = "DarkPause 🌌"
"""Display name of the application."""

MAX_TOOLTIP_LENGTH: int = 127
"""Windows system tray tooltip max characters."""

# ─────────────────────────────────────────────
# Single Instance
# ─────────────────────────────────────────────
SINGLE_INSTANCE_PORT: int = 45678
"""TCP port used to ensure only one instance runs at a time."""

# ─────────────────────────────────────────────
# Permanent Blocks (always blocked, no timer)
# ─────────────────────────────────────────────
PERMANENT_BLOCK_TAG: str = "PERMANENT"
"""Marker tag for permanent blocks in hosts file."""

PERMANENT_BLOCK_DOMAINS: list[str] = [
    # Social media (default blocks)
    "instagram.com", "www.instagram.com",
    "api.instagram.com", "i.instagram.com",
    "graph.instagram.com", "l.instagram.com",
    "static.cdninstagram.com", "scontent.cdninstagram.com",
    "edge-chat.instagram.com",
    "youtube.com", "www.youtube.com",
    "m.youtube.com", "youtu.be",
    "youtube-nocookie.com", "www.youtube-nocookie.com",
    "youtubei.googleapis.com",
    "yt3.ggpht.com", "yt3.googleusercontent.com",
    "i.ytimg.com", "s.ytimg.com",
    # Adult content — Major sites
    "pornhub.com", "www.pornhub.com",
    "xvideos.com", "www.xvideos.com",
    "xnxx.com", "www.xnxx.com",
    "xhamster.com", "www.xhamster.com",
    "redtube.com", "www.redtube.com",
    "youporn.com", "www.youporn.com",
    "tube8.com", "www.tube8.com",
    "spankbang.com", "www.spankbang.com",
    "beeg.com", "www.beeg.com",
    "eporner.com", "www.eporner.com",
    "hqporner.com", "www.hqporner.com",
    "tnaflix.com", "www.tnaflix.com",
    "drtuber.com", "www.drtuber.com",
    "motherless.com", "www.motherless.com",
    "ixxx.com", "www.ixxx.com",
    "thumbzilla.com", "www.thumbzilla.com",
    "porn.com", "www.porn.com",
    "4tube.com", "www.4tube.com",
    "nuvid.com", "www.nuvid.com",
    "porntrex.com", "www.porntrex.com",
    "fuq.com", "www.fuq.com",
    "fapello.com", "www.fapello.com",
    # Live/cam sites
    "chaturbate.com", "www.chaturbate.com",
    "stripchat.com", "www.stripchat.com",
    "bongacams.com", "www.bongacams.com",
    "cam4.com", "www.cam4.com",
    "myfreecams.com", "www.myfreecams.com",
    "camsoda.com", "www.camsoda.com",
    "livejasmin.com", "www.livejasmin.com",
    # OnlyFans / content platforms
    "onlyfans.com", "www.onlyfans.com",
    "fansly.com", "www.fansly.com",
    # Hentai / anime
    "hentaihaven.xxx", "www.hentaihaven.xxx",
    "hanime.tv", "www.hanime.tv",
    "nhentai.net", "www.nhentai.net",
]
"""Domains permanently blocked via hosts file. No timer, no unblock."""

# ─────────────────────────────────────────────
# Allowlist Mode (Deep Work)
# ─────────────────────────────────────────────
ALLOWLIST_DOMAINS: list[str] = [
    # Work essentials
    "docs.google.com",
    "drive.google.com",
    "mail.google.com",
    "calendar.google.com",
    "meet.google.com",
    # Dev tools
    "stackoverflow.com",
    "github.com",
    "gitlab.com",
    "pypi.org",
    "npmjs.com",
    "developer.mozilla.org",
    # Communication
    "slack.com",
    "notion.so",
    "linear.app",
]
"""Domains allowed during Allowlist / Deep Work mode. Everything else is blocked."""

ALLOWLIST_REFRESH_SECONDS: int = 300
"""How often to re-resolve allowlist domain IPs (seconds). CDN IPs change."""

# ─────────────────────────────────────────────
# Colors (for icon generation)
# ─────────────────────────────────────────────
COLOR_BLOCKED: str = "#E74C3C"
"""Red - platform is blocked."""

COLOR_ACTIVE: str = "#2ECC71"
"""Green - session is active (platform unblocked)."""

COLOR_WARNING: str = "#F39C12"
"""Orange - running low on time."""

COLOR_PAUSED: str = "#3498DB"
"""Blue - session is paused."""

COLOR_FOCUS: str = "#6C5CE7"
"""Purple - DarkPause focus mode active."""
