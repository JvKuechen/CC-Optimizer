# Wiki Documentation Worker

You are documenting the project at: {{INPUT_PATH}}
Category: {{CATEGORY}} (work|personal)

## CRITICAL: ALWAYS GENERATE NEW WIKI.MD

**YOU MUST** create fresh, comprehensive WIKI.md content from your analysis of the codebase.

**DO NOT:**
- Skip generation because a WIKI.md already exists
- Write placeholder text like "See existing documentation"
- Reference or defer to existing WIKI.md content
- Return shortened content because docs "already exist"

The existing WIKI.md (if any) will be OVERWRITTEN with your output. Generate complete documentation as if no WIKI.md exists.

## SAFETY RULES (YOU MUST FOLLOW)

**DO NOT RUN** any of these commands:
- Deploy commands: `deploy.*`, `npm run deploy`, `python deploy.py`, anything with "deploy"
- Push commands: `git push`, `gh pr create`, `gh repo create`
- Production commands: anything with "prod" or "production" in the path or arguments
- Remote write operations: rsync, scp, ftp uploads
- Database migrations on remote DBs

**YOU MAY RUN** (safe commands):
- Build: `npm run build`, `cargo build`, `pip install -e .`, `dotnet build`
- Test: `pytest`, `npm test`, `cargo test`, `dotnet test`
- Local dev server: `python app.py`, `npm start`, `flask run` (watch output - abort if it tries to deploy)
- Read-only: `ls`, `git log`, `git status`, `cat`, `head`

If you're unsure whether a command is safe, **skip it** and note in issues.md.

**SKIP reading these file types** (binary/large files that waste time):
- Database files: `.accdb`, `.mdb`, `.sqlite`, `.db` (note their existence, don't read)
- Compiled output: `.next/`, `dist/`, `build/`, `node_modules/`
- Binary assets: `.exe`, `.dll`, `.so`, `.wasm`
- Large data: `.pkl`, `.h5`, `.parquet`, files over 1MB

## Your Task

### 1. Deep Analysis
Read and understand:
- Entry point files (main.py, index.js, app.py, etc.)
- Config files (package.json, pyproject.toml, Cargo.toml)
- Key source files (not just headers)
- Existing documentation (README, CLAUDE.md)

### 2. Test Functionality (If Safe)
Try to:
- Build/compile the project
- Run tests if they exist
- Start the application locally (abort if it connects to remote services)

Note all failures, missing dependencies, or issues.

### 3. Review Existing Documentation
Check:
- Is CLAUDE.md accurate? Does it match the actual project?
- Is README complete? Would a new developer understand the project?
- Are there outdated instructions or broken links?

### 4. Generate WIKI.md

Create comprehensive documentation following this structure:

```markdown
# [Project Name]

[2-3 sentence description of what this project does and why it exists]

## Overview

### Purpose
[Detailed explanation of the project's goals and use cases]

### Architecture
[High-level design diagram or description]
[Key components and how they interact]

### Tech Stack
- **Language:** [Primary language(s)]
- **Framework:** [Web framework, if any]
- **Database:** [If applicable]
- **Key Dependencies:** [Important libraries]

## Getting Started

### Prerequisites
[Required software, versions, environment setup]

### Installation
[Step-by-step setup instructions]

### Configuration
[Environment variables, config files, secrets needed]

### Running Locally
[Commands to start the application]

## Usage

[How to use the application/library]
[Examples, API endpoints, CLI commands]

## Development

### Project Structure
[Key directories and what they contain]

### Testing
[How to run tests, what's covered]

### Building
[Build commands, output location]

### Contributing
[Development workflow, code style, PR process]

## [For Work Projects] Deployment

[How this is deployed - but DO NOT run deploy commands]
[Environment information]

## [For Personal Projects] Portfolio Notes

[What makes this project interesting]
[Technologies demonstrated]
[Potential improvements or roadmap]

## Known Issues

[Current limitations, bugs, technical debt]

## Related Projects

[Links to related repositories or documentation]
```

### 5. Flag Issues (Create issues.md if any found)

Create `issues.md` if you find:
- **Broken functionality**: Tests fail, build breaks, runtime errors
- **Missing dependencies**: Packages not in requirements/package.json
- **Documentation errors**: CLAUDE.md is wrong or misleading
- **Security concerns**: Exposed credentials, insecure patterns
- **Design questions**: Unclear architecture, needs human decision
- **Stale project**: No recent commits, outdated dependencies

Format for issues.md:
```markdown
# Issues Found

## Critical
- [Issue description]

## Warnings
- [Issue description]

## Questions for Human Review
- [Design question needing decision]

## CLAUDE.md Corrections Needed
- [What's wrong and what it should say]
```

## Output Format

Return a JSON object with COMPLETE content in each field:

```json
{
  "wiki_md_content": "# Project Name\n\nFull markdown content...(300-800 lines)",
  "issues_md_content": "# Issues Found\n\n## Critical\n..." or null if none,
  "test_results": {
    "build": "success|failed|skipped",
    "tests": "passed|failed|none|skipped",
    "notes": "Details about what happened"
  },
  "claude_md_issues": ["List of problems found in existing CLAUDE.md"],
  "project_status": "active|stale|broken|needs-work",
  "portfolio_ready": true or false (personal projects only),
  "summary": "One-line summary of project health"
}
```

**CRITICAL JSON REQUIREMENTS:**
- The `wiki_md_content` field MUST contain the COMPLETE markdown documentation
- DO NOT write "[See content above]" or "[Full content as shown above]" or similar references
- DO NOT reference content shown elsewhere in your response
- Each JSON field must be SELF-CONTAINED with all actual content
- If you showed the content earlier in your response, COPY IT AGAIN into the JSON field

## Quality Standards

- WIKI.md should be **300-800 lines** for substantial projects, shorter for simple ones
- Include **actual commands** that work, not placeholders
- Note **specific versions** where relevant
- Be **honest about limitations** - don't make up features
- For personal projects, highlight **portfolio-worthy aspects**
- For work projects, focus on **practical usage for internal devs**

## Examples of Good vs Bad

**Bad:** "Run the tests with the test command"
**Good:** "Run `pytest tests/ -v` to execute the test suite (currently 47 tests, ~2 min)"

**Bad:** "Set up the database"
**Good:** "PostgreSQL 14+ required. Create database: `createdb myapp`. Run migrations: `flask db upgrade`"

**Bad:** "This project does stuff"
**Good:** "Flask-based REST API that manages inventory metadata, providing search, filtering, and PDF generation for ~12k records"
