"""Gather metrics for project comparison/deduplication."""
import json
import os
import subprocess
import sys
from pathlib import Path
from datetime import datetime

EXCLUDE_DIRS = {'.git', 'node_modules', '__pycache__', 'dist', 'build', '.venv', 'venv', '.claude'}
SOURCE_EXTENSIONS = {'.py', '.js', '.ts', '.tsx', '.jsx', '.go', '.rs', '.cs', '.java', '.cpp', '.c', '.h'}


def run_git(path: Path, *args) -> str:
    """Run a git command and return output."""
    try:
        result = subprocess.run(
            ['git', '-C', str(path)] + list(args),
            capture_output=True, text=True, timeout=30
        )
        return result.stdout.strip() if result.returncode == 0 else ''
    except Exception:
        return ''


def count_lines(file_path: Path) -> int:
    """Count lines in a file."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return sum(1 for _ in f)
    except Exception:
        return 0


def get_file_inventory(path: Path) -> dict:
    """Get file counts by extension."""
    inventory = {}
    total_files = 0
    source_files = 0
    total_loc = 0

    for root, dirs, files in os.walk(path):
        # Skip excluded directories
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]

        for f in files:
            if f.startswith('.'):
                continue
            total_files += 1
            ext = Path(f).suffix.lower()
            inventory[ext] = inventory.get(ext, 0) + 1

            if ext in SOURCE_EXTENSIONS:
                source_files += 1
                total_loc += count_lines(Path(root) / f)

    return {
        'total_files': total_files,
        'source_files': source_files,
        'lines_of_code': total_loc,
        'by_extension': inventory
    }


def check_key_files(path: Path) -> dict:
    """Check for presence of key project files."""
    key_files = {
        'readme': ['README.md', 'README.txt', 'README', 'readme.md'],
        'claude_md': ['CLAUDE.md'],
        'package_json': ['package.json'],
        'pyproject': ['pyproject.toml', 'setup.py', 'requirements.txt'],
        'cargo': ['Cargo.toml'],
        'go_mod': ['go.mod'],
        'csproj': list(path.glob('*.csproj')),
        'tests': ['tests', 'test', '__tests__', 'spec'],
        'ci_cd': ['.github/workflows', '.gitlab-ci.yml', 'Jenkinsfile'],
        'docker': ['Dockerfile', 'docker-compose.yml', 'docker-compose.yaml'],
    }

    result = {}
    for key, patterns in key_files.items():
        if key == 'csproj':
            result[key] = len(patterns) > 0
        elif key in ['tests', 'ci_cd']:
            result[key] = any((path / p).exists() for p in patterns)
        else:
            result[key] = any((path / p).exists() for p in patterns)

    return result


def get_git_metrics(path: Path) -> dict:
    """Get git history metrics."""
    commit_count = run_git(path, 'rev-list', '--count', 'HEAD')
    last_commit_date = run_git(path, 'log', '-1', '--format=%ai')
    first_commit_date = run_git(path, 'log', '--reverse', '--format=%ai', '-1')
    recent_commits = run_git(path, 'log', '--oneline', '-10')

    # Get branch info
    branches = run_git(path, 'branch', '-a')
    branch_count = len([b for b in branches.split('\n') if b.strip()]) if branches else 0

    # Check for remote
    remote = run_git(path, 'remote', '-v')

    return {
        'commit_count': int(commit_count) if commit_count.isdigit() else 0,
        'last_commit': last_commit_date[:10] if last_commit_date else 'unknown',
        'first_commit': first_commit_date[:10] if first_commit_date else 'unknown',
        'recent_commits': recent_commits.split('\n') if recent_commits else [],
        'branch_count': branch_count,
        'has_remote': bool(remote),
        'remote_url': remote.split('\n')[0].split('\t')[1].split()[0] if remote else None
    }


def analyze_project(path: Path) -> dict:
    """Full analysis of a project."""
    if not path.exists():
        return {'error': f'Path does not exist: {path}'}

    metrics = {
        'path': str(path),
        'name': path.name,
        'analyzed_at': datetime.now().isoformat(),
    }

    # Check if it's a git repo
    if not (path / '.git').exists():
        metrics['is_git_repo'] = False
        metrics['git'] = {}
    else:
        metrics['is_git_repo'] = True
        metrics['git'] = get_git_metrics(path)

    metrics['files'] = get_file_inventory(path)
    metrics['key_files'] = check_key_files(path)

    # Read CLAUDE.md summary if exists
    claude_md = path / 'CLAUDE.md'
    if claude_md.exists():
        try:
            with open(claude_md, 'r', encoding='utf-8') as f:
                content = f.read()
                # Get first paragraph after # CLAUDE.md
                lines = content.split('\n')
                summary_lines = []
                in_summary = False
                for line in lines:
                    if line.startswith('# '):
                        in_summary = True
                        continue
                    if in_summary:
                        if line.startswith('#') or line.startswith('## '):
                            break
                        if line.strip():
                            summary_lines.append(line.strip())
                metrics['claude_md_summary'] = ' '.join(summary_lines)[:200]
        except Exception:
            metrics['claude_md_summary'] = None

    return metrics


def compare_projects(paths: list[Path]) -> dict:
    """Compare multiple projects and generate report."""
    projects = []
    for p in paths:
        path = Path(p)
        if not path.is_absolute():
            path = Path.cwd() / path
        projects.append(analyze_project(path))

    # Generate comparison
    comparison = {
        'projects': projects,
        'comparison_date': datetime.now().isoformat(),
    }

    # Find potential winner (most commits, most recent, most LOC)
    valid_projects = [p for p in projects if 'error' not in p]
    if len(valid_projects) >= 2:
        # Score each project
        for p in valid_projects:
            score = 0
            score += p['git'].get('commit_count', 0) * 2  # Weight commits heavily
            score += p['files'].get('lines_of_code', 0) / 100  # LOC contributes
            score += p['files'].get('source_files', 0) * 5  # Source files matter
            if p['key_files'].get('tests'):
                score += 50  # Tests are valuable
            if p['key_files'].get('ci_cd'):
                score += 30  # CI/CD is valuable
            p['_score'] = score

        sorted_projects = sorted(valid_projects, key=lambda x: x['_score'], reverse=True)
        comparison['recommended_keep'] = sorted_projects[0]['name']
        comparison['recommended_archive'] = [p['name'] for p in sorted_projects[1:]]
        comparison['confidence'] = 'high' if sorted_projects[0]['_score'] > sorted_projects[1]['_score'] * 1.5 else 'medium'

    return comparison


def main():
    if len(sys.argv) < 3:
        print("Usage: python project-metrics.py <path1> <path2> [path3...]")
        print("       python project-metrics.py --single <path>")
        sys.exit(1)

    if sys.argv[1] == '--single':
        # Single project analysis
        result = analyze_project(Path(sys.argv[2]))
        print(json.dumps(result, indent=2))
    else:
        # Comparison mode
        paths = [Path(p) for p in sys.argv[1:]]
        result = compare_projects(paths)
        print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
