# Fan-Out Skill

Run parallel Claude workers for bulk operations.

## Usage

```
/fan-out discovery [--start PATH] [--max-levels N]
/fan-out status
/fan-out reset
```

## Commands

### discovery

Run BFS project discovery starting from specified paths.

```bash
# Start discovery from user home
python fan-out/discovery.py --start "~/claudes"

# Start from specific folders
python fan-out/discovery.py --start "~/claudes/Documents" "~/claudes/Dropbox"

# Limit depth
python fan-out/discovery.py --start "~/claudes" --max-levels 5
```

### status

Check current discovery progress.

```bash
python fan-out/discovery.py --status
```

### reset

Clear state and start fresh.

```bash
python fan-out/discovery.py --reset
```

## How It Works

1. **BFS Exploration**: Starts at given paths, explores level by level
2. **Parallel Workers**: Each folder is analyzed by a headless Claude (haiku)
3. **Project Detection**: Workers identify projects by markers (.git, package.json, etc.)
4. **Candidate Discovery**: Workers identify subfolders worth exploring
5. **Resumability**: State saved after each level, can resume if interrupted

## Output

Results are saved to `fan-out/results/`:
- `discovery-state.json` - Current state (for resumption)
- `discovery-progress.json` - Worker progress tracking
- `discovery-report-{timestamp}.json` - Final report with all projects

## Configuration

Edit `fan-out/configs/discovery.json`:
- `model`: Primary Claude model for workers (default: haiku)
- `max_concurrent`: Parallel workers (default: 5)
- `timeout_seconds`: Per-worker timeout (default: 90)
- `max_turns`: Max API round-trips per worker (default: 5)
- `error_recovery`: Cascade of models to try on failure (default: ["sonnet", "opus"])

## Error Recovery Cascade

When a haiku worker fails:
1. Sonnet attempts to complete the same task
2. If sonnet fails, opus investigates
3. All recovery attempts are logged to `results/wrangle-log.json`

Review the wrangle log after runs to identify systematic issues in the pipeline.

## After Discovery

Once discovery completes, review the report and:
1. Identify projects to consolidate to `~/claudes/claudes/`
2. Categorize as Work/ or Personal/
3. Initialize as Claude workspaces with `/optimize-workspace`

## Adding New Worker Types

1. Create prompt template in `fan-out/workers/your-worker.md`
2. Create config in `fan-out/configs/your-config.json`
3. Use orchestrator directly or create a wrapper like discovery.py
