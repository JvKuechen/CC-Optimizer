"""Delete Windows 'nul' files created by bad '> nul' redirects in Git Bash.

On Windows, 'nul' is a reserved device name. Git Bash doesn't translate
'> nul' to '> /dev/null', so it creates a literal file named 'nul' that
cannot be deleted through normal means (rm, del, Explorer all fail).

This script uses the Win32 DeleteFileW API with the \\?\ extended-length
path prefix to bypass reserved name restrictions.

Usage:
    python scripts/delete-nul-files.py [directory]

    directory  Path to scan for nul files (default: current directory)

The script scans recursively and reports each file found and deleted.
"""

import ctypes
import sys
from pathlib import Path


def delete_nul_file(path):
    """Delete a reserved-name file using Win32 API."""
    # The \\?\ prefix tells Windows to skip name parsing,
    # allowing deletion of reserved names like 'nul', 'con', 'aux'.
    win_path = "\\\\?\\" + str(Path(path).resolve())
    result = ctypes.windll.kernel32.DeleteFileW(win_path)
    return result != 0


def main():
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()

    if not target.exists():
        print(f"ERROR: {target} does not exist.")
        sys.exit(1)

    found = []
    for nul_file in target.rglob("nul"):
        if nul_file.is_file() and nul_file.name == "nul":
            found.append(nul_file)

    if not found:
        print(f"No 'nul' files found under {target}")
        return

    print(f"Found {len(found)} nul file(s):")
    print()

    deleted = 0
    for f in found:
        print(f"  {f}", end="")
        if delete_nul_file(f):
            print(" -- deleted")
            deleted += 1
        else:
            error = ctypes.get_last_error()
            print(f" -- FAILED (error {error})")

    print()
    print(f"{deleted}/{len(found)} deleted.")


if __name__ == "__main__":
    main()
