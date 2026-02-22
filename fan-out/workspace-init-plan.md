# Workspace Initialization & Optimization Plan

## Overview

Two-phase approach to initialize 64+ newly migrated projects as Claude workspaces:

1. **Phase 1: Deterministic Init** (Python script, no LLM)
   - Create `.claude/` folder structure
   - Run `git init` where needed
   - Deploy baseline permissions

2. **Phase 2: Fan-out Optimization** (Parallel haiku workers)
   - Analyze each project's stack
   - Generate CLAUDE.md
   - Configure stack-specific permissions
   - Cascade error recovery: haiku -> sonnet -> opus

---

## Phase 1: Deterministic Initialization

### Script: `init-workspaces.py`

For each project in Work/ and Personal/:

1. **Git init** if no `.git/` exists
2. **Create `.claude/`** directory
3. **Deploy baseline `settings.json`** with universally safe permissions:
   ```json
   {
     "permissions": {
       "allow": [
         "Bash(git status)",
         "Bash(git diff *)",
         "Bash(git log *)",
         "Bash(ls *)",
         "Bash(pwd)"
       ]
     }
   }
   ```
4. **Log** which projects need optimization (no CLAUDE.md yet)

### Output
- `init-results.json`: List of initialized projects with status
- `optimization-queue.json`: Projects ready for Phase 2

---

## Phase 2: Fan-out Optimization

### Config: `configs/optimize.json`

```json
{
  "worker_prompt_file": "workers/workspace-optimizer.md",
  "model": "haiku",
  "max_concurrent": 5,
  "timeout_seconds": 180,
  "max_turns": 10,
  "error_recovery": ["sonnet", "opus"],
  "resume_file": "optimization-progress.json"
}
```

### Worker Prompt: `workers/workspace-optimizer.md`

The worker will:
1. **Detect project type** from markers:
   - `package.json` -> Node/TypeScript
   - `pyproject.toml` / `requirements.txt` / `*.py` -> Python
   - `Cargo.toml` -> Rust
   - `go.mod` -> Go
   - `*.csproj` -> .NET
   - `docker-compose.yml` -> Docker
   - `Makefile` -> C/C++

2. **Analyze project purpose** from:
   - README.md / README
   - Directory structure
   - Main entry points

3. **Generate CLAUDE.md** with:
   - Project description (1-2 sentences)
   - Stack/tech used
   - Key commands (build, test, run)
   - Important directories
   - @imports for existing docs

4. **Configure permissions** in `.claude/settings.json`:
   - Stack-specific safe commands
   - Deny rules for sensitive files

5. **Return JSON**:
   ```json
   {
     "project_type": "python",
     "created_files": ["CLAUDE.md", ".claude/settings.json"],
     "key_commands": ["pytest", "python main.py"],
     "notes": "Flask web app with PostgreSQL"
   }
   ```

---

## Execution Plan

### Step 1: Run Phase 1
```bash
python fan-out/init-workspaces.py
```
- Creates `.claude/` in all projects
- Outputs `optimization-queue.json`

### Step 2: Run Phase 2
```bash
python fan-out/optimize-workspaces.py
```
- Reads queue
- Spawns parallel haiku workers
- Each worker optimizes one project
- Failed workers retry with sonnet, then opus
- Results logged to `optimization-results.json`

### Step 3: Review
- Check `optimization-results.json` for any failures
- Spot-check a few CLAUDE.md files for quality
- Manually fix any edge cases

---

## Files to Create

| File | Purpose |
|------|---------|
| `fan-out/init-workspaces.py` | Phase 1: deterministic init |
| `fan-out/optimize-workspaces.py` | Phase 2: orchestrator runner |
| `fan-out/configs/optimize.json` | Orchestrator config |
| `fan-out/workers/workspace-optimizer.md` | Worker prompt |

---

## Risk Mitigation

1. **Sandboxing**: Workers can only modify files in their target project directory
2. **Cascading recovery**: haiku failures get retried by smarter models
3. **Dry-run mode**: Can preview what would be created before executing
4. **Resume support**: If interrupted, resumes from last checkpoint

---

## Estimated Resources

- **Projects**: ~64
- **Workers**: 5 concurrent
- **Time per project**: ~30-60 seconds (haiku)
- **Total time**: ~15-20 minutes
- **Cost**: Mostly haiku tokens, minimal sonnet/opus for wrangles

---

## Success Criteria

- [ ] All 64+ projects have `.claude/` folder
- [ ] All projects have CLAUDE.md with accurate description
- [ ] All projects have stack-appropriate permissions
- [ ] < 5% require manual intervention
