# LP-Agent-Pack für claude-base — Integration

Dieses Paket macht aus dem generischen `claude-base`-Bot einen Agenten, der Performance-Ads-Landingpages für Versicherungsvermittler baut.

## Was im Repo aktuell fehlt

| | Ist | Soll |
|---|---|---|
| `workspace-seed/CLAUDE.md` | nur Dual-Graph-Policy, null Domänenwissen | schlanker Router, der auf Skills verweist |
| Subagents | Explore, implement, verify, codex-implementer — alle generisch | plus drei LP-spezifische |
| Skills | keine | drei, mit Referenzdateien |
| MCP-Server | dual-graph, token-counter, posthog | **plus Onepage** — ohne das kann der Agent keine LP bauen |
| `.hermes/` | leer beim Seed | vorbefüllt mit Runtime-Fallen und Kundenprofilen |

## Dateien einsortieren

```
claude-base/
├── workspace-seed/
│   ├── CLAUDE.md                    ← ERSETZEN durch workspace-seed/CLAUDE.md
│   ├── .claude/
│   │   └── skills/                  ← NEU: claude-skills/* hierher
│   │       ├── lp-intake/
│   │       ├── lp-build/
│   │       └── lp-compliance/
│   └── .hermes/                     ← NEU: hermes-seed/* hierher
│       ├── MEMORY.md
│       └── memories/
├── claude-agents/
│   ├── lp-research.md               ← NEU
│   ├── lp-compliance.md             ← NEU
│   └── lp-render-qa.md              ← NEU
└── slack_bot/
    └── claude_session.py            ← PATCHEN (siehe patches/onepage-mcp.md)
```

`integrate-base.sh` kopiert `workspace-seed/` in den Workspace und legt `.hermes/` an. Prüfe nach dem ersten Build, dass `.claude/skills/` und `.hermes/memories/` wirklich im Workspace angekommen sind — falls das Skript nur einzelne Dateien kopiert, muss es um die beiden Ordner erweitert werden:

```bash
docker compose exec claude-slack-bot ls -la /workspace/.claude/skills /workspace/.hermes
```

## Reihenfolge

1. `patches/onepage-mcp.md` anwenden → Onepage-MCP verdrahten
2. Dateien wie oben einsortieren
3. `.dockerignore` prüfen: `claude-agents/` steht dort drin und wird **nicht** ins Image kopiert — die Agents müssen also über `integrate-base.sh` in den Workspace, nicht übers Image
4. `git pull && docker compose up -d --build`
5. Smoke-Test im Slack-Thread: *„Baue eine Test-LP für Zahnzusatz, Makler, Ansprache Sie"* → der Agent muss zuerst nach Vermittlerstatus, Versicherer und Brand fragen, bevor er `create_site` aufruft

## Warum Skills statt einer großen CLAUDE.md

`CLAUDE.md` wird bei **jedem** Request vollständig in den Kontext geladen. Das komplette LP-Wissen dort abzulegen kostet bei jeder Slack-Nachricht Tokens, auch wenn es nur „wie ist der Stand?" heißt.

Skills laden progressiv: Der Agent sieht nur Name und Description, zieht den Body erst, wenn er ihn braucht, und die `references/`-Dateien erst beim konkreten Schritt. Das ist bei diesem Wissensumfang der einzige tragfähige Weg — die drei Skills zusammen sind rund 30.000 Zeichen.

Die `CLAUDE.md` bleibt deshalb ein Router: Sie sagt nur, *wann* welcher Skill zu ziehen ist, plus die Handvoll Regeln, die immer gelten.

## Was der Agent ohne Menschen nicht kann

Diese Punkte gehören in jede Übergabe und dürfen nie als erledigt gemeldet werden:

- Meta-Pixel hinterlegen (Lara)
- Kunden-Domain verbinden
- Vermittlerregisternummer, § 34d Absatz, USt-IdNr., Beteiligungen
- Freigabe der Ich-Texte und der Preisspannen durch den Kunden
- Erster Tap auf einem echten Gerät
