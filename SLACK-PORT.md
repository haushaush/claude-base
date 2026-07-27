# slack_bot — Port des Telegram-Bots

Drop-in-Ersatz für `telegram_bot/`. Der Ordner `slack_bot/` kommt neben (oder
statt) `telegram_bot/` ins Projekt, der Rest des Base-Setups — `.hermes/`,
`CLAUDE.md`, `claude-agents/`, dual-graph, graphify — bleibt unangetastet.

## Was drin ist

| Datei | Status |
|---|---|
| `claude_session.py` | aus dem Original übernommen, Session-Keys `int` → `str`, Modell über `CLAUDE_MODEL` überschreibbar, personalisierte Strings entfernt |
| `headroom.py` | unverändert übernommen (plattformunabhängig) |
| `config.py` | neu — zwei Tokens, User- **und** Channel-Allowlist |
| `auth.py` | neu — Slack-IDs statt Telegram-Ints, plus Bot-Loop-Schutz |
| `md_to_mrkdwn.py` | neu — ersetzt `md_to_html.py` |
| `render.py` | aus `bot.py` herausgelöst: Tool-Trace, DE/EN-Heuristik, `ReplyState` |
| `bot.py` | neu — Socket Mode, Event-Dedupe, Rate-Limit-Gate, Slash-Commands |
| `setup.py` | neu — Credentials setzen |

## Setup

### 1. Slack-App anlegen

api.slack.com/apps → **Create New App** → **From an app manifest** →
`slack-app-manifest.yml` einfügen.

Danach:
- **Basic Information → App-Level Tokens → Generate**, Scope `connections:write`
  → das ist der `xapp-…` Token.
- **Install App** → `xoxb-…` Token.
- Bot in den gewünschten (am besten privaten) Channel einladen.

Die eigene User-ID: Profil → ⋮ → *Mitglieds-ID kopieren* (`U…`).
Die Channel-ID steht am Ende der Channel-URL (`C…`).

### 2. Installieren

```bash
cd <projekt>
cp -r slack_bot/ .
.venv/bin/pip install -r slack_bot/requirements.txt

.venv/bin/python -m slack_bot.setup \
  --bot-token xoxb-… \
  --app-token xapp-… \
  --user-id U01ABCDEF \
  --channel C01ABCDEF

# weitere Personen
.venv/bin/python -m slack_bot.setup --add-user U02GHIJKL
```

`--channel` ist optional, aber empfohlen: ohne Channel-Allowlist kann jeder
erlaubte User den Bot von überall aus ansprechen.

### 3. Claude-Login auf dem Server

Als **derselbe User**, unter dem der Dienst später läuft:

```bash
claude          # Login-Flow, danach liegt die Auth in ~/.claude.json
claude -p "sag hallo"   # Gegenprobe
env | grep ANTHROPIC    # muss leer sein
```

### 4. Testlauf, dann Dienst

```bash
.venv/bin/python -m slack_bot.bot     # Vordergrund, Logs direkt sichtbar

sudo cp deploy/slack-bot.service.template /etc/systemd/system/<slug>-slack-bot.service
# __PROJECT_NAME__ / __USER__ / __HOME__ / __PROJECT_DIR__ ersetzen
sudo systemctl daemon-reload
sudo systemctl enable --now <slug>-slack-bot
journalctl -u <slug>-slack-bot -f
```

## Bedienung

Ein **Thread = eine Session**. Erste Nachricht per `@Claude Code …` im Channel
oder per DM, alles Weitere als Antwort im Thread — ohne erneute Erwähnung.
Mehrere Threads laufen parallel mit getrenntem Kontext.

Slash-Commands beziehen sich auf den Thread, in dem der jeweilige User zuletzt
mit dem Bot geschrieben hat — Slack liefert bei Slash-Commands **kein**
`thread_ts` mit, auch nicht wenn man sie in einem Thread eintippt. Der Bot
merkt sich das pro `(channel, user)`.

## Unterschiede zum Telegram-Original

- **Kein Typing-Indicator.** Ersatz: ⏳ als Reaction auf die User-Nachricht,
  am Ende ✅.
- **Kein aufklappbares Blockquote.** Der fertige Tool-Trace wird zu einem
  Context-Block (kleine graue Schrift).
- **Kein Syntax-Highlighting** in Codeblöcken — Slack kennt keine Sprach-Tags.
- **Kürzere Nachrichten.** 3000 statt 4096 Zeichen pro Block; die Rollover-
  Schwelle liegt entsprechend bei 2400 Markdown-Zeichen.
- **Album-Debounce entfällt** — Slack liefert mehrere Anhänge in einem Event.
- **Downloads brauchen den Bot-Token** als Bearer-Header, sonst kommt eine
  HTML-Loginseite statt der Datei zurück.

## Noch offen

- `.hermes/USER.md` und `memories/telegram-style.md` sind auf eine andere
  Person und auf Telegram-HTML zugeschnitten. Beides ersetzen, bevor der Agent
  das als Grundwahrheit liest.
- `_SYSTEM_APPEND` in `claude_session.py` ist entpersonalisiert, aber die
  Orchestrierungs-Doktrin (Haiku/Sonnet/Codex-Lanes) solltest du gegen dein
  tatsächliches Setup prüfen.
- Der Modellname wird jetzt aus `CLAUDE_MODEL` gelesen, Default `claude-opus-5`.
