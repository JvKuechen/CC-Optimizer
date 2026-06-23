#!/usr/bin/env python
"""Scrub lone UTF-16 surrogates from a Claude Code session transcript.

A lone surrogate (U+D800..U+DFFF not in a valid high+low pair) embedded in a
session's JSONL -- usually echoed in from a tool result that reflected malformed
input -- makes every later API request body invalid JSON. The symptom is a hard,
recurring `400 ... invalid high surrogate in string` that wedges the session: the
poison is replayed on every turn, so the model cannot recover on its own.

This rewrites each affected JSON string, replacing every lone surrogate with an
ASCII token like `[U+DC9D]`, and backs the original up to `<file>.bak` first.
Both representations are handled: the JSON escape form (`\\udc9d`, six literal
characters) and a raw surrogate codepoint.

Close the wedged session before scrubbing, then `/resume` it afterward -- a live
process can rewrite the file and clobber the scrub.

Usage:
    python scripts/scrub-session-surrogates.py <session.jsonl> [--dry-run]
    python scripts/scrub-session-surrogates.py --project <name-or-path> [--dry-run]
"""
import argparse
import glob
import os
import re
import shutil
import sys

# JSON escape form: backslash-u followed by a surrogate-range hex codepoint.
ESCAPE = re.compile(r"\\u(d[89a-f][0-9a-f]{2})", re.IGNORECASE)


def scrub_text(line):
    """Return (scrubbed_line, count) for one raw JSONL line."""
    count = 0

    # 1) Lone surrogate ESCAPES (`\udc9d`). Walk matches, keep valid high+low
    #    pairs, replace anything unpaired with an ASCII token.
    out = []
    pos = 0
    matches = list(ESCAPE.finditer(line))
    i = 0
    while i < len(matches):
        m = matches[i]
        cp = int(m.group(1), 16)
        is_high = 0xD800 <= cp <= 0xDBFF
        nxt = matches[i + 1] if i + 1 < len(matches) else None
        paired = (
            is_high
            and nxt is not None
            and nxt.start() == m.end()
            and 0xDC00 <= int(nxt.group(1), 16) <= 0xDFFF
        )
        if paired:
            i += 2  # leave the valid pair untouched
            continue
        # lone escape -> replace just this 6-char escape with a token
        out.append(line[pos:m.start()])
        out.append("[U+%04X]" % cp)
        pos = m.end()
        count += 1
        i += 1
    out.append(line[pos:])
    line = "".join(out)

    # 2) Raw lone surrogate CHARACTERS (if any slipped in as actual codepoints).
    def repl_char(ch):
        return "[U+%04X]" % ord(ch)

    rebuilt = []
    chars = list(line)
    j = 0
    while j < len(chars):
        c = ord(chars[j])
        if 0xD800 <= c <= 0xDBFF and j + 1 < len(chars) and 0xDC00 <= ord(chars[j + 1]) <= 0xDFFF:
            rebuilt.append(chars[j]); rebuilt.append(chars[j + 1]); j += 2; continue
        if 0xD800 <= c <= 0xDFFF:
            rebuilt.append(repl_char(chars[j])); count += 1; j += 1; continue
        rebuilt.append(chars[j]); j += 1
    line = "".join(rebuilt)

    return line, count


def scrub_file(path, dry_run):
    with open(path, "r", encoding="utf-8", errors="surrogatepass") as fh:
        lines = fh.readlines()

    total = 0
    affected = 0
    new_lines = []
    for ln, line in enumerate(lines, 1):
        scrubbed, n = scrub_text(line)
        if n:
            affected += 1
            total += n
            print("  line %d: scrubbed %d lone surrogate(s)" % (ln, n))
        new_lines.append(scrubbed)

    if total == 0:
        print("%s: clean (no lone surrogates)" % os.path.basename(path))
        return 0

    print("%s: %d lone surrogate(s) across %d line(s)" % (os.path.basename(path), total, affected))
    if dry_run:
        print("  (dry-run; no changes written)")
        return total

    backup = path + ".bak"
    shutil.copy2(path, backup)
    with open(path, "w", encoding="utf-8", errors="surrogatepass", newline="") as fh:
        fh.writelines(new_lines)
    print("  backed up -> %s" % os.path.basename(backup))
    print("  scrubbed in place. Close + /resume the session to pick up the fix.")
    return total


def resolve_project(name_or_path):
    if os.path.isdir(name_or_path):
        d = name_or_path
    else:
        base = os.path.join(os.path.expanduser("~"), ".claude", "projects")
        hits = [p for p in glob.glob(os.path.join(base, "*")) if name_or_path.lower() in os.path.basename(p).lower()]
        if not hits:
            sys.exit("no project session dir matching %r under %s" % (name_or_path, base))
        if len(hits) > 1:
            sys.exit("ambiguous project %r: %s" % (name_or_path, [os.path.basename(h) for h in hits]))
        d = hits[0]
    return sorted(glob.glob(os.path.join(d, "*.jsonl")))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("session", nargs="?", help="path to a session .jsonl")
    ap.add_argument("--project", help="project name fragment or session dir; scrubs all its .jsonl")
    ap.add_argument("--dry-run", action="store_true", help="report only, write nothing")
    args = ap.parse_args()

    if args.project:
        files = resolve_project(args.project)
    elif args.session:
        files = [args.session]
    else:
        ap.error("give a session .jsonl or --project")

    grand = 0
    for f in files:
        grand += scrub_file(f, args.dry_run)
    print("total scrubbed: %d" % grand)
    return 0 if grand == 0 or not args.dry_run else 1


if __name__ == "__main__":
    sys.exit(main())
