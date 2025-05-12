from .tiktok_commands import TikTokCommands

async def setup(bot):
    await bot.add_cog(TikTokCommands(bot)) 