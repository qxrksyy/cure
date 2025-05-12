import json
import os
import logging
import aiosqlite
import datetime

logger = logging.getLogger('bot')

class LastFMDB:
    """Handles database operations for the LastFM module"""
    
    def __init__(self):
        self.data_folder = 'data'
        self.db_path = os.path.join(self.data_folder, 'lastfm.db')
        
    async def initialize(self):
        """Initialize the LastFM database"""
        if not os.path.exists(self.data_folder):
            os.makedirs(self.data_folder)
            
        async with aiosqlite.connect(self.db_path) as db:
            # Create users table
            await db.execute('''
                CREATE TABLE IF NOT EXISTS lastfm_users (
                    user_id TEXT PRIMARY KEY,
                    username TEXT NOT NULL,
                    lastfm_username TEXT NOT NULL,
                    auth_token TEXT,
                    custom_command TEXT,
                    color TEXT DEFAULT NULL,
                    mode TEXT DEFAULT 'default',
                    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create custom reactions table
            await db.execute('''
                CREATE TABLE IF NOT EXISTS lastfm_reactions (
                    user_id TEXT PRIMARY KEY,
                    upvote_emoji TEXT,
                    downvote_emoji TEXT
                )
            ''')
            
            # Create custom commands table
            await db.execute('''
                CREATE TABLE IF NOT EXISTS lastfm_custom_commands (
                    command TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    is_public BOOLEAN DEFAULT FALSE,
                    FOREIGN KEY (user_id) REFERENCES lastfm_users(user_id)
                )
            ''')
            
            # Create blacklist table
            await db.execute('''
                CREATE TABLE IF NOT EXISTS lastfm_blacklist (
                    user_id TEXT PRIMARY KEY
                )
            ''')
            
            # Create crowns table
            await db.execute('''
                CREATE TABLE IF NOT EXISTS lastfm_crowns (
                    guild_id TEXT,
                    artist TEXT,
                    user_id TEXT,
                    play_count INTEGER,
                    PRIMARY KEY (guild_id, artist)
                )
            ''')
            
            # Create favorites table
            await db.execute('''
                CREATE TABLE IF NOT EXISTS lastfm_favorites (
                    user_id TEXT,
                    track TEXT,
                    artist TEXT,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, track, artist)
                )
            ''')
            
            await db.commit()
    
    async def register_user(self, user_id, username, lastfm_username):
        """Register a user with their Last.fm username"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "INSERT OR REPLACE INTO lastfm_users (user_id, username, lastfm_username) VALUES (?, ?, ?)",
                    (str(user_id), username, lastfm_username)
                )
                await db.commit()
                return True
        except Exception as e:
            logger.error(f"Error registering Last.fm user: {e}")
            return False
    
    async def get_lastfm_username(self, user_id):
        """Get a user's Last.fm username"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                    "SELECT lastfm_username FROM lastfm_users WHERE user_id = ?",
                    (str(user_id),)
                ) as cursor:
                    result = await cursor.fetchone()
                    return result[0] if result else None
        except Exception as e:
            logger.error(f"Error getting Last.fm username: {e}")
            return None
    
    async def remove_user(self, user_id):
        """Remove a user's Last.fm registration"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "DELETE FROM lastfm_users WHERE user_id = ?",
                    (str(user_id),)
                )
                await db.commit()
                return True
        except Exception as e:
            logger.error(f"Error removing Last.fm user: {e}")
            return False
    
    async def set_custom_command(self, user_id, command):
        """Set a custom command for a user"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Update user's custom command
                await db.execute(
                    "UPDATE lastfm_users SET custom_command = ? WHERE user_id = ?",
                    (command, str(user_id))
                )
                
                # Add to custom commands table
                await db.execute(
                    "INSERT OR REPLACE INTO lastfm_custom_commands (command, user_id) VALUES (?, ?)",
                    (command, str(user_id))
                )
                
                await db.commit()
                return True
        except Exception as e:
            logger.error(f"Error setting custom command: {e}")
            return False
    
    async def get_custom_command(self, user_id):
        """Get a user's custom command"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                    "SELECT custom_command FROM lastfm_users WHERE user_id = ?",
                    (str(user_id),)
                ) as cursor:
                    result = await cursor.fetchone()
                    return result[0] if result else None
        except Exception as e:
            logger.error(f"Error getting custom command: {e}")
            return None
    
    async def remove_custom_command(self, user_id):
        """Remove a user's custom command"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Get the current custom command
                async with db.execute(
                    "SELECT custom_command FROM lastfm_users WHERE user_id = ?",
                    (str(user_id),)
                ) as cursor:
                    result = await cursor.fetchone()
                    if result and result[0]:
                        # Remove from custom commands table
                        await db.execute(
                            "DELETE FROM lastfm_custom_commands WHERE command = ?",
                            (result[0],)
                        )
                
                # Update user record
                await db.execute(
                    "UPDATE lastfm_users SET custom_command = NULL WHERE user_id = ?",
                    (str(user_id),)
                )
                
                await db.commit()
                return True
        except Exception as e:
            logger.error(f"Error removing custom command: {e}")
            return False
    
    async def set_custom_reactions(self, user_id, upvote_emoji, downvote_emoji):
        """Set custom upvote and downvote reactions for a user"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "INSERT OR REPLACE INTO lastfm_reactions (user_id, upvote_emoji, downvote_emoji) VALUES (?, ?, ?)",
                    (str(user_id), upvote_emoji, downvote_emoji)
                )
                await db.commit()
                return True
        except Exception as e:
            logger.error(f"Error setting custom reactions: {e}")
            return False
    
    async def get_custom_reactions(self, user_id):
        """Get a user's custom reactions"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                    "SELECT upvote_emoji, downvote_emoji FROM lastfm_reactions WHERE user_id = ?",
                    (str(user_id),)
                ) as cursor:
                    result = await cursor.fetchone()
                    if result:
                        return {'upvote': result[0], 'downvote': result[1]}
                    return None
        except Exception as e:
            logger.error(f"Error getting custom reactions: {e}")
            return None
    
    async def set_embed_color(self, user_id, color):
        """Set a custom embed color for a user"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "UPDATE lastfm_users SET color = ? WHERE user_id = ?",
                    (color, str(user_id))
                )
                await db.commit()
                return True
        except Exception as e:
            logger.error(f"Error setting embed color: {e}")
            return False
    
    async def get_embed_color(self, user_id):
        """Get a user's custom embed color"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                    "SELECT color FROM lastfm_users WHERE user_id = ?",
                    (str(user_id),)
                ) as cursor:
                    result = await cursor.fetchone()
                    return result[0] if result and result[0] else None
        except Exception as e:
            logger.error(f"Error getting embed color: {e}")
            return None
    
    async def set_mode(self, user_id, mode):
        """Set a custom mode for a user"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "UPDATE lastfm_users SET mode = ? WHERE user_id = ?",
                    (mode, str(user_id))
                )
                await db.commit()
                return True
        except Exception as e:
            logger.error(f"Error setting mode: {e}")
            return False
    
    async def get_mode(self, user_id):
        """Get a user's custom mode"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                    "SELECT mode FROM lastfm_users WHERE user_id = ?",
                    (str(user_id),)
                ) as cursor:
                    result = await cursor.fetchone()
                    return result[0] if result else 'default'
        except Exception as e:
            logger.error(f"Error getting mode: {e}")
            return 'default'
    
    async def add_to_blacklist(self, user_id):
        """Add a user to the blacklist"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "INSERT OR REPLACE INTO lastfm_blacklist (user_id) VALUES (?)",
                    (str(user_id),)
                )
                await db.commit()
                return True
        except Exception as e:
            logger.error(f"Error adding user to blacklist: {e}")
            return False
    
    async def remove_from_blacklist(self, user_id):
        """Remove a user from the blacklist"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "DELETE FROM lastfm_blacklist WHERE user_id = ?",
                    (str(user_id),)
                )
                await db.commit()
                return True
        except Exception as e:
            logger.error(f"Error removing user from blacklist: {e}")
            return False
    
    async def is_blacklisted(self, user_id):
        """Check if a user is blacklisted"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                    "SELECT 1 FROM lastfm_blacklist WHERE user_id = ?",
                    (str(user_id),)
                ) as cursor:
                    result = await cursor.fetchone()
                    return bool(result)
        except Exception as e:
            logger.error(f"Error checking blacklist: {e}")
            return False
    
    async def get_blacklist(self):
        """Get all blacklisted users"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                    "SELECT user_id FROM lastfm_blacklist"
                ) as cursor:
                    results = await cursor.fetchall()
                    return [result[0] for result in results]
        except Exception as e:
            logger.error(f"Error getting blacklist: {e}")
            return []
    
    async def add_crown(self, guild_id, artist, user_id, play_count):
        """Add or update a crown"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "INSERT OR REPLACE INTO lastfm_crowns (guild_id, artist, user_id, play_count) VALUES (?, ?, ?, ?)",
                    (str(guild_id), artist.lower(), str(user_id), play_count)
                )
                await db.commit()
                return True
        except Exception as e:
            logger.error(f"Error adding crown: {e}")
            return False
    
    async def get_crown(self, guild_id, artist):
        """Get the crown holder for an artist in a guild"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                    "SELECT user_id, play_count FROM lastfm_crowns WHERE guild_id = ? AND artist = ?",
                    (str(guild_id), artist.lower())
                ) as cursor:
                    result = await cursor.fetchone()
                    return {'user_id': result[0], 'play_count': result[1]} if result else None
        except Exception as e:
            logger.error(f"Error getting crown: {e}")
            return None
    
    async def get_user_crowns(self, guild_id, user_id):
        """Get all crowns for a user in a guild"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                    "SELECT artist, play_count FROM lastfm_crowns WHERE guild_id = ? AND user_id = ? ORDER BY play_count DESC",
                    (str(guild_id), str(user_id))
                ) as cursor:
                    results = await cursor.fetchall()
                    return [{'artist': result[0], 'play_count': result[1]} for result in results]
        except Exception as e:
            logger.error(f"Error getting user crowns: {e}")
            return []
    
    async def add_favorite(self, user_id, track, artist):
        """Add a track to a user's favorites"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "INSERT OR REPLACE INTO lastfm_favorites (user_id, track, artist) VALUES (?, ?, ?)",
                    (str(user_id), track, artist)
                )
                await db.commit()
                return True
        except Exception as e:
            logger.error(f"Error adding favorite: {e}")
            return False
    
    async def remove_favorite(self, user_id, track, artist):
        """Remove a track from a user's favorites"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "DELETE FROM lastfm_favorites WHERE user_id = ? AND track = ? AND artist = ?",
                    (str(user_id), track, artist)
                )
                await db.commit()
                return True
        except Exception as e:
            logger.error(f"Error removing favorite: {e}")
            return False
    
    async def get_favorites(self, user_id):
        """Get a user's favorite tracks"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                    "SELECT track, artist, added_at FROM lastfm_favorites WHERE user_id = ? ORDER BY added_at DESC",
                    (str(user_id),)
                ) as cursor:
                    results = await cursor.fetchall()
                    return [{'track': result[0], 'artist': result[1], 'added_at': result[2]} for result in results]
        except Exception as e:
            logger.error(f"Error getting favorites: {e}")
            return []
    
    async def is_favorite(self, user_id, track, artist):
        """Check if a track is in a user's favorites"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                    "SELECT 1 FROM lastfm_favorites WHERE user_id = ? AND track = ? AND artist = ?",
                    (str(user_id), track, artist)
                ) as cursor:
                    result = await cursor.fetchone()
                    return bool(result)
        except Exception as e:
            logger.error(f"Error checking favorite: {e}")
            return False
    
    async def get_all_custom_commands(self):
        """Get all custom commands"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                    "SELECT command, user_id, is_public FROM lastfm_custom_commands"
                ) as cursor:
                    results = await cursor.fetchall()
                    return [{'command': result[0], 'user_id': result[1], 'is_public': bool(result[2])} for result in results]
        except Exception as e:
            logger.error(f"Error getting custom commands: {e}")
            return []
    
    async def set_public_custom_command(self, command, is_public):
        """Set a custom command as public or private"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "UPDATE lastfm_custom_commands SET is_public = ? WHERE command = ?",
                    (is_public, command)
                )
                await db.commit()
                return True
        except Exception as e:
            logger.error(f"Error setting public custom command: {e}")
            return False
    
    async def cleanup_custom_commands(self, active_member_ids):
        """Remove custom commands from users who are no longer in the guild"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Get all users with custom commands
                async with db.execute(
                    "SELECT user_id FROM lastfm_custom_commands"
                ) as cursor:
                    results = await cursor.fetchall()
                    user_ids = [result[0] for result in results]
                
                # Filter out users who are no longer in the guild
                inactive_users = [user_id for user_id in user_ids if user_id not in active_member_ids]
                
                # Remove custom commands for inactive users
                for user_id in inactive_users:
                    await self.remove_custom_command(user_id)
                
                return len(inactive_users)
        except Exception as e:
            logger.error(f"Error cleaning up custom commands: {e}")
            return 0

async def setup(bot):
    # This is a database module, no cog to add
    pass 