"""
Pytest tests for the Email Octopus integration.

Tests use mocking to avoid requiring actual API credentials.
"""

import pytest
import hashlib
from unittest.mock import MagicMock, AsyncMock, patch

import httpx

from api.services.email_octopus import (
    EmailOctopusClient,
    EmailOctopusError,
    Subscriber,
    get_email_client,
    subscribe_to_newsletter,
    subscribe_to_event_reminders,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_httpx_client():
    """Create a mock httpx.AsyncClient."""
    return AsyncMock(spec=httpx.AsyncClient)


@pytest.fixture
def email_client(mock_httpx_client):
    """Create an EmailOctopusClient with mocked HTTP client."""
    client = EmailOctopusClient(
        api_key="test_api_key",
        list_id="test_list_id",
    )
    client._client = mock_httpx_client
    return client


# =============================================================================
# Subscriber Dataclass Tests
# =============================================================================

class TestSubscriber:
    """Tests for the Subscriber dataclass."""

    def test_subscriber_creation(self):
        """Test creating a subscriber."""
        sub = Subscriber(
            email="test@example.com",
            first_name="John",
            last_name="Doe",
        )
        assert sub.email == "test@example.com"
        assert sub.first_name == "John"
        assert sub.status == "SUBSCRIBED"
        assert sub.tags == []

    def test_subscriber_with_tags(self):
        """Test subscriber with tags."""
        sub = Subscriber(
            email="test@example.com",
            tags=["newsletter", "events"],
        )
        assert sub.tags == ["newsletter", "events"]


# =============================================================================
# Client Initialization Tests
# =============================================================================

class TestEmailOctopusClientInit:
    """Tests for client initialization."""

    def test_init_with_credentials(self):
        """Test client initializes with provided credentials."""
        client = EmailOctopusClient(
            api_key="my_key",
            list_id="my_list",
        )
        assert client.api_key == "my_key"
        assert client.list_id == "my_list"

    def test_check_api_key_raises_without_key(self):
        """Test _check_api_key raises error without key."""
        client = EmailOctopusClient(api_key=None)
        with pytest.raises(EmailOctopusError, match="API key not configured"):
            client._check_api_key()

    def test_add_api_key_to_params(self):
        """Test _add_api_key adds key to params."""
        client = EmailOctopusClient(api_key="test_key")
        params = client._add_api_key({"limit": 10})
        assert params["api_key"] == "test_key"
        assert params["limit"] == 10


# =============================================================================
# Get List Tests
# =============================================================================

class TestGetList:
    """Tests for getting list details."""

    @pytest.mark.asyncio
    async def test_get_list_success(self, email_client, mock_httpx_client):
        """Test successfully getting list details."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": "test_list_id",
            "name": "Newsletter",
            "counts": {"subscribed": 100},
        }
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.get.return_value = mock_response

        result = await email_client.get_list()

        assert result["id"] == "test_list_id"
        mock_httpx_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_list_no_list_id(self, email_client):
        """Test get_list raises without list ID."""
        email_client.list_id = None
        with pytest.raises(EmailOctopusError, match="No list ID"):
            await email_client.get_list()


# =============================================================================
# Get Subscribers Tests
# =============================================================================

class TestGetSubscribers:
    """Tests for getting subscribers."""

    @pytest.mark.asyncio
    async def test_get_subscribers_success(self, email_client, mock_httpx_client):
        """Test successfully getting subscribers."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [
                {"email_address": "user1@example.com"},
                {"email_address": "user2@example.com"},
            ],
            "paging": {"next": None},
        }
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.get.return_value = mock_response

        result = await email_client.get_subscribers()

        assert len(result["data"]) == 2

    @pytest.mark.asyncio
    async def test_get_subscribers_with_pagination(self, email_client, mock_httpx_client):
        """Test getting subscribers with pagination."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": []}
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.get.return_value = mock_response

        await email_client.get_subscribers(limit=50, page=2)

        call_args = mock_httpx_client.get.call_args
        assert call_args[1]["params"]["limit"] == 50
        assert call_args[1]["params"]["page"] == 2


# =============================================================================
# Add Subscriber Tests
# =============================================================================

class TestAddSubscriber:
    """Tests for adding subscribers."""

    @pytest.mark.asyncio
    async def test_add_subscriber_success(self, email_client, mock_httpx_client):
        """Test successfully adding a subscriber."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": "contact_123",
            "email_address": "new@example.com",
            "status": "SUBSCRIBED",
        }
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.post.return_value = mock_response

        result = await email_client.add_subscriber(
            email="new@example.com",
            first_name="Jane",
            last_name="Doe",
            tags=["newsletter"],
        )

        assert result["email_address"] == "new@example.com"

        # Verify request payload
        call_args = mock_httpx_client.post.call_args
        payload = call_args[1]["json"]
        assert payload["email_address"] == "new@example.com"
        assert payload["fields"]["FirstName"] == "Jane"
        assert payload["tags"] == ["newsletter"]

    @pytest.mark.asyncio
    async def test_add_subscriber_already_exists(self, email_client, mock_httpx_client):
        """Test adding subscriber that already exists returns status."""
        mock_response = MagicMock()
        mock_response.status_code = 409
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Conflict", request=MagicMock(), response=mock_response
        )
        mock_httpx_client.post.return_value = mock_response

        result = await email_client.add_subscriber(email="existing@example.com")

        assert result["status"] == "ALREADY_EXISTS"


# =============================================================================
# Remove Subscriber Tests
# =============================================================================

class TestRemoveSubscriber:
    """Tests for removing subscribers."""

    @pytest.mark.asyncio
    async def test_remove_subscriber_success(self, email_client, mock_httpx_client):
        """Test successfully removing a subscriber."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.delete.return_value = mock_response

        result = await email_client.remove_subscriber("user@example.com")

        assert result is True

        # Verify correct contact ID (MD5 hash)
        expected_hash = hashlib.md5("user@example.com".encode()).hexdigest()
        call_args = mock_httpx_client.delete.call_args
        assert expected_hash in call_args[0][0]

    @pytest.mark.asyncio
    async def test_remove_subscriber_not_found(self, email_client, mock_httpx_client):
        """Test removing non-existent subscriber returns True."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found", request=MagicMock(), response=mock_response
        )
        mock_httpx_client.delete.return_value = mock_response

        result = await email_client.remove_subscriber("nonexistent@example.com")

        assert result is True  # Not found is treated as success


# =============================================================================
# Update Tags Tests
# =============================================================================

class TestUpdateSubscriberTags:
    """Tests for updating subscriber tags."""

    @pytest.mark.asyncio
    async def test_update_tags_success(self, email_client, mock_httpx_client):
        """Test successfully updating subscriber tags."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "contact_123"}
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.put.return_value = mock_response

        result = await email_client.update_subscriber_tags(
            email="user@example.com",
            tags=["newsletter", "vip"],
        )

        assert result["id"] == "contact_123"

        # Verify tags format
        call_args = mock_httpx_client.put.call_args
        payload = call_args[1]["json"]
        assert payload["tags"] == {"newsletter": True, "vip": True}


# =============================================================================
# Convenience Function Tests
# =============================================================================

class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    @patch("api.services.email_octopus._default_client", None)
    def test_get_email_client_creates_instance(self):
        """Test get_email_client creates new instance."""
        with patch("api.services.email_octopus.EmailOctopusClient") as MockClient:
            MockClient.return_value = MagicMock()
            client = get_email_client()
            MockClient.assert_called_once()
            assert client is not None

    @pytest.mark.asyncio
    async def test_subscribe_to_newsletter(self):
        """Test subscribe_to_newsletter adds newsletter tag."""
        with patch("api.services.email_octopus.get_email_client") as mock_get:
            mock_client = MagicMock()
            mock_client.add_subscriber = AsyncMock(return_value={"status": "ok"})
            mock_get.return_value = mock_client

            await subscribe_to_newsletter(
                email="user@example.com",
                first_name="Test",
            )

            mock_client.add_subscriber.assert_called_once()
            call_args = mock_client.add_subscriber.call_args
            assert call_args[1]["tags"] == ["newsletter"]

    @pytest.mark.asyncio
    async def test_subscribe_to_event_reminders(self):
        """Test subscribe_to_event_reminders adds event tags."""
        with patch("api.services.email_octopus.get_email_client") as mock_get:
            mock_client = MagicMock()
            mock_client.add_subscriber = AsyncMock(return_value={"status": "ok"})
            mock_get.return_value = mock_client

            await subscribe_to_event_reminders(
                email="user@example.com",
                event_name="Pottery Workshop",
            )

            mock_client.add_subscriber.assert_called_once()
            call_args = mock_client.add_subscriber.call_args
            assert "event-reminder" in call_args[1]["tags"]
            assert "event-pottery-workshop" in call_args[1]["tags"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
