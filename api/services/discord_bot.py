"""
Discord bot for Chicago Clay Co-Op.

Runs as a background task in FastAPI. Provides slash commands for:
- Managing studio members
- Managing events/workshops/classes
- Triggering site rebuilds
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands

from api.core.config import settings
from api.services.spaces import get_spaces_client, read_site_json, write_site_json

logger = logging.getLogger(__name__)


class CoopBot(commands.Bot):
    """
    Discord bot for Chicago Clay Co-Op.

    Integrates with Digital Ocean Spaces for data storage
    and triggers GitHub Actions for site rebuilds.
    """

    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True

        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None,
        )

        self.guild_id = settings.DISCORD_GUILD_ID

    async def setup_hook(self):
        """Called when bot is ready. Syncs slash commands."""
        logger.info("Setting up Discord bot slash commands...")

        # Add command cogs
        await self.add_cog(MemberCommands(self))
        await self.add_cog(EventCommands(self))
        await self.add_cog(AdminCommands(self))

        # Sync commands to guild
        if self.guild_id:
            guild = discord.Object(id=int(self.guild_id))
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            logger.info(f"Synced commands to guild {self.guild_id}")
        else:
            await self.tree.sync()
            logger.info("Synced commands globally")

    async def on_ready(self):
        """Called when bot is connected and ready."""
        logger.info(f"Discord bot connected as {self.user}")


class MemberCommands(commands.Cog):
    """Slash commands for managing studio members."""

    def __init__(self, bot: CoopBot):
        self.bot = bot

    @app_commands.command(name="member-add", description="Add a new studio member")
    @app_commands.describe(
        name="Member's name",
        statement="Artist statement",
        image="Image URL",
        instagram="Instagram URL",
        website="Personal website URL",
    )
    async def member_add(
        self,
        interaction: discord.Interaction,
        name: str,
        statement: str,
        image: Optional[str] = None,
        instagram: Optional[str] = None,
        website: Optional[str] = None,
    ):
        """Add a new member to makers.json."""
        await interaction.response.defer(ephemeral=True)

        try:
            # Load current makers data
            makers = read_site_json("makers.json")

            # Create new member entry
            new_member = {
                "name": name,
                "statement": statement,
            }
            if image:
                new_member["image"] = image
            if instagram:
                new_member["instagram"] = instagram
            if website:
                new_member["website"] = website

            # Add to members list
            if "members" not in makers:
                makers["members"] = []
            makers["members"].append(new_member)

            # Save to Spaces
            write_site_json("makers.json", makers)

            await interaction.followup.send(
                f"✅ Added member: **{name}**\n"
                f"Run `/rebuild` to update the website.",
                ephemeral=True,
            )
            logger.info(f"Added member: {name}")

        except Exception as e:
            logger.error(f"Failed to add member: {e}")
            await interaction.followup.send(
                f"❌ Failed to add member: {str(e)}",
                ephemeral=True,
            )

    @app_commands.command(name="member-list", description="List all studio members")
    async def member_list(self, interaction: discord.Interaction):
        """List all members from makers.json."""
        await interaction.response.defer(ephemeral=True)

        try:
            makers = read_site_json("makers.json")
            members = makers.get("members", [])

            if not members:
                await interaction.followup.send("No members found.", ephemeral=True)
                return

            member_list = "\n".join(
                f"• **{m.get('name', 'Unknown')}**" for m in members
            )
            await interaction.followup.send(
                f"📋 **Studio Members ({len(members)})**\n{member_list}",
                ephemeral=True,
            )

        except Exception as e:
            logger.error(f"Failed to list members: {e}")
            await interaction.followup.send(
                f"❌ Failed to list members: {str(e)}",
                ephemeral=True,
            )

    @app_commands.command(name="member-remove", description="Remove a studio member")
    @app_commands.describe(name="Member's name to remove")
    async def member_remove(self, interaction: discord.Interaction, name: str):
        """Remove a member from makers.json."""
        await interaction.response.defer(ephemeral=True)

        try:
            makers = read_site_json("makers.json")
            members = makers.get("members", [])

            # Find and remove member
            original_count = len(members)
            makers["members"] = [m for m in members if m.get("name", "").lower() != name.lower()]

            if len(makers["members"]) == original_count:
                await interaction.followup.send(
                    f"❌ Member not found: {name}",
                    ephemeral=True,
                )
                return

            # Save to Spaces
            write_site_json("makers.json", makers)

            await interaction.followup.send(
                f"✅ Removed member: **{name}**\n"
                f"Run `/rebuild` to update the website.",
                ephemeral=True,
            )
            logger.info(f"Removed member: {name}")

        except Exception as e:
            logger.error(f"Failed to remove member: {e}")
            await interaction.followup.send(
                f"❌ Failed to remove member: {str(e)}",
                ephemeral=True,
            )


class EventCommands(commands.Cog):
    """Slash commands for managing events."""

    def __init__(self, bot: CoopBot):
        self.bot = bot

    @app_commands.command(name="event-add", description="Add a new event")
    @app_commands.describe(
        name="Event name",
        date="Event date (YYYY-MM-DD)",
        time="Event time (e.g., 6pm-9pm)",
        description="Event description",
        cost="Cost in dollars (leave empty for free)",
        instructor="Instructor name",
        image="Image URL",
        link="Registration/purchase link",
    )
    async def event_add(
        self,
        interaction: discord.Interaction,
        name: str,
        date: str,
        time: str,
        description: str,
        cost: Optional[str] = None,
        instructor: Optional[str] = None,
        image: Optional[str] = None,
        link: Optional[str] = None,
    ):
        """Add a new event to events.json."""
        await interaction.response.defer(ephemeral=True)

        try:
            # Validate date format
            try:
                datetime.strptime(date, "%Y-%m-%d")
            except ValueError:
                await interaction.followup.send(
                    "❌ Invalid date format. Use YYYY-MM-DD (e.g., 2025-06-15)",
                    ephemeral=True,
                )
                return

            # Load current events data
            events_data = read_site_json("events.json")

            # Create new event entry
            new_event = {
                "name": name,
                "date": date,
                "time": time,
                "description": description,
            }
            if cost:
                new_event["cost"] = cost
            if instructor:
                new_event["instructor"] = instructor
            if image:
                new_event["image"] = image
            if link:
                new_event["link"] = link

            # Add to events list
            if "events" not in events_data:
                events_data["events"] = []
            events_data["events"].append(new_event)

            # Save to Spaces
            write_site_json("events.json", events_data)

            await interaction.followup.send(
                f"✅ Added event: **{name}** on {date}\n"
                f"Run `/rebuild` to update the website.",
                ephemeral=True,
            )
            logger.info(f"Added event: {name} on {date}")

        except Exception as e:
            logger.error(f"Failed to add event: {e}")
            await interaction.followup.send(
                f"❌ Failed to add event: {str(e)}",
                ephemeral=True,
            )

    @app_commands.command(name="event-list", description="List upcoming events")
    async def event_list(self, interaction: discord.Interaction):
        """List upcoming events from events.json."""
        await interaction.response.defer(ephemeral=True)

        try:
            events_data = read_site_json("events.json")
            events = events_data.get("events", [])

            # Filter to upcoming events
            today = datetime.now().strftime("%Y-%m-%d")
            upcoming = [
                e for e in events
                if e.get("date", "0000-00-00") >= today
            ]
            upcoming.sort(key=lambda e: e.get("date", "9999-99-99"))

            if not upcoming:
                await interaction.followup.send("No upcoming events.", ephemeral=True)
                return

            event_list = "\n".join(
                f"• **{e.get('name')}** - {e.get('date')} {e.get('time', '')}"
                for e in upcoming[:10]  # Limit to 10
            )

            more_text = f"\n...and {len(upcoming) - 10} more" if len(upcoming) > 10 else ""

            await interaction.followup.send(
                f"📅 **Upcoming Events ({len(upcoming)})**\n{event_list}{more_text}",
                ephemeral=True,
            )

        except Exception as e:
            logger.error(f"Failed to list events: {e}")
            await interaction.followup.send(
                f"❌ Failed to list events: {str(e)}",
                ephemeral=True,
            )

    @app_commands.command(name="event-remove", description="Remove an event")
    @app_commands.describe(
        name="Event name",
        date="Event date (YYYY-MM-DD) to disambiguate if needed",
    )
    async def event_remove(
        self,
        interaction: discord.Interaction,
        name: str,
        date: Optional[str] = None,
    ):
        """Remove an event from events.json."""
        await interaction.response.defer(ephemeral=True)

        try:
            events_data = read_site_json("events.json")
            events = events_data.get("events", [])

            # Find and remove event
            original_count = len(events)

            def should_keep(event):
                name_match = event.get("name", "").lower() == name.lower()
                if date:
                    return not (name_match and event.get("date") == date)
                return not name_match

            events_data["events"] = [e for e in events if should_keep(e)]

            removed_count = original_count - len(events_data["events"])

            if removed_count == 0:
                await interaction.followup.send(
                    f"❌ Event not found: {name}",
                    ephemeral=True,
                )
                return

            # Save to Spaces
            write_site_json("events.json", events_data)

            await interaction.followup.send(
                f"✅ Removed {removed_count} event(s): **{name}**\n"
                f"Run `/rebuild` to update the website.",
                ephemeral=True,
            )
            logger.info(f"Removed event: {name}")

        except Exception as e:
            logger.error(f"Failed to remove event: {e}")
            await interaction.followup.send(
                f"❌ Failed to remove event: {str(e)}",
                ephemeral=True,
            )


class AdminCommands(commands.Cog):
    """Admin slash commands."""

    def __init__(self, bot: CoopBot):
        self.bot = bot

    @app_commands.command(name="rebuild", description="Trigger a website rebuild")
    async def rebuild(self, interaction: discord.Interaction):
        """Trigger a GitHub Actions rebuild."""
        await interaction.response.defer(ephemeral=True)

        try:
            # TODO: Implement GitHub Actions trigger
            # For now, just log and confirm
            logger.info("Website rebuild requested")

            await interaction.followup.send(
                "🔄 Website rebuild triggered!\n"
                "The site will update in a few minutes.",
                ephemeral=True,
            )

        except Exception as e:
            logger.error(f"Failed to trigger rebuild: {e}")
            await interaction.followup.send(
                f"❌ Failed to trigger rebuild: {str(e)}",
                ephemeral=True,
            )

    @app_commands.command(name="ping", description="Check if bot is working")
    async def ping(self, interaction: discord.Interaction):
        """Simple ping command to check bot status."""
        latency = round(self.bot.latency * 1000)
        await interaction.response.send_message(
            f"🏓 Pong! Latency: {latency}ms",
            ephemeral=True,
        )


# Bot instance
_bot: Optional[CoopBot] = None


def get_bot() -> CoopBot:
    """Get the Discord bot instance."""
    global _bot
    if _bot is None:
        _bot = CoopBot()
    return _bot


async def start_bot():
    """Start the Discord bot as a background task."""
    if not settings.DISCORD_BOT_TOKEN:
        logger.warning("Discord bot token not configured, skipping bot startup")
        return

    bot = get_bot()

    try:
        logger.info("Starting Discord bot...")
        await bot.start(settings.DISCORD_BOT_TOKEN)
    except Exception as e:
        logger.error(f"Discord bot error: {e}")
        raise


async def stop_bot():
    """Stop the Discord bot gracefully."""
    global _bot
    if _bot:
        logger.info("Stopping Discord bot...")
        await _bot.close()
        _bot = None
