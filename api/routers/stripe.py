"""
Stripe API endpoints for shop integration.

Provides endpoints for:
- Creating checkout sessions (JSON response for JS clients)
- Redirect endpoints for static site links
- Processing webhooks
"""

from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException, Request, Header
from fastapi.responses import RedirectResponse
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


# =============================================================================
# Redirect Endpoints (for static site HTML links)
# =============================================================================

@router.get("/buy/{product_slug}")
async def buy_product_redirect(product_slug: str) -> RedirectResponse:
    """
    Redirect to Stripe Checkout for a shop product.

    This GET endpoint is designed for static site links:
    <a href="/api/stripe/buy/cool-mug-artist-name">Buy</a>

    Args:
        product_slug: URL-safe product identifier (title-artist)

    Returns:
        302 redirect to Stripe Checkout
    """
    try:
        shop = read_site_json("shop.json")

        # Search for product in pots and merch
        product = None
        product_type = "product"
        for pot in shop.get("pots", []):
            pot_slug = slugify(f"{pot.get('title', '')}-{pot.get('artist', '')}")
            if pot_slug == product_slug:
                product = pot
                product_type = "pot"
                break

        if not product:
            for merch in shop.get("merch", []):
                merch_slug = slugify(f"{merch.get('title', '')}-{merch.get('artist', '')}")
                if merch_slug == product_slug:
                    product = merch
                    product_type = "merch"
                    break

        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        if not product.get("cost"):
            raise HTTPException(status_code=400, detail="Product has no price")

        # Create checkout session
        client = get_stripe_client()
        result = await client.create_checkout_session(
            product_name=product.get("title", "Unknown Product"),
            price_cents=int(product.get("cost", 0) * 100),
            success_url=f"https://ccc.quest/shop/{product_slug}.html?success=true",
            cancel_url=f"https://ccc.quest/shop/{product_slug}.html?canceled=true",
            metadata={
                "product_slug": product_slug,
                "product_type": product_type,
                "artist": product.get("artist", ""),
            },
        )

        return RedirectResponse(url=result.url, status_code=302)

    except StripeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/register/{event_slug}")
async def register_event_redirect(event_slug: str) -> RedirectResponse:
    """
    Redirect to Stripe Checkout for an event registration.

    This GET endpoint is designed for static site links:
    <a href="/api/stripe/register/workshop-name-2025-01-15">Register</a>

    Args:
        event_slug: URL-safe event identifier (name-date)

    Returns:
        302 redirect to Stripe Checkout
    """
    try:
        events_data = read_site_json("events.json")
        events = events_data.get("events", [])

        # Find event by slug
        event = None
        for e in events:
            e_slug = f"{slugify(e.get('name', ''))}-{e.get('date', '')}"
            if e_slug == event_slug:
                event = e
                break

        if not event:
            raise HTTPException(status_code=404, detail="Event not found")

        if not event.get("cost"):
            raise HTTPException(status_code=400, detail="Event is free - no checkout needed")

        # Create checkout session
        client = get_stripe_client()
        result = await client.create_checkout_session(
            product_name=event.get("name", "Event Registration"),
            price_cents=int(float(event.get("cost", 0)) * 100),
            success_url=f"https://ccc.quest/event/{event_slug}.html?success=true",
            cancel_url=f"https://ccc.quest/event/{event_slug}.html?canceled=true",
            metadata={
                "event_slug": event_slug,
                "event_name": event.get("name", ""),
                "event_date": event.get("date", ""),
                "instructor": event.get("instructor", ""),
            },
        )

        return RedirectResponse(url=result.url, status_code=302)

    except StripeError as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# JSON Endpoints (for JavaScript clients)
# =============================================================================

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


@router.post("/checkout/event/{event_slug}")
async def checkout_event(event_slug: str) -> CheckoutResponse:
    """
    Create checkout for an event by slug.

    Args:
        event_slug: URL-safe event identifier (name-date)

    Returns:
        Checkout session with redirect URL
    """
    try:
        events_data = read_site_json("events.json")
        events = events_data.get("events", [])

        event = None
        for e in events:
            e_slug = f"{slugify(e.get('name', ''))}-{e.get('date', '')}"
            if e_slug == event_slug:
                event = e
                break

        if not event:
            raise HTTPException(status_code=404, detail="Event not found")

        client = get_stripe_client()
        result = await client.create_checkout_session(
            product_name=event.get("name", "Event Registration"),
            price_cents=int(float(event.get("cost", 0)) * 100),
            metadata={
                "event_slug": event_slug,
                "event_name": event.get("name", ""),
                "event_date": event.get("date", ""),
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


# =============================================================================
# Webhook Handler
# =============================================================================

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
