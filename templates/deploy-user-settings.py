"""Deploy user-level Claude Code settings, guardrail hook, and notifications.

Run this on any machine to set up:
1. ~/.claude/settings.json  (global permissions + hooks)
2. ~/.claude/hooks/guardrail.py (PreToolUse destructive command blocker)
3. Notification hook (audio alert when Claude needs input)

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

    # Resolve guardrail path (template uses ~, deploy uses absolute)
    guardrail_path = str(hooks_dir / "guardrail.py").replace("\\", "/")

    # Override hook commands with resolved absolute paths
    # (template has ~ placeholder, deployed version needs real path)
    for hook_group in template.get("hooks", {}).get("PreToolUse", []):
        for hook in hook_group.get("hooks", []):
            if "guardrail" in hook.get("command", ""):
                hook["command"] = f'python "{guardrail_path}"'

    fix_eol_path = str(hooks_dir / "fix-line-endings.py").replace("\\", "/")
    for hook_group in template.get("hooks", {}).get("PostToolUse", []):
        for hook in hook_group.get("hooks", []):
            if "fix-line-endings" in hook.get("command", ""):
                hook["command"] = f'python "{fix_eol_path}"'

    dst_settings.write_text(
        json.dumps(template, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Deployed: {dst_settings}")

    # Deploy hooks
    for hook_file in ["guardrail.py", "fix-line-endings.py"]:
        src_hook = script_dir / "hooks" / hook_file
        dst_hook = hooks_dir / hook_file
        shutil.copy2(src_hook, dst_hook)
        print(f"Deployed: {dst_hook}")

    print()
    print("Done. Restart any active Claude Code sessions for changes to take effect.")
    print("Hook is snapshotted at session start, so existing sessions won't see it.")
    print()
    print("NEXT STEP: Install recommended plugins (run in terminal, not via script):")
    print()
    print("  claude plugin marketplace add anthropics/claude-code")
    print("  claude plugin install frontend-design@claude-code-plugins")
    print("  claude plugin install feature-dev@claude-code-plugins")
    print("  claude plugin install security-guidance@claude-code-plugins")
    print("  claude plugin install commit-commands@claude-code-plugins")
    print("  claude plugin install code-review@claude-code-plugins")
    print()
    print("See docs/plugin-marketplace-reference.md for full plugin catalog.")


if __name__ == "__main__":
    main()
