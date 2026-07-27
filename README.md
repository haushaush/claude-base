# claude-slack-bot

Claude Code als Slack-Bot auf einem eigenen Server. Portierung des
Telegram-Bots aus `base-claude-setup` — gleicher Kern (Claude Agent SDK,
eine Session pro Konversation, Auto-Compact, Tool-Trace), anderes Interface.

Läuft als eigener Docker-Stack und ist so gebaut, dass er neben einer
bestehenden n8n-Installation auf derselben Maschine koexistiert, ohne sie
sehen zu können.

---

## Vorher: Slack-App anlegen

Auf [api.slack.com/apps](https://api.slack.com/apps) → **Create New App** →
**From an app manifest** → Inhalt von `slack-app-manifest.yml` einfügen.

Danach vier Werte einsammeln:

| Wert | Wo |
|---|---|
| `xoxb-…` Bot Token | Install App → nach der Installation |
| `xapp-…` App Token | Basic Information → App-Level Tokens → Generate, Scope `connections:write` |
| Deine User-ID `U…` | Slack-Profil → ⋮ → Mitglieds-ID kopieren |
| Channel-ID `C…` | steht am Ende der Channel-URL |

Bot anschließend in den gewünschten Channel einladen. Nimm einen privaten —
der Bot führt Shell-Kommandos aus.

---

## Deployment

### 1. Repo auf den Server holen

```bash
sudo mkdir -p /opt/claude-bot && cd /opt/claude-bot
git clone https://github.com/<du>/claude-slack-bot.git .
```

Bei einem privaten Repo fragt Git nach Benutzername und Passwort. Das Passwort
ist ein **Personal Access Token** (GitHub → Settings → Developer settings →
Personal access tokens), das normale Kontopasswort funktioniert nicht mehr.

### 2. Bootstrap

```bash
bash bootstrap.sh
```

Prüft Docker, legt `workspace/` und `credentials.json` an, liest RAM und CPU
der Maschine aus und nennt dir das passende `mem_limit`. Startet nichts.

### 3. Credentials eintragen

```bash
nano credentials.json
```

Die vier Werte von oben. Weitere Personen kommen als zusätzliche Einträge in
`slack_allowed_user_ids` dazu.

### 4. Projekt in den Workspace

In `workspace/` gehört das, woran der Agent arbeiten soll — dein Repo, dein
`CLAUDE.md`, dein `.hermes/`. Aus `base-claude-setup` kannst du `CLAUDE.md`,
`.hermes/` und `claude-agents/` übernehmen.

```bash
cd workspace
git clone git@github.com:<du>/<dein-projekt>.git .
```

### 5. Bauen und einloggen

```bash
cd /opt/claude-bot
docker compose build

# Einmalig: Claude-Login. Läuft ins Named Volume und überlebt Rebuilds.
docker compose run --rm -it --entrypoint claude claude-slack-bot
```

Login-URL im Browser öffnen, Code zurückpasten. Gegenprobe:

```bash
docker compose run --rm --entrypoint claude claude-slack-bot -p "sag hallo"
```

Kommt eine Antwort, läuft die Abrechnung über dein Claude-Abo.

### 6. Starten

```bash
docker compose up -d
docker compose logs -f
```

---

## Bedienung

Ein **Thread ist eine Session.** Erste Nachricht per `@Claude Code …` im
Channel oder als DM, alles Weitere als Antwort im Thread — ohne erneute
Erwähnung. Mehrere Threads laufen parallel mit getrenntem Kontext.

| Command | Wirkung |
|---|---|
| `/claude-help` | Kurzhilfe |
| `/claude-plan` | Plan-Mode an — Claude plant, führt nichts aus |
| `/claude-exitplan` | Plan-Mode aus |
| `/claude-reset` | Session im aktuellen Thread verwerfen |
| `/claude-status` | aktive Sessions |

Slack liefert bei Slash-Commands **kein** `thread_ts` mit, auch nicht wenn du
sie in einem Thread eintippst. Der Bot merkt sich deshalb pro Channel und User
den zuletzt benutzten Thread und wendet die Commands dort an.

---

## Betrieb

```bash
docker compose logs -f --tail=100    # Logs
docker compose restart               # Neustart
git pull && docker compose up -d --build   # nach Code-Änderung
docker stats --no-stream             # Verbrauch
```

Exit Code 137 heißt OOM-Killer: `mem_limit` zu knapp oder eine Session ist
entgleist. Der Container kommt von allein zurück, die laufenden Slack-Sessions
sind dann aber weg.

---

## Sicherheit

Der Bot läuft mit `permission_mode="bypassPermissions"` — er führt beliebige
Shell-Kommandos aus und ändert Dateien, ohne zu fragen. Das ist Absicht und
der Grund, warum das Ding überhaupt nützlich ist. Entsprechend:

**Die Allowlist ist die einzige echte Grenze.** In einem Slack-Workspace kann
jedes Mitglied den Bot per DM erreichen. Ohne Eintrag in
`slack_allowed_user_ids` passiert nichts, und mit Eintrag darf man alles. Trag
dort nur Leute ein, denen du Root auf dem Projektverzeichnis geben würdest.
`slack_allowed_channel_ids` engt zusätzlich ein.

**Der Container ist die zweite Grenze.** Kein Docker-Socket, kein Host-Netz,
`no-new-privileges`, unprivilegierter User, PID- und Speicherlimit. Der Agent
sieht `/workspace` und sonst nichts vom Host. Nachbar-Container wie n8n liegen
in einem anderen Compose-Projekt und sind weder über das Netz noch über
Volumes erreichbar.

**Was trotzdem gilt:** innerhalb von `/workspace` kann der Agent alles löschen.
Leg dort nichts ab, was nicht in Git liegt.

**Abo vs. API-Key.** Der Login in Schritt 5 rechnet gegen dein Claude-Abo.
Sobald mehrere Personen den Bot dauerhaft nutzen, ist ein API-Key auf der
Claude Platform der sauberere Weg — Abo-Nutzung ist auf persönliche
Verwendung ausgelegt, und Anthropic empfiehlt für geteilte Automatisierung
ausdrücklich einen API-Key. Umstellen ist eine Zeile: `ANTHROPIC_API_KEY` in
die `environment:`-Sektion. Nur nicht beides gleichzeitig — der Key gewinnt
immer.

---

## Aufbau

```
Dockerfile                Node 22 + Python + claude CLI + ripgrep
docker-compose.yml        eigener Stack, Limits, keine offenen Ports
bootstrap.sh              Erstinstallation
slack-app-manifest.yml    Slack-App inkl. Socket Mode und Slash-Commands
slack_bot/
  bot.py                  Socket Mode, Event-Dedupe, Rate-Limit-Gate, Commands
  render.py               Tool-Trace, DE/EN-Heuristik, ReplyState
  md_to_mrkdwn.py         Markdown → Slack mrkdwn
  claude_session.py       Agent-SDK-Sessions (aus dem Original, Keys str statt int)
  auth.py                 User- und Channel-Allowlist
  config.py               Credentials, CLAUDE_WORKDIR
  headroom.py             optionaler Kompressions-Proxy (unverändert)
deploy/                   systemd-Unit als Alternative ohne Docker
workspace/                das Projekt, an dem der Agent arbeitet (gitignored)
```

`SLACK-PORT.md` erklärt, was sich gegenüber dem Telegram-Original geändert hat
und warum.

---

## Bekannte Eigenheiten gegenüber Telegram

- Kein Typing-Indicator. Ersatz: ⏳ als Reaction, am Ende ✅.
- Kein aufklappbares Blockquote — der fertige Tool-Trace wird ein Context-Block.
- Kein Syntax-Highlighting in Codeblöcken, Slack kennt keine Sprach-Tags.
- 3000 statt 4096 Zeichen pro Nachricht, Rollover entsprechend früher.
- Anhänge brauchen den Bot-Token als Bearer-Header beim Download.
