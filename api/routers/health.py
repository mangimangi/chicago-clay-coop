"""
Health check endpoints.

Provides endpoints for monitoring application health and readiness.
Used by Digital Ocean App Platform for health checks and by load balancers.
"""

from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter

from api.core.config import settings

router = APIRouter()


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Basic health check endpoint.

    Returns 200 OK if the application is running.
    Used for liveness probes.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "0.1.0"
    }


@router.get("/health/ready")
async def readiness_check() -> Dict[str, Any]:
    """
    Readiness check endpoint.

    Checks if the application is ready to receive traffic.
    Verifies that required services are configured (not necessarily connected).
    """
    services = {
        "spaces": settings.is_spaces_configured(),
        "discord": settings.is_discord_configured(),
        "stripe": settings.is_stripe_configured(),
        "email": settings.is_email_configured(),
    }

    # Application is ready if at least basic config is present
    # Individual services may be optional depending on deployment
    is_ready = True  # Always ready for now, can add checks later

    return {
        "status": "ready" if is_ready else "not_ready",
        "timestamp": datetime.utcnow().isoformat(),
        "services": services
    }


@router.get("/health/live")
async def liveness_check() -> Dict[str, str]:
    """
    Simple liveness check.

    Returns minimal response for quick health verification.
    """
    return {"status": "ok"}
