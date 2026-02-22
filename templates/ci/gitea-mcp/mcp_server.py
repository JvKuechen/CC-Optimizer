"""MCP server wrapper for gitea-mcp.

Thin wrapper that exposes gitea-mcp CLI functions as MCP tools
for Claude Code. Run as: python -m gitea_mcp.mcp_server

Requires: mcp package (pip install mcp)

Environment variables:
    GITEA_URL   - Gitea instance URL (default: https://gitea.example.com)
    GITEA_TOKEN - Gitea API token
"""

import os
import json
import sys
from typing import Any

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
except ImportError:
    print("Error: mcp package not installed. Run: pip install mcp", file=sys.stderr)
    sys.exit(1)

from gitea_mcp.client import GiteaClient
from gitea_mcp.models import GiteaAPIError


def get_client() -> GiteaClient:
    """Create a GiteaClient from environment variables."""
    url = os.getenv("GITEA_URL", "https://gitea.example.com")
    token = os.getenv("GITEA_TOKEN", "")
    if not token:
        raise ValueError("GITEA_TOKEN environment variable not set")
    return GiteaClient(url, token)


def make_result(data: Any) -> list:
    """Format result as MCP TextContent."""
    return [TextContent(type="text", text=json.dumps(data, indent=2))]


def make_error(message: str) -> list:
    """Format error as MCP TextContent."""
    return [TextContent(type="text", text=json.dumps({"error": message}))]


# --- Server setup ---

server = Server("gitea-mcp")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """Return available tools."""
    return [
        Tool(
            name="gitea_repo_list",
            description="List Gitea repositories. Optionally filter by organization.",
            inputSchema={
                "type": "object",
                "properties": {
                    "org": {
                        "type": "string",
                        "description": "Organization name (optional, lists all if omitted)",
                    }
                },
            },
        ),
        Tool(
            name="gitea_repo_create",
            description="Create a new Gitea repository.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Repository name"},
                    "org": {"type": "string", "description": "Organization (optional)"},
                    "private": {"type": "boolean", "description": "Private repo", "default": True},
                    "description": {"type": "string", "description": "Description", "default": ""},
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="gitea_pr_list",
            description="List pull requests for a repository.",
            inputSchema={
                "type": "object",
                "properties": {
                    "owner": {"type": "string", "description": "Repo owner"},
                    "repo": {"type": "string", "description": "Repo name"},
                    "state": {"type": "string", "description": "State: open/closed/all", "default": "open"},
                },
                "required": ["owner", "repo"],
            },
        ),
        Tool(
            name="gitea_pr_create",
            description="Create a pull request.",
            inputSchema={
                "type": "object",
                "properties": {
                    "owner": {"type": "string", "description": "Repo owner"},
                    "repo": {"type": "string", "description": "Repo name"},
                    "title": {"type": "string", "description": "PR title"},
                    "body": {"type": "string", "description": "PR description", "default": ""},
                    "head": {"type": "string", "description": "Source branch"},
                    "base": {"type": "string", "description": "Target branch", "default": "main"},
                },
                "required": ["owner", "repo", "title", "head"],
            },
        ),
        Tool(
            name="gitea_pr_comment",
            description="Add a comment to a pull request.",
            inputSchema={
                "type": "object",
                "properties": {
                    "owner": {"type": "string", "description": "Repo owner"},
                    "repo": {"type": "string", "description": "Repo name"},
                    "pr_number": {"type": "integer", "description": "PR number"},
                    "body": {"type": "string", "description": "Comment text"},
                },
                "required": ["owner", "repo", "pr_number", "body"],
            },
        ),
        Tool(
            name="gitea_pipeline_status",
            description="List recent workflow runs (pipeline status) for a repository.",
            inputSchema={
                "type": "object",
                "properties": {
                    "owner": {"type": "string", "description": "Repo owner"},
                    "repo": {"type": "string", "description": "Repo name"},
                },
                "required": ["owner", "repo"],
            },
        ),
        Tool(
            name="gitea_pipeline_logs",
            description="Get details and jobs for a specific workflow run.",
            inputSchema={
                "type": "object",
                "properties": {
                    "owner": {"type": "string", "description": "Repo owner"},
                    "repo": {"type": "string", "description": "Repo name"},
                    "run_id": {"type": "integer", "description": "Workflow run ID"},
                },
                "required": ["owner", "repo", "run_id"],
            },
        ),
        Tool(
            name="gitea_pipeline_promote",
            description="Trigger a workflow dispatch (e.g., promote to active server).",
            inputSchema={
                "type": "object",
                "properties": {
                    "owner": {"type": "string", "description": "Repo owner"},
                    "repo": {"type": "string", "description": "Repo name"},
                    "workflow_id": {"type": "string", "description": "Workflow filename (e.g., promote.yml)"},
                    "ref": {"type": "string", "description": "Git ref", "default": "main"},
                    "inputs": {
                        "type": "object",
                        "description": "Workflow input parameters",
                        "additionalProperties": {"type": "string"},
                    },
                },
                "required": ["owner", "repo", "workflow_id"],
            },
        ),
        Tool(
            name="gitea_commit_status",
            description="Set commit status (build check result) on a commit.",
            inputSchema={
                "type": "object",
                "properties": {
                    "owner": {"type": "string", "description": "Repo owner"},
                    "repo": {"type": "string", "description": "Repo name"},
                    "sha": {"type": "string", "description": "Commit SHA"},
                    "state": {"type": "string", "description": "State: pending/success/error/failure"},
                    "description": {"type": "string", "description": "Status description"},
                    "context": {"type": "string", "description": "Status context", "default": "ci/pipeline"},
                },
                "required": ["owner", "repo", "sha", "state", "description"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list:
    """Handle tool calls."""
    try:
        client = get_client()

        if name == "gitea_repo_list":
            result = client.list_repos(org=arguments.get("org"))
            return make_result(result)

        elif name == "gitea_repo_create":
            result = client.create_repo(
                name=arguments["name"],
                org=arguments.get("org"),
                private=arguments.get("private", True),
                description=arguments.get("description", ""),
            )
            return make_result(result)

        elif name == "gitea_pr_list":
            result = client.list_prs(
                arguments["owner"],
                arguments["repo"],
                state=arguments.get("state", "open"),
            )
            return make_result(result)

        elif name == "gitea_pr_create":
            result = client.create_pr(
                arguments["owner"],
                arguments["repo"],
                arguments["title"],
                arguments.get("body", ""),
                arguments["head"],
                arguments.get("base", "main"),
            )
            return make_result(result)

        elif name == "gitea_pr_comment":
            result = client.comment_pr(
                arguments["owner"],
                arguments["repo"],
                arguments["pr_number"],
                arguments["body"],
            )
            return make_result(result)

        elif name == "gitea_pipeline_status":
            result = client.list_runs(arguments["owner"], arguments["repo"])
            return make_result(result)

        elif name == "gitea_pipeline_logs":
            run = client.get_run(arguments["owner"], arguments["repo"], arguments["run_id"])
            jobs = client.get_run_jobs(arguments["owner"], arguments["repo"], arguments["run_id"])
            return make_result({"run": run, "jobs": jobs})

        elif name == "gitea_pipeline_promote":
            result = client.dispatch_workflow(
                arguments["owner"],
                arguments["repo"],
                arguments["workflow_id"],
                ref=arguments.get("ref", "main"),
                inputs=arguments.get("inputs"),
            )
            return make_result({"dispatched": True, "workflow": arguments["workflow_id"]})

        elif name == "gitea_commit_status":
            result = client.commit_status(
                arguments["owner"],
                arguments["repo"],
                arguments["sha"],
                arguments["state"],
                arguments["description"],
                arguments.get("context", "ci/pipeline"),
            )
            return make_result(result)

        else:
            return make_error(f"Unknown tool: {name}")

    except GiteaAPIError as e:
        return make_error(f"Gitea API error {e.status_code}: {e.message}")
    except ValueError as e:
        return make_error(str(e))
    except Exception as e:
        return make_error(f"Unexpected error: {str(e)}")


async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
