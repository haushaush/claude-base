"""Rendering layer — everything between a StreamEvent and Slack message text.

Split out of bot.py (where the Telegram original kept it) so the Slack wiring
stays readable. The tool-icon/verb maps and the DE/EN heuristic are carried
over unchanged; _ReplyState is adapted to Slack's message model:

  * Telegram hands you a Message object you keep and call .edit_text() on.
  * Slack hands you a `ts` string you pass back to chat.update(channel, ts).

and to Slack's tighter limits: a section block tops out at 3000 characters,
not Telegram's 4096.
"""

from dataclasses import dataclass, field

from slack_bot.md_to_mrkdwn import escape_mrkdwn, md_to_mrkdwn

# Slack: 3000 chars per section block. Leave headroom for mrkdwn expansion
# (escaping &<> grows the string) and for the trailing ellipsis on rollover.
SLACK_BLOCK_CAP = 2900
# Cap measured on the *markdown* side, before conversion. Conversion can grow
# the text (escapes, <url|text>), so keep a wider margin than Telegram's.
SAFE_MD_CAP = 2400

TOOL_ICONS = {
    "Read": "📖",
    "Edit": "✏️",
    "Write": "📝",
    "MultiEdit": "✏️",
    "NotebookEdit": "📓",
    "Bash": "▶️",
    "Glob": "🔍",
    "Grep": "🔎",
    "TodoWrite": "✅",
    "WebFetch": "🌐",
    "WebSearch": "🌐",
    "Task": "🤖",
    "Agent": "🤖",
}

TOOL_VERBS_DE = {
    "Read": "Lese",
    "Edit": "Schreibe in",
    "Write": "Erstelle",
    "MultiEdit": "Schreibe in",
    "NotebookEdit": "Bearbeite Notebook",
    "Bash": "Führe aus",
    "Glob": "Suche Dateien",
    "Grep": "Suche nach",
    "TodoWrite": "Aktualisiere Todos",
    "WebFetch": "Lade Webseite",
    "WebSearch": "Suche im Web",
    "Task": "Starte Agent",
    "Agent": "Starte Agent",
    "Skill": "Lade Skill",
    "AskUserQuestion": "Frage zurück",
    "ToolSearch": "Lade Tool-Schema",
    "ScheduleWakeup": "Plane Wake-Up",
    "Monitor": "Beobachte Task",
    "TaskOutput": "Lese Task-Output",
    "TaskStop": "Stoppe Task",
    "ExitPlanMode": "Verlasse Plan-Mode",
    "EnterWorktree": "Erstelle Worktree",
    "ExitWorktree": "Verlasse Worktree",
}

TOOL_VERBS_EN = {
    "Read": "Reading",
    "Edit": "Editing",
    "Write": "Creating",
    "MultiEdit": "Editing",
    "NotebookEdit": "Editing notebook",
    "Bash": "Running",
    "Glob": "Globbing for",
    "Grep": "Searching for",
    "TodoWrite": "Updating todos",
    "WebFetch": "Fetching",
    "WebSearch": "Searching web for",
    "Task": "Starting agent",
    "Agent": "Starting agent",
    "Skill": "Loading skill",
    "AskUserQuestion": "Asking back",
    "ToolSearch": "Loading tool schema",
    "ScheduleWakeup": "Scheduling wake-up",
    "Monitor": "Watching task",
    "TaskOutput": "Reading task output",
    "TaskStop": "Stopping task",
    "ExitPlanMode": "Exiting plan mode",
    "EnterWorktree": "Creating worktree",
    "ExitWorktree": "Exiting worktree",
}

_PATH_TOOLS = {"Read", "Edit", "Write", "MultiEdit", "NotebookEdit"}
_CMD_TOOLS = {"Bash"}
_VERB_ONLY_TOOLS = {"TodoWrite", "AskUserQuestion"}

# Per-thread language memory. Keyed by session_key, so two threads in the same
# channel can run in different languages.
_THREAD_LANG: dict[str, str] = {}

_DE_MARKERS = frozenset({
    "ich", "du", "wir", "ihr", "sie", "der", "die", "das", "den", "dem",
    "und", "oder", "aber", "doch", "ja", "nein", "nicht", "kein", "keine",
    "ist", "sind", "war", "waren", "wird", "werden", "hat", "haben", "hatte",
    "ein", "eine", "einen", "einem", "einer",
    "auch", "noch", "schon", "mal", "nur", "sehr", "hier", "dort", "da",
    "wenn", "weil", "dass", "ob", "als", "wie", "was", "wer", "wo", "warum",
    "mit", "ohne", "für", "gegen", "von", "zu", "aus", "bei", "nach", "vor",
    "über", "unter", "auf", "in", "im",
    "kann", "könnte", "muss", "müsste", "soll", "sollte", "will", "würde",
    "machen", "macht", "mache", "machst", "gemacht",
    "weiß", "weißt", "weißte", "wissen", "gewusst",
    "abhängig", "vielleicht", "trotzdem", "deshalb", "obwohl", "schreibst",
    "bitte", "danke", "tschüss",
})
_DE_DIACRITICS = "äöüßÄÖÜẞ"


def detect_lang(text: str) -> str:
    if not text:
        return "en"
    if any(c in text for c in _DE_DIACRITICS):
        return "de"
    lowered = text.lower()
    tokens = {t.strip(".,!?;:\"'()[]") for t in lowered.split()}
    tokens.discard("")
    hits = sum(1 for t in tokens if t in _DE_MARKERS)
    if len(tokens) <= 3 and hits >= 1:
        return "de"
    return "de" if hits >= 2 else "en"


def thread_lang(session_key: str, message_text: str) -> str:
    """Resolve the verb language for a thread; short acks inherit the prior."""
    msg = message_text or ""
    if detect_lang(msg) == "de":
        _THREAD_LANG[session_key] = "de"
        return "de"
    token_count = len([t for t in msg.split() if t.strip()])
    if _THREAD_LANG.get(session_key) == "de" and token_count <= 3:
        return "de"
    _THREAD_LANG[session_key] = "en"
    return "en"


@dataclass
class ToolCall:
    name: str
    preview: str  # raw, unescaped


@dataclass
class ReplyState:
    """Tracks the in-flight reply for one user prompt, inside one thread.

    Two-message layout, same as the Telegram original — it keeps the answer
    body from flickering on every tool call:

      * tool_ts — the "🔄 Arbeite…" message, re-edited only when a tool fires.
      * body_ts — the answer, created on the first text_delta, re-edited as
        text grows. When the rendered mrkdwn would exceed a section block's
        3000-char limit we seal the current message and start a fresh one for
        the overflow (`seal_first_n`).

    Slack difference: there is no `<blockquote expandable>`. The finished tool
    trace is rendered as a context block instead — visually quiet, same job.
    """

    channel: str
    thread_ts: str
    tool_ts: str | None = None
    body_ts: str | None = None
    lang: str = "en"
    tool_calls: list[ToolCall] = field(default_factory=list)
    text_parts: list[str] = field(default_factory=list)
    last_tool_edit_at: float = 0.0
    last_body_edit_at: float = 0.0
    last_tool_rendered: str = ""
    last_body_rendered: str = ""
    _tool_since_text: bool = False
    sealed_chars: int = 0
    body_msgs_sent: int = 0

    def add_tool(self, name: str, preview: str) -> None:
        self.tool_calls.append(ToolCall(name=name, preview=preview))
        self._tool_since_text = True

    def add_text(self, text: str) -> None:
        if self.text_parts and self._tool_since_text:
            # The SDK splits Claude's text into separate TextBlocks around
            # ToolUseBlocks. Joining naively glues "sentence.Next" together.
            tail = self.text_parts[-1]
            if tail and not tail.endswith(("\n", " ")) and not text.startswith(("\n", " ")):
                self.text_parts.append("\n\n")
            elif tail.endswith(("\n", " ")) and not tail.endswith("\n\n") and not text.startswith("\n"):
                self.text_parts.append("\n")
        self.text_parts.append(text)
        self._tool_since_text = False

    def _format_tool_line(self, tc: ToolCall) -> str:
        icon = TOOL_ICONS.get(tc.name, "🔧")
        verb_map = TOOL_VERBS_DE if self.lang == "de" else TOOL_VERBS_EN
        verb = verb_map.get(tc.name, tc.name)
        if tc.name in _VERB_ONLY_TOOLS or not tc.preview:
            return f"{icon} {escape_mrkdwn(verb)}"
        if tc.name in _PATH_TOOLS:
            return f"{icon} {escape_mrkdwn(verb)} `{escape_mrkdwn(tc.preview)}`"
        if tc.name in _CMD_TOOLS or tc.name in ("Glob", "Grep"):
            return f"{icon} {escape_mrkdwn(verb)}: `{escape_mrkdwn(tc.preview)}`"
        return f"{icon} {escape_mrkdwn(verb)} — {escape_mrkdwn(tc.preview)}"

    def render_tool_text(self, done: bool) -> str:
        """Plain-text trace. Consecutive duplicates collapse to `(N×)`."""
        if not self.tool_calls:
            return "✓" if done else "🔄 Arbeite…"
        groups: list[tuple[ToolCall, int]] = []
        for tc in self.tool_calls:
            if groups and groups[-1][0].name == tc.name and groups[-1][0].preview == tc.preview:
                last_tc, last_n = groups[-1]
                groups[-1] = (last_tc, last_n + 1)
            else:
                groups.append((tc, 1))
        lines = []
        for tc, n in groups:
            line = self._format_tool_line(tc)
            if n > 1:
                line = f"{line} _({n}×)_"
            lines.append(line)
        joined = "\n".join(lines)
        # Context blocks cap at 3000 too; when a long run overflows, keep the
        # tail — the most recent tools are the interesting ones.
        if len(joined) > SLACK_BLOCK_CAP:
            joined = "…\n" + joined[-(SLACK_BLOCK_CAP - 2):]
        return joined

    def render_tool_blocks(self, done: bool) -> list[dict]:
        text = self.render_tool_text(done)
        if done and self.tool_calls:
            # Finished: demote to a context block — small grey type, the
            # closest Slack gets to the collapsed blockquote in Telegram.
            return [{"type": "context", "elements": [{"type": "mrkdwn", "text": text}]}]
        return [{"type": "section", "text": {"type": "mrkdwn", "text": text}}]

    def render_body_md(self) -> str:
        """Markdown of the *unsealed* tail — what belongs in the current body."""
        raw = "".join(self.text_parts)
        return raw[self.sealed_chars:].strip()

    def render_body_blocks(self) -> list[dict]:
        text = md_to_mrkdwn(self.render_body_md()) or "…"
        return [{"type": "section", "text": {"type": "mrkdwn", "text": text[:SLACK_BLOCK_CAP]}}]

    def seal_first_n(self, n: int) -> None:
        """Advance past the first N chars of the current body, start a new one."""
        raw = "".join(self.text_parts)
        unsealed = raw[self.sealed_chars:]
        leading_ws = len(unsealed) - len(unsealed.lstrip())
        self.sealed_chars += leading_ws + n
        self.body_ts = None
        self.last_body_rendered = ""


def find_split_point(body_md: str, max_chars: int) -> int:
    """Clean cut index for rollover: paragraph > line > sentence > word > hard."""
    if len(body_md) <= max_chars:
        return len(body_md)
    window = body_md[:max_chars]
    for sep in ("\n\n", "\n", ". ", " "):
        idx = window.rfind(sep)
        if idx > max_chars // 3:
            return idx + len(sep)
    return max_chars
