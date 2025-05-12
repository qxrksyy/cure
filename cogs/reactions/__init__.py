# Reactions module for QxrK Discord Bot
# This module provides both emotion and auto reactions functionality

import logging
from .emotion_commands import EmotionCommands
from .auto_reactions import AutoReactions

logger = logging.getLogger('bot')

async def setup(bot):
    # Load all reaction components
    await bot.add_cog(EmotionCommands(bot))
    await bot.add_cog(AutoReactions(bot))
    
    logger.info("Loaded Reactions extension with all components") 