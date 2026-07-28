#!/usr/bin/env bash
# Integrate the base-setup stack into the running Slack bot.
#
#   cd /opt/claude-bot
#   bash integrate-base.sh
#
# Idempotent. Never overwrites an existing .hermes/ — that store is meant to
# grow, and clobbering it would throw away everything the agent has learned.
set -euo pipefail
cd "$(dirname "$0")"

say()  { printf '\n\033[1m%s\033[0m\n' "$*"; }
ok()   { printf '  ✓ %s\n' "$*"; }
warn() { printf '  ! %s\n' "$*"; }

say "1/5  Subagents"

mkdir -p claude-agents
if compgen -G "claude-agents/*.md" >/dev/null; then
    ok "$(ls claude-agents/*.md | wc -l) Agent-Dateien vorhanden"
else
    warn "claude-agents/ ist leer — Explore.md, verify.md, implement.md und"
    warn "  codex-implementer.md dorthin kopieren, sonst laufen alle"
    warn "  Delegationsversuche ins Leere."
fi

say "2/5  Workspace"

if [ -d workspace/.hermes ]; then
    ok ".hermes/ existiert — wird nicht angefasst"
else
    if [ -d workspace-seed/.hermes ]; then
        cp -r workspace-seed/.hermes workspace/
        ok ".hermes/ angelegt"
    else
        warn "workspace-seed/.hermes fehlt — nichts zu kopieren"
    fi
fi

if [ -f workspace/CLAUDE.md ]; then
    ok "CLAUDE.md existiert — wird nicht angefasst"
elif [ -f workspace-seed/CLAUDE.md ]; then
    cp workspace-seed/CLAUDE.md workspace/
    ok "CLAUDE.md angelegt"
fi

# Der Container laeuft als uid 1000. Ohne das kann der Agent lesen, aber nicht
# schreiben — und das faellt erst beim ersten Edit auf.
chown -R 1000:1000 workspace claude-agents 2>/dev/null || true
ok "Rechte auf uid 1000 gesetzt"

say "3/5  Compose"

python3 - <<'PYEOF'
import pathlib, sys
p = pathlib.Path('docker-compose.yml')
s = p.read_text()
changed = []

if 'claude-agents:/home/node/.claude/agents' not in s:
    s = s.replace(
        '      - ./workspace:/workspace\n',
        '      - ./workspace:/workspace\n'
        '      # Orchestrierungs-Subagents. Nested mount in das claude_home-Volume:\n'
        '      # Docker sortiert Mounts nach Pfadtiefe, der Bind gewinnt fuer diesen Pfad.\n'
        '      - ./claude-agents:/home/node/.claude/agents:ro\n',
        1)
    changed.append('claude-agents-Mount')

if 'CLAUDE_WORKDIR' not in s:
    s = s.replace('    environment:\n',
                  '    environment:\n      CLAUDE_WORKDIR: /workspace\n', 1)
    changed.append('CLAUDE_WORKDIR')

p.write_text(s)
print('  ' + ('ergänzt: ' + ', '.join(changed) if changed else '✓ war schon vollständig'))
PYEOF

say "4/5  Prüfung"

for v in CLAUDE_WORKDIR PYTHONPATH; do
    grep -q "$v" docker-compose.yml Dockerfile && ok "$v gesetzt" || warn "$v FEHLT"
done
grep -q "DUAL_GRAPH_BIN" Dockerfile && ok "DUAL_GRAPH_BIN im Dockerfile" \
    || warn "DUAL_GRAPH_BIN fehlt — neues Dockerfile einspielen"
grep -q "DUAL_GRAPH_BIN" slack_bot/claude_session.py && ok "claude_session.py liest DUAL_GRAPH_BIN" \
    || warn "claude_session.py noch auf dem alten Stand"

python3 -m py_compile slack_bot/*.py && ok "Python-Syntax ok"

say "5/5  Nächste Schritte"

cat <<'EOF'

  docker compose up -d --build          # baut die drei Tool-Venvs mit (dauert)
  docker compose logs -f

  Im Log erwarten:
    dual-graph … gefunden (keine "not installed"-Meldung mehr)
    ⚡Bolt app is running!

  Danach einmalig den graphify-Skill im Projekt registrieren:
    docker compose exec claude-slack-bot graphify install --platform claude --project

  Und in Slack testen:
    @Claude Code lies .hermes/MEMORY.md und sag mir, was du über mich weißt

EOF
