import discord
from discord.ext import commands
import logging

logger = logging.getLogger('bot')

class SpotifyLoader(commands.Cog):
    """Loader for Spotify - loads the spotify module with renamed commands"""
    
    def __init__(self, bot):
        self.bot = bot
        
    @commands.Cog.listener()
    async def on_ready(self):
        """When bot is ready, try to load the spotify module with renamed commands"""
        await self.load_spotify_module()
        
    async def load_spotify_module(self):
        """Load the spotify module with renamed commands"""
        try:
            # Import the spotify module
            from .spotify import SpotifyCog
            
            # Create a modified version of the cog
            spotify_cog = SpotifyCog(self.bot)
            
            # Rename conflicting commands before adding the cog
            for command in list(spotify_cog.__cog_commands__):
                if command.name == "queue":
                    command.name = "spotify_queue"
                elif command.name == "play":
                    command.name = "spotify_play"
                elif command.name == "pause":
                    command.name = "spotify_pause"
                elif command.name == "skip":
                    command.name = "spotify_skip"
                elif command.name == "volume":
                    command.name = "spotify_volume"
                    
            # Add the modified cog
            await self.bot.add_cog(spotify_cog)
            logger.info("Successfully loaded spotify module via loader with renamed commands")
            
        except Exception as e:
            logger.error(f"Error loading spotify module: {str(e)}")
                
async def setup(bot):
    await bot.add_cog(SpotifyLoader(bot)) 