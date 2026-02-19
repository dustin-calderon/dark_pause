"""
DarkPause - Recurring Schedule Manager.

Allows users to create recurring weekly schedules that automatically
trigger blackout sessions. Schedules persist in a JSON file and are
checked every 60 seconds by a background thread.

Example schedule config:
{
  "schedules": [
    {
      "id": "work-mode",
      "name": "Work Mode",
      "days": [0, 1, 2, 3, 4],   # Mon-Fri (0=Monday)
      "start": "09:00",
      "end": "17:00",
      "enabled": true
    }
  ]
}
"""

import json
import logging
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from core.config import APP_DATA_DIR

logger = logging.getLogger(__name__)

_SCHEDULE_FILE: Path = APP_DATA_DIR / "schedules.json"
_CHECK_INTERVAL_SECONDS: int = 60


# ─── Data Types ───

class Schedule:
    """
    Represents a single recurring weekly schedule.

    Attributes:
        id: Unique identifier for this schedule.
        name: Human-readable name.
        days: List of weekday numbers (0=Monday, 6=Sunday).
        start: Start time string in HH:MM format.
        end: End time string in HH:MM format.
        enabled: Whether this schedule is currently active.
    """

    def __init__(
        self,
        name: str,
        days: list[int],
        start: str,
        end: str,
        enabled: bool = True,
        schedule_id: str | None = None,
    ) -> None:
        self.id: str = schedule_id or str(uuid.uuid4())[:8]
        self.name: str = name
        self.days: list[int] = days
        self.start: str = start
        self.end: str = end
        self.enabled: bool = enabled

    def to_dict(self) -> dict:
        """Serialize schedule to a dictionary for JSON persistence."""
        return {
            "id": self.id,
            "name": self.name,
            "days": self.days,
            "start": self.start,
            "end": self.end,
            "enabled": self.enabled,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Schedule":
        """
        Deserialize a schedule from a dictionary.

        Args:
            data: Dictionary with schedule fields.

        Returns:
            Schedule: Reconstructed Schedule instance.
        """
        return cls(
            name=data["name"],
            days=data["days"],
            start=data["start"],
            end=data["end"],
            enabled=data.get("enabled", True),
            schedule_id=data.get("id"),
        )

    def is_active_now(self) -> bool:
        """
        Check if this schedule should be active at the current time.

        Returns:
            bool: True if today's weekday and current time fall within this schedule.
        """
        if not self.enabled:
            return False

        now: datetime = datetime.now()
        current_weekday: int = now.weekday()  # 0=Monday

        if current_weekday not in self.days:
            return False

        try:
            start_parts: list[str] = self.start.split(":")
            end_parts: list[str] = self.end.split(":")
            start_minutes: int = int(start_parts[0]) * 60 + int(start_parts[1])
            end_minutes: int = int(end_parts[0]) * 60 + int(end_parts[1])
            current_minutes: int = now.hour * 60 + now.minute

            return start_minutes <= current_minutes < end_minutes
        except (ValueError, IndexError):
            logger.warning(f"Invalid time format in schedule '{self.name}'.")
            return False

    def remaining_minutes(self) -> int:
        """
        Calculate remaining minutes until this schedule's end time.

        Note: Does NOT re-check is_active_now() — the caller should
        verify activity before calling this to avoid redundant checks.

        Returns:
            int: Minutes remaining, or 0 if not calculable.
        """
        now: datetime = datetime.now()
        try:
            end_parts: list[str] = self.end.split(":")
            end_minutes: int = int(end_parts[0]) * 60 + int(end_parts[1])
            current_minutes: int = now.hour * 60 + now.minute
            return max(0, end_minutes - current_minutes)
        except (ValueError, IndexError):
            return 0

    def __repr__(self) -> str:
        days_str: str = ",".join(str(d) for d in self.days)
        return f"Schedule({self.name}, days=[{days_str}], {self.start}-{self.end})"


# ─── Persistence ───


def _load_schedules() -> list[Schedule]:
    """
    Load schedules from the JSON file.

    Returns:
        list[Schedule]: List of deserialized schedules.
    """
    try:
        if not _SCHEDULE_FILE.exists():
            return []
        raw: str = _SCHEDULE_FILE.read_text(encoding="utf-8")
        data: dict = json.loads(raw)
        return [Schedule.from_dict(s) for s in data.get("schedules", [])]
    except Exception as e:
        logger.warning(f"Failed to load schedules: {e}")
        return []


def _save_schedules(schedules: list[Schedule]) -> None:
    """
    Save schedules to the JSON file.

    Args:
        schedules: List of Schedule instances to persist.
    """
    try:
        APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
        data: dict = {
            "schedules": [s.to_dict() for s in schedules],
        }
        _SCHEDULE_FILE.write_text(
            json.dumps(data, indent=2),
            encoding="utf-8",
        )
    except Exception as e:
        logger.warning(f"Failed to save schedules: {e}")


# ─── Schedule Manager ───


class ScheduleManager:
    """
    Manages recurring weekly schedules with a background check thread.

    The manager loads schedules from disk, checks every 60 seconds
    if any schedule should be active, and triggers a blackout callback
    if one is active and no blackout is currently running.

    Args:
        on_start_blackout: Callback to start a blackout (receives minutes, locked).
        is_blackout_active: Callback to check if a blackout is currently running.
    """

    def __init__(
        self,
        on_start_blackout: Callable[[int, bool], None],
        is_blackout_active: Callable[[], bool],
    ) -> None:
        self._on_start_blackout: Callable[[int, bool], None] = on_start_blackout
        self._is_blackout_active: Callable[[], bool] = is_blackout_active
        self._schedules: list[Schedule] = _load_schedules()
        self._thread: Optional[threading.Thread] = None
        self._stop_event: threading.Event = threading.Event()
        self._lock: threading.Lock = threading.Lock()
        self._triggered_today: set[str] = set()  # Track which schedules triggered today
        self._last_check_date: str = ""

    @property
    def schedules(self) -> list[Schedule]:
        """Get a copy of all schedules."""
        with self._lock:
            return list(self._schedules)

    def add_schedule(self, schedule: Schedule) -> None:
        """
        Add a new schedule and persist to disk.

        Args:
            schedule: The Schedule to add.
        """
        with self._lock:
            self._schedules.append(schedule)
            _save_schedules(self._schedules)
        logger.info(f"📅 Schedule added: {schedule}")

    def remove_schedule(self, schedule_id: str) -> bool:
        """
        Remove a schedule by ID and persist to disk.

        Args:
            schedule_id: The unique ID of the schedule to remove.

        Returns:
            bool: True if a schedule was found and removed.
        """
        with self._lock:
            before_count: int = len(self._schedules)
            self._schedules = [s for s in self._schedules if s.id != schedule_id]
            if len(self._schedules) < before_count:
                _save_schedules(self._schedules)
                logger.info(f"🗑 Schedule removed: {schedule_id}")
                return True
            return False

    def toggle_schedule(self, schedule_id: str) -> bool:
        """
        Toggle a schedule's enabled state.

        Args:
            schedule_id: The unique ID of the schedule to toggle.

        Returns:
            bool: True if the schedule was found and toggled.
        """
        with self._lock:
            for schedule in self._schedules:
                if schedule.id == schedule_id:
                    schedule.enabled = not schedule.enabled
                    _save_schedules(self._schedules)
                    state: str = "enabled" if schedule.enabled else "disabled"
                    logger.info(f"📅 Schedule '{schedule.name}' {state}.")
                    return True
            return False

    def start(self) -> None:
        """Start the background schedule checking thread."""
        if self._thread and self._thread.is_alive():
            return

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._check_loop,
            daemon=True,
            name="scheduler",
        )
        self._thread.start()
        logger.info(f"📅 Scheduler started with {len(self._schedules)} schedules.")

    def stop(self) -> None:
        """Stop the background schedule checking thread."""
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        self._thread = None
        logger.info("📅 Scheduler stopped.")

    def _check_loop(self) -> None:
        """Background loop checking schedules every 60 seconds."""
        while not self._stop_event.is_set():
            self._check_schedules()
            self._stop_event.wait(timeout=_CHECK_INTERVAL_SECONDS)

    def _check_schedules(self) -> None:
        """Check if any schedule should trigger a blackout right now."""
        today: str = datetime.now().strftime("%Y-%m-%d")

        # Reset triggered set on new day
        if today != self._last_check_date:
            self._triggered_today.clear()
            self._last_check_date = today

        # Don't trigger if blackout already active
        if self._is_blackout_active():
            return

        with self._lock:
            for schedule in self._schedules:
                if schedule.id in self._triggered_today:
                    continue

                if schedule.is_active_now():
                    remaining: int = schedule.remaining_minutes()
                    if remaining > 0:
                        logger.info(
                            f"⏰ Schedule '{schedule.name}' triggered! "
                            f"Blackout for {remaining} min."
                        )
                        self._triggered_today.add(schedule.id)
                        self._on_start_blackout(remaining, False)
                        return  # Only one blackout at a time
