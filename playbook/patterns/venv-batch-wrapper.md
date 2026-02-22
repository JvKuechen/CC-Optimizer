# User-Facing Entry Points (Windows Python)

**Source:** Discovered across multiple workspace audits (BAT wrapper and shortcut approaches)

## When

Python projects on Windows where non-technical users (or the developer themselves) need a double-clickable entry point. Also useful for Task Scheduler, desktop shortcuts, or avoiding console window popups.

Note: Claude Code's shell rules (forward slashes, `/dev/null`) already handle venv paths in Git Bash. This pattern is for user-facing entry points, not Claude's internal use.

## Option A: BAT Wrapper (visible console)

Simple, debuggable. Console window appears briefly.

```bat
@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\activate.bat (
    echo ERROR: Virtual environment not found. Run: python -m venv .venv
    exit /b 1
)
call .venv\Scripts\activate.bat
python main.py %*
```

## Option B: Windows Shortcut (no console window)

Uses `pythonw.exe` (windowless Python) via a `.lnk` shortcut. No console flash.

Create shortcut properties:
```
Target:    C:\path\to\project\.venv\Scripts\pythonw.exe main.py
Start in:  C:\path\to\project
```

Best for GUI apps (tkinter, PyQt) or background scripts where console output isn't needed.

## Option C: VBS + BAT (silent scheduled tasks)

For Task Scheduler automation where no window should ever appear. See `patterns/silent-task-scheduler.md`.

## Rules

- Option A for scripts with console output (health checks, diagnostics)
- Option B for GUI apps or background tools (AutoDoc's approach)
- Option C for scheduled automation (CRM integration approach)
- Always use `call` before `activate.bat` in BAT files (without it, BAT exits after activation)
- Always `cd /d "%~dp0"` to handle drive letter changes
