"""UI Styles and colors for Discord bot

Provides consistent styling across all Discord UI components.
"""

import discord
from datetime import datetime, timezone


class BotStyles:
    """Standardized colors and styles for Discord UI"""

    # Button styles
    PRIMARY = discord.ButtonStyle.primary      # Blue for main actions
    SECONDARY = discord.ButtonStyle.secondary  # Gray for navigation
    SUCCESS = discord.ButtonStyle.success      # Green for positive actions
    DANGER = discord.ButtonStyle.danger        # Red for destructive actions

    # Embed colors
    PRIMARY_COLOR = discord.Color.blue()       # Main embed color
    SUCCESS_COLOR = discord.Color.green()      # Success operations
    WARNING_COLOR = discord.Color.orange()     # Warnings
    ERROR_COLOR = discord.Color.red()          # Errors
    INFO_COLOR = discord.Color.blurple()       # Info/neutral
    LOADING_COLOR = discord.Color.yellow()     # Loading states

    # Instance state colors
    RUNNING_COLOR = discord.Color.green()
    STOPPED_COLOR = discord.Color.red()
    PENDING_COLOR = discord.Color.orange()


def create_loading_embed(title: str, description: str = "Please wait...") -> discord.Embed:
    """Create a standardized loading embed

    Args:
        title: Embed title
        description: Loading message

    Returns:
        Discord embed with loading style
    """
    embed = discord.Embed(
        title=f"⏳ {title}",
        description=description,
        color=BotStyles.LOADING_COLOR,
        timestamp=datetime.now(timezone.utc)
    )
    return embed


def create_error_embed(title: str, error: str) -> discord.Embed:
    """Create a standardized error embed

    Args:
        title: Error title
        error: Error message

    Returns:
        Discord embed with error style
    """
    embed = discord.Embed(
        title=f"❌ {title}",
        description=f"```\n{error}\n```",
        color=BotStyles.ERROR_COLOR,
        timestamp=datetime.now(timezone.utc)
    )
    return embed


def create_success_embed(title: str, description: str = "") -> discord.Embed:
    """Create a standardized success embed

    Args:
        title: Success title
        description: Success message

    Returns:
        Discord embed with success style
    """
    embed = discord.Embed(
        title=f"✅ {title}",
        description=description,
        color=BotStyles.SUCCESS_COLOR,
        timestamp=datetime.now(timezone.utc)
    )
    return embed


def get_instance_state_color(state: str) -> discord.Color:
    """Get color based on EC2 instance state

    Args:
        state: EC2 instance state (running, stopped, etc.)

    Returns:
        Discord color matching the state
    """
    state_colors = {
        "running": BotStyles.RUNNING_COLOR,
        "stopped": BotStyles.STOPPED_COLOR,
        "pending": BotStyles.PENDING_COLOR,
        "stopping": BotStyles.PENDING_COLOR,
        "terminated": BotStyles.ERROR_COLOR,
        "shutting-down": BotStyles.PENDING_COLOR,
    }
    return state_colors.get(state.lower(), BotStyles.INFO_COLOR)


def get_instance_state_emoji(state: str) -> str:
    """Get emoji for EC2 instance state

    Args:
        state: EC2 instance state

    Returns:
        Emoji representing the state
    """
    state_emojis = {
        "running": "🟢",
        "stopped": "🔴",
        "pending": "🟡",
        "stopping": "🟡",
        "terminated": "⚫",
        "shutting-down": "🟡",
    }
    return state_emojis.get(state.lower(), "⚪")
