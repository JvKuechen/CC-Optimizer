"""Project discovery: BFS exploration of filesystem to find projects."""
import json
import sys
from datetime import datetime
from pathlib import Path

# Add parent to path for sibling import
sys.path.insert(0, str(Path(__file__).parent))
from orchestrator import FanOutConfig, Orchestrator


class ProjectDiscovery:
    """BFS exploration to find all projects on the filesystem."""

    def __init__(self, config_path: str = "configs/discovery.json"):
        self.base_dir = Path(__file__).parent
        self.config = FanOutConfig.from_file(str(self.base_dir / config_path))
        self.results_dir = self.base_dir / "results"
        self.results_dir.mkdir(exist_ok=True)

        # Track discovered projects and exploration state
        self.projects: list[dict] = []
        self.explored: set[str] = set()
        self.to_explore: list[str] = []

        # State file for resumability
        self.state_file = self.results_dir / "discovery-state.json"
        self._load_state()

    def _load_state(self):
        """Load state from previous run."""
        if self.state_file.exists():
            with open(self.state_file, "r") as f:
                state = json.load(f)
            self.projects = state.get("projects", [])
            self.explored = set(state.get("explored", []))
            self.to_explore = state.get("to_explore", [])
            print(f"Resumed: {len(self.projects)} projects found, {len(self.explored)} folders explored")

    def _save_state(self):
        """Save state for resumability."""
        with open(self.state_file, "w") as f:
            json.dump({
                "projects": self.projects,
                "explored": list(self.explored),
                "to_explore": self.to_explore,
                "last_updated": datetime.now().isoformat()
            }, f, indent=2)

    def _normalize_path(self, path: str) -> str:
        """Normalize path for consistent comparison."""
        return str(Path(path).resolve()).replace("\\", "/")

    def run(self, start_paths: list[str], max_levels: int = 10):
        """Run BFS discovery starting from given paths."""
        # Initialize queue if empty
        if not self.to_explore:
            self.to_explore = [self._normalize_path(p) for p in start_paths]

        level = 0
        while self.to_explore and level < max_levels:
            level += 1
            current_batch = [p for p in self.to_explore if p not in self.explored]
            self.to_explore = []

            if not current_batch:
                print("No more folders to explore")
                break

            print(f"\n=== Level {level}: Exploring {len(current_batch)} folders ===")

            # Create orchestrator for this batch
            orchestrator = Orchestrator(self.config, self.base_dir)
            results = orchestrator.run(current_batch)

            # Process results
            for result in results:
                self.explored.add(result.input_path)

                if not result.success:
                    print(f"  Warning: {result.input_path}: {result.error}")
                    continue

                output = result.output

                # Check if it's a project
                if output.get("is_project"):
                    project_info = {
                        "path": output.get("path", result.input_path),
                        "type": output.get("project_type", "unknown"),
                        "markers": output.get("project_markers", []),
                        "name": output.get("project_name", Path(result.input_path).name),
                        "discovered_at": datetime.now().isoformat()
                    }
                    self.projects.append(project_info)
                    print(f"  PROJECT: {project_info['name']} ({project_info['type']})")

                # Queue subfolders for next level
                candidates = output.get("candidate_subfolders", [])
                for candidate in candidates:
                    norm_candidate = self._normalize_path(candidate)
                    if norm_candidate not in self.explored and norm_candidate not in self.to_explore:
                        self.to_explore.append(norm_candidate)

            # Save progress after each level
            self._save_state()
            print(f"  Level {level} complete. Projects: {len(self.projects)}, Next level: {len(self.to_explore)} folders")

        # Final save
        self._save_state()
        self._save_final_report()

        return self.projects

    def _save_final_report(self):
        """Save final discovery report."""
        report_path = self.results_dir / f"discovery-report-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"

        # Group by type
        by_type: dict[str, list] = {}
        for project in self.projects:
            ptype = project.get("type", "unknown")
            if ptype not in by_type:
                by_type[ptype] = []
            by_type[ptype].append(project)

        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_projects": len(self.projects),
                "folders_explored": len(self.explored),
                "by_type": {k: len(v) for k, v in by_type.items()}
            },
            "projects": self.projects,
            "by_type": by_type
        }

        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)

        print(f"\nFinal report saved to: {report_path}")
        print(f"Total projects found: {len(self.projects)}")
        for ptype, items in sorted(by_type.items()):
            print(f"  {ptype}: {len(items)}")

    def reset(self):
        """Reset discovery state to start fresh."""
        self.projects = []
        self.explored = set()
        self.to_explore = []
        if self.state_file.exists():
            self.state_file.unlink()
        print("Discovery state reset")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Discover projects via BFS")
    parser.add_argument("--start", nargs="+", default=None,
                        help="Starting paths for discovery (default: claudes_dir from config)")
    parser.add_argument("--max-levels", type=int, default=10,
                        help="Maximum depth to explore")
    parser.add_argument("--reset", action="store_true",
                        help="Reset and start fresh")
    parser.add_argument("--status", action="store_true",
                        help="Show current discovery status")

    args = parser.parse_args()

    discovery = ProjectDiscovery()

    if args.reset:
        discovery.reset()
        return

    if args.status:
        print(f"Projects found: {len(discovery.projects)}")
        print(f"Folders explored: {len(discovery.explored)}")
        print(f"Pending exploration: {len(discovery.to_explore)}")
        return

    start_paths = args.start
    if start_paths is None:
        from config import resolve_claudes_dir
        start_paths = [str(resolve_claudes_dir().parent)]

    discovery.run(start_paths, args.max_levels)


if __name__ == "__main__":
    main()
