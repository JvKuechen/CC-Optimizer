# Deduplicate Projects

Analyzes 2+ potentially duplicate projects and consolidates them into one.

## Usage

```
/deduplicate-projects <path1> <path2> [path3...]
```

Example:
```
/deduplicate-projects claudes/Personal/project-a claudes/Personal/project-b
```

## Workflow

### Phase 1: Analysis (Read-Only)

For each project, gather:

1. **Git History**
   ```bash
   git -C "<path>" log --oneline -20
   git -C "<path>" log -1 --format="%ai" # Last commit date
   git -C "<path>" rev-list --count HEAD # Total commits
   ```

2. **File Inventory**
   - Total file count (excluding .git, node_modules, __pycache__, dist, build)
   - Key files present: README, CLAUDE.md, package.json, pyproject.toml, etc.
   - Source file count by extension (.py, .js, .ts, etc.)

3. **Code Metrics**
   - Lines of code (source files only)
   - Test coverage presence (tests/, __tests__, *_test.py, *.spec.ts)
   - Documentation presence

4. **Project Health Indicators**
   - Has working build/run commands in CLAUDE.md?
   - Has dependencies defined (package.json, requirements.txt, etc.)?
   - Has CI/CD config (.github/workflows, .gitlab-ci.yml)?

### Phase 2: Comparison Report

Generate a comparison table:

```
| Metric              | Project A         | Project B         |
|---------------------|-------------------|-------------------|
| Path                | .../project-a     | .../project-b     |
| Last commit         | 2025-08-15        | 2026-01-10        |
| Total commits       | 45                | 127               |
| Source files        | 12                | 23                |
| Lines of code       | 1,200             | 3,400             |
| Has tests           | No                | Yes               |
| Has README          | Basic             | Detailed          |
| Has working build   | Unknown           | Yes               |
```

### Phase 3: Recommendation

Based on analysis, recommend one of:

1. **Keep B, archive A** - B is clearly more developed
2. **Keep A, archive B** - A is more complete despite B being newer (failed refactor)
3. **Merge required** - Each has unique valuable content
4. **Need user input** - Too close to call automatically

For merge scenarios, identify:
- Files unique to each project that should be preserved
- Files that exist in both but differ (need manual review)
- Which project should be the "base" for the merge

### Phase 4: Execution (With User Approval)

After user confirms the recommendation:

**For "Keep X, archive Y":**
1. Create archive: `claudes/Archive/<project-name>-<date>/`
2. Move the deprecated project there
3. Update any cross-references if known

**For "Merge required":**
1. Identify base project (more complete one)
2. Copy unique files from secondary to base
3. Flag conflicting files for manual review
4. Archive the secondary project after merge

## Output Format

The skill outputs a structured analysis then asks for confirmation:

```
## Duplicate Analysis: project-a vs project-b

### Summary
Both projects are VS Code extensions for code visualization. project-b appears
to be the active development version with more commits and features.

### Comparison
[table here]

### Unique Content
- project-a has: experimental-renderer/ (not in project-b)
- project-b has: tests/, multiple language parsers

### Recommendation
**Keep project-b, archive project-a**

The experimental renderer in project-a could be manually reviewed and ported if valuable.

### Proposed Actions
1. Move project-a to claudes/Archive/project-a-20260129/
2. (Optional) Copy experimental-renderer/ to project-b for review

Proceed? [Yes / No / Show more details]
```

## Configuration

Model: **opus** (complex reasoning required for comparing codebases)

This skill does NOT use fan-out - it's interactive and requires user judgment.

## Edge Cases

- **Empty/broken projects**: Flag and recommend deletion
- **Forks of external repos**: Note the upstream and recommend keeping only if local changes exist
- **Same name, different projects**: Detect via completely different file structures
- **3+ duplicates**: Compare all pairwise, recommend consolidation order
