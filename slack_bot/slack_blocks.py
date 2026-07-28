"""Extract and validate Block Kit payloads embedded in Claude's answer.

Claude writes text, not Slack API calls. The contract is a fenced code block:

    ```slack-blocks
    [
      {"type": "section", "text": {"type": "mrkdwn", "text": "*Status*"}},
      {"type": "divider"}
    ]
    ```

The renderer strips these from the streamed body and the bot posts them as a
real Block Kit message once the turn finishes. Two reasons it happens at the
end rather than inline: a half-streamed JSON array looks like garbage while it
grows, and the payload has to be complete before it can be validated.

Everything here is defensive. A model-generated payload is untrusted input —
malformed JSON, oversized text, or an unknown block type must degrade to plain
text rather than making the answer disappear.
"""

import json
import logging
import re

logger = logging.getLogger(__name__)

# The documented fence.
FENCE_RE = re.compile(r"```slack-blocks[ \t]*\n(.*?)\n?```", re.DOTALL)
# An opening fence with no closing one yet — mid-stream.
OPEN_FENCE_RE = re.compile(r"```slack-blocks[ \t]*\n")
# Fallback: models reach for ```json out of habit even when told otherwise.
# Only treated as a payload if the content actually *looks* like Block Kit —
# see _looks_like_blocks. A JSON snippet the user asked for must stay text.
JSON_FENCE_RE = re.compile(r"```(?:json)?[ \t]*\n(.*?)\n?```", re.DOTALL)

# Block types Slack knows. Used both for validation and for recognising an
# untagged payload.
KNOWN_TYPES = {
    "section", "divider", "header", "context", "actions", "rich_text", "image",
    "input", "file", "video",
}

# Slack's limits. Exceeding any of them makes the whole chat.postMessage fail,
# so we check here and fall back rather than losing the message.
MAX_BLOCKS = 50
MAX_SECTION_TEXT = 3000
MAX_HEADER_TEXT = 150
MAX_ELEMENTS = 25

# Block types worth allowing. Anything else is either not useful from a text
# model (input blocks need a modal) or interactive in ways the bot has no
# handler for.
ALLOWED_TYPES = {
    "section", "divider", "header", "context", "actions", "rich_text", "image",
}


def _looks_like_blocks(parsed) -> list | None:
    """Is this parsed JSON a Block Kit payload? Return the block list if so.

    Deliberately strict. An untagged ```json fence is only claimed when every
    entry is a dict carrying a known Slack block ``type`` — otherwise a user
    asking "show me that config as JSON" would watch their answer get eaten.
    """
    if isinstance(parsed, dict) and isinstance(parsed.get("blocks"), list):
        parsed = parsed["blocks"]
    if not isinstance(parsed, list) or not parsed:
        return None
    if all(isinstance(b, dict) and b.get("type") in KNOWN_TYPES for b in parsed):
        return parsed
    return None


def _payload_spans(text: str) -> list[tuple[int, int, list[dict]]]:
    """Find every Block Kit payload with its position in the text."""
    spans: list[tuple[int, int, list[dict]]] = []
    claimed: list[tuple[int, int]] = []

    def scan(pattern, tagged: bool):
        for m in pattern.finditer(text):
            if any(s <= m.start() < e for s, e in claimed):
                continue
            raw = (m.group(1) or "").strip()
            if not raw:
                continue
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError as e:
                if tagged:
                    logger.warning("slack-blocks fence is not valid JSON: %s", e)
                continue
            blocks = _looks_like_blocks(parsed)
            if blocks is None:
                if tagged:
                    logger.warning("slack-blocks fence is not a block list")
                continue
            cleaned = _validate(blocks)
            if cleaned:
                spans.append((m.start(), m.end(), cleaned))
                claimed.append((m.start(), m.end()))

    scan(FENCE_RE, tagged=True)
    scan(JSON_FENCE_RE, tagged=False)
    spans.sort(key=lambda t: t[0])
    return spans


def strip_fences(text: str) -> str:
    """Remove block payloads from text meant for display.

    Complete payloads vanish — their content becomes a separate Block Kit
    message. An *incomplete* tagged fence truncates the rest, so the user never
    watches raw JSON assemble itself character by character.
    """
    for start, end, _ in reversed(_payload_spans(text)):
        text = text[:start] + text[end:]
    m = OPEN_FENCE_RE.search(text)
    if m:
        text = text[: m.start()]
    return text.rstrip()


def extract(text: str) -> list[list[dict]]:
    """Return every valid block payload found in the text, in order."""
    return [blocks for _, _, blocks in _payload_spans(text)]


def _validate(blocks: list) -> list[dict]:
    """Drop what Slack would reject; keep the rest."""
    out: list[dict] = []
    for b in blocks[:MAX_BLOCKS]:
        if not isinstance(b, dict):
            continue
        btype = b.get("type")
        if btype not in ALLOWED_TYPES:
            logger.info("dropping unsupported block type %r", btype)
            continue

        if btype in ("section", "header"):
            txt = b.get("text")
            if isinstance(txt, dict) and isinstance(txt.get("text"), str):
                cap = MAX_HEADER_TEXT if btype == "header" else MAX_SECTION_TEXT
                txt["text"] = txt["text"][:cap]
                # header only accepts plain_text; a mrkdwn header is a 400.
                if btype == "header":
                    txt["type"] = "plain_text"
            elif btype == "header":
                continue

        if btype == "section" and isinstance(b.get("fields"), list):
            b["fields"] = [
                f for f in b["fields"][:10]
                if isinstance(f, dict) and isinstance(f.get("text"), str)
            ]
            for f in b["fields"]:
                f["text"] = f["text"][:2000]
                f.setdefault("type", "mrkdwn")

        if btype in ("actions", "context") and isinstance(b.get("elements"), list):
            b["elements"] = b["elements"][:MAX_ELEMENTS]
            if not b["elements"]:
                continue

        out.append(b)
    return out


def fallback_text(blocks: list[dict]) -> str:
    """Notification/accessibility text for a Block Kit message.

    Slack shows this in the sidebar and in push notifications, and screen
    readers use it. Skipping it produces a silent, unreadable notification.
    """
    parts: list[str] = []
    for b in blocks:
        t = b.get("text")
        if isinstance(t, dict) and isinstance(t.get("text"), str):
            parts.append(t["text"])
        for f in b.get("fields") or []:
            if isinstance(f, dict) and isinstance(f.get("text"), str):
                parts.append(f["text"])
    return (" · ".join(parts) or "Antwort")[:200]
