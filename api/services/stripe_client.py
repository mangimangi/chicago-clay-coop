"""
Stripe API client for shop integration.

Provides functionality for:
- Creating checkout sessions for purchases
- Managing product catalog
- Processing webhook events
- Syncing inventory with shop.json
"""

import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

import stripe

from api.core.config import settings
from api.services.spaces import read_site_json, write_site_json

logger = logging.getLogger(__name__)


class StripeError(Exception):
    """Base exception for Stripe errors."""
    pass


@dataclass
class CheckoutSessionResult:
    """Result from creating a checkout session."""
    session_id: str
    url: str
    product_name: str
    amount: int  # in cents


class StripeClient:
    """
    Client for the Stripe API.

    Handles checkout sessions, webhooks, and inventory management.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        webhook_secret: Optional[str] = None,
    ):
        """
        Initialize the Stripe client.

        Args:
            api_key: Stripe API key (defaults to env var)
            webhook_secret: Webhook signing secret (defaults to env var)
        """
        self.api_key = api_key or settings.STRIPE_API_KEY
        self.webhook_secret = webhook_secret or settings.STRIPE_WEBHOOK_SECRET

        if self.api_key:
            stripe.api_key = self.api_key

    def _check_api_key(self):
        """Verify API key is configured."""
        if not self.api_key:
            raise StripeError(
                "Stripe API key not configured. "
                "Set STRIPE_API_KEY environment variable."
            )

    async def create_checkout_session(
        self,
        product_name: str,
        price_cents: int,
        quantity: int = 1,
        success_url: str = "https://ccc.quest/shop?success=true",
        cancel_url: str = "https://ccc.quest/shop?canceled=true",
        metadata: Optional[Dict[str, str]] = None,
    ) -> CheckoutSessionResult:
        """
        Create a Stripe Checkout session for a product.

        Args:
            product_name: Name of the product
            price_cents: Price in cents
            quantity: Quantity to purchase
            success_url: Redirect URL on success
            cancel_url: Redirect URL on cancel
            metadata: Additional metadata to attach

        Returns:
            CheckoutSessionResult with session ID and URL

        Raises:
            StripeError: On API errors
        """
        self._check_api_key()

        try:
            logger.info(f"Creating checkout session for: {product_name}")

            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[
                    {
                        "price_data": {
                            "currency": "usd",
                            "product_data": {
                                "name": product_name,
                            },
                            "unit_amount": price_cents,
                        },
                        "quantity": quantity,
                    }
                ],
                mode="payment",
                success_url=success_url,
                cancel_url=cancel_url,
                metadata=metadata or {},
            )

            logger.info(f"Created checkout session: {session.id}")

            return CheckoutSessionResult(
                session_id=session.id,
                url=session.url,
                product_name=product_name,
                amount=price_cents * quantity,
            )

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating session: {e}")
            raise StripeError(f"Failed to create checkout session: {e}")

    async def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str,
    ) -> Dict[str, Any]:
        """
        Verify and parse a Stripe webhook event.

        Args:
            payload: Raw request body
            signature: Stripe-Signature header value

        Returns:
            Parsed event data

        Raises:
            StripeError: On signature verification failure
        """
        if not self.webhook_secret:
            raise StripeError(
                "Stripe webhook secret not configured. "
                "Set STRIPE_WEBHOOK_SECRET environment variable."
            )

        try:
            event = stripe.Webhook.construct_event(
                payload,
                signature,
                self.webhook_secret,
            )
            return event

        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Webhook signature verification failed: {e}")
            raise StripeError("Invalid webhook signature")

    async def handle_checkout_completed(
        self,
        session_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Handle a checkout.session.completed webhook event.

        Args:
            session_data: Session data from the webhook

        Returns:
            Processing result
        """
        session_id = session_data.get("id")
        customer_email = session_data.get("customer_details", {}).get("email")
        metadata = session_data.get("metadata", {})

        logger.info(f"Processing completed checkout: {session_id}")
        logger.info(f"Customer email: {customer_email}")

        # TODO: Send confirmation email
        # TODO: Update inventory in shop.json if needed

        return {
            "session_id": session_id,
            "customer_email": customer_email,
            "metadata": metadata,
            "status": "processed",
        }

    async def list_products(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        List products from Stripe.

        Args:
            limit: Maximum number of products to return

        Returns:
            List of product data
        """
        self._check_api_key()

        try:
            products = stripe.Product.list(limit=limit, active=True)
            return [
                {
                    "id": p.id,
                    "name": p.name,
                    "description": p.description,
                    "images": p.images,
                    "metadata": p.metadata,
                }
                for p in products.data
            ]

        except stripe.error.StripeError as e:
            logger.error(f"Failed to list products: {e}")
            raise StripeError(f"Failed to list products: {e}")

    async def sync_products_to_stripe(
        self,
        products: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Sync products from shop.json to Stripe.

        Args:
            products: List of product dictionaries from shop.json

        Returns:
            Sync result with created/updated counts
        """
        self._check_api_key()

        created = 0
        updated = 0
        errors = []

        for product in products:
            try:
                # Check if product exists by metadata
                existing = stripe.Product.search(
                    query=f"metadata['shop_title']:'{product.get('title')}'",
                )

                if existing.data:
                    # Update existing product
                    stripe.Product.modify(
                        existing.data[0].id,
                        name=product.get("title"),
                        description=product.get("description", ""),
                        images=([product.get("image")] if product.get("image") else []),
                    )
                    updated += 1
                else:
                    # Create new product
                    stripe.Product.create(
                        name=product.get("title"),
                        description=product.get("description", ""),
                        images=([product.get("image")] if product.get("image") else []),
                        metadata={
                            "shop_title": product.get("title"),
                            "artist": product.get("artist", ""),
                        },
                    )
                    created += 1

            except stripe.error.StripeError as e:
                errors.append({"product": product.get("title"), "error": str(e)})
                logger.error(f"Failed to sync product {product.get('title')}: {e}")

        return {
            "created": created,
            "updated": updated,
            "errors": errors,
        }


# Module-level client instance
_default_client: Optional[StripeClient] = None


def get_stripe_client() -> StripeClient:
    """Get the default Stripe client instance."""
    global _default_client
    if _default_client is None:
        _default_client = StripeClient()
    return _default_client


async def create_product_checkout(
    product_title: str,
    price_dollars: float,
) -> CheckoutSessionResult:
    """
    Create a checkout session for a shop product.

    Convenience function for creating checkouts from shop items.

    Args:
        product_title: Product title from shop.json
        price_dollars: Price in dollars

    Returns:
        CheckoutSessionResult
    """
    client = get_stripe_client()
    return await client.create_checkout_session(
        product_name=product_title,
        price_cents=int(price_dollars * 100),
        metadata={"source": "ccc_shop"},
    )


async def process_webhook(
    payload: bytes,
    signature: str,
) -> Dict[str, Any]:
    """
    Process a Stripe webhook.

    Args:
        payload: Raw request body
        signature: Stripe-Signature header

    Returns:
        Processing result
    """
    client = get_stripe_client()

    event = await client.verify_webhook_signature(payload, signature)
    event_type = event.get("type")

    logger.info(f"Processing webhook event: {event_type}")

    if event_type == "checkout.session.completed":
        return await client.handle_checkout_completed(event["data"]["object"])

    # Handle other event types as needed
    return {"event_type": event_type, "status": "acknowledged"}
