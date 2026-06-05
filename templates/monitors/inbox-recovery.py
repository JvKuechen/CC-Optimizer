#!/usr/bin/env python3
"""Inbox recovery monitor -- workaround for a dead agent-team inbox consumer.

WHY THIS EXISTS
  A long-lived team lead can silently lose its inbox RECEIVE path on a
  resume/reattach: teammates' SendMessage still writes to the inbox FILE and
  returns a "Message sent to <lead>'s inbox" success receipt, but the lead never
  ingests them -- they sit in the file with read:false and never enter the lead's
  context. SEND still works (lead -> teammate), only RECEIVE is severed. Silence
  then looks identical to "teammates still working."

  Tell "no one sent" from "lead stopped receiving" by inspecting the read flags:
    ~/.claude/teams/<team>/inboxes/<recipient>.json
  Each entry: {from, text, timestamp, color, type, read}

  This script lets the lead poll the inbox file directly until it can restart
  clean. It is a STOPGAP -- once the lead is restarted/reattached, the real
  consumer rebinds and owns the inbox again; stop running this then.

MODES
  --peek      print unread, do NOT mark read (safe preview)
  --drain     print unread, then mark them read (default)
  --watch     block until >=1 unread appears, then exit 0 with a notice.
              Launch with run_in_background: on exit the harness re-invokes the
              agent, which runs --drain and re-arms --watch. That loop IS the
              monitor (Claude Code re-invokes an agent when a background command
              completes), so no cron/timer is needed.

TARGET SELECTION
  --team <name>   team directory under ~/.claude/teams/ (auto-detected if exactly
                  one team has the recipient inbox; otherwise required)
  --to <name>     recipient inbox basename (default: team-lead)
  --interval <s>  --watch poll interval in seconds (default: 15)

EXAMPLES
  python3 inbox-recovery.py --peek
  python3 inbox-recovery.py --drain
  python3 inbox-recovery.py --watch            # run this one in the background
  python3 inbox-recovery.py --team break-glass-impl --to team-lead --drain
"""
import argparse
import glob
import json
import os
import sys
import tempfile
import time

TEAMS_DIR = os.path.expanduser("~/.claude/teams")


def resolve_inbox(team, to):
    """Return the inbox file path, auto-detecting the team when unambiguous."""
    if team:
        return os.path.join(TEAMS_DIR, team, "inboxes", to + ".json")
    matches = sorted(glob.glob(os.path.join(TEAMS_DIR, "*", "inboxes", to + ".json")))
    if len(matches) == 1:
        return matches[0]
    if not matches:
        sys.exit(f"No inbox '{to}.json' found under {TEAMS_DIR}/*/inboxes/. "
                 f"Pass --team and --to explicitly.")
    teams = [m.split(os.sep)[-3] for m in matches]
    sys.exit(f"Multiple teams have a '{to}' inbox: {teams}. Pass --team <name>.")


def load(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        return json.load(f)


def unread_entries(msgs):
    return [m for m in msgs if isinstance(m, dict) and not m.get("read")]


def print_unread(unread):
    print(f"=== {len(unread)} UNREAD message(s) ===\n")
    for m in unread:
        text = (m.get("text") or m.get("summary") or "").strip()
        print(f"--- from {m.get('from', '?')} @ {m.get('timestamp', '?')} ---")
        print(text if text else "(empty body -- idle ping, ignore)")
        print()


def mark_read_atomic(path, msgs, unread):
    for m in unread:
        m["read"] = True
    d = os.path.dirname(path)
    fd, tmp = tempfile.mkstemp(dir=d, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(msgs, f, ensure_ascii=False)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def main():
    ap = argparse.ArgumentParser(add_help=True, description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--peek", action="store_true", help="print unread, do not mark read")
    mode.add_argument("--drain", action="store_true", help="print unread, then mark read (default)")
    mode.add_argument("--watch", action="store_true", help="block until unread, then exit (background)")
    ap.add_argument("--team", default=None)
    ap.add_argument("--to", default="team-lead")
    ap.add_argument("--interval", type=int, default=15)
    args = ap.parse_args()

    path = resolve_inbox(args.team, args.to)

    if args.watch:
        # Block until the inbox has at least one unread entry, then exit so the
        # harness re-invokes the agent. Tolerate a not-yet-created inbox file.
        while True:
            try:
                if unread_entries(load(path)):
                    print(f"NEW UNREAD in {path} -- run inbox-recovery.py --drain")
                    return 0
            except (FileNotFoundError, json.JSONDecodeError):
                pass
            time.sleep(max(1, args.interval))

    msgs = load(path)
    unread = unread_entries(msgs)
    if not unread:
        print(f"INBOX CLEAN -- no unread in {path}")
        return 0
    print_unread(unread)
    if args.peek:
        print("(peek mode -- left unread)")
        return 0
    mark_read_atomic(path, msgs, unread)
    print(f"=== marked {len(unread)} read ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
