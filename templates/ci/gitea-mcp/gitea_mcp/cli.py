"""Click CLI for gitea-mcp."""

import os
import sys
import json
import click
from typing import Optional
from .client import GiteaClient
from .models import GiteaAPIError


def get_client(ctx) -> GiteaClient:
    """Get configured Gitea client from context."""
    url = ctx.obj.get("url")
    token = ctx.obj.get("token")

    if not url:
        click.echo("Error: GITEA_URL environment variable not set", err=True)
        sys.exit(1)

    if not token:
        click.echo("Error: GITEA_TOKEN environment variable not set", err=True)
        sys.exit(1)

    return GiteaClient(url, token)


def output_result(data, as_json: bool):
    """Output result in requested format."""
    if as_json:
        click.echo(json.dumps(data, indent=2))
    else:
        # Human-readable output
        if isinstance(data, list):
            if not data:
                click.echo("No results found.")
                return
            # Simple table-like output
            for item in data:
                if isinstance(item, dict):
                    # Try to find a sensible display format
                    name = item.get("name") or item.get("title") or item.get("id")
                    click.echo(f"- {name}")
                else:
                    click.echo(f"- {item}")
        elif isinstance(data, dict):
            for key, value in data.items():
                click.echo(f"{key}: {value}")
        else:
            click.echo(str(data))


@click.group()
@click.pass_context
def cli(ctx):
    """gitea-mcp: CLI tool for Gitea API operations."""
    ctx.ensure_object(dict)
    ctx.obj["url"] = os.getenv("GITEA_URL", "")
    ctx.obj["token"] = os.getenv("GITEA_TOKEN", "")


@cli.group()
def repo():
    """Repository management commands."""
    pass


@repo.command("list")
@click.option("--org", help="Organization name")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_context
def repo_list(ctx, org: Optional[str], as_json: bool):
    """List repositories."""
    try:
        client = get_client(ctx)
        repos = client.list_repos(org=org)
        output_result(repos, as_json)
    except GiteaAPIError as e:
        click.echo(f"Error: {e.message}", err=True)
        sys.exit(1)


@repo.command("create")
@click.argument("name")
@click.option("--org", help="Organization name")
@click.option("--public", is_flag=True, help="Make repository public")
@click.option("--description", default="", help="Repository description")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_context
def repo_create(
    ctx, name: str, org: Optional[str], public: bool, description: str, as_json: bool
):
    """Create a new repository."""
    try:
        client = get_client(ctx)
        repo = client.create_repo(
            name=name, org=org, private=not public, description=description
        )
        output_result(repo, as_json)
    except GiteaAPIError as e:
        click.echo(f"Error: {e.message}", err=True)
        sys.exit(1)


@repo.command("delete")
@click.argument("owner")
@click.argument("repo")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_context
def repo_delete(ctx, owner: str, repo: str, as_json: bool):
    """Delete a repository."""
    try:
        client = get_client(ctx)
        result = client.delete_repo(owner, repo)
        if not as_json:
            click.echo(f"Repository {owner}/{repo} deleted successfully.")
        else:
            output_result(result, as_json)
    except GiteaAPIError as e:
        click.echo(f"Error: {e.message}", err=True)
        sys.exit(1)


@repo.command("init")
@click.argument("name")
@click.pass_context
def repo_init(ctx, name: str):
    """Initialize a new repository (placeholder)."""
    click.echo(f"Repository initialization for '{name}' not yet implemented.")
    click.echo("This command will be implemented to:")
    click.echo("  1. Create repository on Gitea")
    click.echo("  2. Initialize local git repo")
    click.echo("  3. Set up remote")
    click.echo("  4. Create initial commit")


@cli.group()
def pr():
    """Pull request management commands."""
    pass


@pr.command("list")
@click.argument("owner")
@click.argument("repo")
@click.option("--state", default="open", help="PR state (open, closed, all)")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_context
def pr_list(ctx, owner: str, repo: str, state: str, as_json: bool):
    """List pull requests."""
    try:
        client = get_client(ctx)
        prs = client.list_prs(owner, repo, state=state)
        output_result(prs, as_json)
    except GiteaAPIError as e:
        click.echo(f"Error: {e.message}", err=True)
        sys.exit(1)


@pr.command("create")
@click.argument("owner")
@click.argument("repo")
@click.option("--title", required=True, help="PR title")
@click.option("--body", default="", help="PR description")
@click.option("--head", required=True, help="Source branch")
@click.option("--base", default="main", help="Target branch")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_context
def pr_create(
    ctx, owner: str, repo: str, title: str, body: str, head: str, base: str, as_json: bool
):
    """Create a pull request."""
    try:
        client = get_client(ctx)
        pr = client.create_pr(owner, repo, title, body, head, base)
        output_result(pr, as_json)
    except GiteaAPIError as e:
        click.echo(f"Error: {e.message}", err=True)
        sys.exit(1)


@pr.command("merge")
@click.argument("owner")
@click.argument("repo")
@click.argument("pr_number", type=int)
@click.option(
    "--method",
    default="merge",
    type=click.Choice(["merge", "rebase", "squash"]),
    help="Merge method",
)
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_context
def pr_merge(ctx, owner: str, repo: str, pr_number: int, method: str, as_json: bool):
    """Merge a pull request."""
    try:
        client = get_client(ctx)
        result = client.merge_pr(owner, repo, pr_number, merge_type=method)
        output_result(result, as_json)
    except GiteaAPIError as e:
        click.echo(f"Error: {e.message}", err=True)
        sys.exit(1)


@pr.command("comment")
@click.argument("owner")
@click.argument("repo")
@click.argument("pr_number", type=int)
@click.option("--body", required=True, help="Comment text")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_context
def pr_comment(ctx, owner: str, repo: str, pr_number: int, body: str, as_json: bool):
    """Add a comment to a pull request."""
    try:
        client = get_client(ctx)
        comment = client.comment_pr(owner, repo, pr_number, body)
        output_result(comment, as_json)
    except GiteaAPIError as e:
        click.echo(f"Error: {e.message}", err=True)
        sys.exit(1)


@cli.group()
def pipeline():
    """Pipeline/workflow management commands."""
    pass


@pipeline.command("status")
@click.argument("owner")
@click.argument("repo")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_context
def pipeline_status(ctx, owner: str, repo: str, as_json: bool):
    """List workflow runs (pipeline status)."""
    try:
        client = get_client(ctx)
        runs = client.list_runs(owner, repo)
        output_result(runs, as_json)
    except GiteaAPIError as e:
        click.echo(f"Error: {e.message}", err=True)
        sys.exit(1)


@pipeline.command("logs")
@click.argument("owner")
@click.argument("repo")
@click.argument("run_id", type=int)
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_context
def pipeline_logs(ctx, owner: str, repo: str, run_id: int, as_json: bool):
    """Get workflow run details and jobs (logs)."""
    try:
        client = get_client(ctx)
        run = client.get_run(owner, repo, run_id)
        jobs = client.get_run_jobs(owner, repo, run_id)

        result = {"run": run, "jobs": jobs}
        output_result(result, as_json)
    except GiteaAPIError as e:
        click.echo(f"Error: {e.message}", err=True)
        sys.exit(1)


@pipeline.command("promote")
@click.argument("owner")
@click.argument("repo")
@click.argument("workflow_id")
@click.option("--ref", default="main", help="Git ref to run on")
@click.option("--input", "inputs", multiple=True, help="Input key=value pairs")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_context
def pipeline_promote(
    ctx, owner: str, repo: str, workflow_id: str, ref: str, inputs: tuple, as_json: bool
):
    """Trigger a workflow dispatch (promote)."""
    try:
        # Parse inputs
        input_dict = {}
        for inp in inputs:
            if "=" not in inp:
                click.echo(f"Error: Invalid input format '{inp}'. Use key=value", err=True)
                sys.exit(1)
            key, value = inp.split("=", 1)
            input_dict[key] = value

        client = get_client(ctx)
        result = client.dispatch_workflow(
            owner, repo, workflow_id, ref=ref, inputs=input_dict if input_dict else None
        )

        if not as_json:
            click.echo(f"Workflow '{workflow_id}' dispatched successfully on ref '{ref}'.")
        else:
            output_result(result, as_json)
    except GiteaAPIError as e:
        click.echo(f"Error: {e.message}", err=True)
        sys.exit(1)


@cli.group()
def secrets():
    """Secrets management commands."""
    pass


@secrets.command("list")
@click.argument("owner")
@click.argument("repo")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_context
def secrets_list(ctx, owner: str, repo: str, as_json: bool):
    """List repository secrets."""
    try:
        client = get_client(ctx)
        secrets = client.list_secrets(owner, repo)
        output_result(secrets, as_json)
    except GiteaAPIError as e:
        click.echo(f"Error: {e.message}", err=True)
        sys.exit(1)


@secrets.command("set")
@click.argument("owner")
@click.argument("repo")
@click.argument("name")
@click.option("--value", required=True, help="Secret value")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_context
def secrets_set(ctx, owner: str, repo: str, name: str, value: str, as_json: bool):
    """Create or update a repository secret."""
    try:
        client = get_client(ctx)
        result = client.set_secret(owner, repo, name, value)

        if not as_json:
            click.echo(f"Secret '{name}' set successfully.")
        else:
            output_result(result, as_json)
    except GiteaAPIError as e:
        click.echo(f"Error: {e.message}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()
