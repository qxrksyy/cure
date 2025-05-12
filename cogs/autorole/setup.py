import discord
from discord.ext import commands
import logging

# Import all autorole components
from .autorole import AutoRole
from .button_roles import ButtonRoles
from .reaction_roles import ReactionRoles

logger = logging.getLogger('bot')

async def setup(bot):
    # Load all autorole components, only if they don't already exist
    if not bot.get_cog("AutoRole"):
        await bot.add_cog(AutoRole(bot))
    
    if not bot.get_cog("ButtonRoles"):
        await bot.add_cog(ButtonRoles(bot))
    
    if not bot.get_cog("ReactionRoles"):
        await bot.add_cog(ReactionRoles(bot))
    
    logger.info("Loaded AutoRole extension with components that weren't already loaded") 