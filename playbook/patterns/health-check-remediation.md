# Health Check + Remediation Loop

**Source:** Discovered across multiple workspace audits

## When

Operational or infrastructure projects that manage running services, servers, or deployments. The pattern separates diagnosis from action.

## How

Two-phase loop: diagnostic scripts identify problems, remediation scripts fix them.

```
scripts/
  health/
    check_services.py      # Returns status, no side effects
    check_disk_space.py
    check_api_health.py
  remediation/
    restart_service.py     # Takes action, has safety controls
    clear_cache.py
    rotate_logs.py
  run_health_check.py      # Orchestrator: runs all checks, reports
  run_remediation.py       # Orchestrator: fixes identified issues
```

Key principle: health checks are ALWAYS safe to run (read-only). Remediation scripts ALWAYS have safety controls (see remediation-config pattern).

## Rules

- Health checks must be idempotent and side-effect free
- Health checks return structured output (JSON or exit codes), not prose
- Remediation scripts log every action taken
- Never auto-remediate without explicit opt-in (dry-run by default)
- Pair with remediation-config pattern for production use
