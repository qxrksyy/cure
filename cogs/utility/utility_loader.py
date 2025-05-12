import discord
from discord.ext import commands
import logging

logger = logging.getLogger('bot')

class UtilityLoader(commands.Cog):
    """Loader for Utility - loads the utility module with renamed commands"""
    
    def __init__(self, bot):
        self.bot = bot
        
    @commands.Cog.listener()
    async def on_ready(self):
        """When bot is ready, try to load the utility module with renamed commands"""
        await self.load_utility_module()
        
    async def load_utility_module(self):
        """Load the utility module with renamed commands"""
        try:
            # Import the utility module
            from .utility import Utility
            
            # Create a modified version of the cog
            utility_cog = Utility(self.bot)
            
            # Rename conflicting commands before adding the cog
            for command in list(utility_cog.__cog_commands__):
                if command.name == "serverinfo":
                    command.name = "server_info"
                elif command.name == "userinfo":
                    command.name = "user_info"
                elif command.name == "avatar":
                    command.name = "user_avatar"
                    
            # Add the modified cog
            await self.bot.add_cog(utility_cog)
            logger.info("Successfully loaded utility module via loader with renamed commands")
            
        except Exception as e:
            logger.error(f"Error loading utility module: {str(e)}")
                
async def setup(bot):
    await bot.add_cog(UtilityLoader(bot)) 