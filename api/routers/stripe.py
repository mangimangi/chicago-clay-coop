"""
Stripe API endpoints for shop integration.

Provides endpoints for:
- Creating checkout sessions
- Processing webhooks
- Checking payment status
"""

from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException, Request, Header
from pydantic import BaseModel

from api.services.stripe_client import (
    get_stripe_client,
    create_product_checkout,
    process_webhook,
    StripeError,
)
from api.services.spaces import read_site_json

router = APIRouter()


class CheckoutRequest(BaseModel):
    """Request body for creating a checkout session."""
    product_title: str
    price_dollars: float
    quantity: int = 1
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None


class CheckoutResponse(BaseModel):
    """Response from creating a checkout session."""
    session_id: str
    checkout_url: str
    product_name: str
    amount_cents: int


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout(request: CheckoutRequest) -> CheckoutResponse:
    """
    Create a Stripe Checkout session for a product.

    This endpoint creates a checkout session that redirects
    the user to Stripe's hosted checkout page.

    Args:
        request: Product and pricing information

    Returns:
        Checkout session with redirect URL
    """
    try:
        client = get_stripe_client()
        result = await client.create_checkout_session(
            product_name=request.product_title,
            price_cents=int(request.price_dollars * 100),
            quantity=request.quantity,
            success_url=request.success_url or "https://ccc.quest/shop?success=true",
            cancel_url=request.cancel_url or "https://ccc.quest/shop?canceled=true",
        )

        return CheckoutResponse(
            session_id=result.session_id,
            checkout_url=result.url,
            product_name=result.product_name,
            amount_cents=result.amount,
        )

    except StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/checkout/product/{product_slug}")
async def checkout_product(product_slug: str) -> CheckoutResponse:
    """
    Create checkout for a product from shop.json by slug.

    Looks up the product in shop.json and creates a checkout session.

    Args:
        product_slug: URL-safe product identifier (title-artist)

    Returns:
        Checkout session with redirect URL
    """
    try:
        # Load shop data
        shop = read_site_json("shop.json")

        # Search for product in pots and merch
        product = None
        for pot in shop.get("pots", []):
            pot_slug = slugify(f"{pot.get('title', '')}-{pot.get('artist', '')}")
            if pot_slug == product_slug:
                product = pot
                break

        if not product:
            for merch in shop.get("merch", []):
                merch_slug = slugify(f"{merch.get('title', '')}-{merch.get('artist', '')}")
                if merch_slug == product_slug:
                    product = merch
                    break

        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        # Create checkout session
        client = get_stripe_client()
        result = await client.create_checkout_session(
            product_name=product.get("title", "Unknown Product"),
            price_cents=int(product.get("cost", 0) * 100),
            metadata={
                "product_slug": product_slug,
                "artist": product.get("artist", ""),
            },
        )

        return CheckoutResponse(
            session_id=result.session_id,
            checkout_url=result.url,
            product_name=result.product_name,
            amount_cents=result.amount,
        )

    except StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="Stripe-Signature"),
) -> Dict[str, str]:
    """
    Handle Stripe webhook events.

    Processes events like checkout.session.completed
    for order fulfillment and inventory updates.

    Args:
        request: Raw request with webhook payload
        stripe_signature: Stripe signature header for verification

    Returns:
        Acknowledgement of webhook receipt
    """
    if not stripe_signature:
        raise HTTPException(status_code=400, detail="Missing Stripe-Signature header")

    try:
        payload = await request.body()
        result = await process_webhook(payload, stripe_signature)
        return {"status": "received", "event_type": result.get("event_type", "unknown")}

    except StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))


def slugify(text: str) -> str:
    """Convert text to URL-safe slug."""
    import re
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '-', text)
    return text.strip('-')
