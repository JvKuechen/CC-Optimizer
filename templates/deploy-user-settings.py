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
import shutil
from pathlib import Path


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

    # Resolve hook command paths: the template uses a ~/.claude/hooks placeholder,
    # the deployed settings need the real absolute path. Applies to every event.
    hooks_prefix = str(hooks_dir).replace("\\", "/")
    for event_hooks in template.get("hooks", {}).values():
        for hook_group in event_hooks:
            for hook in hook_group.get("hooks", []):
                cmd = hook.get("command", "")
                if "~/.claude/hooks" in cmd:
                    hook["command"] = cmd.replace("~/.claude/hooks", hooks_prefix)

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
