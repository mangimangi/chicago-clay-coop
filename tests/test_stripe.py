"""
Pytest tests for the Stripe integration.

Tests use mocking to avoid requiring actual Stripe credentials.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from api.services.stripe_client import (
    StripeClient,
    StripeError,
    CheckoutSessionResult,
    get_stripe_client,
    create_product_checkout,
    process_webhook,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_stripe():
    """Create mock stripe module."""
    with patch("api.services.stripe_client.stripe") as mock:
        yield mock


@pytest.fixture
def stripe_client(mock_stripe):
    """Create a StripeClient with mocked stripe module."""
    client = StripeClient(
        api_key="test_api_key",
        webhook_secret="test_webhook_secret",
    )
    return client


# =============================================================================
# Client Initialization Tests
# =============================================================================

class TestStripeClientInit:
    """Tests for client initialization."""

    def test_init_with_credentials(self):
        """Test client initializes with credentials."""
        with patch("api.services.stripe_client.stripe"):
            client = StripeClient(
                api_key="sk_test_xxx",
                webhook_secret="whsec_xxx",
            )
            assert client.api_key == "sk_test_xxx"
            assert client.webhook_secret == "whsec_xxx"

    def test_check_api_key_raises_without_key(self):
        """Test _check_api_key raises without key."""
        client = StripeClient(api_key=None)
        with pytest.raises(StripeError, match="API key not configured"):
            client._check_api_key()


# =============================================================================
# Checkout Session Tests
# =============================================================================

class TestCreateCheckoutSession:
    """Tests for creating checkout sessions."""

    @pytest.mark.asyncio
    async def test_create_session_success(self, stripe_client, mock_stripe):
        """Test successfully creating a checkout session."""
        mock_session = MagicMock()
        mock_session.id = "cs_test_123"
        mock_session.url = "https://checkout.stripe.com/session/cs_test_123"
        mock_stripe.checkout.Session.create.return_value = mock_session

        result = await stripe_client.create_checkout_session(
            product_name="Test Product",
            price_cents=5000,
            quantity=1,
        )

        assert isinstance(result, CheckoutSessionResult)
        assert result.session_id == "cs_test_123"
        assert result.product_name == "Test Product"
        assert result.amount == 5000

    @pytest.mark.asyncio
    async def test_create_session_with_metadata(self, stripe_client, mock_stripe):
        """Test creating session with metadata."""
        mock_session = MagicMock()
        mock_session.id = "cs_test_456"
        mock_session.url = "https://checkout.stripe.com/test"
        mock_stripe.checkout.Session.create.return_value = mock_session

        await stripe_client.create_checkout_session(
            product_name="Test Product",
            price_cents=5000,
            metadata={"order_id": "123"},
        )

        call_kwargs = mock_stripe.checkout.Session.create.call_args[1]
        assert call_kwargs["metadata"] == {"order_id": "123"}

    @pytest.mark.asyncio
    async def test_create_session_stripe_error(self):
        """Test handling Stripe API errors."""
        import stripe

        client = StripeClient(api_key="test_key")

        with patch.object(stripe.checkout.Session, 'create') as mock_create:
            mock_create.side_effect = stripe.error.StripeError("Invalid API key")

            with pytest.raises(StripeError, match="Failed to create"):
                await client.create_checkout_session(
                    product_name="Test",
                    price_cents=1000,
                )


# =============================================================================
# Webhook Tests
# =============================================================================

class TestWebhookVerification:
    """Tests for webhook signature verification."""

    @pytest.mark.asyncio
    async def test_verify_webhook_success(self, stripe_client, mock_stripe):
        """Test successfully verifying webhook signature."""
        mock_event = {
            "id": "evt_123",
            "type": "checkout.session.completed",
            "data": {"object": {"id": "cs_123"}},
        }
        mock_stripe.Webhook.construct_event.return_value = mock_event

        result = await stripe_client.verify_webhook_signature(
            payload=b"test_payload",
            signature="test_signature",
        )

        assert result["id"] == "evt_123"
        mock_stripe.Webhook.construct_event.assert_called_once_with(
            b"test_payload",
            "test_signature",
            "test_webhook_secret",
        )

    @pytest.mark.asyncio
    async def test_verify_webhook_invalid_signature(self):
        """Test invalid webhook signature raises error."""
        import stripe

        client = StripeClient(api_key="test_key", webhook_secret="test_secret")

        with patch.object(stripe.Webhook, 'construct_event') as mock_construct:
            mock_construct.side_effect = stripe.error.SignatureVerificationError(
                "Bad signature", None
            )

            with pytest.raises(StripeError, match="Invalid webhook signature"):
                await client.verify_webhook_signature(
                    payload=b"test",
                    signature="bad_sig",
                )

    @pytest.mark.asyncio
    async def test_verify_webhook_no_secret(self):
        """Test webhook verification without secret raises error."""
        client = StripeClient(api_key="test", webhook_secret=None)

        with pytest.raises(StripeError, match="webhook secret not configured"):
            await client.verify_webhook_signature(
                payload=b"test",
                signature="test",
            )


# =============================================================================
# Webhook Handler Tests
# =============================================================================

class TestHandleCheckoutCompleted:
    """Tests for checkout.session.completed handler."""

    @pytest.mark.asyncio
    async def test_handle_checkout_completed(self, stripe_client):
        """Test processing completed checkout."""
        session_data = {
            "id": "cs_123",
            "customer_details": {"email": "customer@example.com"},
            "metadata": {"product_id": "pot_001"},
        }

        result = await stripe_client.handle_checkout_completed(session_data)

        assert result["session_id"] == "cs_123"
        assert result["customer_email"] == "customer@example.com"
        assert result["status"] == "processed"

    @pytest.mark.asyncio
    async def test_handle_event_checkout_calls_email_octopus(self, stripe_client):
        """Test event checkout adds registrant to Email Octopus list."""
        session_data = {
            "id": "cs_event_123",
            "customer_details": {"email": "attendee@example.com"},
            "metadata": {
                "event_slug": "pottery-workshop-2025-01-20",
                "event_name": "Pottery Workshop",
                "event_date": "2025-01-20",
            },
        }

        with patch("api.services.stripe_client.add_event_registrant") as mock_add:
            mock_add.return_value = {"status": "ok"}

            result = await stripe_client.handle_checkout_completed(session_data)

            # Should call add_event_registrant for event checkouts
            mock_add.assert_called_once_with(
                email="attendee@example.com",
                event_name="Pottery Workshop",
                event_date="2025-01-20",
            )
            assert result["event_registration"] == "added_to_list"

    @pytest.mark.asyncio
    async def test_handle_event_checkout_without_email(self, stripe_client):
        """Test event checkout without customer email logs warning."""
        session_data = {
            "id": "cs_event_123",
            "customer_details": {},  # No email
            "metadata": {
                "event_slug": "pottery-workshop-2025-01-20",
                "event_name": "Pottery Workshop",
                "event_date": "2025-01-20",
            },
        }

        with patch("api.services.stripe_client.add_event_registrant") as mock_add:
            result = await stripe_client.handle_checkout_completed(session_data)

            # Should not call add_event_registrant without email
            mock_add.assert_not_called()
            assert result["status"] == "processed"

    @pytest.mark.asyncio
    async def test_handle_product_checkout_no_email_octopus(self, stripe_client):
        """Test product checkout doesn't call Email Octopus."""
        session_data = {
            "id": "cs_product_123",
            "customer_details": {"email": "buyer@example.com"},
            "metadata": {
                "product_slug": "freak-mug-michael-bridges",
                "product_type": "pot",
            },
        }

        with patch("api.services.stripe_client.add_event_registrant") as mock_add:
            result = await stripe_client.handle_checkout_completed(session_data)

            # Should not call add_event_registrant for product checkouts
            mock_add.assert_not_called()
            assert result["status"] == "processed"

    @pytest.mark.asyncio
    async def test_handle_event_checkout_email_octopus_error(self, stripe_client):
        """Test event checkout handles Email Octopus errors gracefully."""
        session_data = {
            "id": "cs_event_123",
            "customer_details": {"email": "attendee@example.com"},
            "metadata": {
                "event_slug": "pottery-workshop-2025-01-20",
                "event_name": "Pottery Workshop",
                "event_date": "2025-01-20",
            },
        }

        with patch("api.services.stripe_client.add_event_registrant") as mock_add:
            # Simulate Email Octopus error
            from api.services.email_octopus import EmailOctopusError
            mock_add.side_effect = EmailOctopusError("API error")

            # Should not raise, just log the error and continue
            result = await stripe_client.handle_checkout_completed(session_data)

            assert result["status"] == "processed"
            assert result.get("event_registration") == "failed"


# =============================================================================
# Product Management Tests
# =============================================================================

class TestProductManagement:
    """Tests for product listing and syncing."""

    @pytest.mark.asyncio
    async def test_list_products_success(self, stripe_client, mock_stripe):
        """Test listing products."""
        mock_product = MagicMock()
        mock_product.id = "prod_123"
        mock_product.name = "Test Pot"
        mock_product.description = "A nice pot"
        mock_product.images = ["https://example.com/pot.jpg"]
        mock_product.metadata = {}

        mock_stripe.Product.list.return_value = MagicMock(data=[mock_product])

        result = await stripe_client.list_products()

        assert len(result) == 1
        assert result[0]["id"] == "prod_123"
        assert result[0]["name"] == "Test Pot"

    @pytest.mark.asyncio
    async def test_sync_products_creates_new(self, stripe_client, mock_stripe):
        """Test syncing creates new products."""
        # No existing products found
        mock_stripe.Product.search.return_value = MagicMock(data=[])

        products = [
            {
                "title": "New Mug",
                "description": "Handmade mug",
                "image": "https://example.com/mug.jpg",
                "artist": "Test Artist",
            }
        ]

        result = await stripe_client.sync_products_to_stripe(products)

        assert result["created"] == 1
        assert result["updated"] == 0
        mock_stripe.Product.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_products_updates_existing(self, stripe_client, mock_stripe):
        """Test syncing updates existing products."""
        # Existing product found
        mock_existing = MagicMock()
        mock_existing.id = "prod_existing"
        mock_stripe.Product.search.return_value = MagicMock(data=[mock_existing])

        products = [
            {
                "title": "Existing Mug",
                "description": "Updated description",
            }
        ]

        result = await stripe_client.sync_products_to_stripe(products)

        assert result["created"] == 0
        assert result["updated"] == 1
        mock_stripe.Product.modify.assert_called_once()


# =============================================================================
# Convenience Function Tests
# =============================================================================

class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    @patch("api.services.stripe_client._default_client", None)
    def test_get_stripe_client_creates_instance(self):
        """Test get_stripe_client creates new instance."""
        with patch("api.services.stripe_client.StripeClient") as MockClient:
            MockClient.return_value = MagicMock()
            client = get_stripe_client()
            MockClient.assert_called_once()
            assert client is not None

    @pytest.mark.asyncio
    async def test_create_product_checkout(self):
        """Test create_product_checkout convenience function."""
        with patch("api.services.stripe_client.get_stripe_client") as mock_get:
            mock_client = MagicMock()
            mock_client.create_checkout_session = AsyncMock(
                return_value=CheckoutSessionResult(
                    session_id="cs_test",
                    url="https://test.com",
                    product_name="Test",
                    amount=5000,
                )
            )
            mock_get.return_value = mock_client

            result = await create_product_checkout(
                product_title="Test Product",
                price_dollars=50.00,
            )

            assert result.session_id == "cs_test"
            mock_client.create_checkout_session.assert_called_once()
            call_kwargs = mock_client.create_checkout_session.call_args[1]
            assert call_kwargs["price_cents"] == 5000

    @pytest.mark.asyncio
    async def test_process_webhook(self):
        """Test process_webhook convenience function."""
        with patch("api.services.stripe_client.get_stripe_client") as mock_get:
            mock_client = MagicMock()
            mock_client.verify_webhook_signature = AsyncMock(
                return_value={
                    "type": "checkout.session.completed",
                    "data": {"object": {"id": "cs_123"}},
                }
            )
            mock_client.handle_checkout_completed = AsyncMock(
                return_value={"status": "processed"}
            )
            mock_get.return_value = mock_client

            result = await process_webhook(
                payload=b"test",
                signature="sig_test",
            )

            assert result["status"] == "processed"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
