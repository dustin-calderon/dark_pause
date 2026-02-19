"""
DarkPause — The Unstoppable Distraction Killer.

Unified digital discipline app for Windows that:
1. Limits daily usage of specific platforms (Instagram, YouTube)
2. Permanently blocks adult content domains
3. Provides fullscreen blackout mode for deep focus sessions
4. Applies DNS anti-bypass via Windows Firewall rules
5. Periodically verifies hosts file integrity against tampering

Entry point: sets up logging, checks admin privileges,
and starts the system tray + Tkinter event loop.
"""

import ctypes
import logging
import os
import socket
import sys
import threading
import tkinter as tk
from pathlib import Path

# ─── Ensure correct working directory ───
# Task Scheduler launches from C:\Windows\System32 — all relative
# imports (core.*, ui.*) and asset paths would fail without this.
_SCRIPT_DIR: str = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)
os.chdir(_SCRIPT_DIR)

# ─── Windows AppUserModelID ───
# Tell Windows this is a standalone app, not "pythonw.exe".
# This gives DarkPause its own taskbar icon and identity.
try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("darkpause.app.2.1")
except (AttributeError, OSError):
    pass  # Non-critical — app still works, just shows Python icon

logger = logging.getLogger("darkpause")

# ─── Single Instance ───
_instance_socket: socket.socket | None = None

# ─── Integrity Check Interval ───
_INTEGRITY_CHECK_MS: int = 30_000  # 30 seconds


def _check_single_instance(port: int) -> None:
    """
    Ensure only one instance of DarkPause is running.

    Args:
        port: TCP port to bind for single-instance check.
    """
    global _instance_socket
    _instance_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        _instance_socket.bind(("127.0.0.1", port))
    except socket.error:
        logger.warning("DarkPause is already running. Exiting.")
        sys.exit(0)


# ─── Admin Privileges ───
def _is_admin() -> bool:
    """Check if the current process has Administrator privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except AttributeError:
        return False


def _get_pythonw_path() -> str:
    """
    Resolve the path to pythonw.exe robustly.

    Handles case-insensitive executable names and avoids
    double-replacing if sys.executable already is pythonw.exe.

    Returns:
        str: Full path to pythonw.exe.
    """
    exe_path = Path(sys.executable)
    stem_lower: str = exe_path.stem.lower()

    if stem_lower == "pythonw":
        return str(exe_path)

    if stem_lower == "python":
        return str(exe_path.with_name(f"pythonw{exe_path.suffix}"))

    candidate: Path = exe_path.parent / "pythonw.exe"
    if candidate.exists():
        return str(candidate)

    return "pythonw.exe"


def _request_admin_restart() -> None:
    """
    Restart the script with Administrator privileges using UAC.

    Uses pythonw.exe for windowless execution so no console appears.
    """
    try:
        pythonw: str = _get_pythonw_path()
        quoted_args: str = " ".join(f'"{arg}"' for arg in sys.argv)
        ctypes.windll.shell32.ShellExecuteW(
            None,
            "runas",
            pythonw,
            quoted_args,
            None,
            0,  # SW_HIDE
        )
    except Exception as e:
        logger.error(f"Failed to request admin restart: {e}")


# ─── Logging Setup ───
def _setup_logging(log_file: Path) -> None:
    """
    Configure application-wide logging.

    Args:
        log_file: Path to the log file.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.FileHandler(str(log_file), encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


# ─── Main ───
def main() -> None:
    """Main entry point for DarkPause."""
    from core.config import (
        ALL_PLATFORMS, APP_DATA_DIR, APP_NAME, RESET_HOUR, SINGLE_INSTANCE_PORT,
    )

    APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
    log_file: Path = APP_DATA_DIR / "darkpause.log"
    _setup_logging(log_file)

    logger.info("=" * 50)
    logger.info(f"  {APP_NAME} Starting...")
    logger.info("=" * 50)

    # Admin check
    if not _is_admin():
        logger.warning("⚠️ DarkPause requires Administrator privileges.")
        logger.info("🔄 Requesting elevated restart...")
        _request_admin_restart()
        sys.exit(0)

    logger.info("🔑 Running with Administrator privileges.")

    # Single instance
    _check_single_instance(SINGLE_INSTANCE_PORT)

    logger.info(f"   📁 Data dir: {APP_DATA_DIR}")
    logger.info(f"   📝 Log file: {log_file}")
    logger.info(f"   🔄 Daily reset at: {RESET_HOUR:02d}:00")

    # ─── Apply permanent blocks + DNS anti-bypass ───
    from core import hosts_manager, firewall_manager

    hosts_manager.block_permanent_domains()
    firewall_manager.block_alternative_dns()
    firewall_manager.cleanup_orphaned_allowlist()

    for platform in ALL_PLATFORMS:
        hosts_manager.block_platform(platform)

    # ─── Tkinter Root (hidden) ───
    root: tk.Tk = tk.Tk()
    root.withdraw()

    # ─── Blackout ───
    from ui.blackout import ScreenBlackout, load_persisted_blackout

    blackout: ScreenBlackout = ScreenBlackout(
        root=root,
        on_complete=lambda: logger.info("🌌 Focus session completed!"),
    )

    def start_blackout(minutes: int, locked: bool = False) -> None:
        """Start a blackout from any thread (schedules on main thread)."""
        root.after(0, lambda: blackout.start(minutes, locked=locked))

    # ─── Crash recovery: resume persisted blackout ───
    persisted: tuple[int, bool] | None = load_persisted_blackout()
    if persisted is not None:
        persisted_minutes, persisted_locked = persisted
        lock_label: str = " [LOCKED]" if persisted_locked else ""
        logger.info(
            f"🔄 Recovering blackout from crash: {persisted_minutes}m remaining.{lock_label}"
        )
        root.after(
            1500,
            lambda: blackout.start(persisted_minutes, locked=persisted_locked),
        )

    # ─── Recurring Schedules ───
    from core.scheduler import ScheduleManager

    scheduler: ScheduleManager = ScheduleManager(
        on_start_blackout=start_blackout,
        is_blackout_active=lambda: blackout.is_active,
    )
    scheduler.start()

    # ─── Control Panel (lazy-created) ───
    _panel_ref: list = [None]

    def open_panel() -> None:
        """Open the control panel window (create if not exists)."""
        from ui.control_panel import ControlPanel

        def _open():
            try:
                if _panel_ref[0] is None or not _panel_ref[0].winfo_exists():
                    logger.info("📋 Creating control panel...")
                    _panel_ref[0] = ControlPanel(
                        master=root,
                        on_start_blackout=start_blackout,
                        scheduler=scheduler,
                    )
                    logger.info("📋 Control panel created successfully.")
                else:
                    _panel_ref[0].show()
                    logger.info("📋 Control panel restored.")
            except Exception as e:
                logger.error(f"❌ Failed to open control panel: {e}", exc_info=True)

        root.after(0, _open)

    # ─── System Tray (background thread) ───
    def _flush_log() -> None:
        """Force flush all log handlers (critical for pythonw)."""
        for handler in logging.getLogger().handlers:
            handler.flush()

    try:
        logger.info("🔧 Importing tray module...")
        _flush_log()
        from ui.tray import DarkPauseTray

        logger.info("🔧 Creating tray icon...")
        _flush_log()
        tray: DarkPauseTray = DarkPauseTray(
            on_open_panel=open_panel,
            on_start_blackout=start_blackout,
        )
        logger.info("🔧 Tray icon created.")
        _flush_log()
    except Exception as e:
        logger.error(f"❌ Tray initialization failed: {e}", exc_info=True)
        _flush_log()

    def run_tray() -> None:
        """Run the tray icon in a background thread."""
        try:
            tray.run()
        except Exception as e:
            logger.error(f"Tray crashed: {e}", exc_info=True)
            _flush_log()
        finally:
            root.after(0, root.quit)

    tray_thread: threading.Thread = threading.Thread(
        target=run_tray, daemon=True, name="tray",
    )
    tray_thread.start()
    logger.info("🔧 Tray thread started.")
    _flush_log()

    # ─── Auto-open panel on boot (skip if recovering from crash blackout) ───
    if persisted is None:
        root.after(5000, open_panel)
        logger.info("🔧 Auto-open panel scheduled (5s delay).")
        _flush_log()

    # ─── Integrity check loop (every 30s) ───
    def _integrity_check() -> None:
        """
        Periodic verification that protection layers are intact.

        Checks:
        1. Permanent adult content blocks in hosts file
        2. DNS anti-bypass firewall rules
        """
        try:
            hosts_manager.verify_permanent_blocks()
            if not firewall_manager.is_dns_locked():
                logger.warning("⚠️ DNS lock was removed! Re-applying...")
                firewall_manager.block_alternative_dns()
        except Exception as e:
            logger.error(f"Integrity check error: {e}")
        finally:
            root.after(_INTEGRITY_CHECK_MS, _integrity_check)

    root.after(_INTEGRITY_CHECK_MS, _integrity_check)

    logger.info("✅ All systems initialized. Entering main loop.")
    _flush_log()

    # ─── Main Loop ───
    try:
        root.mainloop()
    except KeyboardInterrupt:
        logger.info("🛑 Interrupted by user.")
    finally:
        # Fail-safe: block everything on exit
        logger.info("🔒 Fail-safe: blocking all platforms on exit.")

        for platform in ALL_PLATFORMS:
            try:
                hosts_manager.block_platform(platform)
            except Exception:
                pass
        try:
            hosts_manager.block_permanent_domains()
        except Exception:
            pass
        # NOTE: DNS lock is intentionally NOT removed on exit.
        # It persists to protect permanent blocks across restarts.

        # Disable allowlist if active (don't lock user out of internet)
        try:
            if firewall_manager.is_allowlist_active():
                firewall_manager.disable_allowlist_mode()
        except Exception:
            pass

        if _instance_socket:
            try:
                _instance_socket.close()
            except Exception:
                pass

        logger.info("👋 DarkPause stopped.")


if __name__ == "__main__":
    main()
