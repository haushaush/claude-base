"""One Claude Agent SDK session per Slack thread.

Sessions stay in memory across messages so conversation context is preserved.
`reset(session_key)` tears down the session; the next message starts fresh.
"""

import asyncio
import logging
import os
from dataclasses import dataclass, field
from typing import AsyncIterator, Awaitable, Callable, Optional

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    CLIConnectionError,
    ResultMessage,
    SystemMessage,
    TextBlock,
    ToolUseBlock,
    UserMessage,
)

from slack_bot.config import DEFAULT_WORKDIR

logger = logging.getLogger(__name__)

# Auto-compact threshold. Triggered *before* the next user prompt when the
# previous turn left the context window above this many tokens. Rule:
# (mirrors his adscalr setup): compact at 250k, BUT only between tasks and only
# after memory/CONTEXT.md have been persisted — a mid-task compact may overshoot
# the threshold instead (the SDK's own limit-compaction is the backstop).
COMPACT_THRESHOLD_TOKENS = 250_000

# Appended to the claude_code preset for every bot session. Bot-specific
# operating doctrine — orchestration, voice, and compounding memory — kept here
# (not in CLAUDE.md) so it applies to the Slack bot only, guaranteed per
# session. Deliberately lean: it costs tokens on every turn.
_SYSTEM_APPEND = (
    "# Orchestration — you are the CHIEF (Claude Opus 4.8)\n"
    "You own real intent, architecture, scope, risk, disagreement-resolution, and "
    "the final reply. Keep judgment; push the rest down to stay sharp and cheap:\n"
    "- `Explore` / `verify` (Haiku) — locate code, read/summarize, run tests/lint, "
    "confirm a change matches the plan. Facts only, never direction.\n"
    "- `implement` (Sonnet) — bounded, well-specified coding inside existing "
    "patterns; wire already-designed pieces; tests; clearly-diagnosed fixes.\n"
    "- `codex-implementer` (ChatGPT/GPT via Codex — a SEPARATE vendor, decorrelated "
    "from Claude) — cross-vendor REVIEW / second opinion on risk-flagged diffs "
    "(auth, billing, migrations, security, concurrency, shared state), and isolated "
    "evidence-verifiable batches OFF the Anthropic cap. Never hand it risk-flagged "
    "AUTHORING.\n"
    "Delegate only when a leg is cleanly separable AND its result is checkable "
    "against evidence; default to inline for tightly-coupled edits. A subagent's "
    "claim of success is NOT evidence — re-verify risk-flagged work yourself, and "
    "proactively get a Codex cross-vendor opinion when a diff lands in a risk zone.\n"
    "\n"
    "# Voice — Hermes style\n"
    "Direct, technical, no marketing fluff, no preamble. Lead with the answer, then "
    "the why. Match the user's language (usually German). Slack-friendly: short "
    "paragraphs, minimal formatting, name the remaining risk plainly.\n"
    "\n"
    "# Memory — Hermes style, compound over time\n"
    "A persistent store lives at `.hermes/`: `MEMORY.md` (index), `USER.md` (the "
    "deepening model of the user), `SOUL.md` (your identity + these rules), and "
    "`memories/*.md` (one fact per file, cross-linked with [[slug]]). On the FIRST "
    "turn of a conversation, read `.hermes/MEMORY.md` and `.hermes/USER.md` for "
    "context. Whenever you learn something durable — a user preference, a project "
    "decision or constraint, a hard-won fact — write or update a one-fact note in "
    "`.hermes/memories/`, cross-link related notes with [[slug]], and add a one-line "
    "pointer to `MEMORY.md`. Keep ephemeral task state in `CONTEXT.md`, not memory. "
    "Every session should leave you a little smarter than the last.\n"
)

# Sent as its own turn before /compact. The session decides whether a task is
# mid-flight (defer) or persists memory + CONTEXT.md and green-lights the
# compact. Marker words are parsed from the reply text.
_PRECOMPACT_PROMPT = (
    "Automated pre-compact check: the context window has crossed the auto-compact "
    "threshold, so older turns are about to be summarised.\n"
    "1. If a multi-turn task is currently mid-flight (an in_progress task, a "
    "half-finished edit sequence, or you are waiting on the user's answer to a "
    "question you asked), reply with exactly COMPACT_DEFER and nothing else.\n"
    "2. Otherwise persist everything lasting NOW — save/update auto-memory entries "
    "for anything from this conversation worth keeping, flush durable facts to the "
    ".hermes/ memory (one-fact notes in .hermes/memories/, cross-linked with "
    "[[slug]], plus a MEMORY.md pointer; update USER.md if you learned something "
    "about the user), and refresh CONTEXT.md (Current Task / Key Decisions / Next "
    "Steps) — then reply with exactly COMPACT_OK and nothing else."
)


@dataclass
class StreamEvent:
    """Normalized event the bot layer turns into Slack message edits."""

    kind: str  # "tool_use" | "text_delta" | "done" | "error" | "info"
    text: str = ""
    tool_name: str = ""
    tool_input_preview: str = ""


DEFAULT_PERMISSION_MODE = "bypassPermissions"

# Queue sentinel: the reader enqueues this once it has seen the ResultMessage
# for the active turn, telling _run_turn() to stop yielding.
_TURN_END = object()

# Signature of the proactive-push handler the bot registers: it renders one
# agent-initiated event (a turn Claude produced with no user prompt) into chat.
PushHandler = Callable[[str, "StreamEvent"], Awaitable[None]]


@dataclass
class _Session:
    client: ClaudeSDKClient
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    # Total tokens in context after the most recent turn — read via
    # get_context_usage() once each turn settles. Drives auto-compact.
    last_total_tokens: int = 0
    permission_mode: str = DEFAULT_PERMISSION_MODE
    # Single-reader model: one background task drains client.receive_messages()
    # for the session's whole life. While a user turn is in flight its events
    # route into active_turn_queue (drained by _run_turn); otherwise they are
    # agent-initiated and pushed proactively via SessionManager._push_handler.
    active_turn_queue: Optional["asyncio.Queue"] = None
    reader_task: Optional["asyncio.Task"] = None
    dead: bool = False
    # True once the user has been told a compact is pending but deferred
    # (task mid-flight). Prevents a "deferring…" message on every turn.
    compact_defer_notified: bool = False


class SessionManager:
    """Keeps one ClaudeSDKClient per Slack thread alive across messages."""

    def __init__(self, cwd: str = DEFAULT_WORKDIR):
        self._sessions: dict[str, _Session] = {}
        self._cwd = cwd
        self._global_lock = asyncio.Lock()
        self._push_handler: Optional[PushHandler] = None

    def set_push_handler(self, handler: PushHandler) -> None:
        """Register the coroutine the reader calls for agent-initiated events.

        Called as ``await handler(session_key, ev)`` for every event of a turn
        Claude produces without a user prompt (scheduled wake-ups,
        background-task completions). Set this once at startup, before any
        session exists — without it those events are dropped.
        """
        self._push_handler = handler

    async def _get_or_create(self, session_key: str) -> _Session:
        async with self._global_lock:
            sess = self._sessions.get(session_key)
            if sess is not None:
                return sess
            options = ClaudeAgentOptions(
                cwd=self._cwd,
                permission_mode=DEFAULT_PERMISSION_MODE,
                system_prompt={
                    "type": "preset",
                    "preset": "claude_code",
                    "append": _SYSTEM_APPEND,
                },
                # setting_sources still loads CLAUDE.md (strict_mcp_config only
                # scopes MCP, not settings).
                setting_sources=["user", "project", "local"],
                # Pin only the MCP servers this code bot needs instead of
                # inheriting every account/user server. strict drops the account
                # connectors (Gmail/Calendar/Drive/Remote), appkittie and sentry:
                # a single broken upstream tool schema otherwise 400s every turn.
                mcp_servers={
                    "dual-graph": {
                        "type": "stdio",
                        "command": os.path.expanduser(
                            "~/.dual-graph/venv/bin/mcp-graph-server"
                        ),
                        "args": ["--stdio"],
                        "env": {
                            "DG_DATA_DIR": f"{self._cwd}/.dual-graph",
                            "DUAL_GRAPH_PROJECT_ROOT": self._cwd,
                        },
                    },
                    "token-counter": {
                        "type": "stdio",
                        "command": "npx",
                        "args": ["-y", "token-counter-mcp@latest"],
                        "env": {},
                    },
                    "posthog": {
                        "type": "http",
                        "url": "https://mcp.posthog.com/mcp",
                        "headers": {"x-posthog-mcp-consumer": "plugin"},
                    },
                },
                strict_mcp_config=True,
                model=os.getenv("CLAUDE_MODEL", "claude-opus-5"),
            )
            client = ClaudeSDKClient(options=options)
            await client.connect()
            sess = _Session(client=client)
            self._sessions[session_key] = sess
            # Start the lifelong stream reader. It owns receive_messages() and
            # routes events to the active turn or the proactive-push handler.
            sess.reader_task = asyncio.create_task(self._reader_loop(session_key, sess))
            logger.info("Created Claude session for session_key=%s cwd=%s", session_key, self._cwd)
            return sess

    async def reset(self, session_key: str) -> bool:
        async with self._global_lock:
            sess = self._sessions.pop(session_key, None)
        if sess is None:
            return False
        if sess.reader_task is not None:
            sess.reader_task.cancel()
        try:
            await sess.client.disconnect()
        except Exception:
            logger.warning("Error disconnecting session for session_key=%s", session_key, exc_info=True)
        logger.info("Reset Claude session for session_key=%s", session_key)
        return True

    async def set_mode(self, session_key: str, mode: str) -> str:
        """Switch the chat's session into `mode` (e.g. "plan", "bypassPermissions").

        Creates the session if it doesn't exist yet. Returns the previous mode
        so the bot layer can render an "already on" reply when it's a no-op.
        """
        sess = await self._get_or_create(session_key)
        previous = sess.permission_mode
        if previous == mode:
            return previous
        await sess.client.set_permission_mode(mode)
        sess.permission_mode = mode
        logger.info("session_key=%s permission_mode: %s -> %s", session_key, previous, mode)
        return previous

    async def shutdown_all(self) -> None:
        async with self._global_lock:
            sessions = list(self._sessions.values())
            self._sessions.clear()
        for sess in sessions:
            if sess.reader_task is not None:
                sess.reader_task.cancel()
            try:
                await sess.client.disconnect()
            except Exception:
                pass

    async def _drop_dead_session(
        self, session_key: str, sess: "_Session", cancel_reader: bool = True
    ) -> None:
        """Evict a broken session so the next message creates a fresh one.

        Triggered when the CLI subprocess has terminated (exit 143 from a
        restart, OOM kill, etc). Without this, the dead client stays cached
        and every subsequent prompt fails with CLIConnectionError until the
        bot is restarted.

        `cancel_reader` is False when the reader loop itself calls this (a task
        must not cancel itself — it's already unwinding).
        """
        async with self._global_lock:
            if self._sessions.get(session_key) is sess:
                del self._sessions[session_key]
        if cancel_reader and sess.reader_task is not None:
            sess.reader_task.cancel()
        try:
            await sess.client.disconnect()
        except Exception:
            pass
        logger.info("Dropped dead Claude session for session_key=%s", session_key)

    async def _reader_loop(self, session_key: str, sess: "_Session") -> None:
        """Drain the SDK message stream for this session, for its whole life.

        This is the ONLY consumer of client.receive_messages(). Each normalized
        event is routed to the in-flight user turn's queue, or — when no user
        turn is active — handed to the proactive-push handler so agent-initiated
        turns reach Slack immediately instead of buffering until the user's
        next message (the bug this fixes).
        """
        broke = False
        try:
            async for msg in sess.client.receive_messages():
                turn_end = isinstance(msg, ResultMessage)
                async for ev in _normalize(msg):
                    q = sess.active_turn_queue
                    if q is not None:
                        await q.put(ev)
                    elif self._push_handler is not None:
                        try:
                            await self._push_handler(session_key, ev)
                        except Exception:
                            logger.exception("push handler failed session_key=%s", session_key)
                if turn_end:
                    q = sess.active_turn_queue
                    if q is not None:
                        await q.put(_TURN_END)
                        sess.active_turn_queue = None
        except asyncio.CancelledError:
            raise
        except Exception as e:
            # Stream broke — almost always the CLI subprocess exited (restart,
            # OOM, exit 143). Fall through to unblock a waiting turn + evict.
            logger.warning("reader loop errored for session_key=%s: %s", session_key, e)
            broke = True
        # Normal end (receive_messages saw "end") or a handled break: tear down.
        q = sess.active_turn_queue
        if q is not None:
            await q.put(
                StreamEvent(
                    kind="error",
                    text="Claude subprocess died mid-response — dropping session, resend your message to retry.",
                )
            )
            await q.put(_TURN_END)
            sess.active_turn_queue = None
        if not sess.dead:
            sess.dead = True
            await self._drop_dead_session(session_key, sess, cancel_reader=False)
        del broke

    async def _run_turn(self, sess: "_Session", prompt: str) -> AsyncIterator[StreamEvent]:
        """Send one prompt and yield its events until the turn ends.

        Hands the reader a fresh queue for this turn's events. The reader
        enqueues _TURN_END (and clears active_turn_queue) once it sees the
        ResultMessage, so this stops cleanly at the turn boundary.
        """
        q: "asyncio.Queue" = asyncio.Queue()
        sess.active_turn_queue = q
        try:
            await sess.client.query(prompt)
        except Exception:
            sess.active_turn_queue = None
            raise
        while True:
            ev = await q.get()
            if ev is _TURN_END:
                return
            yield ev

    async def send(self, session_key: str, prompt: str) -> AsyncIterator[StreamEvent]:
        """Send a user prompt; yield StreamEvent objects as Claude responds.

        Events are produced by the session's background reader and delivered
        through a per-turn queue (see _run_turn). The reader, not this method,
        owns the SDK stream — so turns Claude starts on its own still surface
        even when no send() is in flight.
        """
        sess = await self._get_or_create(session_key)
        # Serialize per-session so concurrent messages in the same chat don't tangle.
        async with sess.lock:
            if sess.dead:
                yield StreamEvent(
                    kind="error",
                    text="Claude subprocess is gone — I dropped the dead session. Resend your message to start a fresh one.",
                )
                return

            # Auto-compact pre-flight: if the previous turn left context above
            # the threshold, run `/compact` first and drain it silently.
            if sess.last_total_tokens > COMPACT_THRESHOLD_TOKENS:
                before = sess.last_total_tokens
                try:
                    # Gate turn: defer if a task is mid-flight, otherwise the
                    # session persists memory + CONTEXT.md and replies COMPACT_OK.
                    verdict = ""
                    async for _ev in self._run_turn(sess, _PRECOMPACT_PROMPT):
                        if _ev.kind == "text_delta":
                            verdict += _ev.text
                    if "COMPACT_OK" in verdict:
                        yield StreamEvent(
                            kind="info",
                            text=(
                                f"💾 Auto-compact bei {before/1000:.0f}k Tokens — Memory & "
                                "CONTEXT.md sind gesichert, ältere Turns werden jetzt zusammengefasst."
                            ),
                        )
                        async for _ev in self._run_turn(sess, "/compact"):
                            pass
                        logger.info("Auto-compacted session_key=%s (was %d tokens)", session_key, before)
                        # get_context_usage() below writes the post-compact value.
                        sess.last_total_tokens = 0
                        sess.compact_defer_notified = False
                    else:
                        # Task mid-flight (COMPACT_DEFER or unparseable reply):
                        # overshoot the threshold and re-check next turn. The
                        # SDK's own limit-compaction remains the hard backstop.
                        logger.info(
                            "Auto-compact deferred session_key=%s at %d tokens (verdict=%r)",
                            session_key,
                            before,
                            verdict[:120],
                        )
                        if not sess.compact_defer_notified:
                            sess.compact_defer_notified = True
                            yield StreamEvent(
                                kind="info",
                                text=(
                                    f"💾 Kontext bei {before/1000:.0f}k Tokens — Task läuft noch, "
                                    "Auto-compact wird bis zum Task-Ende aufgeschoben."
                                ),
                            )
                except Exception:
                    # Don't fail the user's message because compact stumbled —
                    # log, reset so we don't loop-trigger, continue with the prompt.
                    logger.exception("auto-compact failed for session_key=%s", session_key)
                    sess.last_total_tokens = 0

            try:
                async for ev in self._run_turn(sess, prompt):
                    yield ev
            except CLIConnectionError as e:
                logger.warning("CLI subprocess dead during turn: session_key=%s err=%s", session_key, e)
                yield StreamEvent(
                    kind="error",
                    text="Claude subprocess is gone — I dropped the dead session. Resend your message to start a fresh one.",
                )
                await self._drop_dead_session(session_key, sess)
                return
            except Exception as e:
                logger.exception("turn failed for session_key=%s", session_key)
                yield StreamEvent(kind="error", text=f"stream failed: {e}")
                return

            # The reader marks the session dead if the stream broke mid-turn; it
            # also enqueued the error event we just yielded. Don't probe usage.
            if sess.dead:
                return

            # Refresh the cached usage so the next turn knows whether to compact.
            # Cheap control-plane call (same data as `/context`).
            try:
                usage = await sess.client.get_context_usage()
                sess.last_total_tokens = int(usage.get("totalTokens", 0))
            except Exception:
                logger.debug("get_context_usage failed for session_key=%s", session_key, exc_info=True)


async def _normalize(msg) -> AsyncIterator[StreamEvent]:
    """Translate SDK message types into StreamEvent objects."""
    if isinstance(msg, AssistantMessage):
        # API-level error on the assistant message itself (rate_limit,
        # billing_error, authentication_failed, server_error, invalid_request,
        # unknown). Without surfacing this, the turn appears to end normally
        # but no text was produced — looks like a silent hang.
        err = getattr(msg, "error", None)
        if err:
            yield StreamEvent(kind="error", text=f"Claude API error: {err}")
            return
        for block in msg.content:
            if isinstance(block, TextBlock):
                if block.text:
                    yield StreamEvent(kind="text_delta", text=block.text)
            elif isinstance(block, ToolUseBlock):
                yield StreamEvent(
                    kind="tool_use",
                    tool_name=block.name,
                    tool_input_preview=_summarize_tool_input(block.name, block.input),
                )
    elif isinstance(msg, ResultMessage):
        if getattr(msg, "is_error", False):
            # Turn ended with an API/CLI failure (429 rate limit, 529
            # overloaded, 500, etc). `api_error_status` is the HTTP code if
            # available; `result` carries the human-readable detail.
            status = getattr(msg, "api_error_status", None)
            detail = getattr(msg, "result", None) or "unknown error"
            status_tag = f" [HTTP {status}]" if status else ""
            yield StreamEvent(kind="error", text=f"Claude returned an error{status_tag}: {detail}")
            return
        yield StreamEvent(kind="done")
    elif isinstance(msg, SystemMessage):
        # Most SystemMessage subtypes are internal bookkeeping, but a few
        # carry user-visible info — surface rate-limit warnings/rejections so
        # the user knows when they're approaching or have hit a cap.
        if getattr(msg, "subtype", "") == "rate_limit":
            data = getattr(msg, "data", {}) or {}
            status = data.get("status", "unknown")
            limit_type = data.get("rate_limit_type", "limit")
            if status == "rejected":
                yield StreamEvent(
                    kind="error",
                    text=f"Rate limit hit ({limit_type}). Try again later.",
                )
            elif status == "allowed_warning":
                util = float(data.get("utilization", 0.0) or 0.0)
                yield StreamEvent(
                    kind="info",
                    text=f"⚠️ Approaching {limit_type} rate limit ({util*100:.0f}% used).",
                )
    elif isinstance(msg, UserMessage):
        # Tool results — ignore in UI, Claude already has them.
        return


def _summarize_tool_input(name: str, inp) -> str:
    """One-line summary of tool input for Slack display."""
    if not isinstance(inp, dict):
        return ""
    if name in ("Read", "Edit", "Write", "NotebookEdit"):
        return str(inp.get("file_path", ""))[-80:]
    if name == "Bash":
        cmd = str(inp.get("command", ""))
        return cmd[:100] + ("…" if len(cmd) > 100 else "")
    if name == "Glob":
        return str(inp.get("pattern", ""))
    if name == "Grep":
        return str(inp.get("pattern", ""))[:80]
    if name == "TodoWrite":
        return "updating todos"
    if name.startswith("mcp__dual-graph__"):
        return str(inp.get("query") or inp.get("file") or "")[:80]
    # Fallback: first short str value
    for v in inp.values():
        if isinstance(v, str) and v:
            return v[:80]
    return ""
