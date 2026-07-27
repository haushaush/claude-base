# Claude Code Slack bot.
#
# Node is the base because the `claude` CLI is a Node program; Python comes on
# top for the bot itself. The other way round (python:slim + nodesource) works
# too but pulls more layers.
FROM node:22-bookworm-slim

# ripgrep is not optional — Claude Code's Grep tool shells out to `rg`.
# git is needed for anything repo-shaped. tini reaps the CLI subprocesses the
# Agent SDK spawns; without it they pile up as zombies over a long uptime.
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3 python3-venv python3-pip \
        git ripgrep curl ca-certificates tini \
    && rm -rf /var/lib/apt/lists/*

RUN npm install -g @anthropic-ai/claude-code

# Unprivileged user. The node image ships uid 1000 as `node`; reuse it rather
# than creating a second uid, so bind-mounted workspace files keep sane owners.
ENV HOME=/home/node
WORKDIR /app

# Python deps into a venv — Debian's python3 is PEP 668 "externally managed",
# so a plain `pip install` would be rejected.
COPY slack_bot/requirements.txt /app/slack_bot/requirements.txt
RUN python3 -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir -r /app/slack_bot/requirements.txt

COPY slack_bot/ /app/slack_bot/

RUN chown -R node:node /app /home/node
USER node

# The workspace the agent actually operates on. Bind-mounted from the host so
# you can inspect and commit its work from outside the container.
WORKDIR /workspace

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["/opt/venv/bin/python", "-m", "slack_bot.bot"]
