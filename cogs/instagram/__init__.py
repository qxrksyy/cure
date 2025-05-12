from .instagram_commands import InstagramCommands

async def setup(bot):
    await bot.add_cog(InstagramCommands(bot)) 