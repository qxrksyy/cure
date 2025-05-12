# Servers module for QxrK Discord Bot
# This module provides server management features including pin archival, image-only channels,
# fake permissions, and various filter systems

from .pins import PinArchive
from .imageonly import ImageOnly
from .permissions import FakePermissions
from .filters import ServerFilters

async def setup(bot):
    # Load all server management cogs
    await bot.add_cog(PinArchive(bot))
    await bot.add_cog(ImageOnly(bot))
    await bot.add_cog(FakePermissions(bot))
    await bot.add_cog(ServerFilters(bot))
    
    # Log successful loading
    try:
        bot.logger.info("Loaded Servers extension")
    except:
        # Fallback to standard logging if bot.logger is not available
        import logging
        logger = logging.getLogger('bot')
        logger.info("Loaded Servers extension") 