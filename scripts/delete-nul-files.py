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
import os
import sys
from pathlib import Path

# Windows reserved device names that pathlib/rglob silently skip.
RESERVED_NAMES = {"nul", "con", "prn", "aux",
                  "com1", "com2", "com3", "com4",
                  "lpt1", "lpt2", "lpt3", "lpt4"}


def delete_reserved_file(filepath):
    """Delete a reserved-name file using Win32 API.

    The \\\\?\\ prefix tells Windows to skip name parsing,
    allowing deletion of reserved names like 'nul', 'con', 'aux'.
    """
    win_path = "\\\\?\\" + str(Path(filepath).resolve())
    result = ctypes.windll.kernel32.DeleteFileW(win_path)
    return result != 0


def find_nul_files(root):
    """Walk directory tree using os.scandir to find reserved-name files.

    pathlib.rglob() silently skips Windows reserved names (nul, con, etc.)
    because Python's path normalization treats them as device references.
    os.scandir sees them as regular directory entries.
    """
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        for name in filenames:
            if name.lower() in RESERVED_NAMES:
                found.append(os.path.join(dirpath, name))
    return found


def main():
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()

    if not target.exists():
        print(f"ERROR: {target} does not exist.")
        sys.exit(1)

    found = find_nul_files(target)

    if not found:
        print(f"No reserved-name files found under {target}")
        return

    print(f"Found {len(found)} reserved-name file(s):")
    print()

    deleted = 0
    for f in found:
        print(f"  {f}", end="")
        if delete_reserved_file(f):
            print(" -- deleted")
            deleted += 1
        else:
            error = ctypes.get_last_error()
            print(f" -- FAILED (error {error})")

    print()
    print(f"{deleted}/{len(found)} deleted.")


if __name__ == "__main__":
    main()
