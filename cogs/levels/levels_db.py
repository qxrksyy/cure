import os
import logging
import aiosqlite
import datetime
import json
import random
import math

logger = logging.getLogger('bot')

class LevelsDB:
    """Handles database operations for the Levels module"""
    
    def __init__(self):
        self.data_folder = 'data'
        self.db_path = os.path.join(self.data_folder, 'levels.db')
        
    async def initialize(self):
        """Initialize the Levels database"""
        if not os.path.exists(self.data_folder):
            os.makedirs(self.data_folder)
            
        async with aiosqlite.connect(self.db_path) as db:
            # Create guild settings table
            await db.execute('''
                CREATE TABLE IF NOT EXISTS levels_settings (
                    guild_id TEXT PRIMARY KEY,
                    enabled BOOLEAN DEFAULT TRUE,
                    stack_roles BOOLEAN DEFAULT FALSE,
                    message_mode TEXT DEFAULT 'channel',
                    level_up_message TEXT DEFAULT 'Congratulations {user}, you reached level {level}!',
                    xp_rate REAL DEFAULT 1.0
                )
            ''')
            
            # Create user levels table
            await db.execute('''
                CREATE TABLE IF NOT EXISTS user_levels (
                    guild_id TEXT,
                    user_id TEXT,
                    level INTEGER DEFAULT 1,
                    xp INTEGER DEFAULT 0,
                    messages_since_xp INTEGER DEFAULT 0,
                    last_xp_earned TIMESTAMP,
                    show_messages BOOLEAN DEFAULT TRUE,
                    PRIMARY KEY (guild_id, user_id)
                )
            ''')
            
            # Create level roles table
            await db.execute('''
                CREATE TABLE IF NOT EXISTS level_roles (
                    guild_id TEXT,
                    level INTEGER,
                    role_id TEXT,
                    PRIMARY KEY (guild_id, level)
                )
            ''')
            
            # Create ignored channels and roles table
            await db.execute('''
                CREATE TABLE IF NOT EXISTS level_ignores (
                    guild_id TEXT,
                    entity_id TEXT,
                    entity_type TEXT,
                    PRIMARY KEY (guild_id, entity_id)
                )
            ''')
            
            await db.commit()
    
    async def get_guild_settings(self, guild_id):
        """Get a guild's levels settings"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(
                    "SELECT * FROM levels_settings WHERE guild_id = ?",
                    (str(guild_id),)
                ) as cursor:
                    result = await cursor.fetchone()
                    if result:
                        return dict(result)
                    
                    # Create default settings if they don't exist
                    await db.execute(
                        "INSERT INTO levels_settings (guild_id) VALUES (?)",
                        (str(guild_id),)
                    )
                    await db.commit()
                    
                    # Return default settings
                    return {
                        "guild_id": str(guild_id),
                        "enabled": True,
                        "stack_roles": False,
                        "message_mode": "channel",
                        "level_up_message": "Congratulations {user}, you reached level {level}!",
                        "xp_rate": 1.0
                    }
        except Exception as e:
            logger.error(f"Error getting guild levels settings: {e}")
            return None
    
    async def update_guild_setting(self, guild_id, setting, value):
        """Update a guild's levels setting"""
        try:
            settings = await self.get_guild_settings(guild_id)
            if not settings:
                return False
                
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    f"UPDATE levels_settings SET {setting} = ? WHERE guild_id = ?",
                    (value, str(guild_id))
                )
                await db.commit()
                return True
        except Exception as e:
            logger.error(f"Error updating guild levels setting: {e}")
            return False
    
    async def enable_leveling(self, guild_id, enabled=True):
        """Enable or disable the leveling system"""
        return await self.update_guild_setting(guild_id, "enabled", enabled)
    
    async def set_stack_roles(self, guild_id, stack=True):
        """Enable or disable role stacking"""
        return await self.update_guild_setting(guild_id, "stack_roles", stack)
    
    async def set_message_mode(self, guild_id, mode):
        """Set the message mode for level up messages"""
        valid_modes = ["channel", "dm", "off"]
        if mode.lower() not in valid_modes:
            return False
        return await self.update_guild_setting(guild_id, "message_mode", mode.lower())
    
    async def set_level_up_message(self, guild_id, message):
        """Set the level up message"""
        return await self.update_guild_setting(guild_id, "level_up_message", message)
    
    async def set_xp_rate(self, guild_id, rate):
        """Set the XP rate multiplier"""
        try:
            rate_float = float(rate)
            if rate_float <= 0:
                return False
            return await self.update_guild_setting(guild_id, "xp_rate", rate_float)
        except ValueError:
            return False
    
    async def add_level_role(self, guild_id, level, role_id):
        """Add a role reward for a level"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "INSERT OR REPLACE INTO level_roles (guild_id, level, role_id) VALUES (?, ?, ?)",
                    (str(guild_id), level, str(role_id))
                )
                await db.commit()
                return True
        except Exception as e:
            logger.error(f"Error adding level role: {e}")
            return False
    
    async def remove_level_role(self, guild_id, level):
        """Remove a role reward for a level"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "DELETE FROM level_roles WHERE guild_id = ? AND level = ?",
                    (str(guild_id), level)
                )
                await db.commit()
                return True
        except Exception as e:
            logger.error(f"Error removing level role: {e}")
            return False
    
    async def get_level_roles(self, guild_id):
        """Get all level roles for a guild"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(
                    "SELECT level, role_id FROM level_roles WHERE guild_id = ? ORDER BY level",
                    (str(guild_id),)
                ) as cursor:
                    results = await cursor.fetchall()
                    return [(row['level'], row['role_id']) for row in results]
        except Exception as e:
            logger.error(f"Error getting level roles: {e}")
            return []
    
    async def ignore_entity(self, guild_id, entity_id, entity_type):
        """Ignore a channel or role for XP gain"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "INSERT OR REPLACE INTO level_ignores (guild_id, entity_id, entity_type) VALUES (?, ?, ?)",
                    (str(guild_id), str(entity_id), entity_type)
                )
                await db.commit()
                return True
        except Exception as e:
            logger.error(f"Error ignoring entity: {e}")
            return False
    
    async def unignore_entity(self, guild_id, entity_id):
        """Unignore a channel or role for XP gain"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "DELETE FROM level_ignores WHERE guild_id = ? AND entity_id = ?",
                    (str(guild_id), str(entity_id))
                )
                await db.commit()
                return True
        except Exception as e:
            logger.error(f"Error unignoring entity: {e}")
            return False
    
    async def get_ignored_entities(self, guild_id):
        """Get all ignored channels and roles for a guild"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(
                    "SELECT entity_id, entity_type FROM level_ignores WHERE guild_id = ?",
                    (str(guild_id),)
                ) as cursor:
                    results = await cursor.fetchall()
                    return [(row['entity_id'], row['entity_type']) for row in results]
        except Exception as e:
            logger.error(f"Error getting ignored entities: {e}")
            return []
    
    async def is_entity_ignored(self, guild_id, entity_id):
        """Check if a channel or role is ignored for XP gain"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                    "SELECT 1 FROM level_ignores WHERE guild_id = ? AND entity_id = ?",
                    (str(guild_id), str(entity_id))
                ) as cursor:
                    result = await cursor.fetchone()
                    return result is not None
        except Exception as e:
            logger.error(f"Error checking if entity is ignored: {e}")
            return False
    
    async def get_user_level(self, guild_id, user_id):
        """Get a user's level information"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(
                    "SELECT * FROM user_levels WHERE guild_id = ? AND user_id = ?",
                    (str(guild_id), str(user_id))
                ) as cursor:
                    result = await cursor.fetchone()
                    if result:
                        return dict(result)
                    
                    # Create user entry if it doesn't exist
                    now = datetime.datetime.now().isoformat()
                    await db.execute(
                        """
                        INSERT INTO user_levels 
                        (guild_id, user_id, level, xp, messages_since_xp, last_xp_earned, show_messages) 
                        VALUES (?, ?, 1, 0, 0, ?, TRUE)
                        """,
                        (str(guild_id), str(user_id), now)
                    )
                    await db.commit()
                    
                    # Return default values
                    return {
                        "guild_id": str(guild_id),
                        "user_id": str(user_id),
                        "level": 1,
                        "xp": 0,
                        "messages_since_xp": 0,
                        "last_xp_earned": now,
                        "show_messages": True
                    }
        except Exception as e:
            logger.error(f"Error getting user level: {e}")
            return None
    
    async def update_user_level(self, guild_id, user_id, **kwargs):
        """Update a user's level information"""
        try:
            user_level = await self.get_user_level(guild_id, user_id)
            if not user_level:
                return False
                
            async with aiosqlite.connect(self.db_path) as db:
                set_clause = ", ".join([f"{key} = ?" for key in kwargs.keys()])
                values = list(kwargs.values()) + [str(guild_id), str(user_id)]
                
                await db.execute(
                    f"UPDATE user_levels SET {set_clause} WHERE guild_id = ? AND user_id = ?",
                    values
                )
                await db.commit()
                return True
        except Exception as e:
            logger.error(f"Error updating user level: {e}")
            return False
    
    async def set_user_level(self, guild_id, user_id, level):
        """Set a user's level"""
        try:
            level_int = int(level)
            if level_int < 1:
                return False
                
            # Calculate XP for this level
            xp = self.xp_for_level(level_int)
            
            return await self.update_user_level(guild_id, user_id, level=level_int, xp=xp)
        except ValueError:
            return False
    
    async def set_user_xp(self, guild_id, user_id, xp):
        """Set a user's XP"""
        try:
            xp_int = int(xp)
            if xp_int < 0:
                return False
                
            # Calculate level for this XP
            level = self.level_for_xp(xp_int)
            
            return await self.update_user_level(guild_id, user_id, xp=xp_int, level=level)
        except ValueError:
            return False
    
    async def add_user_xp(self, guild_id, user_id, xp_to_add):
        """Add XP to a user"""
        try:
            user_level = await self.get_user_level(guild_id, user_id)
            if not user_level:
                return False
                
            # Calculate new XP
            current_xp = user_level['xp']
            current_level = user_level['level']
            new_xp = current_xp + xp_to_add
            
            # Calculate new level
            new_level = self.level_for_xp(new_xp)
            
            # Update user
            now = datetime.datetime.now().isoformat()
            await self.update_user_level(
                guild_id, user_id,
                xp=new_xp,
                level=new_level,
                last_xp_earned=now,
                messages_since_xp=0
            )
            
            # Check if leveled up
            if new_level > current_level:
                return new_level
            return None
        except Exception as e:
            logger.error(f"Error adding user XP: {e}")
            return False
    
    async def remove_user_xp(self, guild_id, user_id, xp_to_remove):
        """Remove XP from a user"""
        try:
            user_level = await self.get_user_level(guild_id, user_id)
            if not user_level:
                return False
                
            # Calculate new XP
            current_xp = user_level['xp']
            new_xp = max(0, current_xp - xp_to_remove)
            
            # Calculate new level
            new_level = self.level_for_xp(new_xp)
            
            # Update user
            return await self.update_user_level(guild_id, user_id, xp=new_xp, level=new_level)
        except Exception as e:
            logger.error(f"Error removing user XP: {e}")
            return False
    
    async def toggle_level_messages(self, guild_id, user_id, show):
        """Toggle level up messages for a user"""
        return await self.update_user_level(guild_id, user_id, show_messages=show)
    
    async def should_show_level_messages(self, guild_id, user_id):
        """Check if level up messages should be shown for a user"""
        user_level = await self.get_user_level(guild_id, user_id)
        if not user_level:
            return True
        return user_level['show_messages']
    
    async def process_message(self, guild_id, user_id, channel_id, member_roles):
        """Process a message for XP gain"""
        try:
            # Check if leveling is enabled
            settings = await self.get_guild_settings(guild_id)
            if not settings or not settings['enabled']:
                return None
                
            # Check if the channel or any of the member's roles are ignored
            if await self.is_entity_ignored(guild_id, channel_id):
                return None
                
            for role_id in member_roles:
                if await self.is_entity_ignored(guild_id, role_id):
                    return None
            
            # Get user level
            user_level = await self.get_user_level(guild_id, user_id)
            if not user_level:
                return None
                
            # Check cooldown (add XP every 5 messages)
            messages_since_xp = user_level['messages_since_xp'] + 1
            if messages_since_xp < 5:
                await self.update_user_level(guild_id, user_id, messages_since_xp=messages_since_xp)
                return None
                
            # Random XP between 15-25, modified by rate
            xp_rate = settings['xp_rate']
            xp_to_add = int(random.randint(15, 25) * xp_rate)
            
            # Add XP
            level_up = await self.add_user_xp(guild_id, user_id, xp_to_add)
            return level_up
        except Exception as e:
            logger.error(f"Error processing message for XP: {e}")
            return None
    
    async def get_leaderboard(self, guild_id, limit=10):
        """Get the top users by level and XP"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(
                    """
                    SELECT user_id, level, xp 
                    FROM user_levels 
                    WHERE guild_id = ? 
                    ORDER BY level DESC, xp DESC 
                    LIMIT ?
                    """,
                    (str(guild_id), limit)
                ) as cursor:
                    results = await cursor.fetchall()
                    return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"Error getting leaderboard: {e}")
            return []
    
    async def reset_levels(self, guild_id):
        """Reset all levels for a guild"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Delete all user levels
                await db.execute(
                    "DELETE FROM user_levels WHERE guild_id = ?",
                    (str(guild_id),)
                )
                
                # Delete all level roles
                await db.execute(
                    "DELETE FROM level_roles WHERE guild_id = ?",
                    (str(guild_id),)
                )
                
                # Delete all ignores
                await db.execute(
                    "DELETE FROM level_ignores WHERE guild_id = ?",
                    (str(guild_id),)
                )
                
                # Reset settings to default
                await db.execute(
                    """
                    UPDATE levels_settings 
                    SET enabled = TRUE, 
                        stack_roles = FALSE, 
                        message_mode = 'channel', 
                        level_up_message = 'Congratulations {user}, you reached level {level}!', 
                        xp_rate = 1.0
                    WHERE guild_id = ?
                    """,
                    (str(guild_id),)
                )
                
                await db.commit()
                return True
        except Exception as e:
            logger.error(f"Error resetting levels: {e}")
            return False
    
    async def cleanup_absent_members(self, guild_id, member_ids):
        """Remove level data for members who are no longer in the guild"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Get all user IDs in the database for this guild
                db.row_factory = aiosqlite.Row
                async with db.execute(
                    "SELECT user_id FROM user_levels WHERE guild_id = ?",
                    (str(guild_id),)
                ) as cursor:
                    results = await cursor.fetchall()
                    db_user_ids = [row['user_id'] for row in results]
                
                # Filter out users who are still in the guild
                absent_user_ids = [user_id for user_id in db_user_ids if user_id not in member_ids]
                
                # Delete absent users
                for user_id in absent_user_ids:
                    await db.execute(
                        "DELETE FROM user_levels WHERE guild_id = ? AND user_id = ?",
                        (str(guild_id), user_id)
                    )
                
                await db.commit()
                return len(absent_user_ids)
        except Exception as e:
            logger.error(f"Error cleaning up absent members: {e}")
            return 0
    
    def xp_for_level(self, level):
        """Calculate the XP needed to reach a level"""
        # Simple quadratic formula: 100 * level^2
        return 100 * (level ** 2)
    
    def level_for_xp(self, xp):
        """Calculate the level for an amount of XP"""
        # Inverse of the formula above: sqrt(xp / 100)
        return max(1, int(math.sqrt(xp / 100)))
    
    async def get_roles_to_assign(self, guild_id, user_level):
        """Get the roles to assign for a user's level"""
        try:
            settings = await self.get_guild_settings(guild_id)
            if not settings:
                return []
                
            # Get all level roles
            roles = await self.get_level_roles(guild_id)
            if not roles:
                return []
                
            # Filter roles based on user's level and stacking setting
            if settings['stack_roles']:
                # Assign all roles up to the user's level
                return [role_id for level, role_id in roles if level <= user_level]
            else:
                # Find the highest role the user qualifies for
                valid_roles = [role_id for level, role_id in roles if level <= user_level]
                if not valid_roles:
                    return []
                
                # Get the role with the highest level
                highest_level_role = max([(level, role_id) for level, role_id in roles if role_id in valid_roles], key=lambda x: x[0])
                return [highest_level_role[1]]
        except Exception as e:
            logger.error(f"Error getting roles to assign: {e}")
            return []

async def setup(bot):
    # This is a database module, no cog to add
    pass 