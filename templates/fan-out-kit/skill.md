# Fan-Out Skill

Run parallel Claude workers to analyze and test examples across repos.

## Usage

```
/fan-out analyze [--inputs-file PATH] [--concurrency N]
/fan-out status
/fan-out reset
```

## Workflow

1. **Workers analyze in parallel** - Test examples, assess portability, make recommendations
2. **Main Claude reviews serially** - Decides what to port based on worker analysis
3. **Main Claude implements** - Ports selected examples with source attribution

## Quick Start

```bash
# 1. List examples to analyze
find /c/repos/bevy/examples -name "*.rs" > fan-out/example-paths.txt
find /c/repos/quinn/quinn/examples -name "*.rs" >> fan-out/example-paths.txt

# 2. Run parallel analysis
python fan-out/orchestrator.py test-examples.json \
  --inputs-file fan-out/example-paths.txt \
  --output analysis-results.json

# 3. Review results, then ask main Claude to port selected examples
```

## Commands

### analyze

Analyze examples from specified paths.

```bash
python fan-out/orchestrator.py test-examples.json \
  --inputs-file fan-out/example-paths.txt \
  --output analysis-results.json

# Or specify paths directly
python fan-out/orchestrator.py test-examples.json \
  --inputs "C:/repos/bevy/examples/3d/lighting.rs" "C:/repos/quinn/examples/client.rs"
```

### status

Check results after a run.

```bash
python -c "import json; r=json.load(open('fan-out/results/analysis-results.json')); print(f\"Total: {r['summary']['total']}, Success: {r['summary']['success']}, Failed: {r['summary']['failed']}\")"
```

### reset

Clear state and start fresh.

```bash
rm fan-out/results/test-examples-progress.json
```

## Worker Output

Each worker returns analysis including:

```json
{
  "example_path": "...",
  "status": "success|build_failed|...",
  "porting_analysis": {
    "core_functionality": "what it does",
    "reusable_parts": ["functions to extract"],
    "required_adaptations": ["changes needed"],
    "integration_points": "how it connects"
  },
  "recommendation": "port|skip|defer",
  "recommendation_reason": "why"
}
```

## Porting Convention

When main Claude ports an example, add source attribution:

```rust
// Ported from: bevy/examples/3d/lighting.rs
// Original: https://github.com/bevyengine/bevy/blob/main/examples/3d/lighting.rs
fn setup_lighting(/* ... */) {
    // ...
}
```

This enables tracing regressions back to the source.

## Configuration

Edit `fan-out/configs/test-examples.json`:

```json
{
  "worker_prompt_file": "workers/example-tester.md",
  "model": "haiku",
  "max_concurrent": 3,
  "timeout_seconds": 180,
  "max_turns": 8,
  "resume_file": "test-examples-progress.json",
  "error_recovery": ["sonnet"]
}
```

| Option | Default | Description |
|--------|---------|-------------|
| `model` | `haiku` | Primary model (haiku/sonnet/opus) |
| `max_concurrent` | `3` | Parallel workers |
| `timeout_seconds` | `180` | Per-worker timeout |
| `max_turns` | `8` | Max API round-trips per worker |
| `error_recovery` | `["sonnet"]` | Cascade models on failure |

## Output

Results saved to `fan-out/results/`:
- `{output}.json` - Full analysis from all workers
- `test-examples-progress.json` - Progress tracking (for resumption)
- `wrangle-log.json` - Error recovery attempts

## Tips

- Start with `max_concurrent: 2` until you verify workers work correctly
- Review `wrangle-log.json` to identify systematic issues
- Workers that just chat instead of using tools may need the prompt strengthened
- Filter results by `recommendation: "port"` to find candidates
