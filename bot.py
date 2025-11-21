"""Enhanced EC2 Discord Controller Bot - Main Entry Point

A modernized Discord bot for controlling AWS EC2 instances with:
- Interactive UI with buttons and menus
- Cost tracking with AWS Cost Explorer
- Caching for reduced API calls
- Structured logging
- Comprehensive error handling
"""

import os
import sys
import asyncio
import discord
from discord.ext import commands, tasks
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime, timezone
from typing import Dict, Any

# Add ec2bot to Python path
sys.path.insert(0, str(Path(__file__).parent))

from ec2bot.utils.logger import setup_logging, log_command
from ec2bot.database.db import Database
from ec2bot.services.ec2_service import EC2Service
from ec2bot.services.cache_service import get_cache
from ec2bot.ui.views import MainMenuView

# Load environment variables
load_dotenv()

# Configuration
TOKEN = os.environ.get('AWSDISCORDTOKEN')
DB_PATH = os.environ.get('DB_PATH', '/data/ec2bot.db')
AWS_REGION = os.environ.get('AWS_DEFAULT_REGION', 'us-east-1')
GUILD_ID = os.environ.get('guild_id', '').strip("'\"")

if not TOKEN:
    print("ERROR: AWSDISCORDTOKEN environment variable not set!")
    sys.exit(1)

if not GUILD_ID:
    print("ERROR: guild_id environment variable not set!")
    sys.exit(1)

# Initialize logging
logger = setup_logging(log_file=DB_PATH.replace('.db', '.log'), level="INFO")

# Initialize services
db = Database(DB_PATH)
cache = get_cache()

# Bot configuration with proper intents
intents = discord.Intents.default()
intents.message_content = True  # Required for message commands
intents.guilds = True

bot = commands.Bot(
    command_prefix='.',
    intents=intents,
    help_command=None  # We'll create our own
)


@bot.event
async def on_ready():
    """Called when bot is ready"""
    logger.info(f"Bot logged in as {bot.user} (ID: {bot.user.id})")
    logger.info(f"Connected to {len(bot.guilds)} guild(s)")
    logger.info(f"Monitoring instances with guild tag: {GUILD_ID}")

    # Initialize database
    try:
        await db.initialize()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}", exc_info=True)

    # Start background tasks
    if not cache_cleanup.is_running():
        cache_cleanup.start()
        logger.info("Started cache cleanup task")

    if not uptime_tracker.is_running():
        uptime_tracker.start()
        logger.info("Started uptime tracker task")

    logger.info("EC2 Discord Bot is ready!")


@bot.event
async def on_command_error(ctx, error):
    """Global error handler"""
    if isinstance(error, commands.CommandNotFound):
        return

    logger.error(f"Command error in {ctx.command}: {error}", exc_info=True)

    await ctx.send(f"❌ Error: {str(error)}", delete_after=10)


@tasks.loop(minutes=5)
async def cache_cleanup():
    """Periodic cache cleanup task"""
    try:
        await cache.cleanup_expired()
        stats = await cache.get_stats()
        logger.info(f"Cache cleanup complete. Stats: {stats}")
    except Exception as e:
        logger.error(f"Cache cleanup failed: {e}", exc_info=True)


@tasks.loop(minutes=10)
async def uptime_tracker():
    """Track uptime for running instances and check for alerts"""
    try:
        ec2_service = EC2Service(region=AWS_REGION)
        instances = await ec2_service.get_instances_by_tag('guild', GUILD_ID, use_cache=False)

        # Get enabled alert configs
        alert_configs = await db.get_alert_configs(enabled_only=True)

        for instance in instances:
            state = await ec2_service.get_instance_state(instance.id, use_cache=False)

            # If instance is running, save metadata and check alerts
            if state['state'] == 'running':
                # Save metadata
                await db.save_instance_metadata(
                    instance.id,
                    state['instance_type'],
                    AWS_REGION,
                    state['launch_time'] or '',
                    state['tags']
                )

                # Check uptime alerts
                uptime = await ec2_service.get_instance_uptime(instance.id)
                if uptime and alert_configs:
                    uptime_hours = uptime.total_seconds() / 3600

                    for alert_config in alert_configs:
                        threshold = alert_config['threshold_hours']
                        reminder_interval = alert_config['reminder_interval_hours']

                        # Check if uptime exceeds threshold
                        if uptime_hours >= threshold:
                            # Check last alert for this config
                            last_alert = await db.get_last_alert_for_instance(
                                instance.id,
                                alert_config['id']
                            )

                            should_alert = False

                            if not last_alert:
                                # First time threshold crossed
                                should_alert = True
                            elif reminder_interval > 0:
                                # Check if reminder interval has passed
                                last_alert_time = datetime.fromisoformat(
                                    last_alert['alert_triggered_at'].replace('Z', '+00:00')
                                )
                                now = datetime.now(timezone.utc)
                                hours_since_last = (now - last_alert_time).total_seconds() / 3600

                                if hours_since_last >= reminder_interval:
                                    should_alert = True

                            if should_alert:
                                # Send alert notification
                                await send_uptime_alert(
                                    instance.id,
                                    state['instance_type'],
                                    uptime_hours,
                                    alert_config,
                                    state.get('public_ip', 'N/A')
                                )

                                # Log the alert
                                await db.log_alert(
                                    instance.id,
                                    alert_config['id'],
                                    uptime_hours,
                                    notification_sent=True
                                )

        logger.info(f"Uptime tracker checked {len(instances)} instances")

    except Exception as e:
        logger.error(f"Uptime tracker failed: {e}", exc_info=True)


async def send_uptime_alert(instance_id: str, instance_type: str, uptime_hours: float,
                           alert_config: Dict[str, Any], public_ip: str):
    """Send uptime alert notification

    Args:
        instance_id: EC2 instance ID
        instance_type: Instance type
        uptime_hours: Current uptime in hours
        alert_config: Alert configuration dict
        public_ip: Public IP address
    """
    try:
        hours = int(uptime_hours)
        minutes = int((uptime_hours - hours) * 60)

        embed = discord.Embed(
            title=f"⏰ {alert_config['alert_name']}",
            description=f"Instance has been running for a long time",
            color=discord.Color.orange(),
            timestamp=datetime.now(timezone.utc)
        )

        embed.add_field(name="Instance ID", value=f"`{instance_id}`", inline=True)
        embed.add_field(name="Instance Type", value=instance_type, inline=True)
        embed.add_field(name="Public IP", value=public_ip, inline=True)
        embed.add_field(
            name="Current Uptime",
            value=f"**{hours}h {minutes}m**",
            inline=False
        )
        embed.add_field(
            name="Alert Threshold",
            value=f"{alert_config['threshold_hours']} hours",
            inline=True
        )

        if alert_config['reminder_interval_hours'] > 0:
            embed.add_field(
                name="Reminder Interval",
                value=f"Every {alert_config['reminder_interval_hours']} hours",
                inline=True
            )

        embed.set_footer(text="Use .menu to stop the instance and save costs")

        # Send to configured channel or find a suitable channel
        channel_id = alert_config.get('channel_id')
        if channel_id:
            try:
                channel = bot.get_channel(int(channel_id))
                if channel:
                    await channel.send(embed=embed)
                    logger.info(f"Sent uptime alert to channel {channel_id} for {instance_id}")
                    return
            except Exception as e:
                logger.error(f"Failed to send alert to channel {channel_id}: {e}")

        # Fallback: Send to first available text channel in guild
        for guild in bot.guilds:
            if str(guild.id) == GUILD_ID:
                # Try to find a channel named 'ec2-alerts' or similar
                for channel in guild.text_channels:
                    if 'ec2' in channel.name.lower() or 'alert' in channel.name.lower() or 'bot' in channel.name.lower():
                        await channel.send(embed=embed)
                        logger.info(f"Sent uptime alert to channel {channel.name} for {instance_id}")
                        return

                # If no specific channel found, use the first available text channel
                if guild.text_channels:
                    await guild.text_channels[0].send(embed=embed)
                    logger.info(f"Sent uptime alert to default channel for {instance_id}")
                    return

        logger.warning(f"No suitable channel found for uptime alert for {instance_id}")

    except Exception as e:
        logger.error(f"Failed to send uptime alert for {instance_id}: {e}", exc_info=True)


@bot.command(name='menu')
async def menu_command(ctx):
    """Open the main EC2 controller menu"""
    log_command(logger, "menu", ctx.author.id, guild_id=ctx.guild.id if ctx.guild else None)

    await db.log_command(
        str(ctx.author.id),
        ctx.author.name,
        "menu",
        success=True
    )

    try:
        # Get instance information
        ec2_service = EC2Service(region=AWS_REGION)
        instances = await ec2_service.get_instances_by_tag('guild', GUILD_ID)

        # Create embed with instance info
        embed = discord.Embed(
            title="EC2 Controller Main Menu",
            color=discord.Color.blue(),
            timestamp=datetime.now(timezone.utc)
        )

        if instances:
            for instance in instances:
                state = await ec2_service.get_instance_state(instance.id)
                status_emoji = {
                    'running': '🟢',
                    'stopped': '🔴',
                    'pending': '🟡',
                    'stopping': '🟡'
                }.get(state['state'], '⚪')

                ip_info = state['public_ip'] if state['public_ip'] else "No Public IP"
                embed.add_field(
                    name=f"{status_emoji} {instance.id}",
                    value=f"**IP**: {ip_info}\n**State**: {state['state']}",
                    inline=True
                )
        else:
            embed.description = f"No instances found with guild tag: {GUILD_ID}"

        await ctx.send(embed=embed, view=MainMenuView())
    except Exception as e:
        logger.error(f"Menu command failed: {e}", exc_info=True)
        await ctx.send("EC2 Controller Main Menu", view=MainMenuView())


@bot.command(name='ping')
async def ping_command(ctx):
    """Check bot latency"""
    log_command(logger, "ping", ctx.author.id)

    latency_ms = round(bot.latency * 1000)
    await ctx.send(f"🏓 Pong! Latency: {latency_ms}ms")

    await db.log_command(
        str(ctx.author.id),
        ctx.author.name,
        "ping",
        success=True
    )


@bot.command(name='state')
async def state_command(ctx):
    """Quick state check for all instances"""
    log_command(logger, "state", ctx.author.id)

    try:
        ec2_service = EC2Service(region=AWS_REGION)
        instances = await ec2_service.get_instances_by_tag('guild', GUILD_ID)

        if not instances:
            await ctx.send(f"No instances found with guild tag: {GUILD_ID}")
            return

        response = "**Instance States:**\n"
        for instance in instances:
            state = await ec2_service.get_instance_state(instance.id)
            emoji_map = {
                'running': '🟢',
                'stopped': '🔴',
                'pending': '🟡',
                'stopping': '🟡'
            }
            emoji = emoji_map.get(state['state'], '⚪')
            response += f"{emoji} `{instance.id}`: **{state['state'].upper()}**\n"

        await ctx.send(response)

        await db.log_command(
            str(ctx.author.id),
            ctx.author.name,
            "state",
            success=True
        )

    except Exception as e:
        logger.error(f"State command failed: {e}", exc_info=True)
        await ctx.send(f"❌ Error: {str(e)}")

        await db.log_command(
            str(ctx.author.id),
            ctx.author.name,
            "state",
            success=False,
            error_message=str(e)
        )


@bot.command(name='start')
async def start_command(ctx, instance_id: str = None):
    """Start an EC2 instance"""
    log_command(logger, "start", ctx.author.id, instance_id=instance_id)

    try:
        ec2_service = EC2Service(region=AWS_REGION)

        # If no instance specified, get first one
        if not instance_id:
            instances = await ec2_service.get_instances_by_tag('guild', GUILD_ID)
            if not instances:
                await ctx.send("No instances found!")
                return
            instance_id = instances[0].id

        msg = await ctx.send(f"⏳ Starting instance `{instance_id}`...")

        result = await ec2_service.start_instance(instance_id)

        if result['success']:
            # Start uptime session
            await db.start_uptime_session(instance_id)

            await msg.edit(content=f"✅ Instance `{instance_id}` is starting!")

            await db.log_command(
                str(ctx.author.id),
                ctx.author.name,
                "start",
                instance_id=instance_id,
                success=True
            )
        else:
            await msg.edit(content=f"❌ Failed to start instance: {result.get('error', 'Unknown error')}")

            await db.log_command(
                str(ctx.author.id),
                ctx.author.name,
                "start",
                instance_id=instance_id,
                success=False,
                error_message=result.get('error')
            )

    except Exception as e:
        logger.error(f"Start command failed: {e}", exc_info=True)
        await ctx.send(f"❌ Error: {str(e)}")


@bot.command(name='stop')
async def stop_command(ctx, instance_id: str = None):
    """Stop an EC2 instance"""
    log_command(logger, "stop", ctx.author.id, instance_id=instance_id)

    try:
        ec2_service = EC2Service(region=AWS_REGION)

        # If no instance specified, get first one
        if not instance_id:
            instances = await ec2_service.get_instances_by_tag('guild', GUILD_ID)
            if not instances:
                await ctx.send("No instances found!")
                return
            instance_id = instances[0].id

        msg = await ctx.send(f"⏳ Stopping instance `{instance_id}`...")

        # End uptime session
        duration = await db.end_uptime_session(instance_id)

        result = await ec2_service.stop_instance(instance_id)

        if result['success']:
            duration_str = ""
            if duration:
                hours = duration // 3600
                minutes = (duration % 3600) // 60
                duration_str = f" (Session: {hours}h {minutes}m)"

            await msg.edit(content=f"✅ Instance `{instance_id}` is stopping!{duration_str}")

            await db.log_command(
                str(ctx.author.id),
                ctx.author.name,
                "stop",
                instance_id=instance_id,
                success=True
            )
        else:
            await msg.edit(content=f"❌ Failed to stop instance: {result.get('error', 'Unknown error')}")

            await db.log_command(
                str(ctx.author.id),
                ctx.author.name,
                "stop",
                instance_id=instance_id,
                success=False,
                error_message=result.get('error')
            )

    except Exception as e:
        logger.error(f"Stop command failed: {e}", exc_info=True)
        await ctx.send(f"❌ Error: {str(e)}")


@bot.command(name='help')
async def help_command(ctx):
    """Show help information"""
    embed = discord.Embed(
        title="EC2 Controller Bot - Help",
        description="Control your AWS EC2 instances from Discord",
        color=discord.Color.blue()
    )

    embed.add_field(
        name="Interactive Menu",
        value="`.menu` - Open the interactive control panel",
        inline=False
    )

    embed.add_field(
        name="Quick Commands",
        value=(
            "`.ping` - Check bot latency\n"
            "`.state` - View all instance states\n"
            "`.start [instance-id]` - Start an instance\n"
            "`.stop [instance-id]` - Stop an instance"
        ),
        inline=False
    )

    embed.add_field(
        name="Features",
        value=(
            "✅ Interactive button-based controls\n"
            "✅ Uptime tracking\n"
            "✅ Cost estimation\n"
            "✅ Monthly/weekly reports\n"
            "✅ Caching for faster responses"
        ),
        inline=False
    )

    embed.set_footer(text="Use .menu for the full interactive interface")

    await ctx.send(embed=embed)


async def main():
    """Main bot entry point"""
    try:
        logger.info("Starting EC2 Discord Bot...")
        async with bot:
            await bot.start(TOKEN)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot crashed: {e}", exc_info=True)
        raise
    finally:
        logger.info("Bot shutdown complete")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot stopped by user")
    except Exception as e:
        print(f"\nFatal error: {e}")
        sys.exit(1)
