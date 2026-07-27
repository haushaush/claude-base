"""Convert Claude's Markdown output to Slack-flavoured mrkdwn.

Slack mrkdwn is *not* Markdown. The differences that matter:

    Markdown          mrkdwn
    **bold**          *bold*
    *italic*          _italic_
    ~~strike~~        ~strike~
    # Heading         *Heading*        (no heading syntax at all)
    - item            • item           (no list syntax at all)
    [text](url)       <url|text>
    ```lang           ```              (no language tag, no highlighting)
    > quote           > quote          (same)

Escaping is narrower than HTML — only &, < and > — but it has to happen
*before* links and code spans inject real < > into the string.

The stash mechanism matters more here than in the Telegram version, because
mrkdwn overloads `*`: Markdown bold becomes a *single* asterisk, which the
italic pass would then eat and turn back into `_underscores_`. So every
finished construct gets parked behind an opaque token and only comes back at
the very end.
"""

import re

_CODE_BLOCK_RE = re.compile(r"```([a-zA-Z0-9_+\-.]*)\n?(.*?)```", re.DOTALL)
_INLINE_CODE_RE = re.compile(r"`([^`\n]+)`")
_BLOCKQUOTE_RE = re.compile(r"(?:^>[ ]?.*(?:\n|$))+", re.MULTILINE)
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*", re.DOTALL)
_STRIKE_RE = re.compile(r"~~(.+?)~~", re.DOTALL)
_ITALIC_STAR_RE = re.compile(r"(?<![\w*])\*([^*\n]+)\*(?![\w*])")
_ITALIC_UNDER_RE = re.compile(r"(?<![\w_])_([^_\n]+)_(?![\w_])")
_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
_BULLET_RE = re.compile(r"^(\s*)[-*+]\s+", re.MULTILINE)
_HR_RE = re.compile(r"^\s*(?:-{3,}|\*{3,}|_{3,})\s*$", re.MULTILINE)

_STASH_PREFIX = "\x00MD"
_STASH_SUFFIX = "\x00"
_TOKEN_RE = re.compile(r"\x00MD(\d+)\x00")


def escape_mrkdwn(text: str) -> str:
    """Escape a plain string for inclusion in a mrkdwn message."""
    if not text:
        return ""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def md_to_mrkdwn(text: str) -> str:
    if not text:
        return text

    stash: list[str] = []

    def _stash(replacement: str) -> str:
        token = f"{_STASH_PREFIX}{len(stash)}{_STASH_SUFFIX}"
        stash.append(replacement)
        return token

    # --- constructs that must dodge the escape pass -------------------------

    def _on_code_block(m: re.Match) -> str:
        # Slack ignores the language tag — drop it rather than leaving it as a
        # stray first line inside the block.
        body = escape_mrkdwn(m.group(2)).rstrip("\n")
        return _stash(f"```\n{body}\n```")

    text = _CODE_BLOCK_RE.sub(_on_code_block, text)
    text = _INLINE_CODE_RE.sub(lambda m: _stash(f"`{escape_mrkdwn(m.group(1))}`"), text)

    def _on_blockquote(m: re.Match) -> str:
        # The `>` markers are syntax, not content — they must not become &gt;.
        # Strip the marker, escape the line, put the marker back.
        lines = []
        for line in m.group(0).rstrip("\n").split("\n"):
            stripped = line[1:].lstrip(" ") if line.startswith(">") else line
            lines.append("> " + escape_mrkdwn(stripped))
        return _stash("\n".join(lines) + "\n")

    text = _BLOCKQUOTE_RE.sub(_on_blockquote, text)

    text = escape_mrkdwn(text)

    # --- inline formatting --------------------------------------------------
    # Headings and bold both render to a single `*`, which the italic pass
    # would otherwise consume. Both get stashed the moment they're rendered.

    def _on_heading(m: re.Match) -> str:
        inner = m.group(2).strip().replace("**", "")
        return _stash(f"*{inner}*")

    text = _HEADING_RE.sub(_on_heading, text)
    text = _BOLD_RE.sub(lambda m: _stash(f"*{m.group(1)}*"), text)
    text = _STRIKE_RE.sub(lambda m: _stash(f"~{m.group(1)}~"), text)
    text = _ITALIC_STAR_RE.sub(lambda m: _stash(f"_{m.group(1)}_"), text)
    text = _ITALIC_UNDER_RE.sub(lambda m: _stash(f"_{m.group(1)}_"), text)
    text = _LINK_RE.sub(lambda m: _stash(f"<{m.group(2)}|{m.group(1)}>"), text)
    text = _BULLET_RE.sub(r"\1• ", text)
    text = _HR_RE.sub("", text)

    # --- unstash ------------------------------------------------------------
    # Stashed content can itself contain earlier tokens (inline code inside a
    # bold run), so resolve repeatedly until the text is token-free. The bound
    # guards against an infinite loop on a malformed stash.
    for _ in range(10):
        if not _TOKEN_RE.search(text):
            break
        text = _TOKEN_RE.sub(
            lambda m: stash[int(m.group(1))] if int(m.group(1)) < len(stash) else "",
            text,
        )

    return text
