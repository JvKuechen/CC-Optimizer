"""Gitea API client."""

import requests
from typing import Optional, Dict, List, Any
from .models import GiteaAPIError


class GiteaClient:
    """Client for interacting with Gitea API."""

    def __init__(self, base_url: str, token: str):
        """
        Initialize Gitea client.

        Args:
            base_url: Base URL of Gitea instance (e.g., https://git.example.com)
            token: API token for authentication
        """
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"token {token}",
            "Content-Type": "application/json",
        })

    def _request(self, method: str, path: str, **kwargs) -> Any:  # noqa: ANN401
        """
        Make an API request.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            path: API path (will be appended to base_url)
            **kwargs: Additional arguments to pass to requests

        Returns:
            Response JSON data

        Raises:
            GiteaAPIError: If the request fails
        """
        url = f"{self.base_url}{path}"
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            if response.status_code == 204:  # No content
                return {}
            return response.json() if response.content else {}
        except requests.exceptions.HTTPError as e:
            message = "Unknown error"
            try:
                error_data = e.response.json()
                message = error_data.get("message", str(error_data))
            except (ValueError, AttributeError):
                message = e.response.text or str(e)
            raise GiteaAPIError(e.response.status_code, message, url)
        except requests.exceptions.RequestException as e:
            raise GiteaAPIError(0, str(e), url)

    def list_repos(self, org: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List repositories.

        Args:
            org: Organization name (if None, lists user repos)

        Returns:
            List of repository objects
        """
        if org:
            path = f"/api/v1/orgs/{org}/repos"
        else:
            path = "/api/v1/repos/search"

        response = self._request("GET", path)

        # Handle search response format vs direct list
        if isinstance(response, dict) and "data" in response:
            return response["data"]
        return response

    def create_repo(
        self,
        name: str,
        org: Optional[str] = None,
        private: bool = True,
        description: str = "",
    ) -> Dict[str, Any]:
        """
        Create a new repository.

        Args:
            name: Repository name
            org: Organization name (if None, creates in user account)
            private: Whether the repository should be private
            description: Repository description

        Returns:
            Created repository object
        """
        data = {
            "name": name,
            "private": private,
            "description": description,
        }

        if org:
            path = f"/api/v1/orgs/{org}/repos"
        else:
            path = "/api/v1/user/repos"

        return self._request("POST", path, json=data)

    def delete_repo(self, owner: str, repo: str) -> Dict[str, Any]:
        """
        Delete a repository.

        Args:
            owner: Repository owner (user or org)
            repo: Repository name

        Returns:
            Empty dict on success
        """
        path = f"/api/v1/repos/{owner}/{repo}"
        return self._request("DELETE", path)

    def list_prs(
        self, owner: str, repo: str, state: str = "open"
    ) -> List[Dict[str, Any]]:
        """
        List pull requests.

        Args:
            owner: Repository owner
            repo: Repository name
            state: PR state (open, closed, all)

        Returns:
            List of pull request objects
        """
        path = f"/api/v1/repos/{owner}/{repo}/pulls"
        params = {"state": state}
        return self._request("GET", path, params=params)

    def create_pr(
        self,
        owner: str,
        repo: str,
        title: str,
        body: str,
        head: str,
        base: str = "main",
    ) -> Dict[str, Any]:
        """
        Create a pull request.

        Args:
            owner: Repository owner
            repo: Repository name
            title: PR title
            body: PR description
            head: Source branch
            base: Target branch (default: main)

        Returns:
            Created pull request object
        """
        path = f"/api/v1/repos/{owner}/{repo}/pulls"
        data = {
            "title": title,
            "body": body,
            "head": head,
            "base": base,
        }
        return self._request("POST", path, json=data)

    def merge_pr(
        self, owner: str, repo: str, pr_number: int, merge_type: str = "merge"
    ) -> Dict[str, Any]:
        """
        Merge a pull request.

        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: Pull request number
            merge_type: Merge method (merge, rebase, squash)

        Returns:
            Merge result object
        """
        path = f"/api/v1/repos/{owner}/{repo}/pulls/{pr_number}/merge"
        data = {"Do": merge_type}
        return self._request("POST", path, json=data)

    def comment_pr(
        self, owner: str, repo: str, pr_number: int, body: str
    ) -> Dict[str, Any]:
        """
        Add a comment to a pull request.

        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: Pull request number
            body: Comment text

        Returns:
            Created comment object
        """
        path = f"/api/v1/repos/{owner}/{repo}/issues/{pr_number}/comments"
        data = {"body": body}
        return self._request("POST", path, json=data)

    def list_runs(self, owner: str, repo: str) -> List[Dict[str, Any]]:
        """
        List workflow runs.

        Args:
            owner: Repository owner
            repo: Repository name

        Returns:
            List of workflow run objects
        """
        path = f"/api/v1/repos/{owner}/{repo}/actions/runs"
        response = self._request("GET", path)
        # Handle paginated response
        if isinstance(response, dict) and "workflow_runs" in response:
            return response["workflow_runs"]
        return response

    def get_run(self, owner: str, repo: str, run_id: int) -> Dict[str, Any]:
        """
        Get details of a specific workflow run.

        Args:
            owner: Repository owner
            repo: Repository name
            run_id: Workflow run ID

        Returns:
            Workflow run object
        """
        path = f"/api/v1/repos/{owner}/{repo}/actions/runs/{run_id}"
        return self._request("GET", path)

    def get_run_jobs(self, owner: str, repo: str, run_id: int) -> List[Dict[str, Any]]:
        """
        Get jobs for a workflow run.

        Args:
            owner: Repository owner
            repo: Repository name
            run_id: Workflow run ID

        Returns:
            List of job objects
        """
        path = f"/api/v1/repos/{owner}/{repo}/actions/runs/{run_id}/jobs"
        response = self._request("GET", path)
        # Handle paginated response
        if isinstance(response, dict) and "jobs" in response:
            return response["jobs"]
        return response

    def dispatch_workflow(
        self,
        owner: str,
        repo: str,
        workflow_id: str,
        ref: str = "main",
        inputs: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Trigger a workflow dispatch event.

        Args:
            owner: Repository owner
            repo: Repository name
            workflow_id: Workflow file name or ID
            ref: Git ref to run workflow on (default: main)
            inputs: Input parameters for the workflow

        Returns:
            Empty dict on success
        """
        path = f"/api/v1/repos/{owner}/{repo}/actions/workflows/{workflow_id}/dispatches"
        data: Dict[str, Any] = {"ref": ref}
        if inputs:
            data["inputs"] = inputs
        return self._request("POST", path, json=data)

    def set_secret(self, owner: str, repo: str, name: str, value: str) -> Dict[str, Any]:
        """
        Create or update a repository secret.

        Args:
            owner: Repository owner
            repo: Repository name
            name: Secret name
            value: Secret value

        Returns:
            Empty dict on success
        """
        path = f"/api/v1/repos/{owner}/{repo}/actions/secrets/{name}"
        data = {"data": value}
        return self._request("PUT", path, json=data)

    def list_secrets(self, owner: str, repo: str) -> List[Dict[str, Any]]:
        """
        List repository secrets.

        Args:
            owner: Repository owner
            repo: Repository name

        Returns:
            List of secret objects (names only, values are hidden)
        """
        path = f"/api/v1/repos/{owner}/{repo}/actions/secrets"
        response = self._request("GET", path)
        # Handle paginated response
        if isinstance(response, dict) and "data" in response:
            return response["data"]
        return response

    def set_branch_protection(
        self, owner: str, repo: str, branch: str, rules: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Set branch protection rules.

        Args:
            owner: Repository owner
            repo: Repository name
            branch: Branch name
            rules: Protection rules configuration

        Returns:
            Updated branch protection object
        """
        path = f"/api/v1/repos/{owner}/{repo}/branch_protections"
        data = {"branch_name": branch, **rules}
        return self._request("POST", path, json=data)

    def commit_status(
        self,
        owner: str,
        repo: str,
        sha: str,
        state: str,
        description: str,
        context: str,
    ) -> Dict[str, Any]:
        """
        Set commit status.

        Args:
            owner: Repository owner
            repo: Repository name
            sha: Commit SHA
            state: Status state (pending, success, error, failure)
            description: Status description
            context: Status context (identifier)

        Returns:
            Created status object
        """
        path = f"/api/v1/repos/{owner}/{repo}/statuses/{sha}"
        data = {
            "state": state,
            "description": description,
            "context": context,
        }
        return self._request("POST", path, json=data)
