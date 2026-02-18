"""
DarkPause - System Tray Application.

The system tray icon is the main process of DarkPause. It:
- Shows platform usage status (IG, YouTube, etc.)
- Allows starting/pausing timed sessions per platform
- Provides access to the focus mode (blackout) and control panel
- Runs permanently in the background
"""

import logging
import threading
import time
from typing import Callable, Optional

import pystray
from pystray import Icon, Menu, MenuItem as Item

from core import usage_tracker, hosts_manager, process_manager
from core.config import (
    ALL_PLATFORMS,
    APP_NAME,
    MAX_TOOLTIP_LENGTH,
    WARNING_THRESHOLD_MINUTES,
    Platform,
)
from core.icon_generator import create_icon

logger = logging.getLogger(__name__)


class PlatformSession:
    """
    Manages a single timed session for one platform.

    Tracks elapsed time, handles blocking/unblocking,
    and sends warning notifications when time is running low.
    """

    def __init__(
        self,
        platform: Platform,
        notify_callback: Callable[[str, str], None],
        update_callback: Callable[[], None],
    ) -> None:
        self.platform: Platform = platform
        self._notify_callback: Callable[[str, str], None] = notify_callback
        self._update_callback: Callable[[], None] = update_callback
        # FIX-4: Lock protects _running and _paused from data races
        self._state_lock: threading.Lock = threading.Lock()
        self._running: bool = False
        self._paused: bool = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event: threading.Event = threading.Event()
        self._warning_sent: bool = False

    @property
    def is_running(self) -> bool:
        with self._state_lock:
            return self._running and not self._paused

    @property
    def is_paused(self) -> bool:
        with self._state_lock:
            return self._running and self._paused

    @property
    def is_stopped(self) -> bool:
        with self._state_lock:
            return not self._running

    def start(self) -> None:
        """Start or resume a session for this platform."""
        if usage_tracker.is_limit_reached(self.platform):
            self._notify_callback(
                f"⛔ {self.platform.display_name}",
                "Límite diario alcanzado.",
            )
            return

        with self._state_lock:
            self._paused = False

            if self._running:
                logger.info(f"▶️ Resumed {self.platform.display_name}")
                hosts_manager.unblock_platform(self.platform)
                self._update_callback()
                return

            self._running = True

        self._stop_event.clear()
        self._warning_sent = False

        hosts_manager.unblock_platform(self.platform)
        usage_tracker.increment_session_count(self.platform)
        logger.info(f"▶️ Started session for {self.platform.display_name}")

        self._thread = threading.Thread(
            target=self._timer_loop, daemon=True,
            name=f"timer-{self.platform.id}",
        )
        self._thread.start()
        self._update_callback()

    def pause(self) -> None:
        """Pause the current session."""
        with self._state_lock:
            self._paused = True
        hosts_manager.block_platform(self.platform)
        process_manager.kill_app(self.platform)
        logger.info(f"⏸ Paused {self.platform.display_name}")
        self._update_callback()

    def stop(self) -> None:
        """Stop the session completely."""
        with self._state_lock:
            self._running = False
            self._paused = False
        self._stop_event.set()
        hosts_manager.block_platform(self.platform)
        process_manager.kill_app(self.platform)
        logger.info(f"⏹ Stopped {self.platform.display_name}")
        self._update_callback()

    def _timer_loop(self) -> None:
        """Timer loop that tracks actual elapsed time via monotonic clock."""
        last_tick: float = time.monotonic()

        while not self._stop_event.is_set():
            self._stop_event.wait(timeout=1.0)

            # FIX-4: Read flags under lock
            with self._state_lock:
                running = self._running
                paused = self._paused

            if not running:
                return

            if paused:
                last_tick = time.monotonic()
                continue

            now: float = time.monotonic()
            elapsed: float = now - last_tick
            last_tick = now

            usage_tracker.add_usage(self.platform, elapsed)
            remaining: float = usage_tracker.get_remaining_seconds(self.platform)

            self._update_callback()

            # Warning notification
            if remaining <= WARNING_THRESHOLD_MINUTES * 60 and not self._warning_sent:
                mins_left: int = max(1, int(remaining // 60))
                self._notify_callback(
                    f"⚠️ {self.platform.display_name}: Poco tiempo",
                    f"Quedan ~{mins_left} min.",
                )
                self._warning_sent = True

            # Limit reached
            if remaining <= 0:
                logger.info(f"⛔ Time limit reached for {self.platform.display_name}")
                self._notify_callback(
                    f"⛔ {self.platform.display_name}",
                    "Límite diario alcanzado. Bloqueando.",
                )
                self.stop()
                return


class DarkPauseTray:
    """
    Main system tray application.

    Manages the tray icon, menu, platform sessions, and orchestrates
    the control panel and blackout features.
    """

    def __init__(
        self,
        on_open_panel: Callable[[], None],
        on_start_blackout: Callable[[int], None],
    ) -> None:
        self._sessions: dict[str, PlatformSession] = {}
        self._icon: Optional[Icon] = None
        self._update_lock: threading.RLock = threading.RLock()
        self._on_open_panel: Callable[[], None] = on_open_panel
        self._on_start_blackout: Callable[[int], None] = on_start_blackout

        for platform in ALL_PLATFORMS:
            self._sessions[platform.id] = PlatformSession(
                platform=platform,
                notify_callback=self._safe_notify,
                update_callback=self._request_update,
            )

    def run(self) -> None:
        """Start the tray icon. This runs the pystray event loop."""
        initial_icon = create_icon("blocked")
        self._icon = Icon(
            name="DarkPause",
            icon=initial_icon,
            title=APP_NAME,
            menu=self._build_menu(),
        )
        self._icon.run(setup=self._setup)

    def stop(self) -> None:
        """Stop all sessions and remove the tray icon."""
        logger.info("🛑 Stopping DarkPause tray...")
        for session in self._sessions.values():
            if session.is_running or session.is_paused:
                session.stop()
        if self._icon:
            self._icon.stop()

    def _setup(self, icon: pystray.Icon) -> None:
        """Initialization callback when tray icon starts."""
        icon.visible = True
        # NOTE: Platform and permanent blocking is handled by main()
        # before the tray starts. No need to duplicate it here.
        logger.info("✅ DarkPause is running in system tray.")

    def _safe_notify(self, title: str, message: str) -> None:
        """Send a notification safely."""
        try:
            if self._icon:
                self._icon.notify(message, title)
        except Exception as e:
            logger.warning(f"Notification failed: {e}")

    def _request_update(self) -> None:
        """Thread-safe request to update icon and menu."""
        with self._update_lock:
            if not self._icon:
                return
            try:
                self._update_icon_visuals()
                self._icon.update_menu()
            except Exception as e:
                logger.error(f"Error during UI update: {e}")

    def _update_icon_visuals(self) -> None:
        """Update the tray icon state and tooltip."""
        any_active: bool = any(s.is_running for s in self._sessions.values())
        any_warning: bool = False
        any_paused: bool = any(s.is_paused for s in self._sessions.values())

        if any_active:
            for s in self._sessions.values():
                if s.is_running:
                    remaining = usage_tracker.get_remaining_seconds(s.platform)
                    if remaining <= WARNING_THRESHOLD_MINUTES * 60:
                        any_warning = True
                        break

        if any_warning:
            state = "warning"
        elif any_active:
            state = "active"
        elif any_paused:
            state = "paused"
        else:
            state = "blocked"

        self._icon.icon = create_icon(state)

        # Build tooltip
        parts: list[str] = [APP_NAME]
        for platform in ALL_PLATFORMS:
            remaining_str = usage_tracker.get_formatted_remaining(platform)
            session = self._sessions[platform.id]
            if session.is_running:
                status = "▶"
            elif session.is_paused:
                status = "⏸"
            else:
                status = "🔒"
            parts.append(f"{status} {platform.display_name}: {remaining_str}")

        tooltip: str = " | ".join(parts)
        if len(tooltip) > MAX_TOOLTIP_LENGTH:
            tooltip = tooltip[:MAX_TOOLTIP_LENGTH - 3] + "..."
        self._icon.title = tooltip

    def _build_menu(self) -> Menu:
        """Build the dynamic tray context menu."""

        # Factory functions for callbacks with correct pystray signature
        def create_start_cb(pid: str):
            sessions = self._sessions
            return lambda icon, item: sessions[pid].start()

        def create_pause_cb(pid: str):
            sessions = self._sessions
            return lambda icon, item: sessions[pid].pause()

        def create_stop_cb(icon, item):
            self.stop()

        def open_panel_cb(icon, item):
            self._on_open_panel()

        def pomo25_cb(icon, item):
            self._on_start_blackout(25)

        def pomo50_cb(icon, item):
            self._on_start_blackout(50)

        menu_items: list[Item] = []
        menu_items.append(Item(APP_NAME, None, enabled=False))
        menu_items.append(Menu.SEPARATOR)

        # Platform items
        for platform in ALL_PLATFORMS:
            pid: str = platform.id

            def make_status_text(item, p=platform):
                session = self._sessions[p.id]
                remaining = usage_tracker.get_formatted_remaining(p)
                limit = p.daily_limit_minutes
                if session.is_running:
                    return f"  ▶️ {p.icon_emoji} {p.display_name} ({remaining} / {limit}m)"
                elif session.is_paused:
                    return f"  ⏸ {p.icon_emoji} {p.display_name} ({remaining} / {limit}m)"
                else:
                    return f"  🔴 {p.icon_emoji} {p.display_name} ({remaining} / {limit}m)"

            menu_items.append(Item(make_status_text, None, enabled=False))

            # Visibility callables
            def visible_start(item, p=platform):
                s = self._sessions[p.id]
                return s.is_stopped or s.is_paused

            def visible_pause(item, p=platform):
                return self._sessions[p.id].is_running

            menu_items.append(Item(
                "    ▶ Iniciar",
                create_start_cb(pid),
                visible=visible_start,
            ))
            menu_items.append(Item(
                "    ⏸ Pausar",
                create_pause_cb(pid),
                visible=visible_pause,
            ))

            menu_items.append(Menu.SEPARATOR)

        # Focus Mode section
        menu_items.append(Item("🌌 Focus Mode", None, enabled=False))
        menu_items.append(Item("    🍅 Pomo 25 min", pomo25_cb))
        menu_items.append(Item("    🧘 Pomo 50 min", pomo50_cb))
        menu_items.append(Item("    ⚙️ Panel de Control", open_panel_cb))
        menu_items.append(Menu.SEPARATOR)

        # Exit
        menu_items.append(Item("❌ Salir", create_stop_cb))

        return Menu(*menu_items)
