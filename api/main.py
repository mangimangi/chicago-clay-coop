"""
Main FastAPI application entry point.

This module creates and configures the FastAPI application, including:
- Health check endpoint
- API routers (Stripe, etc.)
- Discord bot background task (when implemented)
- Startup/shutdown event handlers
"""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.core.config import settings
from api.routers import health

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Handles startup and shutdown events:
    - Startup: Initialize services, start Discord bot
    - Shutdown: Gracefully close connections
    """
    # Startup
    logger.info("Starting Chicago Clay Co-Op API...")

    # TODO: Initialize Discord bot as background task
    # TODO: Initialize Spaces client connection
    # TODO: Initialize Stripe client

    logger.info("API startup complete")

    yield

    # Shutdown
    logger.info("Shutting down Chicago Clay Co-Op API...")

    # TODO: Close Discord bot connection
    # TODO: Close any open connections

    logger.info("API shutdown complete")


def create_app() -> FastAPI:
    """
    Application factory.

    Creates and configures the FastAPI application with all routers,
    middleware, and event handlers.
    """
    app = FastAPI(
        title=settings.APP_NAME,
        description="API for Chicago Clay Co-Op: Discord bot, Stripe payments, and content management",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(health.router, tags=["health"])

    # TODO: Add additional routers as they're implemented
    # app.include_router(stripe.router, prefix="/api/stripe", tags=["stripe"])
    # app.include_router(spaces.router, prefix="/api/spaces", tags=["spaces"])
    # app.include_router(email.router, prefix="/api/email", tags=["email"])

    return app


# Create the application instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
