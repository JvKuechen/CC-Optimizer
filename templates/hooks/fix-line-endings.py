"""PostToolUse hook: Convert CRLF to LF after Write/Edit.

Claude Code's Write tool uses platform-default line endings. On Windows,
that means CRLF -- even for files destined for Linux servers. This hook
runs after every Write/Edit and normalizes to LF.

Skips binary files (null byte detection) and file types that require CRLF
(batch files, PowerShell scripts).

Exit code 0 = success (always). This hook never blocks.
"""

import json
import os
import sys


# Extensions that require CRLF on Windows -- do not convert these.
# .bat/.cmd: cmd.exe requires CRLF for multi-line commands
# .ps1/.psm1/.psd1: PowerShell script signing and ISE expect CRLF
CRLF_REQUIRED = frozenset([
    ".bat", ".cmd",
    ".ps1", ".psm1", ".psd1",
])


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)

    if data.get("tool_name") not in ("Write", "Edit"):
        sys.exit(0)

    file_path = data.get("tool_input", {}).get("file_path", "")
    if not file_path or not os.path.isfile(file_path):
        sys.exit(0)

    # Skip extensions that need CRLF
    ext = os.path.splitext(file_path)[1].lower()
    if ext in CRLF_REQUIRED:
        sys.exit(0)

    try:
        content = open(file_path, "rb").read()
    except OSError:
        sys.exit(0)

    # Skip binary files (null byte = binary)
    if b"\x00" in content:
        sys.exit(0)

    # Skip if already LF-only
    if b"\r\n" not in content:
        sys.exit(0)

    # Convert CRLF -> LF and write back
    fixed = content.replace(b"\r\n", b"\n")
    try:
        with open(file_path, "wb") as f:
            f.write(fixed)
    except OSError:
        sys.exit(0)

    sys.exit(0)


if __name__ == "__main__":
    main()
