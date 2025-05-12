import discord
from discord.ext import commands
import logging

logger = logging.getLogger('bot')

class CounterEvents(commands.Cog):
    """Events for updating counters in real-time"""
    
    def __init__(self, bot, counters_cog):
        self.bot = bot
        self.counters = counters_cog
    
    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Update member count when a member joins"""
        try:
            # Get all counters for this guild
            guild_counters = self.counters._get_guild_counters(member.guild.id)
            
            # Find member count counters
            for counter in guild_counters:
                if counter["type"] == "members":
                    await self.counters._update_counter(member.guild, counter)
        except Exception as e:
            logger.error(f"Error updating counter on member join: {str(e)}")
    
    @commands.Cog.listener()
    async def on_member_remove(self, member):
        """Update member count when a member leaves"""
        try:
            # Get all counters for this guild
            guild_counters = self.counters._get_guild_counters(member.guild.id)
            
            # Find member count counters
            for counter in guild_counters:
                if counter["type"] == "members":
                    await self.counters._update_counter(member.guild, counter)
        except Exception as e:
            logger.error(f"Error updating counter on member remove: {str(e)}")
    
    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        """Update booster count if a member's boost status changes"""
        # Check if the premium status changed
        if before.premium_since != after.premium_since:
            try:
                # Get all counters for this guild
                guild_counters = self.counters._get_guild_counters(after.guild.id)
                
                # Find booster count counters
                for counter in guild_counters:
                    if counter["type"] == "boosters":
                        await self.counters._update_counter(after.guild, counter)
            except Exception as e:
                logger.error(f"Error updating counter on boost status change: {str(e)}")

async def setup(bot, counters_cog):
    await bot.add_cog(CounterEvents(bot, counters_cog)) 