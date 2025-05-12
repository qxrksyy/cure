from .ticket_commands import TicketCommands

async def setup(bot):
    await bot.add_cog(TicketCommands(bot)) 