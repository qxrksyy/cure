import os
import logging
import aiosqlite
import datetime

logger = logging.getLogger('bot')

class BumperDB:
    """Handles database operations for the BumpReminder module"""
    
    def __init__(self):
        self.data_folder = 'data'
        self.db_path = os.path.join(self.data_folder, 'bumper.db')
        
    async def initialize(self):
        """Initialize the BumpReminder database"""
        if not os.path.exists(self.data_folder):
            os.makedirs(self.data_folder)
            
        async with aiosqlite.connect(self.db_path) as db:
            # Create server settings table
            await db.execute('''
                CREATE TABLE IF NOT EXISTS bumper_settings (
                    guild_id TEXT PRIMARY KEY,
                    channel_id TEXT,
                    autoclean BOOLEAN DEFAULT FALSE,
                    autolock BOOLEAN DEFAULT FALSE,
                    reminder_message TEXT DEFAULT 'Time to bump the server! Type /bump',
                    thankyou_message TEXT DEFAULT 'Thanks for bumping the server! I will remind you in 2 hours.',
                    next_bump TIMESTAMP,
                    last_bumped TIMESTAMP,
                    last_user_id TEXT,
                    enabled BOOLEAN DEFAULT TRUE
                )
            ''')
            
            # Create bump logs table
            await db.execute('''
                CREATE TABLE IF NOT EXISTS bump_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id TEXT,
                    user_id TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (guild_id) REFERENCES bumper_settings(guild_id)
                )
            ''')
            
            await db.commit()
    
    async def get_guild_settings(self, guild_id):
        """Get a guild's BumpReminder settings"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(
                    "SELECT * FROM bumper_settings WHERE guild_id = ?",
                    (str(guild_id),)
                ) as cursor:
                    result = await cursor.fetchone()
                    if result:
                        return dict(result)
                    return None
        except Exception as e:
            logger.error(f"Error getting guild BumpReminder settings: {e}")
            return None
            
    async def create_or_update_guild(self, guild_id, **kwargs):
        """Create or update a guild's BumpReminder settings"""
        try:
            settings = await self.get_guild_settings(guild_id)
            
            async with aiosqlite.connect(self.db_path) as db:
                if not settings:
                    # Create new settings
                    placeholders = ", ".join(["?"] * (len(kwargs) + 1))
                    columns = "guild_id, " + ", ".join(kwargs.keys())
                    values = [str(guild_id)] + list(kwargs.values())
                    
                    await db.execute(
                        f"INSERT INTO bumper_settings ({columns}) VALUES ({placeholders})",
                        values
                    )
                else:
                    # Update existing settings
                    set_clause = ", ".join([f"{key} = ?" for key in kwargs.keys()])
                    values = list(kwargs.values()) + [str(guild_id)]
                    
                    await db.execute(
                        f"UPDATE bumper_settings SET {set_clause} WHERE guild_id = ?",
                        values
                    )
                
                await db.commit()
                return True
        except Exception as e:
            logger.error(f"Error updating guild BumpReminder settings: {e}")
            return False
    
    async def set_channel(self, guild_id, channel_id):
        """Set the channel for BumpReminder"""
        return await self.create_or_update_guild(guild_id, channel_id=channel_id)
    
    async def set_autoclean(self, guild_id, enabled):
        """Enable or disable auto-clean feature"""
        return await self.create_or_update_guild(guild_id, autoclean=enabled)
    
    async def set_autolock(self, guild_id, enabled):
        """Enable or disable auto-lock feature"""
        return await self.create_or_update_guild(guild_id, autolock=enabled)
    
    async def set_reminder_message(self, guild_id, message):
        """Set the reminder message"""
        return await self.create_or_update_guild(guild_id, reminder_message=message)
    
    async def set_thankyou_message(self, guild_id, message):
        """Set the thank you message"""
        return await self.create_or_update_guild(guild_id, thankyou_message=message)
    
    async def log_bump(self, guild_id, user_id):
        """Log a bump and update next bump time"""
        try:
            now = datetime.datetime.now()
            next_bump = now + datetime.timedelta(hours=2)
            
            async with aiosqlite.connect(self.db_path) as db:
                # Update guild settings
                await db.execute(
                    "UPDATE bumper_settings SET last_bumped = ?, next_bump = ?, last_user_id = ? WHERE guild_id = ?",
                    (now.isoformat(), next_bump.isoformat(), str(user_id), str(guild_id))
                )
                
                # Add bump log
                await db.execute(
                    "INSERT INTO bump_logs (guild_id, user_id) VALUES (?, ?)",
                    (str(guild_id), str(user_id))
                )
                
                await db.commit()
                return True
        except Exception as e:
            logger.error(f"Error logging bump: {e}")
            return False
    
    async def get_due_reminders(self):
        """Get all guilds that are due for a bump reminder"""
        try:
            now = datetime.datetime.now().isoformat()
            
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(
                    "SELECT * FROM bumper_settings WHERE next_bump <= ? AND enabled = TRUE",
                    (now,)
                ) as cursor:
                    results = await cursor.fetchall()
                    return [dict(result) for result in results]
        except Exception as e:
            logger.error(f"Error getting due reminders: {e}")
            return []
    
    async def get_bump_stats(self, guild_id, days=30):
        """Get bump statistics for a guild"""
        try:
            cutoff_date = (datetime.datetime.now() - datetime.timedelta(days=days)).isoformat()
            
            async with aiosqlite.connect(self.db_path) as db:
                # Get total bumps
                async with db.execute(
                    "SELECT COUNT(*) FROM bump_logs WHERE guild_id = ? AND timestamp >= ?",
                    (str(guild_id), cutoff_date)
                ) as cursor:
                    total_bumps = (await cursor.fetchone())[0]
                
                # Get top bumpers
                db.row_factory = aiosqlite.Row
                async with db.execute(
                    """
                    SELECT user_id, COUNT(*) as count
                    FROM bump_logs
                    WHERE guild_id = ? AND timestamp >= ?
                    GROUP BY user_id
                    ORDER BY count DESC
                    LIMIT 10
                    """,
                    (str(guild_id), cutoff_date)
                ) as cursor:
                    top_bumpers = [dict(row) for row in await cursor.fetchall()]
                
                return {
                    "total_bumps": total_bumps,
                    "top_bumpers": top_bumpers
                }
        except Exception as e:
            logger.error(f"Error getting bump stats: {e}")
            return {"total_bumps": 0, "top_bumpers": []}
    
    async def enable_reminder(self, guild_id, enabled=True):
        """Enable or disable the bump reminder for a guild"""
        return await self.create_or_update_guild(guild_id, enabled=enabled)

async def setup(bot):
    # This is a database module, no cog to add
    pass 