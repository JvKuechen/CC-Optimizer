"""PreToolUse hook: keep non-ASCII characters out of source code on Windows.

Native Windows only. Windows consoles are frequently not UTF-8, so non-ASCII
characters in executed code raise UnicodeEncodeError / SyntaxError at runtime.

For Write/Edit targeting a source-code file, this hook normalizes the incoming
text before it is written:
  - common typography (em/en dashes, curly quotes, ellipsis, arrows, bullets,
    check/cross/warning marks) is transliterated to an ASCII equivalent
  - non-ASCII with no safe ASCII mapping BLOCKS the call, with guidance to write
    the file through a Bash heredoc instead (which this hook does not touch)

Documentation and data files (.md, .json, .yaml, .txt, ...) are left untouched --
the windows-shell rule exempts them. No-op on WSL/Linux/macOS.

This file is itself a source file the hook would process, so its tables are
built from codepoints with chr() -- the file stays pure ASCII and cannot
transliterate its own mapping keys.
"""

import json
import os
import sys

# Only source code is normalized. Docs/data files may carry intentional Unicode.
SOURCE_EXTENSIONS = frozenset([
    ".py", ".pyw", ".pyi",
    ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx",
    ".sh", ".bash", ".zsh",
    ".bat", ".cmd", ".ps1", ".psm1", ".psd1",
    ".rb", ".pl", ".lua", ".r", ".sql",
    ".go", ".rs", ".java", ".kt", ".c", ".h", ".cpp", ".hpp", ".cc", ".cs", ".php",
])

# Codepoint -> ASCII equivalent. Built from numbers so this file stays ASCII.
_MAP = {
    0x2010: "-", 0x2011: "-", 0x2012: "-", 0x2013: "-",   # hyphens / en dash
    0x2014: "--", 0x2015: "--", 0x2212: "-",              # em dash / minus
    0x2018: "'", 0x2019: "'", 0x201A: "'", 0x201B: "'",   # single quotes
    0x201C: '"', 0x201D: '"', 0x201E: '"', 0x201F: '"',   # double quotes
    0x2032: "'", 0x2033: '"', 0x00AB: '"', 0x00BB: '"',   # primes / guillemets
    0x00A0: " ", 0x2002: " ", 0x2003: " ", 0x2007: " ",   # spaces
    0x2009: " ", 0x200A: " ", 0x202F: " ",
    0x2026: "...", 0x2022: "*", 0x00B7: "*", 0x2023: "*", 0x25AA: "*",
    0x00D7: "x", 0x00F7: "/",
    0x2190: "<-", 0x2192: "->", 0x2194: "<->",            # arrows
    0x21D0: "<=", 0x21D2: "=>", 0x21D4: "<=>",
    0x2713: "[OK]", 0x2714: "[OK]", 0x2705: "[OK]",       # check marks
    0x2717: "[X]", 0x2718: "[X]", 0x2716: "[X]",          # cross / ballot X
    0x274C: "[X]", 0x274E: "[X]", 0x26D4: "[X]",
    0x26A0: "[!]", 0x2757: "[!]", 0x2755: "[!]", 0x2139: "[i]",
}
TRANSLITERATE = {chr(cp): repl for cp, repl in _MAP.items()}

# Zero-width / presentation-selector codepoints: drop silently.
DROP = frozenset(chr(cp) for cp in (
    0xFE0E, 0xFE0F,                          # variation selectors
    0x200B, 0x200C, 0x200D, 0x2060, 0xFEFF,  # zero-width spaces / BOM
))


def normalize(text):
    """Return (new_text, unmapped) -- unmapped is a sorted list of (char, cp)
    for non-ASCII characters that have no ASCII mapping."""
    out = []
    unmapped = {}
    for ch in text:
        cp = ord(ch)
        if cp < 128:
            out.append(ch)
        elif ch in DROP or 0x1F3FB <= cp <= 0x1F3FF:  # incl. emoji skin tones
            continue
        elif ch in TRANSLITERATE:
            out.append(TRANSLITERATE[ch])
        else:
            unmapped[ch] = cp
            out.append(ch)
    return "".join(out), sorted(unmapped.items(), key=lambda kv: kv[1])


def main():
    if sys.platform != "win32":
        sys.exit(0)  # non-ASCII is fine on UTF-8 WSL/Linux/macOS consoles

    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)

    tool_name = data.get("tool_name")
    if tool_name not in ("Write", "Edit"):
        sys.exit(0)

    tool_input = data.get("tool_input", {})
    file_path = tool_input.get("file_path", "")
    if not file_path:
        sys.exit(0)

    ext = os.path.splitext(file_path)[1].lower()
    if ext not in SOURCE_EXTENSIONS:
        sys.exit(0)  # docs/data files are exempt

    field = "content" if tool_name == "Write" else "new_string"
    text = tool_input.get(field, "")
    if not isinstance(text, str) or text.isascii():
        sys.exit(0)

    new_text, unmapped = normalize(text)

    if unmapped:
        sample = ", ".join("U+%04X '%s'" % (cp, ch) for ch, cp in unmapped[:8])
        more = "" if len(unmapped) <= 8 else " (and %d more)" % (len(unmapped) - 8)
        reason = (
            "Blocked: non-ASCII characters with no ASCII equivalent in source "
            "file %s: %s%s. Windows consoles cannot reliably encode these. "
            "Replace them with ASCII -- or, if the characters are genuinely "
            "required, write the file through a Bash heredoc "
            "(cat <<'EOF' > file ... EOF), which this hook does not touch."
            % (os.path.basename(file_path), sample, more)
        )
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        }))
        sys.exit(0)

    if new_text == text:
        sys.exit(0)

    updated = dict(tool_input)
    updated[field] = new_text
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "permissionDecisionReason": "Normalized non-ASCII typography to ASCII",
            "updatedInput": updated,
        }
    }))
    sys.exit(0)


if __name__ == "__main__":
    main()
