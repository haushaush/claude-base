"""Slack bot configuration — credentials stored in a local JSON file.

Mirrors the Telegram version's shape so the rest of the codebase reads the
same, but Slack needs *two* tokens instead of one:

- slack_bot_token   (xoxb-…)  — the bot user OAuth token, used for Web API calls
- slack_app_token   (xapp-…)  — the app-level token with connections:write,
                                used to open the Socket Mode WebSocket

Credential keys:
- slack_bot_token
- slack_app_token
- slack_allowed_user_ids:    JSON array of Slack user IDs ("U01ABCDEF")
- slack_allowed_channel_ids: JSON array of channel IDs ("C01ABCDEF"). Empty
                             means "no channel restriction" — see auth.py.

Falls back to env vars SLACK_BOT_TOKEN / SLACK_APP_TOKEN /
SLACK_ALLOWED_USER_IDS / SLACK_ALLOWED_CHANNEL_IDS when the JSON file doesn't
have the value yet (first-run setup, or a systemd EnvironmentFile).
"""

import json
import logging
import os
from pathlib import Path

# Directory the module lives in. The credentials file sits next to it.
MODULE_DIR = Path(__file__).resolve().parent
CREDENTIALS_FILE = MODULE_DIR / ".credentials.json"

logger = logging.getLogger(__name__)

# Where Claude actually works — the directory it reads, edits and runs commands
# in. The Telegram original derived this from the module's position, because
# there the bot package lived *inside* the project it operated on.
#
# In a container that assumption breaks: the code sits at /app/slack_bot and
# the project is bind-mounted at /workspace, so deriving the path would point
# Claude at its own source. CLAUDE_WORKDIR wins when set; the derived value
# stays as the fallback for a bare-metal install that keeps the original
# layout.
DEFAULT_WORKDIR = os.getenv("CLAUDE_WORKDIR") or str(MODULE_DIR.parent)

if not Path(DEFAULT_WORKDIR).is_dir():
    logger.warning(
        "Working directory %s does not exist — Claude sessions will fail to "
        "start. Set CLAUDE_WORKDIR to the project you want the agent to work on.",
        DEFAULT_WORKDIR,
    )


def _read_creds() -> dict:
    try:
        with open(CREDENTIALS_FILE, "r", encoding="utf-8") as fh:
            data = json.load(fh)
            return data if isinstance(data, dict) else {}
    except FileNotFoundError:
        return {}
    except (OSError, json.JSONDecodeError):
        logger.warning("Failed to read %s", CREDENTIALS_FILE, exc_info=True)
        return {}


def _write_creds(data: dict) -> None:
    tmp = CREDENTIALS_FILE.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, sort_keys=True)
    os.replace(tmp, CREDENTIALS_FILE)
    # Tokens are secrets — keep the file owner-readable only.
    try:
        os.chmod(CREDENTIALS_FILE, 0o600)
    except OSError:
        pass


def _read_setting(key: str) -> str | None:
    val = _read_creds().get(key)
    return str(val) if val is not None else None


def _write_setting(key: str, value: str) -> None:
    data = _read_creds()
    data[key] = value
    _write_creds(data)


def _parse_id_list(raw: str) -> set[str]:
    if not raw:
        return set()
    try:
        parsed = (
            json.loads(raw)
            if raw.strip().startswith("[")
            else [x.strip() for x in raw.split(",")]
        )
        return {str(x).strip() for x in parsed if str(x).strip()}
    except (ValueError, json.JSONDecodeError):
        logger.error("Could not parse id list: %r", raw)
        return set()


def get_bot_token() -> str:
    token = _read_setting("slack_bot_token") or os.getenv("SLACK_BOT_TOKEN", "")
    if not token:
        raise RuntimeError(
            "No Slack bot token configured. "
            "Run: python -m slack_bot.setup --bot-token xoxb-… --app-token xapp-… --user-id U…"
        )
    return token


def get_app_token() -> str:
    token = _read_setting("slack_app_token") or os.getenv("SLACK_APP_TOKEN", "")
    if not token:
        raise RuntimeError(
            "No Slack app-level token configured (xapp-…, scope connections:write). "
            "Socket Mode cannot connect without it."
        )
    return token


def get_allowed_user_ids() -> set[str]:
    return _parse_id_list(
        _read_setting("slack_allowed_user_ids")
        or os.getenv("SLACK_ALLOWED_USER_IDS", "")
    )


def get_allowed_channel_ids() -> set[str]:
    return _parse_id_list(
        _read_setting("slack_allowed_channel_ids")
        or os.getenv("SLACK_ALLOWED_CHANNEL_IDS", "")
    )


def set_bot_token(token: str) -> None:
    _write_setting("slack_bot_token", token.strip())


def set_app_token(token: str) -> None:
    _write_setting("slack_app_token", token.strip())


def set_allowed_user_ids(user_ids: list[str]) -> None:
    _write_setting("slack_allowed_user_ids", json.dumps(sorted(set(user_ids))))


def set_allowed_channel_ids(channel_ids: list[str]) -> None:
    _write_setting("slack_allowed_channel_ids", json.dumps(sorted(set(channel_ids))))
