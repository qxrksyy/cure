import discord
from discord.ext import commands
import logging

logger = logging.getLogger('bot')

class CounterEventsLoader(commands.Cog):
    """Loader for CounterEvents - loads the events after the Counters cog is ready"""
    
    def __init__(self, bot):
        self.bot = bot
        self.counters_cog = None
        
    @commands.Cog.listener()
    async def on_ready(self):
        """When bot is ready, try to load the events extension"""
        # Wait a few seconds to ensure the Counters cog is loaded
        await self.load_counter_events()
        
    async def load_counter_events(self):
        """Load the events extension with the Counters cog dependency"""
        try:
            # Get the Counters cog
            self.counters_cog = self.bot.get_cog("Counters")
            
            if self.counters_cog:
                # Load the extension with the counters_cog parameter
                from .events import setup
                await setup(self.bot, self.counters_cog)
                logger.info("Successfully loaded counter events via loader")
            else:
                logger.warning("Could not load counter events: Counters cog not found")
        except Exception as e:
            logger.error(f"Error loading counter events: {str(e)}")
                
async def setup(bot):
    await bot.add_cog(CounterEventsLoader(bot)) 