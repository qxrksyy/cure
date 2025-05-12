import discord
from discord.ext import commands
import logging

logger = logging.getLogger('bot')

class ModuleCommandsLoader(commands.Cog):
    """Loader for ModuleCommands - loads the commands after the AntiNuke cog is ready"""
    
    def __init__(self, bot):
        self.bot = bot
        self.antinuke_cog = None
        
    @commands.Cog.listener()
    async def on_ready(self):
        """When bot is ready, try to load the module_commands extension"""
        # Wait a few seconds to ensure the AntiNuke cog is loaded
        await self.load_module_commands()
        
    async def load_module_commands(self):
        """Load the module_commands extension with the AntiNuke cog dependency"""
        try:
            # Get the AntiNuke cog
            self.antinuke_cog = self.bot.get_cog("AntiNuke")
            
            if self.antinuke_cog:
                # Load the extension with the antinuke_cog parameter
                from .module_commands import setup
                await setup(self.bot, self.antinuke_cog)
                logger.info("Successfully loaded module_commands via loader")
            else:
                logger.warning("Could not load module_commands: AntiNuke cog not found")
        except Exception as e:
            logger.error(f"Error loading module_commands: {str(e)}")
                
async def setup(bot):
    await bot.add_cog(ModuleCommandsLoader(bot)) 