"""
GitHub Actions trigger service.

Provides functionality to trigger GitHub Actions workflows
when JSON files are updated in Digital Ocean Spaces.
"""

import logging
from typing import Any, Dict, Optional

import httpx

from api.core.config import settings

logger = logging.getLogger(__name__)

# GitHub API endpoints
GITHUB_API_BASE = "https://api.github.com"


class GitHubActionsError(Exception):
    """Base exception for GitHub Actions errors."""
    pass


class GitHubActionsClient:
    """
    Client for triggering GitHub Actions workflows.

    Uses the repository dispatch event to trigger workflows.
    """

    def __init__(
        self,
        token: Optional[str] = None,
        repo: Optional[str] = None,
    ):
        """
        Initialize the GitHub Actions client.

        Args:
            token: GitHub personal access token (defaults to env var)
            repo: Repository in format "owner/repo" (defaults to env var)
        """
        self.token = token or settings.GITHUB_TOKEN
        self.repo = repo or settings.GITHUB_REPO
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=GITHUB_API_BASE,
                timeout=30.0,
                headers={
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
            )
        return self._client

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    def _check_config(self):
        """Verify configuration is present."""
        if not self.token:
            raise GitHubActionsError(
                "GitHub token not configured. "
                "Set GITHUB_TOKEN environment variable."
            )
        if not self.repo:
            raise GitHubActionsError(
                "GitHub repo not configured. "
                "Set GITHUB_REPO environment variable."
            )

    async def trigger_rebuild(
        self,
        event_type: str = "spaces-json-updated",
        client_payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Trigger a site rebuild workflow using repository dispatch.

        Args:
            event_type: The event type that triggers the workflow
            client_payload: Optional data to include with the event

        Returns:
            Success status and message

        Raises:
            GitHubActionsError: On API errors
        """
        self._check_config()

        payload = {
            "event_type": event_type,
            "client_payload": client_payload or {"source": "api"},
        }

        try:
            logger.info(f"Triggering GitHub Actions rebuild for {self.repo}")

            response = await self.client.post(
                f"/repos/{self.repo}/dispatches",
                json=payload,
                headers={"Authorization": f"token {self.token}"},
            )

            # 204 No Content is success for dispatches
            if response.status_code == 204:
                logger.info("Successfully triggered rebuild workflow")
                return {
                    "success": True,
                    "message": "Rebuild workflow triggered",
                    "repo": self.repo,
                    "event_type": event_type,
                }

            # Handle errors
            error_text = response.text
            logger.error(f"Failed to trigger rebuild: {response.status_code} - {error_text}")
            raise GitHubActionsError(f"Failed to trigger workflow: {error_text}")

        except httpx.HTTPError as e:
            logger.error(f"HTTP error triggering rebuild: {e}")
            raise GitHubActionsError(f"HTTP error: {e}")

    async def trigger_workflow_dispatch(
        self,
        workflow_id: str = "rebuild-site.yml",
        ref: str = "main",
        inputs: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Trigger a workflow using workflow dispatch.

        Args:
            workflow_id: Workflow file name or ID
            ref: Git reference (branch/tag) to run on
            inputs: Workflow input values

        Returns:
            Success status and message

        Raises:
            GitHubActionsError: On API errors
        """
        self._check_config()

        payload = {
            "ref": ref,
            "inputs": inputs or {},
        }

        try:
            logger.info(f"Triggering workflow {workflow_id} for {self.repo}")

            response = await self.client.post(
                f"/repos/{self.repo}/actions/workflows/{workflow_id}/dispatches",
                json=payload,
                headers={"Authorization": f"token {self.token}"},
            )

            if response.status_code == 204:
                logger.info("Successfully triggered workflow dispatch")
                return {
                    "success": True,
                    "message": f"Workflow {workflow_id} triggered",
                    "repo": self.repo,
                    "ref": ref,
                }

            error_text = response.text
            logger.error(f"Failed to trigger workflow: {response.status_code} - {error_text}")
            raise GitHubActionsError(f"Failed to trigger workflow: {error_text}")

        except httpx.HTTPError as e:
            logger.error(f"HTTP error triggering workflow: {e}")
            raise GitHubActionsError(f"HTTP error: {e}")

    async def get_workflow_runs(
        self,
        workflow_id: str = "rebuild-site.yml",
        limit: int = 5,
    ) -> Dict[str, Any]:
        """
        Get recent workflow runs.

        Args:
            workflow_id: Workflow file name or ID
            limit: Maximum number of runs to return

        Returns:
            Workflow runs data

        Raises:
            GitHubActionsError: On API errors
        """
        self._check_config()

        try:
            response = await self.client.get(
                f"/repos/{self.repo}/actions/workflows/{workflow_id}/runs",
                params={"per_page": limit},
                headers={"Authorization": f"token {self.token}"},
            )
            response.raise_for_status()

            data = response.json()
            runs = [
                {
                    "id": run["id"],
                    "status": run["status"],
                    "conclusion": run.get("conclusion"),
                    "created_at": run["created_at"],
                    "html_url": run["html_url"],
                }
                for run in data.get("workflow_runs", [])
            ]

            return {"runs": runs, "total": data.get("total_count", 0)}

        except httpx.HTTPError as e:
            logger.error(f"Failed to get workflow runs: {e}")
            raise GitHubActionsError(f"Failed to get workflow runs: {e}")


# Module-level client instance
_default_client: Optional[GitHubActionsClient] = None


def get_github_client() -> GitHubActionsClient:
    """Get the default GitHub Actions client instance."""
    global _default_client
    if _default_client is None:
        _default_client = GitHubActionsClient()
    return _default_client


async def trigger_site_rebuild(source: str = "api") -> Dict[str, Any]:
    """
    Trigger a site rebuild.

    Convenience function for triggering rebuilds from the API.

    Args:
        source: Source identifier for logging

    Returns:
        Trigger result
    """
    client = get_github_client()
    return await client.trigger_rebuild(
        client_payload={"source": source, "trigger": "spaces-update"}
    )
