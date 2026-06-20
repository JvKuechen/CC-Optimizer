"""Deploy user-level Claude Code settings, hooks, and notifications.

Run this on any machine to set up:
1. ~/.claude/settings.json   (global permissions + hooks)
2. ~/.claude/hooks/*.py      (every hook in templates/hooks/)
3. ~/.claude/rules/*.md      (shared rules from templates/rules/)

Hooks deployed: guardrail (block destructive commands), fix-line-endings
(CRLF->LF), shell-rewrite (fix Windows-hostile Bash syntax), ascii-normalize
(strip non-ASCII from source). The audio notification hook is settings-only.

Safe to re-run. Overwrites existing files with the latest templates.

Usage: python deploy-user-settings.py
"""

import json
import re
import shutil
import sys
from pathlib import Path


def deploy_monitors(script_dir, claude_dir):
    """Copy monitor templates to ~/.claude/monitors/ (inert until invoked)."""
    src = script_dir / "monitors"
    if not src.exists():
        return
    dst = claude_dir / "monitors"
    dst.mkdir(exist_ok=True)
    for f in sorted(list(src.glob("*.py")) + list(src.glob("*.md"))):
        shutil.copy2(f, dst / f.name)
        print(f"Deployed: {dst / f.name}")


def maybe_install_tmux_config(script_dir, home):
    """Offer the optional tmux teammate-view config (idempotent, opt-in)."""
    src = script_dir / "tmux.conf"
    if not src.exists():
        return
    # tmux teammate-view is Linux/WSL/macOS only; native Windows has no tmux.
    if sys.platform == "win32":
        return
    block = src.read_text(encoding="utf-8")
    marker = ">>> claude-code teammate-view"
    dst = home / ".tmux.conf"
    existing = dst.read_text(encoding="utf-8") if dst.exists() else ""
    if marker in existing:
        print(f"tmux teammate-view already present in {dst} -- skipping.")
        return
    print()
    print("OPTIONAL: tmux teammate-view config (for agent-team tmux / cmux users).")
    print("  Accordion panes: double-left-click to spotlight a teammate, right-click")
    print("  to reset, drag dividers to resize, pane labels, 50k scrollback.")
    if not sys.stdin.isatty():
        print(f"  Non-interactive -- skipping. To install later, append {src} to ~/.tmux.conf")
        return
    try:
        answer = input("  Install into ~/.tmux.conf? [y/N] ").strip().lower()
    except EOFError:
        print("  No input available -- skipping.")
        return
    if answer not in ("y", "yes"):
        print("  Skipped.")
        return
    sep = "" if existing == "" or existing.endswith("\n") else "\n"
    dst.write_text(existing + sep + block, encoding="utf-8")
    print(f"  Appended teammate-view block to {dst}")
    print("  Reload with: tmux source-file ~/.tmux.conf")


def main():
    script_dir = Path(__file__).resolve().parent
    home = Path.home()
    claude_dir = home / ".claude"
    hooks_dir = claude_dir / "hooks"

    # Ensure directories exist
    claude_dir.mkdir(exist_ok=True)
    hooks_dir.mkdir(exist_ok=True)

    # Deploy settings.json
    src_settings = script_dir / "user-settings.json"
    dst_settings = claude_dir / "settings.json"

    # Load template settings
    template = json.loads(src_settings.read_text(encoding="utf-8"))

    # Teammates must run as separate processes (tmux/iTerm2 panes) so a teammate's
    # EnterWorktree isolates only that teammate instead of dragging the lead. Set
    # this only off native Windows: tmux/iTerm2 exist on Linux/WSL/macOS, where
    # agent teams run; on Windows leave the default ("auto") so a non-tmux team
    # session falls back to in-process rather than failing to spawn.
    if sys.platform != "win32":
        template.setdefault("teammateMode", "tmux")

    # Resolve hook command paths: the template uses a ~/.claude/hooks placeholder,
    # the deployed settings need the real absolute path. Applies to every event.
    # Pick the Python that exists on this platform: WSL/Linux/macOS ship only
    # `python3`; native Windows ships only `python`. Hook commands carry a
    # `python`/`python3` token that we normalize here so a hook never silently
    # no-ops because the interpreter name is wrong for the OS.
    py = "python3" if sys.platform != "win32" else "python"
    hooks_prefix = str(hooks_dir).replace("\\", "/")
    for event_hooks in template.get("hooks", {}).values():
        for hook_group in event_hooks:
            for hook in hook_group.get("hooks", []):
                cmd = hook.get("command", "")
                if "~/.claude/hooks" in cmd:
                    cmd = cmd.replace("~/.claude/hooks", hooks_prefix)
                cmd = re.sub(r"^python3?\b", py, cmd)
                hook["command"] = cmd

    dst_settings.write_text(
        json.dumps(template, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Deployed: {dst_settings}")

    # Deploy every hook script in templates/hooks/
    for src_hook in sorted((script_dir / "hooks").glob("*.py")):
        dst_hook = hooks_dir / src_hook.name
        shutil.copy2(src_hook, dst_hook)
        print(f"Deployed: {dst_hook}")

    # Deploy rules from templates/rules/
    rules_src_dir = script_dir / "rules"
    rules_dst_dir = claude_dir / "rules"
    if rules_src_dir.exists():
        rules_dst_dir.mkdir(exist_ok=True)
        for rule_file in sorted(rules_src_dir.glob("*.md")):
            dst = rules_dst_dir / rule_file.name
            shutil.copy2(rule_file, dst)
            print(f"Deployed: {dst}")

    # Deploy monitor templates (inert until invoked by an agent)
    deploy_monitors(script_dir, claude_dir)

    # Optional, opt-in: tmux teammate-view config for agent-team / cmux users
    maybe_install_tmux_config(script_dir, home)

    print()
    print("Done. Restart any active Claude Code sessions for changes to take effect.")
    print("Hook is snapshotted at session start, so existing sessions won't see it.")
    print()
    print("NEXT STEP: Install recommended plugins.")
    print("These are interactive-mode slash commands -- run them inside a Claude Code session:")
    print()
    print("  /plugin marketplace add anthropics/claude-code")
    print("  /plugin install frontend-design@claude-code-plugins")
    print("  /plugin install feature-dev@claude-code-plugins")
    print("  /plugin install security-guidance@claude-code-plugins")
    print("  /plugin install commit-commands@claude-code-plugins")
    print("  /plugin install code-review@claude-code-plugins")
    print()
    print("Or use /plugin to browse and install interactively.")
    print("See docs/plugin-marketplace-reference.md for full plugin catalog.")


if __name__ == "__main__":
    main()
