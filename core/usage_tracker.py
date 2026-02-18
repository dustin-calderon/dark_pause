"""
DarkPause - Daily Usage Tracker.

Tracks cumulative usage per platform per day using individual JSON files.
Persists data across app restarts and handles daily resets at RESET_HOUR.
Uses atomic writes and per-platform locks for thread safety.
"""

import json
import logging
import os
import tempfile
import threading
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import TypedDict

from .config import APP_DATA_DIR, RESET_HOUR, Platform

logger = logging.getLogger(__name__)

_platform_locks: dict[str, threading.Lock] = {}
_locks_lock: threading.Lock = threading.Lock()


def _get_platform_lock(platform: Platform) -> threading.Lock:
    """Get or create a thread lock for a specific platform."""
    if platform.id not in _platform_locks:
        with _locks_lock:
            if platform.id not in _platform_locks:
                _platform_locks[platform.id] = threading.Lock()
    return _platform_locks[platform.id]


class UsageData(TypedDict):
    """Structure for a platform's usage JSON file."""
    date: str
    used_seconds: float
    sessions: int


def _ensure_data_dir() -> None:
    """Create the application data directory if it doesn't exist."""
    APP_DATA_DIR.mkdir(parents=True, exist_ok=True)


def _get_logical_day_str() -> str:
    """Get the current 'logical day' as ISO string. Resets at RESET_HOUR."""
    now: datetime = datetime.now()
    if now.hour < RESET_HOUR:
        logical_date: date = now.date() - timedelta(days=1)
    else:
        logical_date = now.date()
    return logical_date.isoformat()


def _get_usage_file(platform: Platform) -> Path:
    """Get the path to a platform's usage JSON file."""
    return APP_DATA_DIR / platform.usage_file_name


def _load_data(platform: Platform) -> UsageData:
    """Load usage data for a platform. Caller MUST hold the platform lock."""
    _ensure_data_dir()
    today: str = _get_logical_day_str()
    usage_file: Path = _get_usage_file(platform)

    if usage_file.exists():
        try:
            raw: str = usage_file.read_text(encoding="utf-8")
            data: UsageData = json.loads(raw)
            if data.get("date") == today:
                return data
            logger.info(
                f"🔄 New day detected for {platform.display_name}. "
                f"Resetting usage counter for {today}."
            )
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Corrupted usage file for {platform.display_name}, resetting: {e}")

    return UsageData(date=today, used_seconds=0.0, sessions=0)


def _save_data(platform: Platform, data: UsageData) -> None:
    """Atomically save usage data. Caller MUST hold the platform lock."""
    _ensure_data_dir()
    usage_file: Path = _get_usage_file(platform)
    json_content: str = json.dumps(data, indent=2)

    fd: int = -1
    tmp_path: str = ""
    try:
        fd, tmp_path = tempfile.mkstemp(
            dir=str(APP_DATA_DIR),
            prefix=f".{platform.id}_",
            suffix=".tmp",
        )
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            fd = -1
            f.write(json_content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, str(usage_file))
        tmp_path = ""
    except Exception as e:
        logger.error(f"Failed to save usage data for {platform.display_name}: {e}")
        try:
            usage_file.write_text(json_content, encoding="utf-8")
        except Exception as fallback_err:
            logger.error(f"Fallback write also failed: {fallback_err}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
        if fd >= 0:
            try:
                os.close(fd)
            except OSError:
                pass


def get_used_seconds(platform: Platform) -> float:
    """Get the total seconds of usage for a platform today."""
    lock = _get_platform_lock(platform)
    with lock:
        data: UsageData = _load_data(platform)
        return data["used_seconds"]


def get_remaining_seconds(platform: Platform) -> float:
    """Get the remaining seconds of allowance for a platform today."""
    limit_seconds: float = platform.daily_limit_minutes * 60
    used: float = get_used_seconds(platform)
    return max(0.0, limit_seconds - used)


def add_usage(platform: Platform, seconds: float) -> float:
    """Add usage time to a platform's daily counter. Thread-safe."""
    lock = _get_platform_lock(platform)
    with lock:
        data: UsageData = _load_data(platform)
        data["used_seconds"] += seconds
        _save_data(platform, data)
        return data["used_seconds"]


def increment_session_count(platform: Platform) -> int:
    """Increment the session counter for a platform today."""
    lock = _get_platform_lock(platform)
    with lock:
        data: UsageData = _load_data(platform)
        data["sessions"] += 1
        _save_data(platform, data)
        return data["sessions"]


def is_limit_reached(platform: Platform) -> bool:
    """Check if a platform's daily usage limit has been reached."""
    return get_remaining_seconds(platform) <= 0


def format_seconds(total_seconds: float) -> str:
    """Format seconds into MM:SS string."""
    total_seconds = max(0.0, total_seconds)
    minutes: int = int(total_seconds // 60)
    seconds: int = int(total_seconds % 60)
    return f"{minutes:02d}:{seconds:02d}"


def get_formatted_remaining(platform: Platform) -> str:
    """Get human-readable remaining time string."""
    return format_seconds(get_remaining_seconds(platform))


def get_formatted_used(platform: Platform) -> str:
    """Get human-readable used time string."""
    return format_seconds(get_used_seconds(platform))


def reset_platform(platform: Platform) -> None:
    """Reset a platform's usage data to zero for today."""
    lock = _get_platform_lock(platform)
    with lock:
        data = UsageData(date=_get_logical_day_str(), used_seconds=0.0, sessions=0)
        _save_data(platform, data)
    logger.info(f"🔄 Usage data reset for {platform.display_name}.")
