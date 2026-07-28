"""Optional headroom compression proxy for the bot's Claude sessions.

The Agent SDK spawns the `claude` CLI as a subprocess that inherits this
process's environment. Setting ANTHROPIC_BASE_URL to a local headroom proxy
routes every session through it, compressing tool outputs / stale file reads
before they reach the API (see project memory project-headroom-evaluation).

DEFENSIVE BY DESIGN: a dead or missing proxy must never take the bot down.
`ensure_proxy` returns the base URL only when the proxy is confirmed healthy;
on any failure it returns None and the caller leaves ANTHROPIC_BASE_URL unset,
so Claude talks to the API directly exactly as before.
"""

import logging
import os
import shlex
import subprocess
import time
import urllib.request

logger = logging.getLogger(__name__)

# Tunable without code edits. The compression flags default to the verified
# config (tool-result interception + AST code-awareness); override via
# HEADROOM_PROXY_ARGS if needed. HEADROOM_DISABLE=1 skips the proxy entirely.
_PORT = int(os.getenv("HEADROOM_PORT", "8787"))
_BIN = os.path.expanduser(os.getenv("HEADROOM_BIN", "~/.headroom-venv/bin/headroom"))
_LOG = os.getenv("HEADROOM_PROXY_LOG", "/tmp/headroom-proxy.log")
_ARGS = os.getenv("HEADROOM_PROXY_ARGS", "--intercept-tool-results --code-aware")
_STARTUP_TIMEOUT_S = float(os.getenv("HEADROOM_STARTUP_TIMEOUT", "12"))


def _healthy(timeout: float = 1.5) -> bool:
    try:
        with urllib.request.urlopen(
            f"http://127.0.0.1:{_PORT}/readyz", timeout=timeout
        ) as resp:
            return resp.status == 200
    except Exception:
        return False


def ensure_proxy() -> str | None:
    """Return the proxy base URL if a healthy headroom proxy is reachable.

    Reuses an already-running proxy (a bot restart won't spawn a duplicate);
    otherwise starts one detached and waits for it to report ready. Returns
    None — and logs why — on disable, missing binary, or startup failure, so
    the bot runs without compression instead of breaking.
    """
    if os.getenv("HEADROOM_DISABLE") == "1":
        logger.info("headroom disabled (HEADROOM_DISABLE=1) — Claude runs direct")
        return None

    base = f"http://127.0.0.1:{_PORT}"
    if _healthy():
        logger.info("headroom proxy already healthy at %s — reusing", base)
        return base

    if not os.path.exists(_BIN):
        logger.warning(
            "headroom binary not found at %s — Claude runs direct (no compression)", _BIN
        )
        return None

    try:
        log_fh = open(_LOG, "ab")  # noqa: SIM115 — handed to the detached child
        subprocess.Popen(
            [_BIN, "proxy", "--port", str(_PORT), *shlex.split(_ARGS)],
            stdout=log_fh,
            stderr=log_fh,
            stdin=subprocess.DEVNULL,
            start_new_session=True,  # survive the bot; not in our process group
        )
    except Exception:
        logger.warning(
            "failed to start headroom proxy — Claude runs direct (no compression)",
            exc_info=True,
        )
        return None

    deadline = time.monotonic() + _STARTUP_TIMEOUT_S
    while time.monotonic() < deadline:
        if _healthy():
            logger.info("headroom proxy started and healthy at %s", base)
            return base
        time.sleep(0.5)

    logger.warning(
        "headroom proxy did not become ready within %.0fs — Claude runs direct",
        _STARTUP_TIMEOUT_S,
    )
    return None
