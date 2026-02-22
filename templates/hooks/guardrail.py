"""PreToolUse guardrail hook for Bash commands.

Blocks destructive commands before they execute. Runs on every Bash tool call.
Exit code 2 = block (stderr shown to Claude). Exit code 0 = allow.
"""

import json
import re
import sys


# Patterns that are ALWAYS blocked (no exceptions)
HARD_BLOCK = [
    # Docker data destruction
    (r"docker\s+volume\s+(rm|remove|prune)", "BLOCKED: docker volume deletion/pruning"),
    (r"docker\s+system\s+prune", "BLOCKED: docker system prune destroys volumes/images/containers"),
    (r"docker[\s-]+compose\s+down\s+.*(-v|--volumes)", "BLOCKED: compose down with volumes flag destroys data"),

    # Broad filesystem destruction
    (r"rm\s+-[a-zA-Z]*r[a-zA-Z]*f[a-zA-Z]*\s+/(?!tmp)", "BLOCKED: recursive force delete on root-level path"),
    (r"rm\s+-[a-zA-Z]*f[a-zA-Z]*r[a-zA-Z]*\s+/(?!tmp)", "BLOCKED: recursive force delete on root-level path"),
    (r"rm\s+-[a-zA-Z]*r[a-zA-Z]*f[a-zA-Z]*\s+~", "BLOCKED: recursive force delete on home directory"),
    (r"rm\s+-[a-zA-Z]*f[a-zA-Z]*r[a-zA-Z]*\s+~", "BLOCKED: recursive force delete on home directory"),
    (r'rm\s+-[a-zA-Z]*r[a-zA-Z]*f[a-zA-Z]*\s+"?C:\\', "BLOCKED: recursive force delete on C: drive path"),
    (r"rm\s+-[a-zA-Z]*f[a-zA-Z]*r[a-zA-Z]*\s+\"?C:\\", "BLOCKED: recursive force delete on C: drive path"),

    # Windows-specific destruction
    (r"rmdir\s+/[sS]\s+/[qQ]", "BLOCKED: rmdir /s /q is recursive silent delete"),
    (r"del\s+/[sS]\s+/[qQ]", "BLOCKED: del /s /q is recursive silent delete"),
    (r"\bformat\s+[a-zA-Z]:", "BLOCKED: disk format command"),
    (r"\bdiskpart\b", "BLOCKED: diskpart can destroy disk partitions"),
    (r"Remove-Item\s+.*-Recurse.*-Force", "BLOCKED: PowerShell recursive force delete"),
    (r"Remove-Item\s+.*-Force.*-Recurse", "BLOCKED: PowerShell recursive force delete"),

    # Git destruction
    (r"git\s+push\s+.*--force", "BLOCKED: force push can destroy remote history"),
    (r"git\s+push\s+-f\b", "BLOCKED: force push can destroy remote history"),
    (r"git\s+reset\s+--hard", "BLOCKED: hard reset discards uncommitted work"),
    (r"git\s+clean\s+-[a-zA-Z]*f", "BLOCKED: git clean -f deletes untracked files"),

    # Database destruction (broad safety net)
    (r"DROP\s+DATABASE", "BLOCKED: DROP DATABASE"),
    (r"DROP\s+SCHEMA", "BLOCKED: DROP SCHEMA"),
]

# Patterns that trigger a warning (command still proceeds but stderr warns Claude)
SOFT_WARN = [
    (r">\s*nul\b", "WARNING: '> nul' creates an undeletable file on Windows. Use '> /dev/null 2>&1' instead."),
]


def main():
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)  # Can't parse input, allow

    tool_name = input_data.get("tool_name", "")
    if tool_name != "Bash":
        sys.exit(0)

    command = input_data.get("tool_input", {}).get("command", "")
    if not command:
        sys.exit(0)

    # Check hard blocks
    for pattern, message in HARD_BLOCK:
        if re.search(pattern, command, re.IGNORECASE):
            print(message, file=sys.stderr)
            print(f"Command was: {command[:200]}", file=sys.stderr)
            print("If you need to run this command, ask the user to run it manually.", file=sys.stderr)
            sys.exit(2)

    # Check soft warnings (allow but warn)
    for pattern, message in SOFT_WARN:
        if re.search(pattern, command, re.IGNORECASE):
            print(message, file=sys.stderr)
            sys.exit(2)  # Block nul redirect too - it creates real damage

    sys.exit(0)


if __name__ == "__main__":
    main()
