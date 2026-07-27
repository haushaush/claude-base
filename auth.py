"""User + channel allowlist for the Slack bot.

The bot runs with permission_mode="bypassPermissions" — it executes arbitrary
shell commands and edits files on the server without asking. In Telegram the
attack surface was "who knows the bot handle". In a Slack workspace every
member can DM the app or mention it, and guests in shared channels may reach it
too. So this module gates on BOTH axes:

  1. user_id must be on the allowlist — always, no exception.
  2. channel_id must be on the channel allowlist, IF one is configured.
     An empty channel allowlist means "any channel the bot is in", which is
     only sane while you are the sole allowed user.

Bot messages are rejected unconditionally: without that, the bot answering in a
thread can retrigger itself into a loop.
"""

import logging
from functools import wraps

from slack_bot.config import get_allowed_channel_ids, get_allowed_user_ids

logger = logging.getLogger(__name__)


def is_authorized(user_id: str | None, channel_id: str | None) -> bool:
    if not user_id:
        return False
    if user_id not in get_allowed_user_ids():
        return False
    allowed_channels = get_allowed_channel_ids()
    if allowed_channels and (channel_id not in allowed_channels):
        return False
    return True


def is_bot_event(event: dict) -> bool:
    """True for anything the app itself (or another bot) produced."""
    return bool(
        event.get("bot_id")
        or event.get("subtype") == "bot_message"
        or event.get("user") is None
    )


def require_auth(handler):
    """Decorator for Bolt event handlers: deny before any work happens.

    Wraps an ``async def handler(event, client, ...)`` style callable. The
    rejection notice goes back as an ephemeral message so an unauthorized user
    gets feedback without polluting the channel.
    """

    @wraps(handler)
    async def wrapper(event: dict, client, *args, **kwargs):
        uid = event.get("user")
        cid = event.get("channel")
        if is_bot_event(event):
            return
        if not is_authorized(uid, cid):
            logger.warning(
                "Rejected event from user=%s channel=%s text=%r",
                uid,
                cid,
                (event.get("text") or "")[:200],
            )
            try:
                await client.chat_postEphemeral(
                    channel=cid,
                    user=uid,
                    text=f"Nicht autorisiert. Deine User-ID ist `{uid}`.",
                )
            except Exception:
                logger.debug("ephemeral rejection failed", exc_info=True)
            return
        return await handler(event, client, *args, **kwargs)

    return wrapper
