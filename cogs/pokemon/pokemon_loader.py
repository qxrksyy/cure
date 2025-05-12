import discord
from discord.ext import commands
import logging

logger = logging.getLogger('bot')

class PokemonLoader(commands.Cog):
    """Loader for Pokemon - loads the pokemon module with renamed commands"""
    
    def __init__(self, bot):
        self.bot = bot
        
    @commands.Cog.listener()
    async def on_ready(self):
        """When bot is ready, try to load the pokemon module with renamed commands"""
        await self.load_pokemon_module()
        
    async def load_pokemon_module(self):
        """Load the pokemon module with renamed commands"""
        try:
            # Import the pokemon module
            from .pokemon import PokemonCog
            
            # Create a modified version of the cog
            pokemon_cog = PokemonCog(self.bot)
            
            # Rename conflicting commands before adding the cog
            for command in list(pokemon_cog.__cog_commands__):
                if command.name == "buy":
                    command.name = "pokebuy"
                elif command.name == "shop":
                    command.name = "pokeshop"
                    
            # Add the modified cog
            await self.bot.add_cog(pokemon_cog)
            logger.info("Successfully loaded pokemon module via loader with renamed commands")
            
        except Exception as e:
            logger.error(f"Error loading pokemon module: {str(e)}")
                
async def setup(bot):
    await bot.add_cog(PokemonLoader(bot)) 