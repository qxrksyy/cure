# Roleplay module for QxrK Discord Bot
# This module provides various roleplay emotion commands

from .roleplay import Roleplay

async def setup(bot):
    # Load roleplay cog
    await bot.add_cog(Roleplay(bot))
    
    # Log successful loading
    try:
        bot.logger.info("Loaded Roleplay extension")
    except:
        # Fallback to standard logging if bot.logger is not available
        import logging
        logger = logging.getLogger('bot')
        logger.info("Loaded Roleplay extension") 