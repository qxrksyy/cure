import discord
from discord.ext import commands
import logging

logger = logging.getLogger('bot')

class ModerationLoader(commands.Cog):
    """Loader for Moderation - loads the moderation module with renamed commands"""
    
    def __init__(self, bot):
        self.bot = bot
        
    @commands.Cog.listener()
    async def on_ready(self):
        """When bot is ready, try to load the moderation module with renamed commands"""
        await self.load_moderation_module()
        
    async def load_moderation_module(self):
        """Load the moderation module with renamed commands"""
        try:
            # Import the moderation module
            from .moderation import ModerationCog
            
            # Create a modified version of the cog
            mod_cog = ModerationCog(self.bot)
            
            # Rename conflicting commands before adding the cog
            # Find commands that might conflict and rename them
            for command in list(mod_cog.__cog_commands__):
                if command.name == "kick":
                    command.name = "mod_kick"
                elif command.name == "ban":
                    command.name = "mod_ban"
                elif command.name == "mute":
                    command.name = "mod_mute"
                    
            # Add the modified cog
            await self.bot.add_cog(mod_cog)
            logger.info("Successfully loaded moderation module via loader with renamed commands")
            
        except Exception as e:
            logger.error(f"Error loading moderation module: {str(e)}")
                
async def setup(bot):
    await bot.add_cog(ModerationLoader(bot)) 