"""
DarkPause - User-Configurable Permanent Blocks.

JSON-backed storage for custom permanent website blocks.
Users can add/remove blocks from the UI, which persist across restarts.
These blocks merge with the hardcoded PERMANENT_BLOCK_DOMAINS in config.py.
"""

import json
import logging
from pathlib import Path

from core.config import APP_DATA_DIR, PERMANENT_BLOCK_DOMAINS

logger = logging.getLogger(__name__)

_BLOCKS_FILE: Path = APP_DATA_DIR / "permanent_blocks.json"

# ─── Quick-Add Presets ───

PRESETS: list[dict[str, str | list[str]]] = [
    {
        "label": "Twitter / X",
        "domains": ["twitter.com", "www.twitter.com", "x.com", "www.x.com"],
    },
    {
        "label": "TikTok",
        "domains": [
            "tiktok.com", "www.tiktok.com",
            "vm.tiktok.com", "m.tiktok.com",
        ],
    },
    {
        "label": "Reddit",
        "domains": [
            "reddit.com", "www.reddit.com",
            "old.reddit.com", "i.redd.it",
        ],
    },
    {
        "label": "Facebook",
        "domains": [
            "facebook.com", "www.facebook.com",
            "m.facebook.com", "web.facebook.com",
        ],
    },
]


# ─── Load / Save ───


def load_user_blocks() -> list[dict]:
    """
    Load user-configured permanent blocks from disk.

    Returns:
        list[dict]: List of block entries, each with 'label' and 'domains'.
    """
    try:
        if not _BLOCKS_FILE.exists():
            return []
        raw: str = _BLOCKS_FILE.read_text(encoding="utf-8")
        data = json.loads(raw)
        if not isinstance(data, list):
            return []
        return data
    except Exception as e:
        logger.warning(f"Failed to load user blocks: {e}")
        return []


def save_user_blocks(blocks: list[dict]) -> None:
    """
    Save user-configured permanent blocks to disk.

    Args:
        blocks: List of block entries, each with 'label' and 'domains'.
    """
    try:
        APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
        _BLOCKS_FILE.write_text(
            json.dumps(blocks, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception as e:
        logger.error(f"Failed to save user blocks: {e}")


# ─── CRUD ───


def add_block(label: str, domains: list[str]) -> None:
    """
    Add a new permanent block entry.

    Args:
        label: Human-readable name (e.g. "Twitter").
        domains: List of domains to block.
    """
    blocks: list[dict] = load_user_blocks()
    blocks.append({"label": label.strip(), "domains": domains})
    save_user_blocks(blocks)
    logger.info(f"🔒 Added permanent block: {label} ({len(domains)} domains)")


def remove_block(label: str) -> None:
    """
    Remove a permanent block entry by label.

    Args:
        label: The label of the block to remove.
    """
    blocks: list[dict] = load_user_blocks()
    blocks = [b for b in blocks if b.get("label") != label]
    save_user_blocks(blocks)
    logger.info(f"🔓 Removed permanent block: {label}")


def get_all_permanent_domains() -> list[str]:
    """
    Get the merged list of all permanently blocked domains.

    Combines the hardcoded PERMANENT_BLOCK_DOMAINS from config.py
    with any user-configured blocks from the JSON file.

    Returns:
        list[str]: All domains that should be permanently blocked.
    """
    all_domains: list[str] = list(PERMANENT_BLOCK_DOMAINS)

    for block in load_user_blocks():
        domains = block.get("domains", [])
        if isinstance(domains, list):
            all_domains.extend(domains)

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for d in all_domains:
        if d not in seen:
            seen.add(d)
            unique.append(d)

    return unique
