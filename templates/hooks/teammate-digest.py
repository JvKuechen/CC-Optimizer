#!/usr/bin/env python3
"""TeammateIdle hook -- deterministic close-out digest.

Fires whenever an agent-team teammate goes idle. Reads the hook event JSON on
stdin, then appends a structured entry to the MAIN checkout's
`.claude/team-digest/<teammate>.md`:

  - the teammate's last assistant message (pulled from its transcript)
  - `git diff --stat main...worktree-<teammate>` + `git log` for its branch,
    when such a branch exists

The lead reads that digest on the idle trigger to decide merge / kick-back --
no dependency on the teammate calling SendMessage.

Non-blocking by contract: always exits 0. (Exit 2 would feed stderr back to the
teammate and keep it working; this hook only observes.)
"""
import sys
import os
import re
import json
import subprocess
from datetime import datetime, timezone


def extract_state(text):
    """Pull the close-out STATE token the worker declares as its final signal.
    The board reads this -- not the lead's memory -- so it must be greppable."""
    m = re.search(
        r"STATE:\s*(READY-FOR-MERGE|WAITING-FEEDBACK|BLOCKED)", text or "", re.IGNORECASE
    )
    return m.group(1).upper() if m else "UNDECLARED"


def run(args, cwd):
    try:
        out = subprocess.run(
            args, cwd=cwd, capture_output=True, text=True, timeout=15
        )
        return out.stdout.strip(), out.returncode
    except Exception:
        return "", 1


def main_checkout(cwd):
    """First entry of `git worktree list --porcelain` is the main checkout."""
    out, rc = run(["git", "worktree", "list", "--porcelain"], cwd)
    if rc == 0:
        for line in out.splitlines():
            if line.startswith("worktree "):
                return line[len("worktree "):].strip()
    return cwd


def last_assistant_text(transcript_path):
    if not transcript_path or not os.path.exists(transcript_path):
        return "(transcript not found)"
    last = None
    try:
        with open(transcript_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                msg = obj.get("message", obj)
                is_assistant = msg.get("role") == "assistant" or obj.get("type") == "assistant"
                if not is_assistant:
                    continue
                content = msg.get("content")
                text = ""
                if isinstance(content, list):
                    text = "".join(
                        b.get("text", "")
                        for b in content
                        if isinstance(b, dict) and b.get("type") == "text"
                    )
                elif isinstance(content, str):
                    text = content
                if text.strip():
                    last = text.strip()
    except Exception:
        return "(transcript unreadable)"
    return last or "(no assistant text in transcript)"


def current_branch(cwd):
    b, rc = run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd)
    return b if rc == 0 else ""


def branch_summary(root, branch):
    """Diff a teammate's branch against main. branch is derived from the
    teammate's live cwd (EnterWorktree picks an auto-slug name, not the
    teammate name, so guessing worktree-<name> is wrong)."""
    if not branch or branch == "main":
        return None
    stat, _ = run(["git", "diff", "--stat", "main...%s" % branch], root)
    log, _ = run(["git", "log", "--oneline", "main..%s" % branch], root)
    return stat, log


def main():
    raw = sys.stdin.read()
    try:
        ev = json.loads(raw)
    except Exception:
        return 0

    name = ev.get("teammate_name") or "unknown"
    team = ev.get("team_name") or "unknown"
    transcript = ev.get("transcript_path") or ""
    cwd = ev.get("cwd") or os.getcwd()

    root = main_checkout(cwd)
    branch = current_branch(cwd)  # the teammate's live branch (EnterWorktree auto-slug)
    tail = last_assistant_text(transcript)
    state = extract_state(tail)
    summary = branch_summary(root, branch)

    digest_dir = os.path.join(root, ".claude", "team-digest")
    try:
        os.makedirs(digest_dir, exist_ok=True)
    except Exception:
        return 0
    path = os.path.join(digest_dir, "%s.md" % name)

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    # Greppable header: worktrees-status.sh parses `branch=` and `state=` from
    # the last `## ` line per digest file.
    parts = ["\n## %s @ %s | branch=%s | state=%s | team=%s\n" % (name, stamp, branch or "unknown", state, team)]
    if summary is None:
        parts.append("\n_On `%s` -- no isolated worktree branch yet (still in the shared checkout, or no commits)._\n" % (branch or "unknown"))
    else:
        stat, log = summary
        parts.append("\n**Branch `%s` vs main:**\n\n```\n%s\n```\n" % (branch, stat or "(no diff)"))
        parts.append("\n**Commits:**\n\n```\n%s\n```\n" % (log or "(none)"))
    parts.append("\n**Last output:**\n\n%s\n" % tail)

    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write("".join(parts))
    except Exception:
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
