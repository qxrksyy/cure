# AutoPfp module for QxrK Discord Bot
# This module provides auto profile picture and banner channels

from .autopfp import AutoPfp

async def setup(bot):
    # Load autopfp cog
    await bot.add_cog(AutoPfp(bot))
    
    # Log successful loading
    bot.logger.info("Loaded AutoPfp extension") 