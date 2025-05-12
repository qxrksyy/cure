import discord
from discord.ext import commands
import asyncio
from datetime import datetime, timedelta
import logging
from collections import defaultdict, deque

logger = logging.getLogger('bot')

class MassJoinHandler:
    """Handles detection and response to mass joins"""
    
    def __init__(self, antiraid_cog):
        self.antiraid_cog = antiraid_cog
        self.bot = antiraid_cog.bot
        # Tracks recent joins per guild {guild_id: deque([(member, join_time), ...]), ...}
        self.recent_joins = defaultdict(lambda: deque(maxlen=100))
        # Tracks if a guild is already in lockdown
        self.guild_lockdowns = set()
        
    async def handle_member_join(self, member):
        """Process a member join event to detect potential raid"""
        guild_id = str(member.guild.id)
        settings = self.antiraid_cog._get_guild_settings(guild_id)
        raid_state = self.antiraid_cog._get_guild_raid_state(guild_id)
        
        # Skip if mass join detection is disabled or raid mode is already active
        if not settings["massjoin"]["enabled"] or raid_state["active"]:
            return
            
        # Add this join to recent joins
        self.recent_joins[guild_id].append((member, datetime.utcnow()))
        
        # Check for potential raid
        await self._check_mass_join(member.guild)
        
    async def _check_mass_join(self, guild):
        """Check if there's an ongoing mass join raid"""
        guild_id = str(guild.id)
        settings = self.antiraid_cog._get_guild_settings(guild_id)
        
        # Don't check if already in lockdown
        if guild_id in self.guild_lockdowns:
            return
            
        # Get settings
        threshold = settings["massjoin"]["threshold"]
        timeframe = settings["massjoin"]["timeframe"]
        action = settings["massjoin"]["action"]
        
        # Calculate joins within timeframe
        now = datetime.utcnow()
        timeframe_cutoff = now - timedelta(seconds=timeframe)
        
        # Count joins within timeframe
        recent_joins_count = sum(1 for _, join_time in self.recent_joins[guild_id] 
                              if join_time >= timeframe_cutoff)
        
        # If threshold exceeded, take action
        if recent_joins_count >= threshold:
            logger.warning(f"Mass join detected in {guild.name} ({guild.id}): {recent_joins_count} joins in {timeframe}s")
            
            if action == "lockdown":
                await self._activate_lockdown(guild, recent_joins_count, timeframe)
            elif action == "verification":
                await self._activate_verification(guild, recent_joins_count, timeframe)
    
    async def _activate_lockdown(self, guild, join_count, timeframe):
        """Put guild in lockdown due to mass join detection"""
        guild_id = str(guild.id)
        
        # Set raid state
        raid_state = self.antiraid_cog._get_guild_raid_state(guild_id)
        raid_state["active"] = True
        raid_state["started_at"] = datetime.utcnow().isoformat()
        raid_state["reason"] = f"Mass join detected: {join_count} joins in {timeframe}s"
        self.antiraid_cog._save_settings()
        
        # Mark as in lockdown
        self.guild_lockdowns.add(guild_id)
        
        # Try to notify in system channel or first writeable channel
        embed = discord.Embed(
            title="⚠️ RAID PROTECTION ACTIVATED",
            description=f"Mass join detected: {join_count} joins in {timeframe} seconds",
            color=discord.Color.red(),
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(
            name="Action Taken", 
            value="Server is now in lockdown mode. New members will be automatically kicked.", 
            inline=False
        )
        
        embed.add_field(
            name="To Disable", 
            value="When the raid is over, server admins can run `antiraid state` to disable raid protection.", 
            inline=False
        )
        
        # Try to send notification to system channel first
        notification_sent = False
        if guild.system_channel and guild.system_channel.permissions_for(guild.me).send_messages:
            try:
                await guild.system_channel.send(embed=embed)
                notification_sent = True
            except Exception as e:
                logger.error(f"Failed to send raid notification to system channel: {str(e)}")
        
        # If that fails, try to find another channel
        if not notification_sent:
            for channel in guild.text_channels:
                if channel.permissions_for(guild.me).send_messages:
                    try:
                        await channel.send(embed=embed)
                        break
                    except Exception as e:
                        continue
        
        # Schedule lockdown release after 30 minutes if not manually disabled
        self.bot.loop.create_task(self._auto_release_lockdown(guild))
    
    async def _activate_verification(self, guild, join_count, timeframe):
        """Enable verification mode for new users due to mass join detection"""
        guild_id = str(guild.id)
        
        # Get default role to adjust permissions
        default_role = guild.default_role
        
        # Set raid state
        raid_state = self.antiraid_cog._get_guild_raid_state(guild_id)
        raid_state["active"] = True
        raid_state["started_at"] = datetime.utcnow().isoformat()
        raid_state["reason"] = f"Mass join detected: {join_count} joins in {timeframe}s"
        self.antiraid_cog._save_settings()
        
        # Mark as in lockdown
        self.guild_lockdowns.add(guild_id)
        
        # Notification embed
        embed = discord.Embed(
            title="⚠️ RAID PROTECTION ACTIVATED",
            description=f"Mass join detected: {join_count} joins in {timeframe} seconds",
            color=discord.Color.orange(),
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(
            name="Action Taken", 
            value="Server is now in verification mode. New members will need extra verification.", 
            inline=False
        )
        
        embed.add_field(
            name="To Disable", 
            value="When the raid is over, server admins can run `antiraid state` to disable raid protection.", 
            inline=False
        )
        
        # Try to send notification to system channel first
        notification_sent = False
        if guild.system_channel and guild.system_channel.permissions_for(guild.me).send_messages:
            try:
                await guild.system_channel.send(embed=embed)
                notification_sent = True
            except Exception as e:
                logger.error(f"Failed to send raid notification to system channel: {str(e)}")
        
        # If that fails, try to find another channel
        if not notification_sent:
            for channel in guild.text_channels:
                if channel.permissions_for(guild.me).send_messages:
                    try:
                        await channel.send(embed=embed)
                        break
                    except Exception as e:
                        continue
        
        # Schedule verification mode release after 30 minutes if not manually disabled
        self.bot.loop.create_task(self._auto_release_lockdown(guild))
    
    async def _auto_release_lockdown(self, guild):
        """Automatically release lockdown after 30 minutes"""
        guild_id = str(guild.id)
        
        # Wait 30 minutes
        await asyncio.sleep(1800)  # 30 minutes
        
        # Check if still in lockdown
        raid_state = self.antiraid_cog._get_guild_raid_state(guild_id)
        if guild_id in self.guild_lockdowns and raid_state["active"]:
            # Auto-release lockdown
            raid_state["active"] = False
            raid_state["started_at"] = None
            raid_state["reason"] = None
            self.antiraid_cog._save_settings()
            
            # Remove from lockdowns
            self.guild_lockdowns.discard(guild_id)
            
            # Notification embed
            embed = discord.Embed(
                title="Raid Protection Deactivated",
                description="Raid protection has been automatically disabled after the timeout period.",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            
            # Try to send notification
            notification_sent = False
            if guild.system_channel and guild.system_channel.permissions_for(guild.me).send_messages:
                try:
                    await guild.system_channel.send(embed=embed)
                    notification_sent = True
                except Exception:
                    pass
            
            # If that fails, try to find another channel
            if not notification_sent:
                for channel in guild.text_channels:
                    if channel.permissions_for(guild.me).send_messages:
                        try:
                            await channel.send(embed=embed)
                            break
                        except Exception:
                            continue

async def setup(bot):
    # This is not a cog by itself, but a helper class used by the antiraid cog
    pass 