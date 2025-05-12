# Counters module for QxrK Discord Bot
# This module provides channel and category counters for member and booster counts

from .counters import Counters
from .events import CounterEvents, setup as setup_events

async def setup(bot):
    # First load the main Counters cog
    counters_cog = Counters(bot)
    await bot.add_cog(counters_cog)
    
    # Then load the events cog, passing the counters cog as a reference
    await setup_events(bot, counters_cog) 