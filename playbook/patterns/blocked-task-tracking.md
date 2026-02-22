# Blocked Task Tracking

**Source:** Discovered across multiple workspace audits

## When

Multi-phase projects with external dependencies, waiting on access/credentials, or projects that get paused and resumed weeks later.

## How

Add a status section to CLAUDE.md with three categories.

```markdown
## Project Status

### Completed
- Gitea Docker Compose + PostgreSQL setup script
- LDAP/AD auth configuration
- Backup strategy documented

### Blocked
- SSH access to target server (waiting on IT ticket #1234)
- Word content control placeholder display issue (see MONDAY_PLAN.md)

### Next (when unblocked)
- Deploy Gitea to production server
- Configure webhook integrations
```

## Rules

- Update status at session end, not just when something blocks
- Include ticket/issue numbers for blocked items so you can follow up
- "Next" items should be concrete actions, not vague goals
- When a blocked item unblocks, move it to Completed (don't delete the history)
