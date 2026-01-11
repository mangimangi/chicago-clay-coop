"""
Pytest tests for the Discord bot.

Tests use mocking to avoid requiring actual Discord connections.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime

from api.services.discord_bot import (
    CoopBot,
    MemberCommands,
    EventCommands,
    AdminCommands,
    get_bot,
    start_bot,
    stop_bot,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_bot():
    """Create a mock CoopBot."""
    with patch("api.services.discord_bot.discord.Intents"):
        bot = MagicMock(spec=CoopBot)
        bot.latency = 0.05  # 50ms
        return bot


@pytest.fixture
def mock_interaction():
    """Create a mock Discord interaction."""
    interaction = MagicMock()
    interaction.response = MagicMock()
    interaction.response.defer = AsyncMock()
    interaction.response.send_message = AsyncMock()
    interaction.followup = MagicMock()
    interaction.followup.send = AsyncMock()
    return interaction


# =============================================================================
# Bot Initialization Tests
# =============================================================================

class TestBotInitialization:
    """Tests for bot initialization."""

    @patch("api.services.discord_bot.discord.Intents")
    @patch("api.services.discord_bot.commands.Bot.__init__")
    def test_bot_init(self, mock_bot_init, mock_intents):
        """Test CoopBot initializes correctly."""
        mock_bot_init.return_value = None
        mock_intents.default.return_value = MagicMock()

        bot = CoopBot()

        mock_bot_init.assert_called_once()
        call_kwargs = mock_bot_init.call_args[1]
        assert call_kwargs["command_prefix"] == "!"

    def test_get_bot_returns_instance(self):
        """Test get_bot returns a bot instance."""
        with patch("api.services.discord_bot._bot", None):
            with patch("api.services.discord_bot.CoopBot") as MockBot:
                MockBot.return_value = MagicMock()
                bot = get_bot()
                assert bot is not None


# =============================================================================
# Member Commands Tests
# =============================================================================

class TestMemberCommands:
    """Tests for member management commands."""

    @pytest.mark.asyncio
    async def test_member_add_success(self, mock_bot, mock_interaction):
        """Test adding a member successfully."""
        cog = MemberCommands(mock_bot)

        with patch("api.services.discord_bot.read_site_json") as mock_read:
            with patch("api.services.discord_bot.write_site_json") as mock_write:
                mock_read.return_value = {"members": []}

                # Call the underlying callback function directly
                await cog.member_add.callback(
                    cog,
                    mock_interaction,
                    name="New Artist",
                    statement="I make pots",
                    image="https://example.com/img.jpg",
                    instagram="https://instagram.com/artist",
                    website=None,
                )

                mock_interaction.response.defer.assert_called_once()
                mock_write.assert_called_once()

                # Check written data
                written_data = mock_write.call_args[0][1]
                assert len(written_data["members"]) == 1
                assert written_data["members"][0]["name"] == "New Artist"

    @pytest.mark.asyncio
    async def test_member_list_success(self, mock_bot, mock_interaction):
        """Test listing members successfully."""
        cog = MemberCommands(mock_bot)

        with patch("api.services.discord_bot.read_site_json") as mock_read:
            mock_read.return_value = {
                "members": [
                    {"name": "Artist One"},
                    {"name": "Artist Two"},
                ]
            }

            await cog.member_list.callback(cog, mock_interaction)

            mock_interaction.followup.send.assert_called_once()
            message = mock_interaction.followup.send.call_args[0][0]
            assert "Artist One" in message
            assert "Artist Two" in message

    @pytest.mark.asyncio
    async def test_member_list_empty(self, mock_bot, mock_interaction):
        """Test listing members when list is empty."""
        cog = MemberCommands(mock_bot)

        with patch("api.services.discord_bot.read_site_json") as mock_read:
            mock_read.return_value = {"members": []}

            await cog.member_list.callback(cog, mock_interaction)

            message = mock_interaction.followup.send.call_args[0][0]
            assert "No members found" in message

    @pytest.mark.asyncio
    async def test_member_remove_success(self, mock_bot, mock_interaction):
        """Test removing a member successfully."""
        cog = MemberCommands(mock_bot)

        with patch("api.services.discord_bot.read_site_json") as mock_read:
            with patch("api.services.discord_bot.write_site_json") as mock_write:
                mock_read.return_value = {
                    "members": [
                        {"name": "Keep Me"},
                        {"name": "Remove Me"},
                    ]
                }

                await cog.member_remove.callback(cog, mock_interaction, name="Remove Me")

                written_data = mock_write.call_args[0][1]
                assert len(written_data["members"]) == 1
                assert written_data["members"][0]["name"] == "Keep Me"

    @pytest.mark.asyncio
    async def test_member_remove_not_found(self, mock_bot, mock_interaction):
        """Test removing non-existent member."""
        cog = MemberCommands(mock_bot)

        with patch("api.services.discord_bot.read_site_json") as mock_read:
            mock_read.return_value = {"members": [{"name": "Other"}]}

            await cog.member_remove.callback(cog, mock_interaction, name="Not Found")

            message = mock_interaction.followup.send.call_args[0][0]
            assert "not found" in message.lower()


# =============================================================================
# Event Commands Tests
# =============================================================================

class TestEventCommands:
    """Tests for event management commands."""

    @pytest.mark.asyncio
    async def test_event_add_success(self, mock_bot, mock_interaction):
        """Test adding an event successfully."""
        cog = EventCommands(mock_bot)

        with patch("api.services.discord_bot.read_site_json") as mock_read:
            with patch("api.services.discord_bot.write_site_json") as mock_write:
                mock_read.return_value = {"events": []}

                await cog.event_add.callback(
                    cog,
                    mock_interaction,
                    name="Test Workshop",
                    date="2025-06-15",
                    time="6pm-9pm",
                    description="A fun workshop",
                    cost="50",
                    instructor="Jane Doe",
                    image=None,
                    link=None,
                )

                written_data = mock_write.call_args[0][1]
                assert len(written_data["events"]) == 1
                assert written_data["events"][0]["name"] == "Test Workshop"
                assert written_data["events"][0]["cost"] == "50"

    @pytest.mark.asyncio
    async def test_event_add_invalid_date(self, mock_bot, mock_interaction):
        """Test adding event with invalid date format."""
        cog = EventCommands(mock_bot)

        await cog.event_add.callback(
            cog,
            mock_interaction,
            name="Bad Event",
            date="06/15/2025",  # Wrong format
            time="6pm",
            description="Test",
            cost=None,
            instructor=None,
            image=None,
            link=None,
        )

        message = mock_interaction.followup.send.call_args[0][0]
        assert "Invalid date format" in message

    @pytest.mark.asyncio
    async def test_event_list_success(self, mock_bot, mock_interaction):
        """Test listing upcoming events."""
        cog = EventCommands(mock_bot)

        with patch("api.services.discord_bot.read_site_json") as mock_read:
            mock_read.return_value = {
                "events": [
                    {"name": "Past Event", "date": "2020-01-01", "time": "6pm"},
                    {"name": "Future Event", "date": "2099-12-31", "time": "6pm"},
                ]
            }

            await cog.event_list.callback(cog, mock_interaction)

            message = mock_interaction.followup.send.call_args[0][0]
            assert "Future Event" in message
            assert "Past Event" not in message

    @pytest.mark.asyncio
    async def test_event_remove_success(self, mock_bot, mock_interaction):
        """Test removing an event successfully."""
        cog = EventCommands(mock_bot)

        with patch("api.services.discord_bot.read_site_json") as mock_read:
            with patch("api.services.discord_bot.write_site_json") as mock_write:
                mock_read.return_value = {
                    "events": [
                        {"name": "Keep Event", "date": "2025-01-01"},
                        {"name": "Remove Event", "date": "2025-02-01"},
                    ]
                }

                await cog.event_remove.callback(cog, mock_interaction, name="Remove Event", date=None)

                written_data = mock_write.call_args[0][1]
                assert len(written_data["events"]) == 1

    @pytest.mark.asyncio
    async def test_event_remove_with_date(self, mock_bot, mock_interaction):
        """Test removing specific event by name and date."""
        cog = EventCommands(mock_bot)

        with patch("api.services.discord_bot.read_site_json") as mock_read:
            with patch("api.services.discord_bot.write_site_json") as mock_write:
                mock_read.return_value = {
                    "events": [
                        {"name": "Workshop", "date": "2025-01-01"},
                        {"name": "Workshop", "date": "2025-02-01"},
                    ]
                }

                await cog.event_remove.callback(
                    cog,
                    mock_interaction,
                    name="Workshop",
                    date="2025-01-01",
                )

                written_data = mock_write.call_args[0][1]
                assert len(written_data["events"]) == 1
                assert written_data["events"][0]["date"] == "2025-02-01"


# =============================================================================
# Admin Commands Tests
# =============================================================================

class TestAdminCommands:
    """Tests for admin commands."""

    @pytest.mark.asyncio
    async def test_rebuild_command(self, mock_bot, mock_interaction):
        """Test rebuild command."""
        cog = AdminCommands(mock_bot)

        await cog.rebuild.callback(cog, mock_interaction)

        mock_interaction.response.defer.assert_called_once()
        message = mock_interaction.followup.send.call_args[0][0]
        assert "rebuild triggered" in message.lower()

    @pytest.mark.asyncio
    async def test_ping_command(self, mock_bot, mock_interaction):
        """Test ping command."""
        mock_bot.latency = 0.05  # 50ms
        cog = AdminCommands(mock_bot)

        await cog.ping.callback(cog, mock_interaction)

        mock_interaction.response.send_message.assert_called_once()
        message = mock_interaction.response.send_message.call_args[0][0]
        assert "Pong" in message
        assert "50ms" in message


# =============================================================================
# Bot Lifecycle Tests
# =============================================================================

class TestBotLifecycle:
    """Tests for bot start/stop functions."""

    @pytest.mark.asyncio
    async def test_start_bot_without_token(self):
        """Test start_bot does nothing without token."""
        with patch("api.services.discord_bot.settings") as mock_settings:
            mock_settings.DISCORD_BOT_TOKEN = None

            await start_bot()

            # Should return without error

    @pytest.mark.asyncio
    async def test_stop_bot(self):
        """Test stop_bot closes connection."""
        with patch("api.services.discord_bot._bot") as mock_bot:
            mock_bot.close = AsyncMock()

            await stop_bot()

            mock_bot.close.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
