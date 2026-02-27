# Health Check Standard

Design doc for cross-workspace health monitoring integration with Claude Code.

## Audience

Every Claude instance managing an environment implements independently
based on this shared spec. Environment-specific details (hostnames, services,
node names, SSH credentials) belong in `configs/health-check-environments.md`
in the CC-Optimizer repo (gitignored).

## Principles

1. **Exceptions-only output.** Healthy is the default. The hook output lists only what
   deviates from healthy. If everything is fine, one line.
2. **Each Claude sees only its own environment.** No cross-site checks. Each workspace's
   health scripts check only the systems that workspace manages.
3. **Deterministic scripts, not LLM reasoning.** Health checks are Python/PowerShell/bash
   scripts with structured output. Claude interprets the results, not the checks themselves.
4. **Push for aggregation, pull for local.** Each environment's scripts serve double duty:
   local output for the SessionStart hook, and a push to the environment's Uptime Kuma
   instance for the human dashboard.

## Shared Output Format

All health check scripts MUST output plain text following this contract.

### When everything is healthy

```
Health: all [N] checks passed ([timestamp])
```

One line. Minimal tokens. Claude knows the system is fine and moves on.

### When something is wrong

```
Health: [N] issues ([timestamp])
- [service]: [DOWN|DEGRADED|WARN] - [one-line reason]
- [service]: [DOWN|DEGRADED|WARN] - [one-line reason]
([M] other checks passed)
```

Example (single-node service):

```
Health: 2 issues (2026-02-25 14:32)
- contact-form: WARN - 3 errors in last 24h (was 0 yesterday)
- webserver: DEGRADED - avg response 4.2s (threshold 2s)
(5 other checks passed)
```

### Multi-Node / HA Services

Services running on multiple nodes (blue/green, active/active, active/passive)
MUST include the node name and role so Claude knows which instance is which
and does not accidentally take action against the wrong node.

Format:

```
- [service] [node]([role]): [STATUS] - [reason]
```

Roles: `active`, `passive`, `blue`, `green`, `primary`, `secondary`, or
whatever the deployment uses. The role reflects current operational state,
not the permanent label.

Example (one node unhealthy, other serving traffic):

```
Health: 1 issue (2026-02-25 14:32)
- dashboard node-b(passive): DOWN - container exited 3h ago
- dashboard node-a(active): OK
(8 other checks passed)
```

Example (both nodes of an active/active service degraded):

```
Health: 2 issues (2026-02-25 14:32)
- git-server node-a(active): DEGRADED - response 6.1s (threshold 2s)
- git-server node-b(active): DEGRADED - response 5.8s (threshold 2s)
(7 other checks passed)
```

**Why this matters:** If Claude sees "dashboard: DOWN" without node context,
it may restart or troubleshoot the wrong instance. The node+role format
prevents Claude from taking down the active copy while investigating the
passive one. Claude should always confirm which node it is operating on
before taking remediation actions on multi-node services.

### Severity Levels

| Level    | Meaning                                      | Claude should...              |
|----------|----------------------------------------------|-------------------------------|
| DOWN     | Service unreachable or critical failure       | Flag immediately to user      |
| DEGRADED | Service responding but outside thresholds     | Mention, suggest investigation |
| WARN     | Anomaly detected, not yet impacting service   | Note, proceed with task       |

### Output Rules

- ASCII only. No emoji, no unicode symbols.
- One line per issue. No multi-line explanations in hook output.
- Timestamp format: YYYY-MM-DD HH:MM (24h, local time).
- The `/health-check` skill can provide verbose detail. The hook is the summary.
- Always exit 0. Do NOT use `sys.exit(1)` for health issues. The output format
  already conveys severity. Non-zero exit codes cause the Bash tool to double
  the output display, and the SessionStart hook does not key off exit codes.

## Claude Code Integration Pattern

Every workspace implements these three layers:

### Layer 1: SessionStart Hook (automatic, every session)

Fires on startup, resume, and post-compact. Runs the health check script.
Outputs the summary format above to stdout.

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup",
        "hooks": [{
          "type": "command",
          "command": "python scripts/health/check_all.py --summary",
          "timeout": 15
        }]
      },
      {
        "matcher": "resume",
        "hooks": [{
          "type": "command",
          "command": "python scripts/health/check_all.py --summary",
          "timeout": 15
        }]
      },
      {
        "matcher": "compact",
        "hooks": [{
          "type": "command",
          "command": "python scripts/health/check_all.py --summary",
          "timeout": 15
        }]
      }
    ]
  }
}
```

On Windows/PowerShell environments, replace with:
```json
"command": "powershell -NoProfile -File scripts/health/check_all.ps1 -Summary"
```

### Layer 2: /health-check Skill (on-demand, verbose)

A skill that runs the same scripts with verbose output. Claude invokes this when:
- The user asks about system health
- The SessionStart summary flagged issues and Claude needs detail
- As part of buttoning up a session

```yaml
---
name: health-check
description: Run health checks and report current system status
---
```

The skill body runs `scripts/health/check_all.py --verbose` and presents
structured results for Claude to analyze and summarize.

### Layer 3: CLAUDE.md Instruction (behavioral)

Each workspace's CLAUDE.md includes:

```markdown
## Health Awareness

A SessionStart hook injects current system health at the start of every session.
If any issues are flagged, acknowledge them before proceeding with the task.
Before concluding a session where system changes were made, run `/health-check`
to verify the environment has not regressed.
```

## Per-Environment Implementation Notes

Environment-specific details are in `configs/health-check-environments.md`
in the CC-Optimizer repo (gitignored). The patterns below describe what each
environment TYPE should check, without revealing specific hostnames, credentials,
or service inventories.

### Container Host (Docker + Uptime Kuma)

- **Health script:** Queries local Uptime Kuma API for monitor statuses.
  Falls back to `docker inspect` for containers not in Kuma.
- **Human dashboard:** Uptime Kuma's built-in status page.
- **Link dashboard integration:** Kuma widget or link on the link dashboard.

### Multi-Node Server (HA services)

- **Health script:** Direct checks -- `curl` endpoints, `systemctl --failed`,
  `docker inspect`. For services running on multiple nodes, checks MUST
  report per-node status with role (see Multi-Node format above).
- **Human dashboard:** Hosts the central Uptime Kuma instance for the
  environment group. Other environments in the group push to it.
- **Link dashboard role:** Stays as the link launcher. Kuma widget or link
  for at-a-glance status. Link dashboard ping checks are NOT the source
  of truth for health data.

### Shared Hosting (SSH access, no containers)

- **Health script -- external (runs where Claude Code runs):**
  - HTTP checks: Is each URL serving expected content (not just 200, but
    content validation -- look for expected strings/elements on the page)
  - SSL certificate expiry
  - DNS resolution
- **Health script -- internal (runs on server over SSH):**
  - Application-specific log parsing (error counts, activity metrics)
  - Web server error log for recent 5xx entries
  - Disk usage, database connectivity
  - Must be compatible with the server's Python version. Check version
    constraints: f-strings require 3.6+, dataclasses require 3.7+,
    walrus operator requires 3.8+, match/case requires 3.10+.
- **Server-side script deployment:** The server-side health script lives in
  the local repo and must be deployed to the server. Use scp, rclone, or
  the workspace's existing deploy mechanism. The orchestrator can optionally
  scp the script on each run, or it can be deployed once and updated manually.
- **Invocation:** The local health script SSHs in, runs the server-side
  script, parses JSON output, formats to standard summary. SSH timeout
  should be short (10s) -- if SSH fails, external checks still report
  and the SSH failure itself becomes a WARN.
- **Human dashboard:** Results pushed to the environment group's central
  Uptime Kuma (push monitor endpoint).

### Windows Domain (Active Directory)

- **Health script:** PowerShell. Runs locally on the management machine.
  - `dcdiag /q` -- DC health (quiet = errors only)
  - `repadmin /replsummary` -- replication status
  - SQL Server: connectivity, recent agent job failures, backup age
  - SMB share accessibility for key shares
  - DNS resolution for critical internal names
  - DHCP scope utilization (warn if >85%)
- **Human dashboard:** Push results to environment group's Uptime Kuma.

### Cloud Management (MDM / VPN)

- **Health script:** Python or PowerShell. Uses management API (read-only).
  - Device compliance summary (X of Y compliant)
  - Policy assignment failures
  - VPN/mesh peer connectivity status
- **Human dashboard:** Push results to environment group's Uptime Kuma.
- **Auth:** App registration with read-only permissions. Token stored in
  environment variable, not in scripts.

## Human Dashboard Architecture

Each environment group has one Uptime Kuma instance. Environments that
can't run their own Kuma push results to the group's central instance.

```
Environment Group (one Kuma instance)
======================================
  Local services --------local----> Uptime Kuma
  Remote env A scripts ---push---/       |
  Remote env B scripts ---push--/        v
  Remote env C scripts ---push-/   Status page
                                   (single pane of glass
                                    for the group)
                                        |
                                        v
                                  Link dashboard
                                  - Service links
                                  - Kuma widget or link
```

Separate groups (e.g., work vs personal) run completely separate Kuma
instances. No cross-group monitoring.

## Manual Upgrade Tracking

Some components require manual "coffee and a plan" upgrade sessions rather than
auto-updates. Track these in the workspace's CLAUDE.md or a dedicated file:

```markdown
## Manual Upgrade Log

| Component       | Current  | Available | Last reviewed |
|-----------------|----------|-----------|---------------|
| Docker Engine   | 28.3     | 29.2      | 2026-01-01    |
| containerd      | 1.7      | 2.2       | 2026-01-01    |
```

The health check script can optionally WARN when the last review date exceeds
the deferral threshold. Uses exponential backoff to avoid pestering for stable
services that have been consciously deferred:

| Consecutive deferrals | Next reminder after |
|-----------------------|---------------------|
| 0 (first review)      | 90 days             |
| 1                     | 180 days            |
| 2                     | 360 days            |
| 3+                    | 360 days (cap)      |

A "deferral" is when the review date is updated without changing the version
(reviewed, decided not to upgrade). Upgrading resets the counter.

Track in a state file alongside the upgrade log:

```json
{
  "docker-engine": {
    "current": "28.3",
    "available": "29.2",
    "last_reviewed": "2026-01-01",
    "deferrals": 1,
    "next_reminder_days": 180
  }
}
```

## Implementation Order

1. **Container host** -- Kuma is likely already running. Wire up the hook, write the script, validate the pattern.
2. **Multi-node server** -- Deploy Kuma, write direct-check scripts, push to Kuma, wire up hook.
3. **Shared hosting** -- Write server-side health script, write local SSH wrapper, wire up hook, push to Kuma.
4. **Windows domain** -- Write PowerShell scripts, wire up hook, push to Kuma.
5. **Cloud management** -- Set up API app registration, write scripts, wire up hook, push to Kuma.

## File Structure Convention

Every workspace follows this layout:

```
scripts/
  health/
    check_all.py (or .ps1)     # Orchestrator: runs all checks, formats output
    check_[service].py          # Individual service checks (optional granularity)
    requirements.txt            # Dependencies if any (requests, etc.)
.claude/
  hooks/                        # Hook configs reference scripts/health/
  skills/
    health-check/
      SKILL.md                  # /health-check skill definition
```

The orchestrator script accepts:
- `--summary`  : One-line-per-issue format for SessionStart hook
- `--verbose`  : Full detail for /health-check skill
- `--push`     : Push results to Uptime Kuma (for scheduled task / cron)
- `--json`     : Machine-readable output (for other tools to consume)
