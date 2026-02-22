# Remediation Config

**Source:** Discovered across multiple workspace audits

## When

Any tool that automatically fixes problems -- service restarters, cache clearers, config fixers, data cleaners. Prevents auto-fix tools from causing more damage than the original problem.

## How

YAML config with safety controls for each remediation action.

```yaml
# remediation.yaml
global:
  dry_run: true          # Default safe. Set false to enable actions.
  kill_switch: false     # Emergency stop. If true, no actions run.
  log_file: remediation.log

actions:
  restart_plex:
    enabled: true
    cooldown_minutes: 30   # Don't run again within 30 min
    max_retries: 3         # Give up after 3 attempts
    requires_confirmation: false
    command: "ssh admin@nas 'systemctl restart plex'"

  clear_cache:
    enabled: true
    cooldown_minutes: 60
    max_retries: 1
    requires_confirmation: true   # Prompt before executing
    command: "ssh admin@nas 'rm -rf /tmp/cache/*'"
```

Implementation reads config before every action:
```python
def should_run(action_name, config):
    action = config["actions"][action_name]
    if config["global"]["kill_switch"]:
        return False
    if not action["enabled"]:
        return False
    if within_cooldown(action_name, action["cooldown_minutes"]):
        return False
    return True
```

## Rules

- `dry_run: true` is the default. Require explicit opt-in for destructive actions
- Kill switch stops ALL actions immediately (for "oh no" moments)
- Cooldowns prevent cascading restarts
- Log every action (attempted, skipped, succeeded, failed) with timestamps
