"""Lay a Markdown answer out as several Slack blocks instead of one.

A single 2400-character section renders as an undifferentiated wall. Slack's
own spacing between blocks is the cheapest readability win available, and it
costs nothing at inference time: the structure is already in Claude's Markdown
(headings, blank lines, rules, code fences), it just has to survive the trip.

Why here and not via a Block Kit payload from the model:
  * Payloads can only be posted once complete, so routing every answer through
    one would kill live streaming — the body would appear all at once at the
    end of the turn.
  * JSON costs output tokens on every single answer.
  * A missing comma costs the entire message.

The explicit ```slack-blocks fence stays available in slack_blocks.py for what
this cannot do: fields, buttons, images. This module handles layout, that one
handles interaction.
"""

import os
import re

from slack_bot.md_to_mrkdwn import md_to_mrkdwn

MAX_SECTION = 2900
MAX_HEADER = 150
MAX_BLOCKS = 45
# Paragraphs are merged into one section up to this size. Smaller values give
# more visual separation; too small and a normal answer becomes confetti.
SOFT_SECTION = 900

_CODE_FENCE_RE = re.compile(r"(```.*?```)", re.DOTALL)
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_RULE_RE = re.compile(r"^\s*(?:-{3,}|\*{3,}|_{3,})\s*$")


def enabled() -> bool:
    return os.getenv("BLOCK_LAYOUT", "1") != "0"


def _section(text: str) -> dict:
    return {"type": "section", "text": {"type": "mrkdwn", "text": text[:MAX_SECTION]}}


def md_to_blocks(markdown: str) -> list[dict]:
    """Convert a Markdown answer into a list of Slack blocks."""
    markdown = (markdown or "").strip()
    if not markdown:
        return [_section("…")]
    if not enabled():
        return [_section(md_to_mrkdwn(markdown))]

    blocks: list[dict] = []
    buffer: list[str] = []
    used_header = False

    def flush():
        if not buffer:
            return
        text = md_to_mrkdwn("\n\n".join(buffer)).strip()
        buffer.clear()
        if text:
            blocks.append(_section(text))

    # Split on code fences first so their blank lines are never treated as
    # paragraph breaks — a fenced block must stay in one piece.
    for chunk in _CODE_FENCE_RE.split(markdown):
        if not chunk.strip():
            continue

        if chunk.startswith("```"):
            flush()
            blocks.append(_section(md_to_mrkdwn(chunk)))
            continue

        for para in re.split(r"\n\s*\n", chunk):
            para = para.strip("\n")
            if not para.strip():
                continue

            if _RULE_RE.match(para):
                flush()
                blocks.append({"type": "divider"})
                continue

            m = _HEADING_RE.match(para.split("\n", 1)[0])
            if m and "\n" not in para:
                flush()
                title = m.group(2)
                # One real header per message, at the top. Slack renders header
                # blocks large — using them for every ## reads as shouting.
                if not used_header and len(m.group(1)) <= 2 and len(title) <= MAX_HEADER:
                    blocks.append({
                        "type": "header",
                        "text": {"type": "plain_text", "text": title[:MAX_HEADER],
                                 "emoji": True},
                    })
                    used_header = True
                else:
                    buffer.append(f"**{title}**")
                continue

            current = sum(len(b) for b in buffer)
            if current and current + len(para) > SOFT_SECTION:
                flush()
            buffer.append(para)

    flush()

    if not blocks:
        return [_section(md_to_mrkdwn(markdown))]

    # Trailing divider is a line under nothing.
    while blocks and blocks[-1].get("type") == "divider":
        blocks.pop()

    if len(blocks) > MAX_BLOCKS:
        head, tail = blocks[: MAX_BLOCKS - 1], blocks[MAX_BLOCKS - 1:]
        merged = "\n\n".join(
            b["text"]["text"] for b in tail
            if b.get("type") == "section" and isinstance(b.get("text"), dict)
        )
        blocks = head + [_section(merged)]

    return blocks
