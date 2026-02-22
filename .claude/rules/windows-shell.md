# Windows Shell Rules

This workspace targets **Windows 11 only**. YOU MUST follow these rules in all shell commands.

## Path Separators

- ALWAYS use forward slashes (`/`) in paths passed to Bash, even on Windows. Git Bash, Python, Node, and most CLI tools handle them correctly.
- NEVER use unquoted backslashes in Bash commands — they are interpreted as escape characters and silently swallowed (e.g., `.venv\scripts\activate` becomes `.venvscriptsactivate`).
- If you must use backslashes (rare), double them: `.venv\\scripts\\activate`
- When constructing paths in Python/Node scripts, use `pathlib.Path` or `path.join()` — never string concatenation with `\`.

## Null Device

- NEVER redirect to `nul` in Bash commands. On Windows, `nul` is a reserved device name only in CMD — in Git Bash/MSYS2 it creates a literal file named `nul` that cannot be deleted through normal means.
- IMPORTANT: Use `> /dev/null 2>&1` in Bash commands. Git Bash translates this correctly on Windows.
- In Python scripts, use `subprocess.DEVNULL` or `os.devnull`.

## Avoid Unix-Only Constructs

- `grep -P` (Perl regex) — not available on Windows grep. Use `grep -E` or Python regex.
- `mapfile` / `readarray` — bash 4.0+ only, not in all Git Bash versions. Use `while read` loops or Python.
- `python3` — on Windows the command is `python`. Scripts should use `python` or `py`.
- `sed -i` (in-place) — behaves differently across platforms. Prefer Python for text transforms.
- `wc -l` — may return 0 on Windows for files with Windows line endings. Use `find ... | measure` or Python.
- `chmod` — no-op on Windows. Don't rely on it for permissions.
- `ln -s` — symlinks require elevated privileges on Windows. Avoid.

## ASCII Only in Code

IMPORTANT: NEVER use non-ASCII characters in Python scripts, shell commands, or any generated code. The Windows console often does not use UTF-8 by default, and non-ASCII characters cause `UnicodeEncodeError` or `SyntaxError`.

- **Arrow operator**: Write `->` (hyphen + greater-than), NEVER the Unicode arrow `→` (U+2192). Python syntax requires the ASCII form.
- **Emojis**: NEVER put emojis in `print()` statements, log messages, or console output. Use plain text: `print("Done")` not `print("✅ Done")`.
- **Fancy quotes**: Use straight quotes `"` and `'`, NEVER curly/smart quotes `"` `"` `'` `'`.
- **Dashes**: Use `-` (hyphen) or `--`, NEVER `—` (em dash) or `–` (en dash) in code.
- **Ellipsis**: Write `...` (three dots), NEVER `…` (U+2026) in code.
- **Other**: No bullet characters (`•`), no check marks (`✓`), no multiplication signs (`×`). Use ASCII equivalents.

This applies to ALL generated code — Python, JavaScript, shell scripts, config files. Markdown documentation is exempt.

## Line Endings

- Git for Windows defaults to `core.autocrlf=true` (converts LF to CRLF on checkout). This breaks shell scripts, hooks, and deployed configs.
- The global config should have `core.autocrlf=false` and `core.eol=lf`. If not, run: `git config --global core.autocrlf false && git config --global core.eol lf`
- Every repo should have `.gitattributes` with `* text=auto eol=lf` as per-repo reinforcement.
- When writing files from Python, use `newline="\n"` in `open()` to ensure LF output.

## Quoting

- ALWAYS double-quote paths that may contain spaces: `"C:/Users/My Name/project"`
- Prefer double quotes over single quotes in Bash on Windows (single quotes can cause issues in some contexts).
