"""Slack code bot — Claude Agent SDK with full tool access, one session per thread.

Port of the Telegram bot. What changed and why:

  * Socket Mode instead of webhooks. No public HTTPS endpoint, no reverse
    proxy, no certificate on the VPS — the process dials out.
  * A "chat" is a Slack **thread**, not a channel. Session key is
    "<channel>:<thread_ts>", so several parallel conversations can run in the
    same channel with separate Claude contexts.
  * Every event is acked immediately and the actual work runs in a background
    task. Slack retries any event it doesn't hear back from within 3 seconds,
    and a retry here would mean the agent runs the same prompt twice against
    the repo. `_seen_events` catches retries that slip through anyway.
  * chat.update is rate limited per channel (~1/s). The Telegram version
    throttled the tool message and the body message independently; here they
    share one gate, otherwise two independent 1.2s throttles produce ~1.7
    calls/s and start collecting 429s mid-stream.
"""

import asyncio
import logging
import os
import time
from collections import OrderedDict

import aiohttp
from slack_bolt.adapter.socket_mode.aiohttp import AsyncSocketModeHandler
from slack_bolt.async_app import AsyncApp
from slack_sdk.errors import SlackApiError

from slack_bot import headroom
from slack_bot.auth import is_authorized, is_bot_event, require_auth
from slack_bot.claude_session import SessionManager, StreamEvent
from slack_bot.config import (
    DEFAULT_WORKDIR,
    get_allowed_user_ids,
    get_app_token,
    get_bot_token,
)
from slack_bot.render import (
    SAFE_MD_CAP,
    ReplyState,
    find_split_point,
    thread_lang,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)
logging.getLogger("slack_bolt").setLevel(
    logging.DEBUG if os.getenv("SLACK_DEBUG") == "1" else logging.WARNING
)

# --- Slack API pacing -------------------------------------------------------
# chat.update sits in Slack's per-channel "1 message per second" band. Both the
# tool trace and the answer body update through this gate.
MIN_UPDATE_INTERVAL = 1.1
# Additional per-message throttle so a fast token stream doesn't burn the whole
# channel budget on the body while the tool trace starves.
EDIT_MIN_INTERVAL = 1.6

FILE_DIR = os.environ.get("SLACK_BOT_FILE_DIR", "/tmp/slack-files")
FILE_MAX_AGE_SECONDS = 7 * 24 * 3600

# Announce restarts here (channel ID). Optional.
BROADCAST_CHANNEL = os.environ.get("SLACK_BROADCAST_CHANNEL", "")

app = AsyncApp(token=get_bot_token())
session_manager = SessionManager(cwd=DEFAULT_WORKDIR)

# Slack retries events; dedupe on the client_msg_id / event ts.
_seen_events: "OrderedDict[str, float]" = OrderedDict()
_SEEN_MAX = 2000

# Slash commands arrive WITHOUT thread_ts, even when invoked inside a thread.
# So remember the thread each user last talked to the bot in, per channel, and
# apply /claude-reset & friends there.
_last_thread: dict[tuple[str, str], str] = {}

# Per-channel timestamp of the last chat.update, for the shared gate.
_last_update_at: dict[str, float] = {}
_update_locks: dict[str, asyncio.Lock] = {}


if os.getenv("SLACK_DEBUG") == "1":

    @app.middleware
    async def _log_every_payload(body, next):
        """Log every inbound Socket Mode payload before any routing happens.

        Kept in the codebase because it is the only way to tell "Slack sent
        nothing" apart from "a handler dropped it" — a distinction that costs
        hours to make without it.
        """
        logger.info("RAW EVENT: %s", str(body)[:400])
        await next()


def _session_key(channel: str, thread_ts: str) -> str:
    return f"{channel}:{thread_ts}"


def _split_key(session_key: str) -> tuple[str, str]:
    channel, _, thread_ts = session_key.partition(":")
    return channel, thread_ts


def _is_duplicate(event_id: str | None) -> bool:
    if not event_id:
        return False
    now = time.monotonic()
    if event_id in _seen_events:
        return True
    _seen_events[event_id] = now
    while len(_seen_events) > _SEEN_MAX:
        _seen_events.popitem(last=False)
    return False


# ---------------------------------------------------------------------------
# Slack write helpers — everything that touches chat.update goes through here
# ---------------------------------------------------------------------------


async def _channel_gate(channel: str) -> None:
    """Hold until this channel is allowed another write."""
    lock = _update_locks.setdefault(channel, asyncio.Lock())
    async with lock:
        elapsed = time.monotonic() - _last_update_at.get(channel, 0.0)
        if elapsed < MIN_UPDATE_INTERVAL:
            await asyncio.sleep(MIN_UPDATE_INTERVAL - elapsed)
        _last_update_at[channel] = time.monotonic()


async def _post(client, channel: str, thread_ts: str, blocks: list[dict], text: str) -> str | None:
    """Post into a thread. `text` is the notification fallback, not the body."""
    await _channel_gate(channel)
    try:
        resp = await client.chat_postMessage(
            channel=channel, thread_ts=thread_ts, blocks=blocks, text=text
        )
        return resp["ts"]
    except SlackApiError as e:
        if e.response.get("error") == "ratelimited":
            await asyncio.sleep(float(e.response.headers.get("Retry-After", 2)))
            return await _post(client, channel, thread_ts, blocks, text)
        logger.warning("chat_postMessage failed: %s", e)
        return None


async def _update(client, channel: str, ts: str, blocks: list[dict], text: str) -> bool:
    await _channel_gate(channel)
    try:
        await client.chat_update(channel=channel, ts=ts, blocks=blocks, text=text)
        return True
    except SlackApiError as e:
        err = e.response.get("error")
        if err == "ratelimited":
            await asyncio.sleep(float(e.response.headers.get("Retry-After", 2)))
            return await _update(client, channel, ts, blocks, text)
        # msg_too_long / invalid_blocks: the caller's rollover logic should have
        # prevented this. Log loudly — a silent failure looks like a frozen stream.
        logger.warning("chat_update failed (%s) channel=%s ts=%s", err, channel, ts)
        return False


async def _react(client, channel: str, ts: str, name: str, add: bool = True) -> None:
    """Slack has no typing indicator — a reaction on the user's message is the
    conventional substitute."""
    try:
        if add:
            await client.reactions_add(channel=channel, timestamp=ts, name=name)
        else:
            await client.reactions_remove(channel=channel, timestamp=ts, name=name)
    except SlackApiError:
        pass  # already_reacted / no_reaction are both harmless


# ---------------------------------------------------------------------------
# Flushing
# ---------------------------------------------------------------------------


async def _flush_tool(client, state: ReplyState, done: bool, force: bool = False) -> None:
    now = time.monotonic()
    if not force and not done and (now - state.last_tool_edit_at) < EDIT_MIN_INTERVAL:
        return
    rendered = state.render_tool_text(done)
    if rendered == state.last_tool_rendered:
        return
    blocks = state.render_tool_blocks(done)
    if state.tool_ts is None:
        state.tool_ts = await _post(client, state.channel, state.thread_ts, blocks, "🔄")
    else:
        await _update(client, state.channel, state.tool_ts, blocks, "🔄")
    state.last_tool_rendered = rendered
    state.last_tool_edit_at = now


async def _flush_body(client, state: ReplyState, done: bool, force: bool = False) -> None:
    now = time.monotonic()
    if not force and not done and (now - state.last_body_edit_at) < EDIT_MIN_INTERVAL:
        return
    body_md = state.render_body_md()
    if not body_md:
        return

    # Rollover: seal the current message and continue in a new one rather than
    # letting the update silently fail past the block limit.
    while len(body_md) > SAFE_MD_CAP:
        cut = find_split_point(body_md, SAFE_MD_CAP)
        head = body_md[:cut].strip()
        blocks = [{"type": "section", "text": {"type": "mrkdwn", "text": _md(head)}}]
        if state.body_ts is None:
            state.body_ts = await _post(client, state.channel, state.thread_ts, blocks, head[:120])
            state.body_msgs_sent += 1
        else:
            await _update(client, state.channel, state.body_ts, blocks, head[:120])
        state.seal_first_n(cut)
        body_md = state.render_body_md()

    rendered = body_md
    if rendered == state.last_body_rendered:
        return
    blocks = state.render_body_blocks()
    if state.body_ts is None:
        state.body_ts = await _post(
            client, state.channel, state.thread_ts, blocks, rendered[:120]
        )
        state.body_msgs_sent += 1
    else:
        await _update(client, state.channel, state.body_ts, blocks, rendered[:120])
    state.last_body_rendered = rendered
    state.last_body_edit_at = now


def _md(text: str) -> str:
    from slack_bot.md_to_mrkdwn import md_to_mrkdwn

    return md_to_mrkdwn(text)[:2900] or "…"


async def _finalize(client, state: ReplyState) -> None:
    await _flush_body(client, state, done=True, force=True)
    await _flush_tool(client, state, done=True, force=True)
    # No tools fired and we have a body: the "🔄 Arbeite…" placeholder is noise.
    if state.tool_ts and not state.tool_calls and state.body_ts:
        try:
            await client.chat_delete(channel=state.channel, ts=state.tool_ts)
        except SlackApiError:
            pass


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------


async def _dispatch(client, channel: str, thread_ts: str, user_ts: str, prompt: str) -> None:
    key = _session_key(channel, thread_ts)
    state = ReplyState(
        channel=channel, thread_ts=thread_ts, lang=thread_lang(key, prompt)
    )
    await _react(client, channel, user_ts, "hourglass_flowing_sand", add=True)

    done = False
    try:
        async for ev in session_manager.send(key, prompt):
            tool_changed = body_changed = False
            if ev.kind == "tool_use":
                state.add_tool(ev.tool_name, ev.tool_input_preview)
                tool_changed = True
            elif ev.kind == "text_delta":
                state.add_text(ev.text)
                body_changed = True
            elif ev.kind == "info":
                await _post(
                    client,
                    channel,
                    thread_ts,
                    [{"type": "context", "elements": [{"type": "mrkdwn", "text": ev.text}]}],
                    ev.text[:120],
                )
            elif ev.kind == "done":
                done = True
            elif ev.kind == "error":
                state.add_text(f"\n\n⚠️ {ev.text}")
                body_changed = True
                done = True

            if tool_changed or done:
                await _flush_tool(client, state, done=done)
            if body_changed or done:
                await _flush_body(client, state, done=done)
            if done:
                break
    except Exception as e:  # noqa: BLE001 — never let a turn kill the process
        logger.exception("dispatch failed channel=%s thread=%s", channel, thread_ts)
        state.add_text(f"\n\n⚠️ Unerwarteter Fehler: {e}")
        await _flush_body(client, state, done=True, force=True)
        await _flush_tool(client, state, done=True, force=True)
    finally:
        await _react(client, channel, user_ts, "hourglass_flowing_sand", add=False)
        await _react(client, channel, user_ts, "white_check_mark", add=True)

    await _finalize(client, state)


# ---------------------------------------------------------------------------
# Files
# ---------------------------------------------------------------------------


def _cleanup_old_files() -> None:
    try:
        now = time.time()
        for name in os.listdir(FILE_DIR):
            path = os.path.join(FILE_DIR, name)
            if os.path.isfile(path) and now - os.path.getmtime(path) > FILE_MAX_AGE_SECONDS:
                os.remove(path)
    except OSError:
        pass


async def _download_files(event: dict) -> list[str]:
    """Pull attachments to disk so Claude can Read them.

    Slack file URLs are private — unlike Telegram's file_id flow you must send
    the bot token as a Bearer header or you get an HTML login page back.
    """
    files = event.get("files") or []
    if not files:
        return []
    os.makedirs(FILE_DIR, exist_ok=True)
    _cleanup_old_files()
    token = get_bot_token()
    paths: list[str] = []
    async with aiohttp.ClientSession() as sess:
        for f in files:
            url = f.get("url_private_download") or f.get("url_private")
            if not url:
                continue
            safe = "".join(c for c in (f.get("name") or f["id"]) if c.isalnum() or c in "._-")
            path = os.path.join(FILE_DIR, f"{f['id']}_{safe}")
            try:
                async with sess.get(url, headers={"Authorization": f"Bearer {token}"}) as resp:
                    if resp.status != 200:
                        logger.warning("file download %s -> HTTP %s", f["id"], resp.status)
                        continue
                    with open(path, "wb") as fh:
                        fh.write(await resp.read())
                paths.append(path)
            except Exception:
                logger.warning("file download failed for %s", f.get("id"), exc_info=True)
    return paths


def _build_prompt(text: str, file_paths: list[str]) -> str:
    if not file_paths:
        return text
    listing = "\n".join(f"- {p}" for p in file_paths)
    note = (
        f"\n\n[Der User hat {len(file_paths)} Datei(en) angehängt. "
        f"Lies sie mit dem Read-Tool:\n{listing}\n]"
    )
    return (text or "Schau dir die angehängten Dateien an.") + note


# ---------------------------------------------------------------------------
# Event handlers
# ---------------------------------------------------------------------------


def _strip_mention(text: str, bot_user_id: str) -> str:
    return (text or "").replace(f"<@{bot_user_id}>", "").strip()


@require_auth
async def _handle_user_message(event: dict, client) -> None:
    channel = event["channel"]
    ts = event["ts"]
    thread_ts = event.get("thread_ts") or ts
    user = event["user"]
    _last_thread[(channel, user)] = thread_ts

    auth = await client.auth_test()
    text = _strip_mention(event.get("text", ""), auth["user_id"])
    paths = await _download_files(event)
    prompt = _build_prompt(text, paths)
    if not prompt.strip():
        return
    await _dispatch(client, channel, thread_ts, ts, prompt)


@app.event("app_mention")
async def on_mention(event, client, ack=None):
    if ack:
        await ack()
    if _is_duplicate(event.get("client_msg_id") or f"{event.get('channel')}:{event.get('ts')}"):
        return
    asyncio.create_task(_handle_user_message(event, client))


@app.event("message")
async def on_message(event, client, logger_=None):
    """DMs, and follow-up replies inside a thread the bot is already in.

    Skips anything that also produced an app_mention (Slack sends both), and
    anything from a bot — including this app, which would otherwise answer
    itself in a loop.
    """
    if is_bot_event(event) or event.get("subtype"):
        return
    channel_type = event.get("channel_type")
    thread_ts = event.get("thread_ts")

    if channel_type != "im":
        # In channels: only follow-ups inside a thread that already has a
        # session. A fresh in-channel message needs an explicit @mention.
        if not thread_ts:
            return
        key = _session_key(event["channel"], thread_ts)
        if key not in session_manager._sessions:  # noqa: SLF001
            return
        auth = await client.auth_test()
        if f"<@{auth['user_id']}>" in (event.get("text") or ""):
            return  # app_mention already handled it

    if _is_duplicate(event.get("client_msg_id") or f"{event.get('channel')}:{event.get('ts')}"):
        return
    asyncio.create_task(_handle_user_message(event, client))


# ---------------------------------------------------------------------------
# Slash commands
#
# Socket Mode delivers these over the WebSocket, so no Request URL is needed in
# the app manifest. They do NOT carry thread_ts even when typed inside a
# thread — hence the _last_thread fallback.
# ---------------------------------------------------------------------------


async def _resolve_thread(command: dict, client) -> str | None:
    key = (command["channel_id"], command["user_id"])
    thread = _last_thread.get(key)
    if thread is None:
        await client.chat_postEphemeral(
            channel=command["channel_id"],
            user=command["user_id"],
            text="Kein aktiver Thread in diesem Channel. Schreib mich erst in einem Thread an.",
        )
    return thread


def _guard(command: dict) -> bool:
    return command["user_id"] in get_allowed_user_ids()


@app.command("/claude-reset")
async def cmd_reset(ack, command, client):
    await ack()
    if not _guard(command):
        return
    thread = await _resolve_thread(command, client)
    if not thread:
        return
    existed = await session_manager.reset(_session_key(command["channel_id"], thread))
    await client.chat_postMessage(
        channel=command["channel_id"],
        thread_ts=thread,
        text="🧹 Session zurückgesetzt." if existed else "Keine aktive Session in diesem Thread.",
    )


@app.command("/claude-plan")
async def cmd_plan(ack, command, client):
    await ack()
    if not _guard(command):
        return
    thread = await _resolve_thread(command, client)
    if not thread:
        return
    prev = await session_manager.set_mode(_session_key(command["channel_id"], thread), "plan")
    await client.chat_postMessage(
        channel=command["channel_id"],
        thread_ts=thread,
        text="📋 Plan-Mode an." if prev != "plan" else "📋 Plan-Mode war schon an.",
    )


@app.command("/claude-exitplan")
async def cmd_exitplan(ack, command, client):
    await ack()
    if not _guard(command):
        return
    thread = await _resolve_thread(command, client)
    if not thread:
        return
    prev = await session_manager.set_mode(
        _session_key(command["channel_id"], thread), "bypassPermissions"
    )
    await client.chat_postMessage(
        channel=command["channel_id"],
        thread_ts=thread,
        text="🟢 Plan-Mode aus." if prev == "plan" else "🟢 Plan-Mode war schon aus.",
    )


@app.command("/claude-help")
async def cmd_help(ack, command, client):
    await ack()
    if not _guard(command):
        return
    await client.chat_postEphemeral(
        channel=command["channel_id"],
        user=command["user_id"],
        text=(
            "*Claude Code Bot*\n"
            "Erwähn mich in einem Channel oder schreib mir per DM. "
            "Jeder Thread ist eine eigene Session mit eigenem Kontext.\n\n"
            "`/claude-plan` · Plan-Mode an (nur planen, nichts ausführen)\n"
            "`/claude-exitplan` · Plan-Mode aus\n"
            "`/claude-reset` · Session im aktuellen Thread verwerfen\n"
            "`/claude-status` · aktive Sessions\n\n"
            "Commands beziehen sich auf den Thread, in dem du zuletzt geschrieben hast."
        ),
    )


@app.command("/claude-status")
async def cmd_status(ack, command, client):
    await ack()
    if not _guard(command):
        return
    keys = list(session_manager._sessions.keys())  # noqa: SLF001
    lines = [f"• `{k}`" for k in keys] or ["_keine aktiven Sessions_"]
    await client.chat_postEphemeral(
        channel=command["channel_id"],
        user=command["user_id"],
        text="*Aktive Sessions*\n" + "\n".join(lines),
    )


# ---------------------------------------------------------------------------
# Proactive push — turns Claude starts on its own (wake-ups, background tasks)
# ---------------------------------------------------------------------------


async def _push(session_key: str, ev: StreamEvent) -> None:
    channel, thread_ts = _split_key(session_key)
    if ev.kind not in ("text_delta", "error", "info"):
        return
    text = ev.text.strip()
    if not text:
        return
    try:
        await _post(
            app.client,
            channel,
            thread_ts,
            [{"type": "section", "text": {"type": "mrkdwn", "text": _md(text)}}],
            text[:120],
        )
    except Exception:
        logger.exception("proactive push failed for %s", session_key)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------


async def _main() -> None:
    if not get_allowed_user_ids():
        raise SystemExit(
            "Refusing to start with an empty user allowlist — the bot executes "
            "shell commands. Run: python -m slack_bot.setup --user-id U…"
        )

    base_url = headroom.ensure_proxy()
    if base_url:
        os.environ["ANTHROPIC_BASE_URL"] = base_url

    session_manager.set_push_handler(_push)

    if BROADCAST_CHANNEL:
        try:
            await app.client.chat_postMessage(
                channel=BROADCAST_CHANNEL, text="· online"
            )
        except SlackApiError:
            logger.warning("broadcast failed", exc_info=True)

    handler = AsyncSocketModeHandler(app, get_app_token())
    try:
        await handler.start_async()
    finally:
        await session_manager.shutdown_all()


def main() -> None:
    try:
        asyncio.run(_main())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
