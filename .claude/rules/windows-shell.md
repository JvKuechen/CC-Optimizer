---
paths:
  - "scripts/**"
  - "templates/hooks/**"
  - "**/*.bat"
  - "**/*.cmd"
  - "**/*.ps1"
  - "**/*.psm1"
  - "**/*.psd1"
---

# Windows Shell Rules

These rules apply when authoring shell or hook code targeted at native Windows (Git Bash, CMD, PowerShell). They apply on Windows only -- WSL is exempt. **Follow them when editing files matched by the `paths:` above.**

On a machine set up with `deploy-user-settings.py`, the `shell-rewrite.py` and `ascii-normalize.py` user hooks auto-correct the most common violations (`nul` redirects, `python3`, non-ASCII typography) before they take effect. Treat the hooks as a safety net -- these rules still describe the code to write.

## Path Separators

- Always use forward slashes (`/`) in paths passed to Bash, even on Windows. Git Bash, Python, Node, and most CLI tools handle them correctly.
- Keep backslashes out of unquoted Bash commands. Rejected: `.venv\scripts\activate` -- Bash reads each `\` as an escape character and silently swallows it, leaving `.venvscriptsactivate`.
- If a backslash is genuinely required (rare), double it: `.venv\\scripts\\activate`.
- Build paths in Python/Node scripts with `pathlib.Path` or `path.join()` -- the safe construction. Rejected: string concatenation with a literal `\`.

## Null Device

- In Bash commands, redirect to `/dev/null`: `> /dev/null 2>&1`. Git Bash translates this correctly on Windows.
- In Python scripts, use `subprocess.DEVNULL` or `os.devnull`.
- Rejected: redirecting to `nul` in Bash. On Windows `nul` is a CMD-only device name; in Git Bash/MSYS2 it creates a literal file named `nul` that resists normal deletion.

## Portable Shell Constructs

Prefer the portable form on the right; the construct on the left misbehaves on Windows:

- `grep -P` (Perl regex) -- absent from Windows grep. Use `grep -E` or Python regex.
- `mapfile` / `readarray` -- bash 4.0+ only, missing from some Git Bash versions. Use `while read` loops or Python.
- `python3` -- on Windows the command is `python`. Scripts should call `python` or `py`.
- `sed -i` (in-place) -- behaves differently across platforms. Prefer Python for text transforms.
- `wc -l` -- may return 0 on Windows for files with Windows line endings. Use `find ... | measure` or Python.
- `chmod` -- a no-op on Windows; treat file permissions as unmanaged there.
- `ln -s` -- symlinks require elevated privileges on Windows; prefer a copy or a junction.

## ASCII Only in Code

**Write all generated code -- Python, shell, JavaScript, config files -- in plain ASCII.** The Windows console often runs a non-UTF-8 codepage, where non-ASCII characters trigger `UnicodeEncodeError` or `SyntaxError`. Markdown documentation is exempt.

Use the ASCII form; the Rejected column lists what to keep out of code:

- **Arrow operator** -- write `->` (hyphen + greater-than). Rejected: the Unicode arrow U+2192 -- Python syntax requires the ASCII form.
- **Emojis** -- write plain text, e.g. `print("Done")`. Rejected: emojis in `print()` statements, log messages, or console output.
- **Quotes** -- write straight `"` and `'`. Rejected: curly/smart quote characters.
- **Dashes** -- write `-` (hyphen) or `--`. Rejected: the em dash U+2014 or en dash U+2013 in code.
- **Ellipsis** -- write `...` (three dots). Rejected: the single-character ellipsis U+2026.
- **Other symbols** -- use ASCII equivalents. Rejected: bullet U+2022, check mark U+2713, multiplication sign U+00D7.

## Line Endings

- Git for Windows defaults to `core.autocrlf=true` (converts LF to CRLF on checkout), which breaks shell scripts, hooks, and deployed configs.
- The global config should set `core.autocrlf=false` and `core.eol=lf`. To correct it: `git config --global core.autocrlf false && git config --global core.eol lf`.
- Every repo should carry a `.gitattributes` with `* text=auto eol=lf` as per-repo reinforcement.
- When writing files from Python, pass `newline="\n"` to `open()` to force LF output.

## Quoting

- Always double-quote paths that may contain spaces: `"C:/Users/My Name/project"`.
- Prefer double quotes over single quotes in Bash on Windows (single quotes misbehave in some contexts).
