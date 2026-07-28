# Repo neu aufsetzen — einmal sauber, danach nur noch pull & build

Der Zustand aktuell: auf dem Server steht der richtige Code, im GitHub-Repo
liegt alles flach im Wurzelverzeichnis. Deshalb hat `git reset --hard` vorhin
`slack_bot/` gelöscht. Diese Anleitung zieht das gerade.

Beruhigend vorweg: `credentials.json` und `workspace/` sind in der
`.gitignore`. Git fasst sie bei keinem der folgenden Schritte an — auch
`reset --hard` nicht, das entfernt keine ignorierten oder untracked Dateien.
(Was sie entfernen *würde*, wäre `git clean -fdx`. Den Befehl hier nicht
benutzen.)

---

## 1. Repo leeren

Am schnellsten über GitHub: Repo → **Settings** → ganz unten *Danger Zone* →
**Delete this repository**. Danach neu anlegen, gleicher Name, **privat**,
komplett leer (kein README, keine .gitignore, keine Lizenz).

Warum löschen statt aufräumen: die flachen Dateien einzeln zu entfernen ist
mehr Klickarbeit als ein Neuanfang, und du sparst dir die divergenten Branches.

## 2. Hochladen

ZIP lokal entpacken. Auf der leeren Repo-Seite steht *uploading an existing
file* — draufklicken, dann den **Inhalt** des Ordners `claude-slack-bot` ins
Fenster ziehen. Nicht den Ordner selbst, sonst hast du eine Ebene zu viel.
Unterordner nimmt der Upload mit.

Commit-Nachricht eintragen, **Commit changes**.

### Danach zwei Dateien von Hand nachlegen

GitHubs Browser-Upload überspringt Dateien mit führendem Punkt. Diese beiden
fehlen anschließend und müssen über *Add file → Create new file* angelegt
werden. Namen exakt so eintippen:

**`.gitignore`**

```
credentials.json
credentials.json.tmp
slack_bot/.credentials.json
workspace/*
!workspace/.gitkeep
__pycache__/
*.py[cod]
.venv/
venv/
.DS_Store
.idea/
.vscode/
```

**`.dockerignore`**

```
workspace/
workspace-seed/
credentials.json
credentials.example.json
claude-agents/
.git/
__pycache__/
*.pyc
deploy/
*.md
```

Prüf danach im Browser, dass die Ordner `slack_bot/`, `claude-agents/`,
`deploy/` und `workspace-seed/` da sind und `slack_bot/` zehn Dateien enthält —
inklusive `__init__.py`. Die hat diesmal Inhalt, damit der Uploader sie nicht
als leer verwirft.

## 3. Auf dem Server

```bash
cd /opt/claude-bot

# Sicherheitskopie der einzigen Datei, die es nicht im Repo gibt
cp credentials.json /root/credentials.json.bak

git remote set-url origin https://github.com/<du>/<repo>.git
git fetch origin
git reset --hard origin/main

ls -la && echo '---' && ls slack_bot/ && echo '---' && ls claude-agents/
```

Bei einem privaten Repo fragt `git fetch` nach Zugangsdaten. Benutzername ist
dein GitHub-Name, Passwort ein Personal Access Token mit *Contents: Read*.

`credentials.json` muss danach noch da sein. Falls nicht: aus dem Backup zurück.

## 4. Bauen

```bash
bash integrate-base.sh
docker compose up -d --build
docker compose logs -f
```

`integrate-base.sh` legt `.hermes/` und `CLAUDE.md` im Workspace an (ohne
Vorhandenes zu überschreiben) und setzt die Rechte auf uid 1000. Der Build
dauert diesmal länger, weil dual-graph, graphify und headroom mitkommen und
teilweise nativ kompilieren.

Danach einmalig:

```bash
docker compose exec claude-slack-bot graphify install --platform claude --project
```

## 5. Ab jetzt

```bash
cd /opt/claude-bot && git pull && docker compose up -d --build
```

Das ist der Normalfall für jede künftige Änderung. Keine Handedits mehr in
600-Zeilen-Dateien über ein Browser-Terminal — die haben uns zwei
Syntaxfehler und einen verlorenen Zeilenumbruch gekostet.

---

## Optional: pushen vom Server aus

Wenn du Änderungen künftig auch zurückschieben willst, ist ein SSH-Deploy-Key
zuverlässiger als ein Token — läuft nicht ab, kein Einfügen langer Strings ins
Browser-Terminal:

```bash
ssh-keygen -t ed25519 -C "srv965240-claude-bot" -f ~/.ssh/id_ed25519 -N ""
cat ~/.ssh/id_ed25519.pub
```

Public Key kopieren → Repo → **Settings** → **Deploy keys** → **Add deploy
key** → **„Allow write access" ankreuzen**. Genau dieser Haken hat beim Token
gefehlt und den 403 verursacht.

```bash
git remote set-url origin git@github.com:<du>/<repo>.git
ssh -T git@github.com     # einmal "yes"
git push
```
