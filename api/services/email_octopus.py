"""
Email Octopus API client for newsletter management.

Provides functionality for:
- Managing subscriber lists
- Adding/removing subscribers
- Sending automated event reminders
"""

import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

import httpx

from api.core.config import settings

logger = logging.getLogger(__name__)

# Email Octopus API base URL
API_BASE_URL = "https://emailoctopus.com/api/1.6"


@dataclass
class Subscriber:
    """Represents an Email Octopus subscriber."""
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    status: str = "SUBSCRIBED"
    tags: List[str] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []


class EmailOctopusError(Exception):
    """Base exception for Email Octopus errors."""
    pass


class EmailOctopusClient:
    """
    Client for the Email Octopus API.

    Handles newsletter subscription management and email campaigns.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        list_id: Optional[str] = None,
    ):
        """
        Initialize the Email Octopus client.

        Args:
            api_key: Email Octopus API key (defaults to env var)
            list_id: Default list ID for operations (defaults to env var)
        """
        self.api_key = api_key or settings.EMAIL_OCTOPUS_API_KEY
        self.list_id = list_id or settings.EMAIL_OCTOPUS_LIST_ID
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=API_BASE_URL,
                timeout=30.0,
            )
        return self._client

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    def _check_api_key(self):
        """Verify API key is configured."""
        if not self.api_key:
            raise EmailOctopusError(
                "Email Octopus API key not configured. "
                "Set EMAIL_OCTOPUS_API_KEY environment variable."
            )

    def _add_api_key(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Add API key to request parameters."""
        params["api_key"] = self.api_key
        return params

    async def get_list(self, list_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get details of a mailing list.

        Args:
            list_id: List ID (uses default if not specified)

        Returns:
            List details including subscriber count

        Raises:
            EmailOctopusError: On API errors
        """
        self._check_api_key()
        list_id = list_id or self.list_id

        if not list_id:
            raise EmailOctopusError("No list ID specified")

        try:
            response = await self.client.get(
                f"/lists/{list_id}",
                params=self._add_api_key({}),
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get list {list_id}: {e}")
            raise EmailOctopusError(f"Failed to get list: {e}")

    async def get_subscribers(
        self,
        list_id: Optional[str] = None,
        limit: int = 100,
        page: int = 1,
    ) -> Dict[str, Any]:
        """
        Get subscribers from a list.

        Args:
            list_id: List ID (uses default if not specified)
            limit: Number of subscribers per page (max 100)
            page: Page number

        Returns:
            Subscribers data with pagination info

        Raises:
            EmailOctopusError: On API errors
        """
        self._check_api_key()
        list_id = list_id or self.list_id

        if not list_id:
            raise EmailOctopusError("No list ID specified")

        try:
            response = await self.client.get(
                f"/lists/{list_id}/contacts",
                params=self._add_api_key({
                    "limit": min(limit, 100),
                    "page": page,
                }),
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get subscribers: {e}")
            raise EmailOctopusError(f"Failed to get subscribers: {e}")

    async def add_subscriber(
        self,
        email: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        tags: Optional[List[str]] = None,
        list_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Add a subscriber to a list.

        Args:
            email: Subscriber email address
            first_name: Subscriber first name
            last_name: Subscriber last name
            tags: List of tags to apply
            list_id: List ID (uses default if not specified)

        Returns:
            Created subscriber data

        Raises:
            EmailOctopusError: On API errors
        """
        self._check_api_key()
        list_id = list_id or self.list_id

        if not list_id:
            raise EmailOctopusError("No list ID specified")

        fields = {}
        if first_name:
            fields["FirstName"] = first_name
        if last_name:
            fields["LastName"] = last_name

        payload = {
            "api_key": self.api_key,
            "email_address": email,
            "fields": fields,
            "tags": tags or [],
            "status": "SUBSCRIBED",
        }

        try:
            logger.info(f"Adding subscriber: {email}")
            response = await self.client.post(
                f"/lists/{list_id}/contacts",
                json=payload,
            )
            response.raise_for_status()
            logger.info(f"Successfully added subscriber: {email}")
            return response.json()

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 409:
                logger.info(f"Subscriber already exists: {email}")
                return {"email_address": email, "status": "ALREADY_EXISTS"}
            logger.error(f"Failed to add subscriber {email}: {e}")
            raise EmailOctopusError(f"Failed to add subscriber: {e}")

    async def remove_subscriber(
        self,
        email: str,
        list_id: Optional[str] = None,
    ) -> bool:
        """
        Remove a subscriber from a list.

        Args:
            email: Subscriber email address
            list_id: List ID (uses default if not specified)

        Returns:
            True if successful

        Raises:
            EmailOctopusError: On API errors
        """
        self._check_api_key()
        list_id = list_id or self.list_id

        if not list_id:
            raise EmailOctopusError("No list ID specified")

        # Email Octopus uses MD5 hash of lowercase email as contact ID
        import hashlib
        contact_id = hashlib.md5(email.lower().encode()).hexdigest()

        try:
            logger.info(f"Removing subscriber: {email}")
            response = await self.client.delete(
                f"/lists/{list_id}/contacts/{contact_id}",
                params=self._add_api_key({}),
            )
            response.raise_for_status()
            logger.info(f"Successfully removed subscriber: {email}")
            return True

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.info(f"Subscriber not found: {email}")
                return True  # Consider not found as success
            logger.error(f"Failed to remove subscriber {email}: {e}")
            raise EmailOctopusError(f"Failed to remove subscriber: {e}")

    async def update_subscriber_tags(
        self,
        email: str,
        tags: List[str],
        list_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Update tags for a subscriber.

        Args:
            email: Subscriber email address
            tags: New list of tags
            list_id: List ID (uses default if not specified)

        Returns:
            Updated subscriber data

        Raises:
            EmailOctopusError: On API errors
        """
        self._check_api_key()
        list_id = list_id or self.list_id

        if not list_id:
            raise EmailOctopusError("No list ID specified")

        import hashlib
        contact_id = hashlib.md5(email.lower().encode()).hexdigest()

        payload = {
            "api_key": self.api_key,
            "tags": {tag: True for tag in tags},
        }

        try:
            logger.info(f"Updating tags for subscriber: {email}")
            response = await self.client.put(
                f"/lists/{list_id}/contacts/{contact_id}",
                json=payload,
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to update subscriber tags: {e}")
            raise EmailOctopusError(f"Failed to update subscriber tags: {e}")


# Module-level client instance
_default_client: Optional[EmailOctopusClient] = None


def get_email_client() -> EmailOctopusClient:
    """Get the default Email Octopus client instance."""
    global _default_client
    if _default_client is None:
        _default_client = EmailOctopusClient()
    return _default_client


async def subscribe_to_newsletter(
    email: str,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Subscribe someone to the newsletter.

    Convenience function for adding newsletter subscribers.

    Args:
        email: Email address
        first_name: First name (optional)
        last_name: Last name (optional)

    Returns:
        Subscriber data
    """
    client = get_email_client()
    return await client.add_subscriber(
        email=email,
        first_name=first_name,
        last_name=last_name,
        tags=["newsletter"],
    )


async def subscribe_to_event_reminders(
    email: str,
    event_name: str,
    first_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Subscribe someone to event reminders.

    Args:
        email: Email address
        event_name: Name of the event
        first_name: First name (optional)

    Returns:
        Subscriber data
    """
    client = get_email_client()
    return await client.add_subscriber(
        email=email,
        first_name=first_name,
        tags=["event-reminder", f"event-{event_name.lower().replace(' ', '-')}"],
    )
