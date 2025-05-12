import discord
from discord.ext import commands

def has_any_of(*checks):
    """
    A custom check that passes if any of the given checks pass.
    Usage:
        @commands.has_any_of(commands.has_permissions(administrator=True), commands.has_role("Role Name"))
    """
    async def predicate(ctx):
        for check in checks:
            try:
                if await check(ctx):
                    return True
            except:
                continue
        return False
    return commands.check(predicate)

# Add this to discord.ext.commands namespace
commands.has_any_of = has_any_of 