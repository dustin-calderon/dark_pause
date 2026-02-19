"""DarkPause - UI Sections package."""

from .allowlist import AllowlistSection
from .blackout import BlackoutSection
from .schedule import ScheduleSection
from .task_queue import TaskQueueSection
from .web_block import WebBlockSection

__all__: list[str] = [
    "BlackoutSection",
    "ScheduleSection",
    "AllowlistSection",
    "TaskQueueSection",
    "WebBlockSection",
]
