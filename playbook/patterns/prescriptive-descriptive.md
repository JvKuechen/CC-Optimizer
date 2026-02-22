# Prescriptive vs Descriptive Split

**Source:** Project Flat

## When

Projects with complex architecture where Claude needs both "how it works" (descriptive) and "what to do" (prescriptive). Common in game dev, framework-heavy apps, and domain-specific codebases.

## How

Separate CLAUDE.md into two clear sections. Prescriptive rules go in CLAUDE.md (always loaded). Descriptive reference goes in `.claude/rules/` or `.claude/skills/` (loaded on demand).

```
CLAUDE.md (prescriptive - always loaded):
  "All new systems MUST use the plugin pattern. Create a Plugin struct, register in app.rs."
  "NEVER use direct component access. Always go through the facade."

.claude/rules/architecture.md (descriptive - loaded when editing src/):
  "The ECS pattern separates data (Components) from logic (Systems).
   Bevy schedules systems automatically based on their parameters..."

.claude/skills/ecs-reference/SKILL.md (descriptive - loaded on /ecs):
  [Detailed framework reference, examples, migration history]
```

## Rules

- CLAUDE.md = commands ("do X", "never Y", "always Z")
- Rules/skills = explanations ("X works by...", "the reason for Y is...")
- If a descriptive section in CLAUDE.md doesn't prevent mistakes, move it out
- Learning mode (teaching Claude a framework) belongs in skills, not CLAUDE.md
