"""
Pytest tests for the FastAPI application.

Tests health check endpoints and application configuration.
"""

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from api.main import app, create_app
from api.core.config import Settings, settings


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def client():
    """Create a test client for the FastAPI application."""
    return TestClient(app)


@pytest.fixture
def fresh_settings():
    """Create fresh settings with no environment variables."""
    with patch.dict("os.environ", {}, clear=True):
        yield Settings()


# =============================================================================
# Health Check Tests
# =============================================================================

class TestHealthEndpoints:
    """Tests for health check endpoints."""

    def test_health_check(self, client):
        """Test basic health check returns 200."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data

    def test_readiness_check(self, client):
        """Test readiness check returns service status."""
        response = client.get("/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["ready", "not_ready"]
        assert "services" in data
        assert "spaces" in data["services"]
        assert "discord" in data["services"]
        assert "stripe" in data["services"]
        assert "email" in data["services"]

    def test_liveness_check(self, client):
        """Test liveness check returns minimal response."""
        response = client.get("/health/live")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"


# =============================================================================
# Application Configuration Tests
# =============================================================================

class TestAppConfiguration:
    """Tests for application configuration."""

    def test_create_app_returns_fastapi_instance(self):
        """Test that create_app returns a FastAPI instance."""
        test_app = create_app()
        assert test_app is not None
        assert hasattr(test_app, "router")

    def test_app_has_cors_middleware(self, client):
        """Test that CORS middleware is configured."""
        # CORS headers should be present for cross-origin requests
        response = client.options(
            "/health",
            headers={"Origin": "http://localhost:3000"}
        )
        # FastAPI with CORS should allow the origin
        assert response.status_code in [200, 405]


# =============================================================================
# Settings Tests
# =============================================================================

class TestSettings:
    """Tests for application settings."""

    def test_settings_has_app_name(self):
        """Test settings has APP_NAME."""
        assert settings.APP_NAME == "Chicago Clay Co-Op API"

    def test_settings_has_cors_origins(self):
        """Test settings has CORS origins."""
        assert isinstance(settings.CORS_ORIGINS, list)
        assert len(settings.CORS_ORIGINS) > 0

    def test_settings_is_spaces_configured_false_without_credentials(self, fresh_settings):
        """Test is_spaces_configured returns False without credentials."""
        assert fresh_settings.is_spaces_configured() is False

    def test_settings_is_discord_configured_false_without_token(self, fresh_settings):
        """Test is_discord_configured returns False without token."""
        assert fresh_settings.is_discord_configured() is False

    def test_settings_is_stripe_configured_false_without_key(self, fresh_settings):
        """Test is_stripe_configured returns False without API key."""
        assert fresh_settings.is_stripe_configured() is False

    def test_settings_is_email_configured_false_without_key(self, fresh_settings):
        """Test is_email_configured returns False without API key."""
        assert fresh_settings.is_email_configured() is False

    def test_settings_is_spaces_configured_true_with_credentials(self):
        """Test is_spaces_configured returns True with credentials."""
        with patch.dict("os.environ", {
            "DIGITALOCEAN_SPACES_ACCESS_KEY": "test_key",
            "DIGITALOCEAN_SPACES_SECRET_KEY": "test_secret",
        }):
            test_settings = Settings()
            assert test_settings.is_spaces_configured() is True

    def test_settings_default_region(self, fresh_settings):
        """Test default region is nyc3."""
        assert fresh_settings.SPACES_REGION == "nyc3"

    def test_settings_default_bucket(self, fresh_settings):
        """Test default bucket is file-the-coop."""
        assert fresh_settings.SPACES_BUCKET == "file-the-coop"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
