# QA Scripts Directory

**Source:** Discovered across multiple workspace audits

## When

Projects with 5+ validation, test, or diagnostic scripts. Prevents scripts from getting lost in the project root and gives Claude a clear inventory of available tools.

## How

Create a `qa/` or `scripts/qa/` directory with a README index.

```
qa/
  README.md              # Index of all scripts with one-liner descriptions
  test_email_parsing.py
  test_api_connection.py
  validate_config.py
  check_duplicates.py
  simulate_webhook.py
```

README.md format:
```markdown
# QA Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| test_email_parsing.py | Validate email filter patterns against sample data | `python qa/test_email_parsing.py samples/` |
| test_api_connection.py | Verify API credentials and endpoints | `python qa/test_api_connection.py` |
| validate_config.py | Check config files for required fields | `python qa/validate_config.py config.json` |
```

## Rules

- README is the single source of truth for available QA tools
- Each script should be runnable standalone (no complex setup)
- Update README when adding/removing scripts
- Reference the README from CLAUDE.md: `@qa/README.md`
