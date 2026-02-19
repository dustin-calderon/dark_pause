"""
DarkPause - Windows Firewall Manager.

Adds outbound firewall rules to prevent DNS-based bypass of hosts file
blocking. Two layers:

1. Block known public DNS server IPs (Google, Cloudflare, OpenDNS, Quad9).
   This prevents users from changing their system DNS or using browser
   DNS-over-HTTPS (DoH) to circumvent hosts file entries.

2. Block DNS-over-TLS (DoT) port 853 to any server.
   This closes the DoT bypass vector completely.

These rules are intentionally designed to PERSIST across app restarts
and system reboots. They should only be removed via explicit cleanup
(uninstall scenario).

Note: If the user's ISP/router uses one of these DNS servers as the
primary resolver, internet connectivity will be affected. This is
an acceptable trade-off for a digital discipline tool.
"""

import logging
import socket
import subprocess
import threading
from pathlib import Path

logger = logging.getLogger(__name__)

_RULE_PREFIX: str = "DarkPause"
_SUBPROCESS_TIMEOUT: int = 10

# Well-known public DNS IPs that enable hosts file bypass
_PUBLIC_DNS_SERVERS: list[str] = [
    "8.8.8.8",         # Google DNS
    "8.8.4.4",         # Google DNS secondary
    "1.1.1.1",         # Cloudflare DNS (also DoH)
    "1.0.0.1",         # Cloudflare DNS secondary
    "208.67.222.222",  # OpenDNS
    "208.67.220.220",  # OpenDNS secondary
    "9.9.9.9",         # Quad9
    "149.112.112.112", # Quad9 secondary
]

_DNS_RULE_NAME: str = f"{_RULE_PREFIX}-DNS-Lock"
_DOT_RULE_NAME: str = f"{_RULE_PREFIX}-DoT-Lock"


def _run_netsh(args: list[str]) -> tuple[bool, str]:
    """
    Execute a netsh command and return the result.

    Args:
        args: Arguments to pass to netsh.

    Returns:
        tuple[bool, str]: (success, combined stdout+stderr output).
    """
    cmd: list[str] = ["netsh"] + args
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
            timeout=_SUBPROCESS_TIMEOUT,
        )
        output: str = (result.stdout + result.stderr).strip()
        return result.returncode == 0, output
    except subprocess.TimeoutExpired:
        logger.warning(f"netsh timed out: {' '.join(cmd)}")
        return False, "timeout"
    except Exception as e:
        logger.error(f"netsh execution failed: {e}")
        return False, str(e)


def _delete_rule(name: str) -> bool:
    """Delete a firewall rule by name (idempotent, no error on missing)."""
    success, _ = _run_netsh([
        "advfirewall", "firewall", "delete", "rule",
        f"name={name}",
    ])
    return success


# ─── Public API ───


def block_alternative_dns() -> bool:
    """
    Block outbound traffic to known public DNS servers and DoT port.

    Creates two firewall rules:
    - DarkPause-DNS-Lock: blocks IPs of Google/Cloudflare/OpenDNS/Quad9
    - DarkPause-DoT-Lock: blocks TCP port 853 (DNS-over-TLS)

    This is idempotent — safe to call multiple times.

    Returns:
        bool: True if at least the DNS IP rule was applied successfully.
    """
    # Clean up existing rules first (idempotent)
    _delete_rule(_DNS_RULE_NAME)
    _delete_rule(_DOT_RULE_NAME)

    ip_list: str = ",".join(_PUBLIC_DNS_SERVERS)

    # Rule 1: Block known public DNS server IPs
    dns_ok, dns_out = _run_netsh([
        "advfirewall", "firewall", "add", "rule",
        f"name={_DNS_RULE_NAME}",
        "dir=out", "action=block",
        "protocol=any",
        f"remoteip={ip_list}",
        "enable=yes",
    ])

    if dns_ok:
        logger.info(
            f"🔒 DNS lock: blocked {len(_PUBLIC_DNS_SERVERS)} public DNS servers."
        )
    else:
        logger.warning(f"⚠️ DNS lock failed: {dns_out}")

    # Rule 2: Block DNS-over-TLS (port 853) to ANY server
    dot_ok, dot_out = _run_netsh([
        "advfirewall", "firewall", "add", "rule",
        f"name={_DOT_RULE_NAME}",
        "dir=out", "action=block",
        "protocol=tcp",
        "remoteport=853",
        "enable=yes",
    ])

    if dot_ok:
        logger.info("🔒 DoT lock: blocked outbound port 853.")
    else:
        logger.warning(f"⚠️ DoT lock failed: {dot_out}")

    return dns_ok


def unblock_alternative_dns() -> bool:
    """
    Remove all DNS lock firewall rules.

    Only call this during explicit uninstall, NOT during normal exit.
    The DNS lock is meant to persist across restarts.

    Returns:
        bool: True if rules were removed successfully.
    """
    dns_ok: bool = _delete_rule(_DNS_RULE_NAME)
    dot_ok: bool = _delete_rule(_DOT_RULE_NAME)

    if dns_ok or dot_ok:
        logger.info("🔓 DNS lock removed (all rules).")
    return dns_ok or dot_ok


def is_dns_locked() -> bool:
    """
    Check if the DNS lock firewall rule is currently active.

    Returns:
        bool: True if the DNS lock rule exists in Windows Firewall.
    """
    success, output = _run_netsh([
        "advfirewall", "firewall", "show", "rule",
        f"name={_DNS_RULE_NAME}",
    ])
    return success and _DNS_RULE_NAME in output


def cleanup_all_rules() -> None:
    """
    Remove ALL DarkPause firewall rules.

    Use this during uninstall to leave the system clean.
    """
    _delete_rule(_DNS_RULE_NAME)
    _delete_rule(_DOT_RULE_NAME)
    disable_allowlist_mode()
    logger.info("🧹 All DarkPause firewall rules cleaned up.")


# ─── Allowlist Mode (Deep Work) ───

_ALLOWLIST_BLOCK_ALL_RULE: str = f"{_RULE_PREFIX}-Allowlist-BlockAll"
_ALLOWLIST_ALLOW_PREFIX: str = f"{_RULE_PREFIX}-Allowlist-Allow"
_allowlist_active: bool = False
_allowlist_thread: threading.Thread | None = None
_allowlist_stop_event: threading.Event = threading.Event()

# State file for crash recovery
_ALLOWLIST_STATE_FILE: Path | None = None


def _get_allowlist_state_file() -> Path:
    """Lazy-load the state file path (avoids circular import at module level)."""
    global _ALLOWLIST_STATE_FILE
    if _ALLOWLIST_STATE_FILE is None:
        from core.config import APP_DATA_DIR
        _ALLOWLIST_STATE_FILE = APP_DATA_DIR / "allowlist_active.flag"
    return _ALLOWLIST_STATE_FILE


def _persist_allowlist_state(active: bool) -> None:
    """Persist allowlist active flag to disk for crash recovery."""
    try:
        state_file: Path = _get_allowlist_state_file()
        if active:
            state_file.parent.mkdir(parents=True, exist_ok=True)
            state_file.write_text("1", encoding="utf-8")
        else:
            state_file.unlink(missing_ok=True)
    except Exception as e:
        logger.debug(f"Allowlist state persist error: {e}")


def cleanup_orphaned_allowlist() -> None:
    """
    Remove orphaned allowlist firewall rules from a previous crash.

    Should be called during app startup. If the state file exists but
    the app wasn't running, it means a crash left rules behind.
    """
    try:
        state_file: Path = _get_allowlist_state_file()
        if state_file.exists():
            logger.warning("⚠️ Orphaned allowlist rules detected. Cleaning up...")
            _delete_rule(_ALLOWLIST_BLOCK_ALL_RULE)
            for suffix in ["0", "local"]:
                _delete_rule(f"{_ALLOWLIST_ALLOW_PREFIX}-{suffix}")
            state_file.unlink(missing_ok=True)
            logger.info("✅ Orphaned allowlist rules cleaned.")
    except Exception as e:
        logger.warning(f"Orphaned allowlist cleanup error: {e}")


def _resolve_domain_ips(domain: str) -> set[str]:
    """
    Resolve a domain name to its IP addresses.

    Args:
        domain: The domain name to resolve.

    Returns:
        set[str]: Set of resolved IPv4 addresses.
    """
    ips: set[str] = set()
    try:
        results = socket.getaddrinfo(domain, None, socket.AF_INET)
        for result in results:
            ips.add(result[4][0])
    except socket.gaierror as e:
        logger.debug(f"Could not resolve {domain}: {e}")
    except Exception as e:
        logger.warning(f"DNS resolution error for {domain}: {e}")
    return ips


def _get_all_allowed_ips(domains: list[str]) -> set[str]:
    """
    Resolve all allowlist domains and return combined IP set.

    Always includes essential system IPs to prevent total network breakage.

    Args:
        domains: List of domain names to resolve.

    Returns:
        set[str]: Combined set of all allowed IPs.
    """
    # Essential IPs that must always be reachable
    allowed: set[str] = {
        "127.0.0.1",       # localhost
        "255.255.255.255", # broadcast
    }

    for domain in domains:
        resolved: set[str] = _resolve_domain_ips(domain)
        if resolved:
            logger.debug(f"Resolved {domain} -> {resolved}")
            allowed.update(resolved)

    return allowed


def _apply_allowlist_rules(allowed_ips: set[str]) -> bool:
    """
    Apply firewall rules: block all outbound, then allow specific IPs.

    Args:
        allowed_ips: Set of IP addresses to allow through the firewall.

    Returns:
        bool: True if block-all rule was applied successfully.
    """
    # Remove existing allowlist rules first
    _delete_rule(_ALLOWLIST_BLOCK_ALL_RULE)
    # Delete known allow rules (fast, no probing loop)
    for suffix in ["0", "local"]:
        _delete_rule(f"{_ALLOWLIST_ALLOW_PREFIX}-{suffix}")

    # Create Block All Outbound rule
    block_ok, block_out = _run_netsh([
        "advfirewall", "firewall", "add", "rule",
        f"name={_ALLOWLIST_BLOCK_ALL_RULE}",
        "dir=out", "action=block",
        "protocol=any",
        "enable=yes",
    ])

    if not block_ok:
        logger.error(f"Failed to create block-all rule: {block_out}")
        return False

    logger.info("🚫 Allowlist: Block All Outbound rule applied.")

    # Create Allow rules for each IP
    ip_list: list[str] = sorted(allowed_ips)
    # netsh supports comma-separated IPs in a single rule
    if ip_list:
        ip_csv: str = ",".join(ip_list)
        allow_ok, allow_out = _run_netsh([
            "advfirewall", "firewall", "add", "rule",
            f"name={_ALLOWLIST_ALLOW_PREFIX}-0",
            "dir=out", "action=allow",
            "protocol=any",
            f"remoteip={ip_csv}",
            "enable=yes",
        ])
        if allow_ok:
            logger.info(f"✅ Allowlist: Allowed {len(ip_list)} IPs.")
        else:
            logger.warning(f"Failed to create allow rule: {allow_out}")

    # Always allow local network (DHCP, gateway, etc.)
    _run_netsh([
        "advfirewall", "firewall", "add", "rule",
        f"name={_ALLOWLIST_ALLOW_PREFIX}-local",
        "dir=out", "action=allow",
        "protocol=any",
        "remoteip=LocalSubnet",
        "enable=yes",
    ])

    return True


def _allowlist_refresh_loop(domains: list[str], interval: int) -> None:
    """
    Background loop that periodically re-resolves allowlist IPs.

    CDN IPs change frequently, so we need to keep rules updated.

    Args:
        domains: List of domain names to resolve.
        interval: Seconds between refresh cycles.
    """
    while not _allowlist_stop_event.is_set():
        _allowlist_stop_event.wait(timeout=interval)
        if _allowlist_stop_event.is_set():
            break
        logger.debug("🔄 Allowlist: refreshing domain IPs...")
        allowed_ips: set[str] = _get_all_allowed_ips(domains)
        _apply_allowlist_rules(allowed_ips)


def enable_allowlist_mode() -> bool:
    """
    Enable Allowlist / Deep Work mode.

    Blocks ALL outbound internet traffic except for domains in
    ALLOWLIST_DOMAINS. Starts a background thread to periodically
    re-resolve domain IPs.

    Returns:
        bool: True if allowlist mode was enabled successfully.
    """
    global _allowlist_active, _allowlist_thread

    from core.config import ALLOWLIST_DOMAINS, ALLOWLIST_REFRESH_SECONDS

    if _allowlist_active:
        logger.warning("Allowlist mode already active.")
        return True

    logger.info("🌐 Enabling Allowlist / Deep Work mode...")

    # BUG-3 FIX: Clear stop event BEFORE applying rules, so the refresh
    # thread always starts clean even if a previous enable/disable cycle
    # left the event in a set state.
    _allowlist_stop_event.clear()

    allowed_ips: set[str] = _get_all_allowed_ips(ALLOWLIST_DOMAINS)
    if not _apply_allowlist_rules(allowed_ips):
        return False

    _allowlist_active = True

    _allowlist_thread = threading.Thread(
        target=_allowlist_refresh_loop,
        args=(ALLOWLIST_DOMAINS, ALLOWLIST_REFRESH_SECONDS),
        daemon=True,
        name="allowlist-refresh",
    )
    _allowlist_thread.start()

    logger.info("✅ Allowlist mode ACTIVE. Only allowed domains are reachable.")
    _persist_allowlist_state(active=True)
    return True


def disable_allowlist_mode() -> None:
    """
    Disable Allowlist / Deep Work mode.

    Removes all allowlist firewall rules and stops the refresh thread.
    Internet access is fully restored.
    """
    global _allowlist_active, _allowlist_thread

    _allowlist_stop_event.set()
    if _allowlist_thread and _allowlist_thread.is_alive():
        _allowlist_thread.join(timeout=5)
    _allowlist_thread = None

    _delete_rule(_ALLOWLIST_BLOCK_ALL_RULE)
    # Clean up allow rules
    for suffix in ["0", "local"]:
        _delete_rule(f"{_ALLOWLIST_ALLOW_PREFIX}-{suffix}")

    _allowlist_active = False
    _persist_allowlist_state(active=False)
    logger.info("🔓 Allowlist mode DISABLED. Full internet restored.")


def is_allowlist_active() -> bool:
    """Check if Allowlist / Deep Work mode is currently active."""
    return _allowlist_active
