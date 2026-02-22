---
paths:
  - "**/settings.json"
  - "**/settings.local.json"
---

# Writing Claude Code Settings Files

## Permission Rule Syntax
- `Bash(npm run *)` — wildcard after space = word boundary match
- `Bash(npm*)` — wildcard without space = matches anything starting with "npm"
- `Read(.env.*)` — file pattern match
- `Read(./secrets/**)` — recursive directory match
- `WebFetch(domain:github.com)` — domain filtering

## Evaluation Order
deny rules always win. Evaluation: deny → ask → allow (first match wins).

## Scope Precedence (highest to lowest)
1. managed-settings.json (IT-enforced, cannot override)
2. CLI arguments (session only)
3. .claude/settings.local.json (user, this project, gitignored)
4. .claude/settings.json (team, in git)
5. ~/.claude/settings.json (user, all projects)

## Common Patterns by Stack
- Node.js: `Bash(npm *)`, `Bash(npx *)`, `Bash(node *)`
- Python: `Bash(python *)`, `Bash(pip *)`, `Bash(pytest *)`, `Bash(uv *)`
- Rust: `Bash(cargo *)`, `Bash(rustc *)`
- Go: `Bash(go *)`
- Java: `Bash(gradle *)`, `Bash(mvn *)`, `Bash(java *)`
- .NET: `Bash(dotnet *)`
- Docker: `Bash(docker *)`, `Bash(docker-compose *)`

## Always Deny
- `Bash(git push --force *)`, `Bash(git push -f *)`
- `Bash(git reset --hard *)`, `Bash(git clean -f *)`
- `Read(.env)`, `Read(.env.*)`, `Read(~/.ssh/**)`, `Read(~/.aws/**)`
