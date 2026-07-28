#!/usr/bin/env python3
"""Add STRICT_MCP + ONEPAGE_MCP support to slack_bot/claude_session.py.

Idempotent: run it as often as you like, it only inserts what is missing.
Writes a .bak next to the file before touching anything.

    cd /opt/claude-bot && python3 patch-onepage.py
"""

import pathlib
import shutil
import sys

TARGET = pathlib.Path("slack_bot/claude_session.py")

ONEPAGE_BLOCK = '''    # Onepage is an OAuth-based remote MCP. The token lives in the CLI
    # credential store under ~/.claude (the claude_home volume) after a one-off
    # `claude mcp add` + /mcp authenticate. Declaring the server explicitly is
    # more reliable than hoping file-based config gets merged into the session —
    # the URL is what the stored credentials are keyed against, so it must match
    # `claude mcp list` exactly, trailing slash included.
    onepage_url = os.getenv("ONEPAGE_MCP_URL", "https://mcp.onepage.io/")
    if os.getenv("ONEPAGE_MCP") == "1":
        servers["onepage"] = {"type": "http", "url": onepage_url}
        logger.info("onepage MCP enabled (%s)", onepage_url)

'''

STRICT_OLD = "                strict_mcp_config=True,"
STRICT_NEW = '''                # Off lets the CLI's own config contribute servers. Not needed
                # when servers are declared explicitly above, and strict keeps
                # surprises out — so this defaults to on.
                strict_mcp_config=os.getenv("STRICT_MCP", "1") != "0",'''


def main() -> int:
    if not TARGET.exists():
        print(f"FEHLER: {TARGET} nicht gefunden. Im Verzeichnis /opt/claude-bot ausführen.")
        return 1

    src = TARGET.read_text()
    shutil.copy(TARGET, str(TARGET) + ".bak")
    changed = []

    if "_available_mcp_servers" not in src:
        print("FEHLER: Diese Datei kennt _available_mcp_servers noch nicht.")
        print("       Sie ist älter als erwartet — hier hilft nur die komplette")
        print("       Datei aus dem Repo statt eines Patches.")
        return 1

    # --- onepage ------------------------------------------------------------
    if "ONEPAGE_MCP" in src:
        print("· onepage: war schon drin")
    else:
        # Insert before whichever optional server comes first in the function.
        for anchor in (
            '    if os.getenv("ENABLE_TOKEN_COUNTER") == "1":',
            '    if os.getenv("POSTHOG_MCP") == "1":',
            "    return servers",
        ):
            if anchor in src:
                src = src.replace(anchor, ONEPAGE_BLOCK + anchor, 1)
                changed.append("onepage")
                print("✓ onepage ergänzt")
                break
        else:
            print("FEHLER: keinen Einfügepunkt in _available_mcp_servers gefunden")
            return 1

    # --- strict_mcp_config --------------------------------------------------
    if "STRICT_MCP" in src:
        print("· STRICT_MCP: war schon drin")
    elif STRICT_OLD in src:
        src = src.replace(STRICT_OLD, STRICT_NEW, 1)
        changed.append("STRICT_MCP")
        print("✓ STRICT_MCP ergänzt")
    else:
        print("! strict_mcp_config=True nicht gefunden — übersprungen")

    if not changed:
        print("\nNichts zu tun, Datei ist aktuell.")
        return 0

    TARGET.write_text(src)

    # Syntax check before anyone tries to build this.
    import ast

    try:
        ast.parse(src)
    except SyntaxError as e:
        print(f"\nFEHLER: Ergebnis ist kein gültiges Python ({e}).")
        print(f"       Zurückgesetzt aus {TARGET}.bak")
        shutil.copy(str(TARGET) + ".bak", TARGET)
        return 1

    print(f"\nGeändert: {', '.join(changed)}. Syntax ok.")
    print("\nWeiter mit:")
    print("  docker compose up -d --build")
    print('  docker compose exec claude-slack-bot grep -c ONEPAGE_MCP /app/slack_bot/claude_session.py')
    print("  docker compose logs --tail=30 | grep -i onepage")
    return 0


if __name__ == "__main__":
    sys.exit(main())
