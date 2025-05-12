from .x_commands import XCommands

async def setup(bot):
    await bot.add_cog(XCommands(bot)) 