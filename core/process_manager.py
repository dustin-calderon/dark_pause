"""
DarkPause - Process Manager.

Handles detection and termination of platform desktop app processes.
Uses taskkill with PowerShell fallback for UWP/Store apps.
"""

import logging
import subprocess

from .config import Platform

logger = logging.getLogger(__name__)

_SUBPROCESS_TIMEOUT: int = 10


def _run_tasklist() -> str:
    """Run Windows tasklist command and return its output."""
    try:
        result = subprocess.run(
            ["tasklist", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
            timeout=_SUBPROCESS_TIMEOUT,
        )
        return result.stdout
    except subprocess.TimeoutExpired:
        logger.warning("tasklist command timed out.")
        return ""
    except Exception as e:
        logger.error(f"Failed to run tasklist: {e}")
        return ""


def is_app_running(platform: Platform) -> bool:
    """Check if a platform's desktop app is currently running."""
    if not platform.process_names:
        return False

    tasklist_output: str = _run_tasklist()
    lower_output: str = tasklist_output.lower()

    for process_name in platform.process_names:
        if process_name.lower() in lower_output:
            logger.debug(f"{platform.display_name} process detected: {process_name}")
            return True

    return False


def _kill_with_taskkill(process_name: str) -> bool:
    """Attempt to kill a process using taskkill (Win32 apps)."""
    try:
        result = subprocess.run(
            ["taskkill", "/F", "/IM", process_name],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
            timeout=_SUBPROCESS_TIMEOUT,
        )
        if result.returncode == 0:
            return True
        stderr_lower: str = result.stderr.lower()
        if "access" in stderr_lower and "denied" in stderr_lower:
            logger.debug(f"taskkill Access denied for {process_name}. Trying PowerShell...")
            return False
        return False
    except subprocess.TimeoutExpired:
        logger.warning(f"taskkill timed out for {process_name}.")
        return False
    except Exception as e:
        logger.error(f"taskkill failed for {process_name}: {e}")
        return False


def _kill_with_powershell(process_name: str) -> bool:
    """Fallback: kill UWP/Store apps via PowerShell Stop-Process."""
    name_without_ext: str = process_name
    if name_without_ext.lower().endswith(".exe"):
        name_without_ext = name_without_ext[:-4]

    try:
        result = subprocess.run(
            [
                "powershell", "-NoProfile", "-NonInteractive", "-Command",
                f"Get-Process -Name '{name_without_ext}' -ErrorAction SilentlyContinue | "
                f"Stop-Process -Force -ErrorAction SilentlyContinue",
            ],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
            timeout=_SUBPROCESS_TIMEOUT,
        )
        if result.returncode == 0:
            logger.debug(f"PowerShell Stop-Process executed for {process_name}.")
            return True
        return False
    except subprocess.TimeoutExpired:
        logger.warning(f"PowerShell Stop-Process timed out for {process_name}.")
        return False
    except Exception as e:
        logger.error(f"PowerShell Stop-Process failed for {process_name}: {e}")
        return False


def kill_app(platform: Platform) -> bool:
    """
    Terminate all desktop app processes for a platform.
    Two-stage: taskkill first, PowerShell fallback for UWP.
    """
    if not platform.process_names:
        logger.debug(f"No processes configured for {platform.display_name}.")
        return True

    killed_any: bool = False

    for process_name in platform.process_names:
        if _kill_with_taskkill(process_name):
            logger.info(f"🔨 Killed process (taskkill): {process_name}")
            killed_any = True
            continue
        if _kill_with_powershell(process_name):
            logger.info(f"🔨 Killed process (PowerShell): {process_name}")
            killed_any = True

    if killed_any:
        logger.info(f"✅ {platform.display_name} app processes terminated.")
    else:
        logger.debug(f"No {platform.display_name} app processes were running.")

    return True
