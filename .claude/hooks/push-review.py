"""PreToolUse hook: intercept git push on public repos.

When Claude tries to push a repo with a .public-repo marker, this
hook replaces the push command with scripts/push-review.py, which
outputs a formatted diff review. The user then executes the actual
push via the ! command shown at the end of the review.

Non-public repos and repos with nothing to push are not affected.
"""
import json
import re
import subprocess
import sys
from pathlib import Path


def main():
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        return

    tool_name = input_data.get("tool_name", "")
    if tool_name != "Bash":
        return

    command = input_data.get("tool_input", {}).get("command", "")

    # Match git push commands (with optional args, pipes, chaining)
    if not re.search(r"\bgit\s+push\b", command):
        return

    # Derive repo root from script location (.claude/hooks/push-review.py)
    repo_root = Path(__file__).resolve().parent.parent.parent

    # Only gate public repos
    if not (repo_root / ".public-repo").exists():
        return

    # Extract remote from command if specified
    # Pattern: git push [flags] [remote] [refspec]
    remote_arg = ""
    match = re.search(r"\bgit\s+push\s+(.*)", command)
    if match:
        args = match.group(1).strip().split()
        for arg in args:
            if not arg.startswith("-") and not arg.startswith("$"):
                remote_arg = arg
                break

    # Auto-detect remote if not specified
    if not remote_arg:
        remotes = subprocess.run(
            "git remote", cwd=str(repo_root),
            capture_output=True, text=True, shell=True,
        ).stdout.strip().splitlines()
        if "public" in remotes:
            remote_arg = "public"
        elif remotes:
            remote_arg = remotes[0]
        else:
            return  # No remotes, allow push through

    # Determine branch
    branch = subprocess.run(
        "git symbolic-ref --short HEAD", cwd=str(repo_root),
        capture_output=True, text=True, shell=True,
    ).stdout.strip() or "main"

    # Check if there are unpushed commits
    count_result = subprocess.run(
        "git rev-list --count {}/{}..HEAD".format(remote_arg, branch),
        cwd=str(repo_root), capture_output=True, text=True, shell=True,
    )
    if count_result.returncode != 0:
        return  # Remote ref doesn't exist (first push?), allow through
    if count_result.stdout.strip() in ("0", ""):
        return  # Nothing to push, allow through

    # Replace push with review script (use forward slashes for Windows)
    repo_path = str(repo_root).replace("\\", "/")
    review_cmd = 'cd "{}" && python scripts/push-review.py'.format(repo_path)
    if remote_arg:
        review_cmd += " {}".format(remote_arg)

    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "updatedInput": {
                "command": review_cmd,
            },
            "additionalContext": (
                "The git push was replaced with a diff review script. "
                "IMPORTANT: The Bash output is truncated in the UI. "
                "You MUST re-present the COMPLETE Bash output as "
                "markdown -- every section, every line of the diff, "
                "nothing omitted. Use ```diff fencing for syntax "
                "coloring. Do NOT run git push -- the user will "
                "execute it via the ! command at the end of the review."
            ),
        }
    }
    print(json.dumps(output))


if __name__ == "__main__":
    main()
