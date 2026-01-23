"""
API endpoints for triggering site rebuilds.

Provides endpoints for:
- Triggering rebuilds after Spaces updates
- Checking rebuild status
"""

from typing import Dict, Any

from fastapi import APIRouter, HTTPException

from api.services.github_actions import (
    get_github_client,
    trigger_site_rebuild,
    GitHubActionsError,
)

router = APIRouter()


@router.post("/trigger")
async def trigger_rebuild(source: str = "api") -> Dict[str, Any]:
    """
    Trigger a site rebuild.

    Sends a repository dispatch event to GitHub Actions
    which runs the rebuild-site.yml workflow.

    Args:
        source: Identifier for what triggered the rebuild

    Returns:
        Trigger result with status
    """
    try:
        result = await trigger_site_rebuild(source=source)
        return result
    except GitHubActionsError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def rebuild_status() -> Dict[str, Any]:
    """
    Get status of recent rebuild runs.

    Returns:
        Recent workflow runs with their status
    """
    try:
        client = get_github_client()
        result = await client.get_workflow_runs(limit=5)
        return result
    except GitHubActionsError as e:
        raise HTTPException(status_code=500, detail=str(e))
