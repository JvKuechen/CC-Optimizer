# Credential Hygiene

**Source:** Discovered across multiple workspace audits (anti-patterns and good patterns)

## When

Every project that uses API keys, passwords, tokens, or connection strings.

## How

**Do:**
```
.env                  # Actual secrets (gitignored)
.env.example          # Template with placeholder values (tracked)
.gitignore            # Must contain .env, .env.*, *.key, *.pem
```

`.env.example`:
```
CRM_API_KEY=your-key-here
GRAPH_CLIENT_SECRET=your-secret-here
DATABASE_URL=postgresql://user:pass@localhost:5432/db
```

`.claude/settings.json` deny rules:
```json
{
  "permissions": {
    "deny": [
      "Read(.env)",
      "Read(.env.*)",
      "Read(~/.ssh/**)",
      "Read(~/.aws/**)"
    ]
  }
}
```

**Don't:**
- Plaintext password files in the project root
- API keys hardcoded in scripts (`api_key = "sk-abc123"`)
- Credentials in CLAUDE.md (Claude reads this every request)
- Secrets in settings.local.json allow rules

## Rules

- `.env.example` is the contract for required secrets
- Real `.env` is never committed (verify with `git status`)
- Claude's deny rules prevent accidental reads of secret files
- If credentials are already exposed in git history, rotate them
