"""One-shot setup helper.

Usage:
    python -m slack_bot.setup --bot-token xoxb-… --app-token xapp-… --user-id U01ABCDEF
    python -m slack_bot.setup --add-user U02GHIJKL
    python -m slack_bot.setup --channel C01ABCDEF
    python -m slack_bot.setup --show
"""

import argparse
import sys

from slack_bot.config import (
    get_allowed_channel_ids,
    get_allowed_user_ids,
    get_app_token,
    get_bot_token,
    set_allowed_channel_ids,
    set_allowed_user_ids,
    set_app_token,
    set_bot_token,
)


def main() -> int:
    p = argparse.ArgumentParser(description="Configure the Slack code bot.")
    p.add_argument("--bot-token", help="Bot user OAuth token (xoxb-…)")
    p.add_argument("--app-token", help="App-level token for Socket Mode (xapp-…)")
    p.add_argument("--user-id", help="Slack user ID to allow (U…). Repeatable via --add-user.")
    p.add_argument("--add-user", help="Add another allowed Slack user ID")
    p.add_argument("--channel", help="Restrict the bot to this channel ID (C…). Repeatable.")
    p.add_argument("--show", action="store_true", help="Print current config (masked)")
    args = p.parse_args()

    if args.bot_token:
        set_bot_token(args.bot_token)
        print(f"Stored bot token (length {len(args.bot_token)}).")
    if args.app_token:
        set_app_token(args.app_token)
        print(f"Stored app token (length {len(args.app_token)}).")

    for uid in (args.user_id, args.add_user):
        if uid:
            ids = get_allowed_user_ids() | {uid}
            set_allowed_user_ids(list(ids))
            print(f"Allowed user IDs: {sorted(ids)}")

    if args.channel:
        cids = get_allowed_channel_ids() | {args.channel}
        set_allowed_channel_ids(list(cids))
        print(f"Allowed channel IDs: {sorted(cids)}")

    if args.show or not any(
        [args.bot_token, args.app_token, args.user_id, args.add_user, args.channel]
    ):
        for label, getter in (("Bot token", get_bot_token), ("App token", get_app_token)):
            try:
                tok = getter()
                print(f"{label}: …{tok[-5:]}  (length {len(tok)})")
            except RuntimeError as e:
                print(f"{label}: NOT SET ({e})")
        print(f"Allowed user IDs:    {sorted(get_allowed_user_ids()) or 'NONE'}")
        print(f"Allowed channel IDs: {sorted(get_allowed_channel_ids()) or 'ANY'}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
