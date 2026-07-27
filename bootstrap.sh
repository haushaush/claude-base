#!/usr/bin/env bash
# First-run helper. Idempotent — safe to re-run.
#
#   cd /opt/claude-bot && bash bootstrap.sh
#
# Creates the files Compose expects, checks the host has room, and tells you
# what to do next. It does not start anything.
set -euo pipefail

cd "$(dirname "$0")"

say()  { printf '\n\033[1m%s\033[0m\n' "$*"; }
warn() { printf '  ! %s\n' "$*"; }
ok()   { printf '  ✓ %s\n' "$*"; }

say "1/4  Voraussetzungen"

if ! command -v docker >/dev/null; then
    warn "docker nicht gefunden — abbruch."
    exit 1
fi
ok "docker $(docker --version | awk '{print $3}' | tr -d ,)"

if ! docker compose version >/dev/null 2>&1; then
    warn "'docker compose' (v2) nicht verfügbar — abbruch."
    exit 1
fi
ok "compose $(docker compose version --short)"

say "2/4  Verzeichnisse"

mkdir -p workspace
ok "workspace/ vorhanden"
if [ -z "$(ls -A workspace 2>/dev/null | grep -v '^\.gitkeep$' || true)" ]; then
    warn "workspace/ ist leer — dort gehört das Projekt hinein, an dem der"
    warn "  Agent arbeiten soll (CLAUDE.md, .hermes/, dein Repo)."
fi

say "3/4  Credentials"

if [ -f credentials.json ]; then
    ok "credentials.json existiert"
    if grep -q 'xoxb-…\|xoxb-DEIN' credentials.json 2>/dev/null; then
        warn "…enthält aber noch Platzhalter. Jetzt ausfüllen."
    fi
else
    cp credentials.example.json credentials.json
    ok "credentials.json aus Vorlage erzeugt"
    warn "Jetzt ausfüllen: nano credentials.json"
fi
chmod 600 credentials.json

say "4/4  Ressourcen"

TOTAL_MB=$(free -m | awk '/^Mem:/{print $2}')
CPUS=$(nproc)
printf '  Host: %s MB RAM, %s vCPU\n' "$TOTAL_MB" "$CPUS"

if   [ "$TOTAL_MB" -lt 3500 ]; then SUGGEST="1g";  CPUSUG="1.0"
elif [ "$TOTAL_MB" -lt 7000 ]; then SUGGEST="2g";  CPUSUG="1.5"
elif [ "$TOTAL_MB" -lt 15000 ]; then SUGGEST="4g"; CPUSUG="2.5"
else SUGGEST="8g"; CPUSUG="$(( CPUS - 1 )).0"
fi
printf '  Vorschlag für docker-compose.yml: mem_limit: %s  cpus: %s\n' "$SUGGEST" "$CPUSUG"

if ! swapon --show 2>/dev/null | grep -q .; then
    warn "Kein Swap aktiv. Auf kleinen VPS ist das riskant — 2 GB anlegen:"
    warn "  fallocate -l 2G /swapfile && chmod 600 /swapfile"
    warn "  mkswap /swapfile && swapon /swapfile"
    warn "  echo '/swapfile none swap sw 0 0' >> /etc/fstab"
fi

cat <<'EOF'

Nächste Schritte:

  1. credentials.json ausfüllen        nano credentials.json
  2. mem_limit ggf. anpassen           nano docker-compose.yml
  3. Image bauen                       docker compose build
  4. Claude einloggen (einmalig)       docker compose run --rm -it \
                                         --entrypoint claude claude-slack-bot
  5. Starten                           docker compose up -d
  6. Zuschauen                         docker compose logs -f

EOF
