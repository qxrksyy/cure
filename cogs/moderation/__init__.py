from .moderation import Moderation
from .kick_commands import KickCommands
from .advanced_moderation import AdvancedModeration
from .purge_commands import PurgeCommands
from .purge_commands2 import PurgeCommands2
from .lockdown_commands import LockdownCommands
from .role_commands import RoleCommands
from .member_restrictions import MemberRestrictions
from .raid_protection import RaidProtection
from .command_restrictions import CommandRestrictions
from .reminder_commands import ReminderCommands
from .mod_utils import ModUtils
from .channel_commands import ChannelCommands

async def setup(bot):
    await bot.add_cog(Moderation(bot))
    await bot.add_cog(KickCommands(bot))
    await bot.add_cog(AdvancedModeration(bot))
    await bot.add_cog(PurgeCommands(bot))
    await bot.add_cog(PurgeCommands2(bot))
    await bot.add_cog(LockdownCommands(bot))
    await bot.add_cog(RoleCommands(bot))
    await bot.add_cog(MemberRestrictions(bot))
    await bot.add_cog(RaidProtection(bot))
    await bot.add_cog(CommandRestrictions(bot))
    await bot.add_cog(ReminderCommands(bot))
    await bot.add_cog(ModUtils(bot))
    await bot.add_cog(ChannelCommands(bot)) 