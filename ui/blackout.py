"""
DarkPause - Screen Blackout Module.

Deploys fullscreen black overlays on all monitors, blocking
access to the desktop for a set duration. Multi-monitor aware.

Includes persistent state: if the app crashes mid-blackout,
the state is saved to disk and can be resumed on restart.
"""

import json
import logging
import threading
import tkinter as tk
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Optional

from core.config import APP_DATA_DIR

logger = logging.getLogger(__name__)

_STATE_FILE: Path = APP_DATA_DIR / "blackout_state.json"


# ─── Persistent State Helpers ───


def _save_blackout_state(
    end_time: datetime,
    duration: int,
    locked: bool = False,
) -> None:
    """
    Save blackout state to disk for crash recovery.

    Args:
        end_time: When the blackout should end.
        duration: Original duration in minutes.
        locked: Whether this blackout is in Lock Mode (irreversible).
    """
    try:
        APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
        data: dict = {
            "end_iso": end_time.isoformat(),
            "duration_minutes": duration,
            "locked": locked,
        }
        _STATE_FILE.write_text(json.dumps(data), encoding="utf-8")
        logger.debug(f"Blackout state saved: ends at {end_time.isoformat()}, locked={locked}")
    except Exception as e:
        logger.warning(f"Failed to save blackout state: {e}")


def _clear_blackout_state() -> None:
    """Remove persisted blackout state file."""
    try:
        _STATE_FILE.unlink(missing_ok=True)
    except Exception:
        pass


def load_persisted_blackout() -> tuple[int, bool] | None:
    """
    Check for a persisted blackout from a previous crash.

    Returns:
        tuple[int, bool] | None: (remaining_minutes, locked) if valid, else None.
    """
    try:
        if not _STATE_FILE.exists():
            return None
        raw: str = _STATE_FILE.read_text(encoding="utf-8")
        data: dict = json.loads(raw)
        end_time: datetime = datetime.fromisoformat(data["end_iso"])
        locked: bool = data.get("locked", False)
        remaining_secs: float = (end_time - datetime.now()).total_seconds()
        if remaining_secs > 60:  # At least 1 minute left
            return max(1, int(remaining_secs / 60)), locked
        # Expired — clean up
        _clear_blackout_state()
        return None
    except Exception:
        _clear_blackout_state()
        return None


class ScreenBlackout:
    """
    Manages fullscreen black overlay windows for focus mode.

    Attributes:
        is_active: Whether the blackout is currently active.
        remaining_seconds: Seconds remaining in the current blackout.
    """

    def __init__(
        self,
        root: tk.Tk,
        on_complete: Optional[Callable[[], None]] = None,
    ) -> None:
        """
        Initialize the ScreenBlackout.

        Args:
            root: The Tkinter root window (for creating Toplevels and after()).
            on_complete: Optional callback invoked when the blackout timer ends.
        """
        self._root: tk.Tk = root
        self._on_complete: Optional[Callable[[], None]] = on_complete
        self._overlays: list[tk.Toplevel] = []
        self._is_active: bool = False
        self._is_locked: bool = False
        self._end_time: Optional[datetime] = None
        self._timer_id: Optional[str] = None
        self._focus_id: Optional[str] = None

    @property
    def is_active(self) -> bool:
        """Whether the blackout is currently active."""
        return self._is_active

    @property
    def is_locked(self) -> bool:
        """Whether the blackout is in Lock Mode (cannot be cancelled)."""
        return self._is_active and self._is_locked

    @property
    def remaining_seconds(self) -> float:
        """Seconds remaining in the current blackout session."""
        if not self._is_active or not self._end_time:
            return 0.0
        delta: float = (self._end_time - datetime.now()).total_seconds()
        return max(0.0, delta)

    def start(self, minutes: int, locked: bool = False) -> None:
        """
        Start a blackout session for the given number of minutes.

        Creates fullscreen black overlays on all detected monitors.

        Args:
            minutes: Duration of the blackout in minutes.
            locked: If True, enables Lock Mode — blackout cannot be cancelled.
        """
        if self._is_active:
            logger.warning("Blackout already active, ignoring start request.")
            return

        lock_label: str = " [LOCKED]" if locked else ""
        logger.info(f"🌌 Starting blackout for {minutes} minutes.{lock_label}")
        self._is_active = True
        self._is_locked = locked
        self._end_time = datetime.now() + timedelta(minutes=minutes)
        self._overlays = []

        # FIX-1: Detect monitors using existing root (no second Tk())
        monitors = self._get_monitors(self._root)

        for i, mon in enumerate(monitors):
            overlay: tk.Toplevel = tk.Toplevel(self._root)
            overlay.geometry(f"{mon['w']}x{mon['h']}+{mon['x']}+{mon['y']}")
            overlay.attributes("-topmost", True)
            overlay.overrideredirect(True)
            overlay.configure(bg="black")
            overlay.config(cursor="none")

            # FIX-6: Properly suppress close events
            def _block_close() -> None:
                """Intentionally empty — prevents window destruction."""
                pass

            overlay.protocol("WM_DELETE_WINDOW", _block_close)
            overlay.bind("<Alt-F4>", lambda e: "break")

            # Timer label on primary monitor
            if i == 0:
                self._timer_label = tk.Label(
                    overlay,
                    text="",
                    bg="black",
                    fg="#333333",
                    font=("Segoe UI", 48, "bold"),
                )
                self._timer_label.place(relx=0.5, rely=0.5, anchor="center")

                subtitle_text: str = "🔒 LOCKED — NO ESCAPE" if locked else "FOCUS MODE"
                subtitle_color: str = "#2d1010" if locked else "#1a1a1a"
                subtitle = tk.Label(
                    overlay,
                    text=subtitle_text,
                    bg="black",
                    fg=subtitle_color,
                    font=("Segoe UI", 14),
                )
                subtitle.place(relx=0.5, rely=0.58, anchor="center")

            self._overlays.append(overlay)

        # Persist state for crash recovery
        _save_blackout_state(self._end_time, minutes, locked=locked)

        # Start timer update loop
        self._update_timer()
        # Start focus enforcement loop
        self._keep_focus()

    def stop(self, force: bool = False) -> None:
        """
        Stop the blackout and destroy all overlays.

        Args:
            force: If True, bypass Lock Mode protection (used by timer expiry only).
        """
        if self._is_locked and not force:
            logger.warning("🔒 Lock Mode active — stop request DENIED.")
            return

        logger.info("🌌 Blackout ended.")
        self._is_active = False
        self._is_locked = False
        self._end_time = None

        # Clear persisted state
        _clear_blackout_state()

        if self._timer_id:
            try:
                self._root.after_cancel(self._timer_id)
            except Exception:
                pass
            self._timer_id = None

        if self._focus_id:
            try:
                self._root.after_cancel(self._focus_id)
            except Exception:
                pass
            self._focus_id = None

        for overlay in self._overlays:
            try:
                overlay.destroy()
            except Exception:
                pass
        self._overlays = []

    def _update_timer(self) -> None:
        """Update the countdown timer display on the overlay."""
        if not self._is_active:
            return

        remaining: float = self.remaining_seconds
        if remaining <= 0:
            self.stop(force=True)
            if self._on_complete:
                self._on_complete()
            return

        minutes: int = int(remaining // 60)
        seconds: int = int(remaining % 60)

        try:
            self._timer_label.configure(text=f"{minutes:02d}:{seconds:02d}")
        except Exception:
            pass

        self._timer_id = self._root.after(1000, self._update_timer)

    def _keep_focus(self) -> None:
        """Periodically ensure overlays stay on top of all other windows."""
        if not self._is_active:
            return

        for overlay in self._overlays:
            try:
                overlay.lift()
                overlay.attributes("-topmost", True)
            except Exception:
                pass

        # Also grab focus on primary overlay
        if self._overlays:
            try:
                self._overlays[0].focus_force()
            except Exception:
                pass

        self._focus_id = self._root.after(500, self._keep_focus)

    @staticmethod
    def _get_monitors(root: tk.Tk) -> list[dict[str, int]]:
        """
        Detect all connected monitors.

        FIX-1: Uses the existing root window for fallback dimensions
        instead of creating a second tk.Tk() which crashes the mainloop.

        Args:
            root: The existing Tkinter root window.

        Returns:
            list: Dicts with keys 'x', 'y', 'w', 'h' for each monitor.
        """
        try:
            from screeninfo import get_monitors
            return [
                {"x": m.x, "y": m.y, "w": m.width, "h": m.height}
                for m in get_monitors()
            ]
        except ImportError:
            logger.warning("screeninfo not installed, using single monitor fallback.")
        except Exception as e:
            logger.warning(f"Monitor detection failed: {e}")

        # FIX-1: Fallback using the EXISTING root — never create a second Tk()
        try:
            w: int = root.winfo_screenwidth()
            h: int = root.winfo_screenheight()
        except Exception:
            w, h = 1920, 1080

        return [{"x": 0, "y": 0, "w": w, "h": h}]
