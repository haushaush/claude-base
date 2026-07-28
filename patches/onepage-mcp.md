# Onepage-MCP verdrahten

Ohne diesen Schritt kann der Agent keine Landingpage bauen. In `slack_bot/claude_session.py` sind aktuell nur `dual-graph`, `token-counter` und `posthog` in `_available_mcp_servers()` registriert.

## 1. Env-Variablen

In `.env` bzw. `docker-compose.yml` unter `environment:`:

```
ONEPAGE_MCP_URL=https://mcp.onepage.io/mcp
ONEPAGE_API_KEY=<dein Key>
```

Den exakten Endpunkt aus deiner Onepage-Integrationsseite übernehmen — er kann abweichen. Der Key gehört nicht ins Repo; `.env` steht bereits in `.gitignore`, `credentials.json` ebenfalls.

## 2. Server registrieren

In `_available_mcp_servers()` ergänzen, analog zum bestehenden `posthog`-Block (HTTP mit Header-Auth):

```python
onepage_key = os.getenv("ONEPAGE_API_KEY")
if onepage_key:
    servers["onepage"] = {
        "type": "http",
        "url": os.getenv("ONEPAGE_MCP_URL", "https://mcp.onepage.io/mcp"),
        "headers": {"Authorization": f"Bearer {onepage_key}"},
    }
```

Ist der Onepage-MCP bei dir ein lokaler stdio-Server, stattdessen dem `dual-graph`-Block folgen (`"type": "stdio"`, `command`, `args`).

**`strict_mcp_config=True` bleibt stehen.** Nur explizit registrierte Server werden geladen — genau deshalb muss Onepage hier rein.

## 3. Websuche sicherstellen

Der Agent muss Zahlen live verifizieren können. Läuft das Basis-Preset `claude_code` mit WebSearch und WebFetch, ist nichts zu tun. Falls `allowed_tools` irgendwo eingeschränkt wird, müssen `WebSearch` und `WebFetch` drin sein — sonst kann der Agent die Compliance-Regel „keine Zahl ohne Verifikation" nicht einhalten und wird sie stillschweigend brechen.

## 4. Prüfen

```bash
docker compose up -d --build
docker compose logs -f | grep -i mcp
```

Dann im Slack-Thread:

> Liste meine Onepage-Sites auf.

Kommt eine Liste, sitzt die Verdrahtung. Kommt „Tool nicht verfügbar", ist der Server nicht registriert oder der Key falsch.

## 5. Rechte im Container

Onepage-Sections werden serverseitig gebaut — es braucht keinen Schreibzugriff auf den Workspace dafür. Der Workspace wird nur für `.hermes/`, `CONTEXT.md` und Briefings gebraucht. `integrate-base.sh` setzt die Rechte bereits auf uid 1000; wenn `.hermes/` nach dem Build nicht beschreibbar ist, schlägt das Gedächtnis still fehl:

```bash
docker compose exec claude-slack-bot touch /workspace/.hermes/_write_test && echo ok
```
