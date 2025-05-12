# Miscellaneous module for QxrK Discord Bot
# This module provides various utility commands that don't fit into other categories

from .utils import MiscUtils
from .ping import PingTools
from .embed import EmbedManager
from .history import UserHistory
from .information import Information

async def setup(bot):
    # Load all miscellaneous cogs
    await bot.add_cog(MiscUtils(bot))
    await bot.add_cog(PingTools(bot))
    await bot.add_cog(EmbedManager(bot))
    await bot.add_cog(UserHistory(bot))
    await bot.add_cog(Information(bot))
    
    # Log successful loading
    try:
        bot.logger.info("Loaded Miscellaneous extension")
    except:
        # Fallback to standard logging if bot.logger is not available
        import logging
        logger = logging.getLogger('bot')
        logger.info("Loaded Miscellaneous extension") 