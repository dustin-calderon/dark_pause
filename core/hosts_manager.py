"""
DarkPause - Hosts File Manager.

Manages blocking/unblocking of platform domains by modifying
the Windows hosts file. Supports both timed platform blocks
and permanent blocks (adult content).

Thread-safe via global lock. Uses atomic writes and UTF-8 BOM
encoding for Windows compatibility.
"""

import logging
import subprocess
import threading
from pathlib import Path

from .config import HOSTS_FILE_PATH, REDIRECT_IP, Platform

logger = logging.getLogger(__name__)

# Thread lock for hosts file operations
_hosts_lock: threading.Lock = threading.Lock()


def _remove_readonly(path: Path = HOSTS_FILE_PATH) -> None:
    """Remove read-only attribute from hosts file if present."""
    import os
    import stat
    try:
        current = os.stat(path).st_mode
        if not (current & stat.S_IWRITE):
            os.chmod(path, current | stat.S_IWRITE)
    except Exception as e:
        logger.debug(f"Could not remove read-only attribute: {e}")


def _ensure_hosts_backup() -> None:
    """Create a backup of the hosts file if one doesn't exist."""
    from .config import APP_DATA_DIR
    backup_path = APP_DATA_DIR / "hosts.backup"
    if not backup_path.exists():
        try:
            APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
            import shutil
            shutil.copy2(HOSTS_FILE_PATH, backup_path)
            logger.info(f"📋 Hosts file backup created at: {backup_path}")
        except Exception as e:
            logger.warning(f"Could not create hosts backup: {e}")


def _read_hosts_file() -> str:
    """Read the current contents of the Windows hosts file."""
    return HOSTS_FILE_PATH.read_text(encoding="utf-8-sig")


def _write_hosts_file(content: str) -> None:
    """
    Write content to the Windows hosts file atomically.

    FIX-8: Uses tempfile.mkstemp + os.replace for true atomic writes,
    preventing corruption if the process is killed mid-write.
    Falls back to direct write if atomic write fails.
    """
    import os
    import tempfile

    _ensure_hosts_backup()
    _remove_readonly()

    fd: int = -1
    tmp_path: str = ""
    try:
        fd, tmp_path = tempfile.mkstemp(
            dir=str(HOSTS_FILE_PATH.parent),
            prefix=".hosts_",
            suffix=".tmp",
        )
        with os.fdopen(fd, "w", encoding="utf-8-sig") as f:
            fd = -1  # os.fdopen takes ownership
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, str(HOSTS_FILE_PATH))
        tmp_path = ""
        logger.info("Hosts file updated successfully (atomic).")
    except Exception as e:
        logger.warning(f"Atomic write failed ({e}), falling back to direct write.")
        try:
            HOSTS_FILE_PATH.write_text(content, encoding="utf-8-sig")
            logger.info("Hosts file updated successfully (fallback).")
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


def _build_block_section(platform: Platform) -> str:
    """Build the hosts file block section for a platform."""
    lines: list[str] = [platform.marker_start]
    lines.append(f"# DarkPause - {platform.display_name} block")
    for domain in platform.domains:
        lines.append(f"{REDIRECT_IP} {domain}")
    lines.append(platform.marker_end)
    return "\n".join(lines)


def _remove_existing_block(content: str, platform: Platform) -> str:
    """Remove existing block for a platform from hosts content."""
    result: list[str] = []
    inside_block: bool = False
    skipped_lines: list[str] = []

    for line in content.splitlines():
        if platform.marker_start in line:
            inside_block = True
            skipped_lines = []
            continue
        if inside_block and platform.marker_end in line:
            inside_block = False
            continue
        if inside_block:
            skipped_lines.append(line)
        else:
            result.append(line)

    # BUG-03 FIX: If end marker missing, restore buffered lines
    if inside_block and skipped_lines:
        logger.warning(
            f"⚠️ Corrupted hosts file: marker_end missing for {platform.display_name}. "
            f"Restoring {len(skipped_lines)} orphaned lines."
        )
        result.extend(skipped_lines)

    return "\n".join(result)


def block_platform(platform: Platform) -> bool:
    """
    Block a platform by adding redirect entries to the hosts file.

    This operation is idempotent and thread-safe.

    Args:
        platform: The Platform to block.

    Returns:
        bool: True if blocking was successful, False otherwise.
    """
    with _hosts_lock:
        try:
            content: str = _read_hosts_file()
            clean_content: str = _remove_existing_block(content, platform)
            block_section: str = _build_block_section(platform)
            new_content: str = clean_content.rstrip("\n") + "\n\n" + block_section + "\n"
            _write_hosts_file(new_content)
            _flush_dns()
            logger.info(f"✅ {platform.display_name} BLOCKED in hosts file.")
            return True
        except PermissionError:
            logger.error(
                "❌ Permission denied. Run DarkPause as Administrator."
            )
            return False
        except Exception as e:
            logger.error(f"❌ Failed to block {platform.display_name}: {e}")
            return False


def unblock_platform(platform: Platform) -> bool:
    """
    Unblock a platform by removing redirect entries from the hosts file.

    This operation is idempotent and thread-safe.

    Args:
        platform: The Platform to unblock.

    Returns:
        bool: True if unblocking was successful, False otherwise.
    """
    with _hosts_lock:
        try:
            content: str = _read_hosts_file()
            clean_content: str = _remove_existing_block(content, platform)
            _write_hosts_file(clean_content)
            _flush_dns()
            logger.info(f"✅ {platform.display_name} UNBLOCKED from hosts file.")
            return True
        except PermissionError:
            logger.error(
                "❌ Permission denied. Run DarkPause as Administrator."
            )
            return False
        except Exception as e:
            logger.error(f"❌ Failed to unblock {platform.display_name}: {e}")
            return False


def is_blocked(platform: Platform) -> bool:
    """Check if a platform is currently blocked in the hosts file."""
    try:
        content: str = _read_hosts_file()
        return (
            platform.marker_start in content
            and platform.marker_end in content
        )
    except Exception:
        return False


def _flush_dns() -> None:
    """Flush the Windows DNS cache."""
    try:
        subprocess.run(
            ["ipconfig", "/flushdns"],
            capture_output=True,
            check=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
            timeout=10,
        )
        logger.debug("DNS cache flushed.")
    except subprocess.CalledProcessError as e:
        logger.warning(f"Failed to flush DNS cache: {e}")
    except subprocess.TimeoutExpired:
        logger.warning("DNS flush timed out.")
    except Exception as e:
        logger.warning(f"DNS flush error: {e}")


def block_permanent_domains() -> bool:
    """
    Block all domains in PERMANENT_BLOCK_DOMAINS permanently.

    These are always-on blocks that have no timer and no unblock option.
    Uses its own marker section separate from timed platforms.

    Returns:
        bool: True if blocking was successful, False otherwise.
    """
    from .config import PERMANENT_BLOCK_TAG
    from .permanent_blocks import get_all_permanent_domains

    all_domains: list[str] = get_all_permanent_domains()

    if not all_domains:
        logger.debug("No permanent block domains configured.")
        return True

    marker_start: str = f"# >>> DARKPAUSE-{PERMANENT_BLOCK_TAG}-START <<<"
    marker_end: str = f"# >>> DARKPAUSE-{PERMANENT_BLOCK_TAG}-END <<<"

    lines: list[str] = [marker_start]
    lines.append("# DarkPause - Permanent Blocks (DO NOT EDIT)")
    lines.append(f"# {len(all_domains)} domains blocked")
    for domain in all_domains:
        lines.append(f"{REDIRECT_IP} {domain}")
    lines.append(marker_end)
    block_section: str = "\n".join(lines)

    with _hosts_lock:
        try:
            content: str = _read_hosts_file()

            result_lines: list[str] = []
            inside_block: bool = False
            for line in content.splitlines():
                if marker_start in line:
                    inside_block = True
                    continue
                if marker_end in line:
                    inside_block = False
                    continue
                if not inside_block:
                    result_lines.append(line)

            clean_content: str = "\n".join(result_lines)
            new_content: str = clean_content.rstrip("\n") + "\n\n" + block_section + "\n"
            _write_hosts_file(new_content)
            _flush_dns()
            logger.info(
                f"🔒 Permanent blocks applied: {len(all_domains)} domains."
            )
            return True
        except PermissionError:
            logger.error("❌ Permission denied. Run DarkPause as Administrator.")
            return False
        except Exception as e:
            logger.error(f"❌ Failed to apply permanent blocks: {e}")
            return False


def verify_permanent_blocks() -> bool:
    """
    Verify that permanent blocks are still present in the hosts file.

    If blocks were removed (manual tampering), re-applies them.
    Designed to be called periodically from an integrity check loop.

    Returns:
        bool: True if blocks are confirmed present (or re-applied).
    """
    from .config import PERMANENT_BLOCK_TAG

    marker_start: str = f"# >>> DARKPAUSE-{PERMANENT_BLOCK_TAG}-START <<<"

    try:
        content: str = _read_hosts_file()
        if marker_start in content:
            return True

        logger.warning("⚠️ Permanent blocks were removed! Re-applying...")
        return block_permanent_domains()
    except Exception as e:
        logger.error(f"Integrity check failed: {e}")
        return False

