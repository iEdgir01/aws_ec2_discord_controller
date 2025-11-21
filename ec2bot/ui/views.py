"""Interactive Discord UI views

Provides button-based interactive UI that updates in the same message,
similar to the traffic_manager bot pattern.
"""

import discord
from discord.ui import View, Button, Select
from discord import SelectOption
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
import asyncio

from .styles import (
    BotStyles, create_loading_embed, create_error_embed, create_success_embed,
    get_instance_state_color, get_instance_state_emoji
)


class BackToMenuButton(Button):
    """Button to return to main menu"""

    def __init__(self):
        super().__init__(label="Main Menu", style=BotStyles.SECONDARY)

    async def callback(self, interaction: discord.Interaction):
        try:
            await interaction.response.edit_message(
                content="EC2 Controller Main Menu",
                embed=None,
                view=MainMenuView()
            )
        except (discord.NotFound, discord.HTTPException):
            pass


class BackToMenuView(View):
    """View with just a back button"""

    def __init__(self):
        super().__init__(timeout=300)
        self.add_item(BackToMenuButton())


class MainMenuView(View):
    """Main menu with all primary actions"""

    def __init__(self):
        super().__init__(timeout=300)
        self.add_item(InstanceControlButton())
        self.add_item(PanelControlButton())
        self.add_item(ViewReportsButton())
        self.add_item(ViewCostsButton())
        self.add_item(AlertSettingsButton())
        self.add_item(CacheStatsButton())


class InstanceControlButton(Button):
    """Button to access instance controls"""

    def __init__(self):
        super().__init__(label="Control Instances", style=BotStyles.PRIMARY, emoji="🖥️")

    async def callback(self, interaction: discord.Interaction):
        from ..services.ec2_service import EC2Service
        from os import environ

        try:
            await interaction.response.edit_message(
                embed=create_loading_embed("Loading Instances", "Fetching EC2 instances..."),
                view=None
            )

            ec2_service = EC2Service(region=environ.get('AWS_DEFAULT_REGION', 'us-east-1'))
            guild_id = environ.get('guild_id', '').strip("'\"")

            instances = await ec2_service.get_instances_by_tag('guild', guild_id)

            if not instances:
                embed = create_error_embed(
                    "No Instances Found",
                    f"No EC2 instances found with guild tag: {guild_id}"
                )
                await interaction.edit_original_response(embed=embed, view=BackToMenuView())
                return

            # Create pagination view for instances
            view = InstancePaginationView(instances, ec2_service)
            embed = await view.get_current_embed()

            await interaction.edit_original_response(embed=embed, view=view)

        except Exception as e:
            embed = create_error_embed("Error Loading Instances", str(e))
            await interaction.edit_original_response(embed=embed, view=BackToMenuView())


class InstancePaginationView(View):
    """Paginated view of EC2 instances with controls"""

    def __init__(self, instances: List[Any], ec2_service):
        super().__init__(timeout=300)
        self.instances = instances
        self.ec2_service = ec2_service
        self.current_index = 0

        # Add control buttons
        self.add_item(StartInstanceButton(self))
        self.add_item(StopInstanceButton(self))
        self.add_item(RebootInstanceButton(self))
        self.add_item(RefreshButton(self))

        # Navigation
        self.prev_button = Button(label="Previous", style=BotStyles.SECONDARY, row=1)
        self.next_button = Button(label="Next", style=BotStyles.SECONDARY, row=1)
        self.prev_button.callback = self.prev_callback
        self.next_button.callback = self.next_callback
        self.add_item(self.prev_button)
        self.add_item(self.next_button)
        self.add_item(BackToMenuButton())

        self.update_nav_buttons()

    def update_nav_buttons(self):
        """Update navigation button states"""
        self.prev_button.disabled = self.current_index == 0
        self.next_button.disabled = self.current_index >= len(self.instances) - 1

    async def get_current_embed(self) -> discord.Embed:
        """Get embed for current instance"""
        instance = self.instances[self.current_index]
        instance_id = instance.id

        # Get fresh state
        state = await self.ec2_service.get_instance_state(instance_id, use_cache=False)

        emoji = get_instance_state_emoji(state['state'])
        color = get_instance_state_color(state['state'])

        embed = discord.Embed(
            title=f"{emoji} EC2 Instance: {instance_id}",
            color=color,
            timestamp=datetime.now(timezone.utc)
        )

        embed.add_field(name="State", value=state['state'].upper(), inline=True)
        embed.add_field(name="Type", value=state['instance_type'], inline=True)
        embed.add_field(name="Zone", value=state['availability_zone'], inline=True)

        if state['public_ip']:
            embed.add_field(name="Public IP", value=state['public_ip'], inline=True)
        if state['private_ip']:
            embed.add_field(name="Private IP", value=state['private_ip'], inline=True)

        # Uptime if running
        if state['state'] == 'running':
            uptime = await self.ec2_service.get_instance_uptime(instance_id)
            if uptime:
                hours = int(uptime.total_seconds() // 3600)
                minutes = int((uptime.total_seconds() % 3600) // 60)
                embed.add_field(name="Uptime", value=f"{hours}h {minutes}m", inline=True)

        # Tags
        if state['tags']:
            tags_str = "\n".join([f"**{k}**: {v}" for k, v in state['tags'].items()])
            embed.add_field(name="Tags", value=tags_str, inline=False)

        embed.set_footer(text=f"Instance {self.current_index + 1} of {len(self.instances)}")

        return embed

    async def refresh_view(self, interaction: discord.Interaction):
        """Refresh the current view"""
        try:
            embed = await self.get_current_embed()
            self.update_nav_buttons()
            await interaction.response.edit_message(embed=embed, view=self)
        except (discord.NotFound, discord.HTTPException):
            pass

    async def prev_callback(self, interaction: discord.Interaction):
        """Go to previous instance"""
        if self.current_index > 0:
            self.current_index -= 1
            await self.refresh_view(interaction)

    async def next_callback(self, interaction: discord.Interaction):
        """Go to next instance"""
        if self.current_index < len(self.instances) - 1:
            self.current_index += 1
            await self.refresh_view(interaction)


class StartInstanceButton(Button):
    """Button to start an instance"""

    def __init__(self, parent_view: InstancePaginationView):
        super().__init__(label="Start", style=BotStyles.SUCCESS, emoji="▶️")
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        instance = self.parent_view.instances[self.parent_view.current_index]
        instance_id = instance.id

        try:
            await interaction.response.edit_message(
                embed=create_loading_embed("Starting Instance", f"Starting {instance_id}..."),
                view=None
            )

            result = await self.parent_view.ec2_service.start_instance(instance_id)

            if result['success']:
                # Wait for running state
                success = await self.parent_view.ec2_service.wait_for_state(
                    instance_id, 'running', timeout_seconds=120
                )

                if success:
                    embed = create_success_embed(
                        "Instance Started",
                        f"Instance {instance_id} is now running"
                    )
                else:
                    embed = create_success_embed(
                        "Start Initiated",
                        f"Instance {instance_id} is starting (may take a few moments)"
                    )
            else:
                embed = create_error_embed("Start Failed", result.get('error', 'Unknown error'))

            # Refresh instance view
            await asyncio.sleep(2)
            fresh_embed = await self.parent_view.get_current_embed()
            await interaction.edit_original_response(embed=fresh_embed, view=self.parent_view)

        except Exception as e:
            embed = create_error_embed("Error Starting Instance", str(e))
            await interaction.edit_original_response(embed=embed, view=BackToMenuView())


class StopInstanceButton(Button):
    """Button to stop an instance"""

    def __init__(self, parent_view: InstancePaginationView):
        super().__init__(label="Stop", style=BotStyles.DANGER, emoji="⏹️")
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        from ..database.db import Database
        from os import environ

        instance = self.parent_view.instances[self.parent_view.current_index]
        instance_id = instance.id

        try:
            await interaction.response.edit_message(
                embed=create_loading_embed("Stopping Instance", f"Stopping {instance_id}..."),
                view=None
            )

            # End uptime session
            db = Database(environ.get('DB_PATH', '/data/ec2bot.db'))
            duration = await db.end_uptime_session(instance_id)

            result = await self.parent_view.ec2_service.stop_instance(instance_id)

            if result['success']:
                embed = create_success_embed(
                    "Instance Stopped",
                    f"Instance {instance_id} is stopping"
                )

                if duration:
                    hours = duration // 3600
                    minutes = (duration % 3600) // 60
                    embed.add_field(name="Session Duration", value=f"{hours}h {minutes}m", inline=False)
            else:
                embed = create_error_embed("Stop Failed", result.get('error', 'Unknown error'))

            # Refresh instance view
            await asyncio.sleep(2)
            fresh_embed = await self.parent_view.get_current_embed()
            await interaction.edit_original_response(embed=fresh_embed, view=self.parent_view)

        except Exception as e:
            embed = create_error_embed("Error Stopping Instance", str(e))
            await interaction.edit_original_response(embed=embed, view=BackToMenuView())


class RebootInstanceButton(Button):
    """Button to reboot an instance"""

    def __init__(self, parent_view: InstancePaginationView):
        super().__init__(label="Reboot", style=BotStyles.PRIMARY, emoji="🔄")
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        instance = self.parent_view.instances[self.parent_view.current_index]
        instance_id = instance.id

        try:
            await interaction.response.edit_message(
                embed=create_loading_embed("Rebooting Instance", f"Rebooting {instance_id}..."),
                view=None
            )

            result = await self.parent_view.ec2_service.reboot_instance(instance_id)

            if result['success']:
                embed = create_success_embed(
                    "Instance Rebooting",
                    f"Instance {instance_id} is rebooting"
                )
            else:
                embed = create_error_embed("Reboot Failed", result.get('error', 'Unknown error'))

            # Refresh instance view
            await asyncio.sleep(2)
            fresh_embed = await self.parent_view.get_current_embed()
            await interaction.edit_original_response(embed=fresh_embed, view=self.parent_view)

        except Exception as e:
            embed = create_error_embed("Error Rebooting Instance", str(e))
            await interaction.edit_original_response(embed=embed, view=BackToMenuView())


class RefreshButton(Button):
    """Button to refresh instance state"""

    def __init__(self, parent_view: InstancePaginationView):
        super().__init__(label="Refresh", style=BotStyles.SECONDARY, emoji="🔄")
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        await self.parent_view.refresh_view(interaction)


class ViewReportsButton(Button):
    """Button to view uptime reports"""

    def __init__(self):
        super().__init__(label="View Reports", style=BotStyles.PRIMARY, emoji="📊")

    async def callback(self, interaction: discord.Interaction):
        try:
            await interaction.response.edit_message(
                content="Select Report Type:",
                embed=None,
                view=ReportsMenuView()
            )
        except (discord.NotFound, discord.HTTPException):
            pass


class ReportsMenuView(View):
    """Menu for selecting report types"""

    def __init__(self):
        super().__init__(timeout=300)
        self.add_item(DailyReportButton())
        self.add_item(WeeklyReportButton())
        self.add_item(MonthlyReportButton())
        self.add_item(BackToMenuButton())


class DailyReportButton(Button):
    """Show daily uptime report"""

    def __init__(self):
        super().__init__(label="Today's Report", style=BotStyles.PRIMARY)

    async def callback(self, interaction: discord.Interaction):
        from ..database.db import Database
        from ..services.ec2_service import EC2Service
        from os import environ

        try:
            await interaction.response.edit_message(
                embed=create_loading_embed("Generating Report", "Calculating today's uptime..."),
                view=None
            )

            db = Database(environ.get('DB_PATH', '/data/ec2bot.db'))
            ec2_service = EC2Service(region=environ.get('AWS_DEFAULT_REGION', 'us-east-1'))
            guild_id = environ.get('guild_id', '').strip("'\"")

            instances = await ec2_service.get_instances_by_tag('guild', guild_id)

            embed = discord.Embed(
                title="📊 Daily Uptime Report",
                description=f"Report for {datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
                color=BotStyles.PRIMARY_COLOR,
                timestamp=datetime.now(timezone.utc)
            )

            for instance in instances:
                # Get completed uptime sessions for today
                uptime_seconds = await db.get_daily_uptime(instance.id)

                # If instance is currently running, add current session uptime
                state = await ec2_service.get_instance_state(instance.id, use_cache=False)

                if state['state'] == 'running':
                    current_uptime = await ec2_service.get_instance_uptime(instance.id)
                    if current_uptime:
                        # Add current session time to today's total
                        uptime_seconds += int(current_uptime.total_seconds())

                hours = uptime_seconds // 3600
                minutes = (uptime_seconds % 3600) // 60

                emoji = get_instance_state_emoji(state['state'])

                # Add additional context for running instances
                status_text = f"**State**: {state['state']}"
                if state['state'] == 'running':
                    status_text += f" (currently running)"

                embed.add_field(
                    name=f"{emoji} {instance.id}",
                    value=f"**Uptime**: {hours}h {minutes}m\n{status_text}",
                    inline=False
                )

            await interaction.edit_original_response(embed=embed, view=BackToMenuView())

        except Exception as e:
            embed = create_error_embed("Report Generation Failed", str(e))
            await interaction.edit_original_response(embed=embed, view=BackToMenuView())


class WeeklyReportButton(Button):
    """Show weekly uptime report"""

    def __init__(self):
        super().__init__(label="Weekly Report", style=BotStyles.SUCCESS)

    async def callback(self, interaction: discord.Interaction):
        # Implementation similar to daily but for the past 7 days
        await interaction.response.send_message("Weekly report coming soon!", ephemeral=True)


class MonthlyReportButton(Button):
    """Show monthly uptime report"""

    def __init__(self):
        super().__init__(label="Monthly Report", style=BotStyles.SUCCESS)

    async def callback(self, interaction: discord.Interaction):
        from ..database.db import Database
        from ..services.ec2_service import EC2Service
        from ..services.cost_service import CostService
        from os import environ

        try:
            await interaction.response.edit_message(
                embed=create_loading_embed("Generating Report", "Calculating monthly uptime and costs..."),
                view=None
            )

            now = datetime.now(timezone.utc)
            db = Database(environ.get('DB_PATH', '/data/ec2bot.db'))
            ec2_service = EC2Service(region=environ.get('AWS_DEFAULT_REGION', 'us-east-1'))
            cost_service = CostService(region=environ.get('AWS_DEFAULT_REGION', 'us-east-1'))
            guild_id = environ.get('guild_id', '').strip("'\"")

            instances = await ec2_service.get_instances_by_tag('guild', guild_id)

            embed = discord.Embed(
                title="📊 Monthly Report",
                description=f"{now.strftime('%B %Y')}",
                color=BotStyles.PRIMARY_COLOR,
                timestamp=now
            )

            total_cost = 0.0

            for instance in instances:
                uptime_seconds = await db.get_monthly_uptime(instance.id, now.year, now.month)
                hours = uptime_seconds // 3600
                minutes = (uptime_seconds % 3600) // 60

                state = await ec2_service.get_instance_state(instance.id)
                cost = await cost_service.estimate_monthly_cost(state['instance_type'], uptime_seconds)
                total_cost += cost

                emoji = get_instance_state_emoji(state['state'])

                embed.add_field(
                    name=f"{emoji} {instance.id}",
                    value=f"**Uptime**: {hours}h {minutes}m\n**Est. Cost**: ${cost:.2f}",
                    inline=False
                )

            embed.add_field(name="💰 Total Estimated Cost", value=f"${total_cost:.2f}", inline=False)

            await interaction.edit_original_response(embed=embed, view=BackToMenuView())

        except Exception as e:
            embed = create_error_embed("Report Generation Failed", str(e))
            await interaction.edit_original_response(embed=embed, view=BackToMenuView())


class ViewCostsButton(Button):
    """Button to view cost information"""

    def __init__(self):
        super().__init__(label="View Costs", style=BotStyles.PRIMARY, emoji="💰")

    async def callback(self, interaction: discord.Interaction):
        from ..services.cost_service import CostService
        from os import environ

        try:
            await interaction.response.edit_message(
                embed=create_loading_embed("Loading Cost Data", "Fetching costs from AWS..."),
                view=None
            )

            cost_service = CostService(region=environ.get('AWS_DEFAULT_REGION', 'us-east-1'))
            now = datetime.now(timezone.utc)

            # Get current month costs with breakdown
            breakdown_data = await cost_service.get_cost_breakdown_by_service(now.year, now.month)
            forecast = await cost_service.get_cost_forecast(days=30)
            recommendations = await cost_service.get_cost_optimization_recommendations(now.year, now.month)

            embed = discord.Embed(
                title="💰 Cost Overview",
                description=f"**{now.strftime('%B %Y')}** Cost Analysis",
                color=BotStyles.INFO_COLOR,
                timestamp=now
            )

            # Total cost
            embed.add_field(
                name="Total Monthly Cost",
                value=f"**${breakdown_data['total_cost']:.2f}**",
                inline=False
            )

            # Service breakdown
            if breakdown_data.get('breakdown'):
                breakdown_text = ""
                for service, cost in breakdown_data['breakdown'].items():
                    percentage = (cost / breakdown_data['total_cost'] * 100) if breakdown_data['total_cost'] > 0 else 0
                    breakdown_text += f"• **{service}**: ${cost:.2f} ({percentage:.1f}%)\n"

                embed.add_field(
                    name="📊 Cost Breakdown by Service",
                    value=breakdown_text or "No breakdown available",
                    inline=False
                )

            # Forecast
            if 'forecasted_cost' in forecast and forecast['forecasted_cost'] > 0:
                embed.add_field(
                    name="📈 30-Day Forecast",
                    value=f"${forecast['forecasted_cost']:.2f}",
                    inline=True
                )

            # Recommendations
            if recommendations:
                rec_text = ""
                severity_emoji = {
                    "high": "🔴",
                    "medium": "🟡",
                    "low": "🟢",
                    "info": "ℹ️",
                    "error": "❌"
                }

                for rec in recommendations[:3]:  # Show top 3 recommendations
                    emoji = severity_emoji.get(rec['severity'], "•")
                    rec_text += f"{emoji} **{rec['title']}**\n{rec['message']}\n\n"

                embed.add_field(
                    name="💡 Cost Optimization Recommendations",
                    value=rec_text or "No recommendations at this time",
                    inline=False
                )

            embed.set_footer(text="Data from AWS Cost Explorer | Click 'Main Menu' to go back")

            await interaction.edit_original_response(embed=embed, view=BackToMenuView())

        except Exception as e:
            embed = create_error_embed("Cost Loading Failed", str(e))
            await interaction.edit_original_response(embed=embed, view=BackToMenuView())


class CacheStatsButton(Button):
    """Button to view cache statistics"""

    def __init__(self):
        super().__init__(label="Cache Stats", style=BotStyles.SECONDARY, emoji="📈")

    async def callback(self, interaction: discord.Interaction):
        from ..services.cache_service import get_cache

        try:
            cache = get_cache()
            stats = await cache.get_stats()

            embed = discord.Embed(
                title="📈 Cache Statistics",
                color=BotStyles.INFO_COLOR,
                timestamp=datetime.now(timezone.utc)
            )

            embed.add_field(name="Total Requests", value=str(stats['total_requests']), inline=True)
            embed.add_field(name="Cache Hits", value=str(stats['hits']), inline=True)
            embed.add_field(name="Cache Misses", value=str(stats['misses']), inline=True)
            embed.add_field(name="Hit Rate", value=f"{stats['hit_rate']:.1%}", inline=True)
            embed.add_field(name="Current Entries", value=str(stats['current_entries']), inline=True)
            embed.add_field(name="Evictions", value=str(stats['evictions']), inline=True)

            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            embed = create_error_embed("Error Loading Stats", str(e))
            await interaction.response.send_message(embed=embed, ephemeral=True)


class PanelControlButton(Button):
    """Button to access Pterodactyl panel controls"""

    def __init__(self):
        super().__init__(label="Panel Servers", style=BotStyles.PRIMARY, emoji="🎮")

    async def callback(self, interaction: discord.Interaction):
        try:
            await interaction.response.edit_message(
                content="Pterodactyl Panel Controls",
                embed=None,
                view=PanelMenuView()
            )
        except (discord.NotFound, discord.HTTPException):
            pass


class PanelMenuView(View):
    """Menu for Pterodactyl panel server controls"""

    def __init__(self):
        super().__init__(timeout=300)
        self.add_item(ServerStatusButton())
        self.add_item(RunningServersButton())
        self.add_item(ServerDetailsButton())
        self.add_item(BackToMenuButton())


class ServerStatusButton(Button):
    """Show server status overview"""

    def __init__(self):
        super().__init__(label="Server Status", style=BotStyles.PRIMARY, emoji="📊")

    async def callback(self, interaction: discord.Interaction):
        from ..services.panel_service import PanelService

        try:
            await interaction.response.edit_message(
                embed=create_loading_embed("Loading Status", "Fetching server status from panel..."),
                view=None
            )

            panel_service = PanelService()
            counts = await panel_service.get_server_count()

            embed = discord.Embed(
                title="🎮 Pterodactyl Panel Status",
                color=BotStyles.INFO_COLOR,
                timestamp=datetime.now(timezone.utc)
            )

            embed.add_field(name="Total Servers", value=str(counts['total']), inline=True)
            embed.add_field(name="Running", value=f"🟢 {counts['running']}", inline=True)
            embed.add_field(name="Offline", value=f"⚫ {counts['offline']}", inline=True)

            if counts['starting'] > 0:
                embed.add_field(name="Starting", value=f"🟡 {counts['starting']}", inline=True)
            if counts['stopping'] > 0:
                embed.add_field(name="Stopping", value=f"🟠 {counts['stopping']}", inline=True)

            await interaction.edit_original_response(embed=embed, view=PanelMenuView())

        except Exception as e:
            embed = create_error_embed("Panel Connection Failed", str(e))
            await interaction.edit_original_response(embed=embed, view=BackToMenuView())


class RunningServersButton(Button):
    """List all running servers"""

    def __init__(self):
        super().__init__(label="Running Servers", style=BotStyles.SUCCESS, emoji="🟢")

    async def callback(self, interaction: discord.Interaction):
        from ..services.panel_service import PanelService

        try:
            await interaction.response.edit_message(
                embed=create_loading_embed("Loading Servers", "Fetching running servers from panel..."),
                view=None
            )

            panel_service = PanelService()
            running_servers = await panel_service.get_running_servers()

            embed = discord.Embed(
                title="🟢 Running Servers",
                color=BotStyles.SUCCESS_COLOR,
                timestamp=datetime.now(timezone.utc)
            )

            if running_servers:
                server_list = "\n".join([f"• {name}" for name in running_servers])
                embed.description = server_list
                embed.set_footer(text=f"{len(running_servers)} server(s) running")
            else:
                embed.description = "No servers are currently running"
                embed.color = BotStyles.WARNING_COLOR

            await interaction.edit_original_response(embed=embed, view=PanelMenuView())

        except Exception as e:
            embed = create_error_embed("Failed to List Servers", str(e))
            await interaction.edit_original_response(embed=embed, view=BackToMenuView())


class ServerDetailsButton(Button):
    """Show detailed server information table"""

    def __init__(self):
        super().__init__(label="Server Details", style=BotStyles.PRIMARY, emoji="📋")

    async def callback(self, interaction: discord.Interaction):
        from ..services.panel_service import PanelService

        try:
            await interaction.response.edit_message(
                embed=create_loading_embed("Loading Details", "Fetching server details from panel..."),
                view=None
            )

            panel_service = PanelService()
            table = await panel_service.get_server_details_table()

            embed = discord.Embed(
                title="📋 Server Details",
                color=BotStyles.INFO_COLOR,
                timestamp=datetime.now(timezone.utc)
            )

            # Discord embeds have a 4096 character limit for description
            if len(table) > 4000:
                embed.description = "Server details table too large to display"
                embed.add_field(name="Note", value="Use the 'Running Servers' button for a simpler view", inline=False)
            else:
                embed.description = f"```\n{table}\n```"

            await interaction.edit_original_response(embed=embed, view=PanelMenuView())

        except Exception as e:
            embed = create_error_embed("Failed to Load Details", str(e))
            await interaction.edit_original_response(embed=embed, view=BackToMenuView())


class AlertSettingsButton(Button):
    """Button to access uptime alert settings"""

    def __init__(self):
        super().__init__(label="Alert Settings", style=BotStyles.PRIMARY, emoji="⏰")

    async def callback(self, interaction: discord.Interaction):
        try:
            await interaction.response.edit_message(
                content="Uptime Alert Settings",
                embed=None,
                view=AlertSettingsMenuView()
            )
        except (discord.NotFound, discord.HTTPException):
            pass


class AlertSettingsMenuView(View):
    """Menu for managing uptime alert settings"""

    def __init__(self):
        super().__init__(timeout=300)
        self.add_item(ViewAlertsButton())
        self.add_item(CreateAlertButton())
        self.add_item(BackToMenuButton())


class ViewAlertsButton(Button):
    """Show all configured alerts"""

    def __init__(self):
        super().__init__(label="View Alerts", style=BotStyles.PRIMARY, emoji="📋")

    async def callback(self, interaction: discord.Interaction):
        from ..database.db import Database
        from os import environ

        try:
            await interaction.response.edit_message(
                embed=create_loading_embed("Loading Alerts", "Fetching alert configurations..."),
                view=None
            )

            db = Database(environ.get('DB_PATH', '/data/ec2bot.db'))
            alerts = await db.get_alert_configs(enabled_only=False)

            embed = discord.Embed(
                title="⏰ Uptime Alert Configurations",
                color=BotStyles.INFO_COLOR,
                timestamp=datetime.now(timezone.utc)
            )

            if not alerts:
                embed.description = "No alerts configured yet. Use 'Create Alert' to add one."
            else:
                for alert in alerts:
                    status = "✅ Enabled" if alert['enabled'] else "❌ Disabled"
                    reminder_text = f"\nReminders: Every {alert['reminder_interval_hours']}h" if alert['reminder_interval_hours'] > 0 else ""

                    embed.add_field(
                        name=f"{alert['alert_name']} (ID: {alert['id']})",
                        value=f"**Threshold**: {alert['threshold_hours']} hours\n**Status**: {status}{reminder_text}",
                        inline=False
                    )

            embed.set_footer(text="Use 'Create Alert' to add new alerts")

            await interaction.edit_original_response(embed=embed, view=AlertSettingsMenuView())

        except Exception as e:
            embed = create_error_embed("Failed to Load Alerts", str(e))
            await interaction.edit_original_response(embed=embed, view=AlertSettingsMenuView())


class CreateAlertButton(Button):
    """Create predefined alert configurations"""

    def __init__(self):
        super().__init__(label="Create Alert", style=BotStyles.SUCCESS, emoji="➕")

    async def callback(self, interaction: discord.Interaction):
        try:
            await interaction.response.edit_message(
                content="Select an alert threshold to create:",
                embed=None,
                view=CreateAlertSelectView()
            )
        except (discord.NotFound, discord.HTTPException):
            pass


class CreateAlertSelectView(View):
    """View for selecting alert threshold"""

    def __init__(self):
        super().__init__(timeout=300)
        self.add_item(CreateAlert4HButton())
        self.add_item(CreateAlert8HButton())
        self.add_item(CreateAlert24HButton())
        self.add_item(BackToAlertMenuButton())


class BackToAlertMenuButton(Button):
    """Button to return to alert settings menu"""

    def __init__(self):
        super().__init__(label="Back", style=BotStyles.SECONDARY)

    async def callback(self, interaction: discord.Interaction):
        try:
            await interaction.response.edit_message(
                content="Uptime Alert Settings",
                embed=None,
                view=AlertSettingsMenuView()
            )
        except (discord.NotFound, discord.HTTPException):
            pass


class CreateAlert4HButton(Button):
    """Create 4-hour alert"""

    def __init__(self):
        super().__init__(label="4 Hour Alert", style=BotStyles.PRIMARY)

    async def callback(self, interaction: discord.Interaction):
        from ..database.db import Database
        from os import environ

        try:
            await interaction.response.edit_message(
                embed=create_loading_embed("Creating Alert", "Setting up 4-hour uptime alert..."),
                view=None
            )

            db = Database(environ.get('DB_PATH', '/data/ec2bot.db'))
            alert_id = await db.create_alert_config(
                alert_name="4 Hour Uptime Warning",
                threshold_hours=4,
                reminder_interval_hours=2
            )

            embed = create_success_embed(
                "Alert Created",
                f"4-hour uptime alert created successfully!\n\n"
                f"**Alert ID**: {alert_id}\n"
                f"**Threshold**: 4 hours\n"
                f"**Reminders**: Every 2 hours"
            )

            await interaction.edit_original_response(embed=embed, view=AlertSettingsMenuView())

        except Exception as e:
            embed = create_error_embed("Failed to Create Alert", str(e))
            await interaction.edit_original_response(embed=embed, view=AlertSettingsMenuView())


class CreateAlert8HButton(Button):
    """Create 8-hour alert"""

    def __init__(self):
        super().__init__(label="8 Hour Alert", style=BotStyles.PRIMARY)

    async def callback(self, interaction: discord.Interaction):
        from ..database.db import Database
        from os import environ

        try:
            await interaction.response.edit_message(
                embed=create_loading_embed("Creating Alert", "Setting up 8-hour uptime alert..."),
                view=None
            )

            db = Database(environ.get('DB_PATH', '/data/ec2bot.db'))
            alert_id = await db.create_alert_config(
                alert_name="8 Hour Uptime Warning",
                threshold_hours=8,
                reminder_interval_hours=4
            )

            embed = create_success_embed(
                "Alert Created",
                f"8-hour uptime alert created successfully!\n\n"
                f"**Alert ID**: {alert_id}\n"
                f"**Threshold**: 8 hours\n"
                f"**Reminders**: Every 4 hours"
            )

            await interaction.edit_original_response(embed=embed, view=AlertSettingsMenuView())

        except Exception as e:
            embed = create_error_embed("Failed to Create Alert", str(e))
            await interaction.edit_original_response(embed=embed, view=AlertSettingsMenuView())


class CreateAlert24HButton(Button):
    """Create 24-hour alert"""

    def __init__(self):
        super().__init__(label="24 Hour Alert", style=BotStyles.PRIMARY)

    async def callback(self, interaction: discord.Interaction):
        from ..database.db import Database
        from os import environ

        try:
            await interaction.response.edit_message(
                embed=create_loading_embed("Creating Alert", "Setting up 24-hour uptime alert..."),
                view=None
            )

            db = Database(environ.get('DB_PATH', '/data/ec2bot.db'))
            alert_id = await db.create_alert_config(
                alert_name="24 Hour Uptime Warning",
                threshold_hours=24,
                reminder_interval_hours=6
            )

            embed = create_success_embed(
                "Alert Created",
                f"24-hour uptime alert created successfully!\n\n"
                f"**Alert ID**: {alert_id}\n"
                f"**Threshold**: 24 hours\n"
                f"**Reminders**: Every 6 hours"
            )

            await interaction.edit_original_response(embed=embed, view=AlertSettingsMenuView())

        except Exception as e:
            embed = create_error_embed("Failed to Create Alert", str(e))
            await interaction.edit_original_response(embed=embed, view=AlertSettingsMenuView())
