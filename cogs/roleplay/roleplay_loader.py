import discord
from discord.ext import commands
import logging

logger = logging.getLogger('bot')

class RoleplayLoader(commands.Cog):
    """Loader for Roleplay - loads the roleplay module with renamed commands"""
    
    def __init__(self, bot):
        self.bot = bot
        
    @commands.Cog.listener()
    async def on_ready(self):
        """When bot is ready, try to load the roleplay module with renamed commands"""
        await self.load_roleplay_module()
        
    async def load_roleplay_module(self):
        """Load the roleplay module with renamed commands"""
        try:
            # Import the roleplay module
            from .roleplay import RoleplayCog
            
            # Create a modified version of the cog
            roleplay_cog = RoleplayCog(self.bot)
            
            # Rename conflicting commands - these are the ones that conflict with emotion_commands.py
            conflicting_commands = ["pat", "hug", "kiss", "slap", "cuddle", "poke"]
            
            # Rename conflicting commands before adding the cog
            for command in list(roleplay_cog.__cog_commands__):
                if command.name in conflicting_commands:
                    command.name = "rp_" + command.name
                    
            # Add the modified cog
            await self.bot.add_cog(roleplay_cog)
            logger.info("Successfully loaded roleplay module via loader with renamed commands")
            
        except Exception as e:
            logger.error(f"Error loading roleplay module: {str(e)}")
                
async def setup(bot):
    await bot.add_cog(RoleplayLoader(bot)) 