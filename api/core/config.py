"""
Application configuration.

Loads environment variables and provides typed settings access.
All sensitive values should be set via environment variables, not in code.
"""

import os
from typing import List, Optional
from dataclasses import dataclass, field


@dataclass
class Settings:
    """Application settings loaded from environment variables."""

    # Application
    APP_NAME: str = "Chicago Clay Co-Op API"
    DEBUG: bool = field(default_factory=lambda: os.getenv("DEBUG", "false").lower() == "true")

    # CORS
    CORS_ORIGINS: List[str] = field(default_factory=lambda: [
        "https://ccc.quest",
        "http://localhost:3000",
        "http://localhost:8000",
    ])

    # Digital Ocean Spaces (S3-compatible)
    SPACES_ACCESS_KEY: Optional[str] = field(
        default_factory=lambda: os.getenv("DIGITALOCEAN_SPACES_ACCESS_KEY")
    )
    SPACES_SECRET_KEY: Optional[str] = field(
        default_factory=lambda: os.getenv("DIGITALOCEAN_SPACES_SECRET_KEY")
    )
    SPACES_REGION: str = field(
        default_factory=lambda: os.getenv("DIGITALOCEAN_REGION", "nyc3")
    )
    SPACES_BUCKET: str = field(
        default_factory=lambda: os.getenv("DIGITALOCEAN_SPACES_BUCKET", "file-the-coop")
    )
    SPACES_ENDPOINT: str = field(
        default_factory=lambda: os.getenv(
            "DIGITALOCEAN_SPACES_ENDPOINT",
            f"https://{os.getenv('DIGITALOCEAN_REGION', 'nyc3')}.digitaloceanspaces.com"
        )
    )

    # Discord
    DISCORD_BOT_TOKEN: Optional[str] = field(
        default_factory=lambda: os.getenv("DISCORD_BOT_TOKEN")
    )
    DISCORD_WEBHOOK_URL: Optional[str] = field(
        default_factory=lambda: os.getenv("DISCORD_WEBHOOK_URL")
    )
    DISCORD_GUILD_ID: Optional[str] = field(
        default_factory=lambda: os.getenv("DISCORD_GUILD_ID")
    )

    # Stripe
    STRIPE_API_KEY: Optional[str] = field(
        default_factory=lambda: os.getenv("STRIPE_API_KEY")
    )
    STRIPE_WEBHOOK_SECRET: Optional[str] = field(
        default_factory=lambda: os.getenv("STRIPE_WEBHOOK_SECRET")
    )

    # Email Octopus
    EMAIL_OCTOPUS_API_KEY: Optional[str] = field(
        default_factory=lambda: os.getenv("EMAIL_OCTOPUS_API_KEY")
    )
    EMAIL_OCTOPUS_LIST_ID: Optional[str] = field(
        default_factory=lambda: os.getenv("EMAIL_OCTOPUS_LIST_ID")
    )

    # GitHub Actions
    GITHUB_TOKEN: Optional[str] = field(
        default_factory=lambda: os.getenv("GITHUB_TOKEN")
    )
    GITHUB_REPO: str = field(
        default_factory=lambda: os.getenv("GITHUB_REPO", "chicago-clay-coop/chicago-clay-coop")
    )

    def is_spaces_configured(self) -> bool:
        """Check if Spaces credentials are configured."""
        return bool(self.SPACES_ACCESS_KEY and self.SPACES_SECRET_KEY)

    def is_discord_configured(self) -> bool:
        """Check if Discord bot is configured."""
        return bool(self.DISCORD_BOT_TOKEN)

    def is_stripe_configured(self) -> bool:
        """Check if Stripe is configured."""
        return bool(self.STRIPE_API_KEY)

    def is_email_configured(self) -> bool:
        """Check if Email Octopus is configured."""
        return bool(self.EMAIL_OCTOPUS_API_KEY)


# Global settings instance
settings = Settings()
