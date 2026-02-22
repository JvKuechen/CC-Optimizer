# Silent Task Scheduler (Windows)

**Source:** Discovered across multiple workspace audits

## When

Windows scheduled Python automation that should run invisibly (no console window flash).

## How

Three-file chain: Task Scheduler -> VBS wrapper (hides window) -> BAT script (activates venv + runs Python).

```
run_watcher_silent.vbs    # Task Scheduler points here
run_watcher.bat           # Activates venv + runs Python
watcher.py                # Actual script
```

**run_watcher_silent.vbs:**
```vbs
Set WshShell = CreateObject("WScript.Shell")
WshShell.Run Chr(34) & Replace(WScript.ScriptFullName, ".vbs", ".bat") & Chr(34), 0
Set WshShell = Nothing
```

**run_watcher.bat:**
```bat
@echo off
cd /d "%~dp0"
call .venv\Scripts\activate.bat
python watcher.py
```

Task Scheduler config:
- Action: Start a program -> `path\to\run_watcher_silent.vbs`
- Trigger: Your schedule (e.g., every 1 minute, at logon)
- "Run whether user is logged on or not" if needed

## Rules

- VBS `Run` with `,0` hides the console window entirely
- BAT uses `%~dp0` to find its own directory (path-independent)
- Always `cd /d` to handle drive letter changes
- If moving the folder, update the Task Scheduler action path (requires admin)
