"""PreToolUse hook: intercept git push on public repos.

When Claude tries to push a repo with a .public-repo marker, this
hook blocks the push and returns a formatted review via
scripts/push-review.py. Claude presents it to the user, who then
executes the push via the ! command.

Non-public repos are not affected -- pushes proceed normally.
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

    # Run push-review script
    cmd = "python scripts/push-review.py"
    if remote_arg:
        cmd += " {}".format(remote_arg)

    result = subprocess.run(
        cmd, cwd=str(repo_root),
        capture_output=True, text=True, shell=True,
    )

    review = result.stdout.strip()

    if not review:
        return  # Script had no output, allow push
    if "Nothing to push" in review or "No remote ref" in review:
        return  # Nothing to review, allow push
    if "No remotes" in review:
        return  # Can't determine remote, allow push

    output = {
        "decision": "block",
        "reason": (
            "PUSH BLOCKED for review. The diff review and the ! push "
            "command are already visible to the user in this hook "
            "output. Do NOT re-print, re-format, or summarize any of "
            "it. Just say: check the review above.\n\n"
            + review
        ),
    }
    print(json.dumps(output))


if __name__ == "__main__":
    main()
