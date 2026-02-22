"""Deploy fan-out kit to a target workspace."""
import shutil
import sys
from pathlib import Path


def deploy(target_dir: str):
    target = Path(target_dir)
    if not target.exists():
        print(f"Error: Target directory does not exist: {target}")
        sys.exit(1)

    # Source directories
    kit_dir = Path(__file__).parent
    fanout_src = kit_dir.parent.parent / "fan-out"

    # Create target fan-out directory
    fanout_dest = target / "fan-out"
    fanout_dest.mkdir(exist_ok=True)

    # Copy orchestrator
    shutil.copy2(fanout_src / "orchestrator.py", fanout_dest / "orchestrator.py")
    print(f"  Copied orchestrator.py")

    # Copy kit files
    (fanout_dest / "workers").mkdir(exist_ok=True)
    (fanout_dest / "configs").mkdir(exist_ok=True)
    (fanout_dest / "results").mkdir(exist_ok=True)

    shutil.copy2(kit_dir / "workers" / "example-tester.md", fanout_dest / "workers" / "example-tester.md")
    shutil.copy2(kit_dir / "configs" / "test-examples.json", fanout_dest / "configs" / "test-examples.json")
    print(f"  Copied worker template and config")

    # Create empty example-paths.txt as starter
    (fanout_dest / "example-paths.txt").write_text("# Add example paths here, one per line\n")

    # Copy skill to .claude/skills
    skills_dir = target / ".claude" / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(kit_dir / "skill.md", skills_dir / "fan-out.md")
    print(f"  Copied skill to .claude/skills/fan-out.md")

    # Create .gitignore for results
    gitignore = fanout_dest / ".gitignore"
    gitignore.write_text("results/\n__pycache__/\n")

    print(f"\nFan-out kit deployed to: {fanout_dest}")
    print(f"\nNext steps:")
    print(f"  1. Create example-paths.txt with paths to test")
    print(f"  2. Run: python fan-out/orchestrator.py test-examples.json --inputs-file fan-out/example-paths.txt")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python deploy.py <target-workspace-path>")
        print("Example: python deploy.py C:/Users/you/claudes/hybridyne")
        sys.exit(1)

    deploy(sys.argv[1])
