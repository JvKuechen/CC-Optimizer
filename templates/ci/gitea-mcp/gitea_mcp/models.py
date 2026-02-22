"""Exception models for gitea-mcp."""


class GiteaAPIError(Exception):
    """Exception raised when Gitea API returns an error."""

    def __init__(self, status_code: int, message: str, url: str):
        self.status_code = status_code
        self.message = message
        self.url = url
        super().__init__(f"Gitea API error {status_code} at {url}: {message}")
