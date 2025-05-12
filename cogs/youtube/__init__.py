from .youtube_commands import YouTubeCommands
from .twitch_commands import TwitchCommands

async def setup(bot):
    await bot.add_cog(YouTubeCommands(bot))
    await bot.add_cog(TwitchCommands(bot)) 