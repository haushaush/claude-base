# Claude Code Slack bot — with the base-setup tool stack baked in.
#
# install.sh puts dual-graph / graphify / headroom under $HOME. That does not
# survive here: /home/node is a named volume, so anything written there at
# build time is shadowed the moment the container starts. Everything therefore
# lives in /opt, and the paths are handed to the code via env vars.
FROM node:22-bookworm-slim

# ripgrep is not optional — Claude Code's Grep tool shells out to `rg`.
# git is needed for anything repo-shaped. tini reaps the CLI subprocesses the
# Agent SDK spawns; without it they pile up as zombies over a long uptime.
# build-essential + python3-dev: some of graphify's AST deps compile on install.
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3 python3-venv python3-pip python3-dev \
        build-essential git ripgrep curl ca-certificates tini \
    && rm -rf /var/lib/apt/lists/*

RUN npm install -g @anthropic-ai/claude-code

ENV HOME=/home/node
ENV PYTHONPATH=/app

# --- base-setup tool stack --------------------------------------------------
# One venv each, mirroring install.sh but rooted in /opt.

RUN python3 -m venv /opt/dual-graph \
    && /opt/dual-graph/bin/pip install --no-cache-dir --upgrade pip graperoot

RUN python3 -m venv /opt/graphify \
    && /opt/graphify/bin/pip install --no-cache-dir --upgrade pip "graphifyy[mcp]" \
    && ln -sf /opt/graphify/bin/graphify /usr/local/bin/graphify

RUN python3 -m venv /opt/headroom \
    && /opt/headroom/bin/pip install --no-cache-dir --upgrade pip headroom-ai

# Where the code looks for them. claude_session.py reads DUAL_GRAPH_BIN,
# headroom.py reads HEADROOM_BIN.
ENV DUAL_GRAPH_BIN=/opt/dual-graph/bin/mcp-graph-server
ENV HEADROOM_BIN=/opt/headroom/bin/headroom
ENV GRAPHIFY_BIN=/usr/local/bin/graphify

# --- the bot itself ---------------------------------------------------------
WORKDIR /app

COPY slack_bot/requirements.txt /app/slack_bot/requirements.txt
RUN python3 -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir -r /app/slack_bot/requirements.txt

COPY slack_bot/ /app/slack_bot/

RUN chown -R node:node /app /home/node
USER node

# The workspace the agent actually operates on. Bind-mounted from the host.
WORKDIR /workspace

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["/opt/venv/bin/python", "-m", "slack_bot.bot"]
