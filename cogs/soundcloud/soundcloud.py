import discord
from discord.ext import commands, tasks
import aiohttp
import json
import os
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Union
import re

logger = logging.getLogger('bot')

class SoundCloudAPI:
    """Handles SoundCloud API interactions"""
    
    def __init__(self, client_id=None):
        self.base_url = "https://api.soundcloud.com"
        self.client_id = client_id or os.environ.get('SOUNDCLOUD_CLIENT_ID', '')
        if not self.client_id:
            logger.warning("SoundCloud client ID not set. Some functionality will be limited.")
    
    async def resolve_url(self, url):
        """Resolve a SoundCloud URL to get entity data"""
        params = {
            'url': url,
            'client_id': self.client_id
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/resolve", params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"Error resolving URL: {response.status}")
                    return None
    
    async def search_tracks(self, query, limit=5):
        """Search for tracks on SoundCloud"""
        params = {
            'q': query,
            'limit': limit,
            'client_id': self.client_id
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/tracks", params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"Error searching tracks: {response.status}")
                    return []
    
    async def get_user(self, username):
        """Get a user by username"""
        params = {
            'q': username,
            'client_id': self.client_id
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/users", params=params) as response:
                if response.status == 200:
                    users = await response.json()
                    # Find best match
                    for user in users:
                        if user.get('username', '').lower() == username.lower():
                            return user
                    return users[0] if users else None
                else:
                    logger.error(f"Error getting user: {response.status}")
                    return None
    
    async def get_user_tracks(self, user_id, limit=10):
        """Get a user's tracks"""
        params = {
            'limit': limit,
            'client_id': self.client_id
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/users/{user_id}/tracks", params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"Error getting user tracks: {response.status}")
                    return []

class SoundCloud(commands.Cog):
    """SoundCloud integration for Discord"""
    
    def __init__(self, bot):
        self.bot = bot
        self.api = SoundCloudAPI()
        self.data_folder = 'data'
        self.data_file = os.path.join(self.data_folder, 'soundcloud.json')
        self.notifications = {}  # guild_id -> { channel_id -> { username -> { message, last_track_id } } }
        self.check_interval = 30 * 60  # 30 minutes
        
        # Create data directory if it doesn't exist
        if not os.path.exists(self.data_folder):
            os.makedirs(self.data_folder)
            
        # Load existing data
        self.load_data()
        
        # Start background task
        self.check_for_new_tracks.start()
    
    def load_data(self):
        """Load notification data from JSON file"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r') as f:
                    self.notifications = json.load(f)
                logger.info(f"Loaded SoundCloud notification data for {len(self.notifications)} guilds")
            else:
                logger.info("No SoundCloud notification data found. Starting fresh.")
                self.notifications = {}
        except json.JSONDecodeError:
            logger.error(f"Error decoding {self.data_file}. Using empty data.")
            self.notifications = {}
    
    def save_data(self):
        """Save notification data to JSON file"""
        with open(self.data_file, 'w') as f:
            json.dump(self.notifications, f, indent=4)
        logger.info("Saved SoundCloud notification data")
    
    def cog_unload(self):
        """Save data when cog is unloaded and cancel tasks"""
        self.save_data()
        self.check_for_new_tracks.cancel()
    
    async def get_username_data(self, guild_id, channel_id, username):
        """Get data for a specific username in a channel"""
        guild_id = str(guild_id)
        channel_id = str(channel_id)
        
        if guild_id not in self.notifications:
            return None
            
        if channel_id not in self.notifications[guild_id]:
            return None
            
        if username.lower() not in self.notifications[guild_id][channel_id]:
            return None
            
        return self.notifications[guild_id][channel_id][username.lower()]
    
    async def add_notification(self, guild_id, channel_id, username, message=None):
        """Add a new notification for a SoundCloud user"""
        guild_id = str(guild_id)
        channel_id = str(channel_id)
        username = username.lower()
        
        # Get the user from SoundCloud
        user = await self.api.get_user(username)
        if not user:
            return False, "User not found on SoundCloud"
            
        # Get the user's most recent track
        tracks = await self.api.get_user_tracks(user['id'], limit=1)
        last_track_id = tracks[0]['id'] if tracks else None
        
        # Initialize guild data if needed
        if guild_id not in self.notifications:
            self.notifications[guild_id] = {}
            
        # Initialize channel data if needed
        if channel_id not in self.notifications[guild_id]:
            self.notifications[guild_id][channel_id] = {}
            
        # Add the notification
        self.notifications[guild_id][channel_id][username] = {
            'user_id': user['id'],
            'username': user['username'],  # Store actual username with proper capitalization
            'message': message or "New track from {username}! 🎵",
            'last_track_id': last_track_id,
            'added_at': datetime.now().isoformat()
        }
        
        # Save the data
        self.save_data()
        
        return True, f"Added notification for {user['username']}"
    
    async def remove_notification(self, guild_id, channel_id, username):
        """Remove a notification for a SoundCloud user"""
        guild_id = str(guild_id)
        channel_id = str(channel_id)
        username = username.lower()
        
        if guild_id not in self.notifications:
            return False, "No notifications set up for this server"
            
        if channel_id not in self.notifications[guild_id]:
            return False, "No notifications set up for this channel"
            
        if username not in self.notifications[guild_id][channel_id]:
            return False, f"No notifications set up for {username} in this channel"
            
        # Remove the notification
        del self.notifications[guild_id][channel_id][username]
        
        # Clean up empty dictionaries
        if not self.notifications[guild_id][channel_id]:
            del self.notifications[guild_id][channel_id]
            
        if not self.notifications[guild_id]:
            del self.notifications[guild_id]
            
        # Save the data
        self.save_data()
        
        return True, f"Removed notification for {username}"
    
    async def set_notification_message(self, guild_id, channel_id, username, message):
        """Set a custom message for a SoundCloud notification"""
        guild_id = str(guild_id)
        channel_id = str(channel_id)
        username = username.lower()
        
        user_data = await self.get_username_data(guild_id, channel_id, username)
        if not user_data:
            return False, f"No notifications set up for {username} in this channel"
            
        # Update the message
        self.notifications[guild_id][channel_id][username]['message'] = message
        
        # Save the data
        self.save_data()
        
        return True, f"Updated notification message for {username}"
    
    @tasks.loop(minutes=30)
    async def check_for_new_tracks(self):
        """Check for new tracks from monitored users"""
        logger.info("Checking for new SoundCloud tracks...")
        
        for guild_id, guild_data in self.notifications.items():
            for channel_id, channel_data in guild_data.items():
                # Get the channel
                channel = self.bot.get_channel(int(channel_id))
                if not channel:
                    logger.warning(f"Channel {channel_id} not found, skipping")
                    continue
                    
                for username, user_data in channel_data.items():
                    try:
                        # Get the user's tracks
                        user_id = user_data['user_id']
                        tracks = await self.api.get_user_tracks(user_id, limit=3)
                        
                        if not tracks:
                            logger.warning(f"No tracks found for {username}, skipping")
                            continue
                            
                        # Check if there are new tracks
                        last_track_id = user_data.get('last_track_id')
                        new_tracks = []
                        
                        for track in tracks:
                            if str(track['id']) == str(last_track_id):
                                break
                            new_tracks.append(track)
                            
                        if not new_tracks:
                            continue
                            
                        # Update the last track ID
                        self.notifications[guild_id][channel_id][username]['last_track_id'] = str(tracks[0]['id'])
                        self.save_data()
                        
                        # Send notifications for new tracks (newest first)
                        for track in reversed(new_tracks):
                            # Format the message
                            message_template = user_data.get('message', "New track from {username}! 🎵")
                            message = message_template.format(
                                username=user_data.get('username', username),
                                title=track.get('title', 'Unknown Track'),
                                url=track.get('permalink_url', '')
                            )
                            
                            # Create an embed
                            embed = discord.Embed(
                                title=track.get('title', 'New Track'),
                                url=track.get('permalink_url', ''),
                                description=track.get('description', '')[:1000] if track.get('description') else '',
                                color=0xFF7700  # SoundCloud orange
                            )
                            
                            # Add track details
                            embed.add_field(name="Artist", value=user_data.get('username', username), inline=True)
                            embed.add_field(name="Genre", value=track.get('genre', 'Unknown'), inline=True)
                            
                            # Add track stats
                            embed.add_field(
                                name="Stats", 
                                value=f"Plays: {track.get('playback_count', 0):,} | Likes: {track.get('likes_count', 0):,}", 
                                inline=False
                            )
                            
                            # Set the thumbnail to the track artwork if available
                            artwork_url = track.get('artwork_url')
                            if artwork_url:
                                # Convert to high-resolution artwork
                                high_res_artwork = artwork_url.replace('large', 't500x500')
                                embed.set_thumbnail(url=high_res_artwork)
                                
                            # Add footer with timestamp
                            embed.set_footer(
                                text="SoundCloud", 
                                icon_url="https://developers.soundcloud.com/assets/logo_white-af5006050dd9cba09b0c48be04feac57.png"
                            )
                            embed.timestamp = datetime.strptime(track.get('created_at', datetime.now().isoformat()), "%Y-%m-%dT%H:%M:%SZ")
                            
                            # Send the notification
                            await channel.send(content=message, embed=embed)
                            logger.info(f"Sent notification for new track from {username} in {channel.guild.name}/#{channel.name}")
                            
                            # Small delay between notifications to avoid rate limits
                            await asyncio.sleep(1)
                    
                    except Exception as e:
                        logger.error(f"Error checking tracks for {username}: {str(e)}")
    
    @check_for_new_tracks.before_loop
    async def before_check_for_new_tracks(self):
        """Wait for the bot to be ready before starting the task"""
        await self.bot.wait_until_ready()
        logger.info("Starting SoundCloud track check task")
    
    @commands.group(name="soundcloud", aliases=["sc"], invoke_without_command=True)
    async def soundcloud(self, ctx, *, query=None):
        """Search for tracks on SoundCloud"""
        if query is None:
            await ctx.send("Please provide a search query. Example: `!soundcloud lofi beats`")
            return
            
        # Search for tracks
        tracks = await self.api.search_tracks(query)
        
        if not tracks:
            await ctx.send(f"No tracks found for: {query}")
            return
            
        # Create an embed with the results
        embed = discord.Embed(
            title=f"SoundCloud Search Results for: {query}",
            color=0xFF7700  # SoundCloud orange
        )
        
        for i, track in enumerate(tracks[:5], 1):
            title = track.get('title', 'Unknown Track')
            artist = track.get('user', {}).get('username', 'Unknown Artist')
            url = track.get('permalink_url', '')
            duration = track.get('duration', 0) // 1000  # Convert ms to seconds
            minutes, seconds = divmod(duration, 60)
            
            embed.add_field(
                name=f"{i}. {title}",
                value=f"by **{artist}** | {minutes}:{seconds:02d}\n[Listen on SoundCloud]({url})",
                inline=False
            )
            
        # Set the thumbnail to the first track's artwork if available
        if tracks and 'artwork_url' in tracks[0] and tracks[0]['artwork_url']:
            embed.set_thumbnail(url=tracks[0]['artwork_url'].replace('large', 't500x500'))
            
        # Add footer
        embed.set_footer(
            text="SoundCloud", 
            icon_url="https://developers.soundcloud.com/assets/logo_white-af5006050dd9cba09b0c48be04feac57.png"
        )
        
        await ctx.send(embed=embed)
    
    @soundcloud.command(name="add")
    @commands.has_permissions(manage_guild=True)
    async def soundcloud_add(self, ctx, channel: discord.TextChannel, username: str):
        """Add stream notifications to channel"""
        success, message = await self.add_notification(ctx.guild.id, channel.id, username)
        
        if success:
            embed = discord.Embed(
                title="SoundCloud Notifications Added",
                description=message,
                color=discord.Color.green()
            )
            embed.add_field(name="Username", value=username, inline=True)
            embed.add_field(name="Channel", value=channel.mention, inline=True)
        else:
            embed = discord.Embed(
                title="Error Adding SoundCloud Notifications",
                description=message,
                color=discord.Color.red()
            )
            
        await ctx.send(embed=embed)
    
    @soundcloud.command(name="list")
    @commands.has_permissions(manage_guild=True)
    async def soundcloud_list(self, ctx):
        """View all SoundCloud stream notifications"""
        guild_id = str(ctx.guild.id)
        
        if guild_id not in self.notifications or not self.notifications[guild_id]:
            await ctx.send("No SoundCloud notifications set up for this server.")
            return
            
        embed = discord.Embed(
            title="SoundCloud Notifications",
            description=f"Notifications set up in {ctx.guild.name}",
            color=0xFF7700
        )
        
        for channel_id, channel_data in self.notifications[guild_id].items():
            channel = ctx.guild.get_channel(int(channel_id))
            if not channel:
                continue
                
            users = []
            for username, user_data in channel_data.items():
                display_name = user_data.get('username', username)
                users.append(f"• [{display_name}](https://soundcloud.com/{username})")
                
            if users:
                embed.add_field(
                    name=f"#{channel.name}",
                    value="\n".join(users),
                    inline=False
                )
                
        if not embed.fields:
            await ctx.send("No valid SoundCloud notifications found.")
            return
            
        embed.set_footer(text="Use !soundcloud message view <username> to see notification messages")
        await ctx.send(embed=embed)
    
    @soundcloud.command(name="remove")
    @commands.has_permissions(manage_channels=True)
    async def soundcloud_remove(self, ctx, channel: discord.TextChannel, username: str):
        """Remove feed for new SoundCloud posts"""
        success, message = await self.remove_notification(ctx.guild.id, channel.id, username)
        
        if success:
            embed = discord.Embed(
                title="SoundCloud Notifications Removed",
                description=message,
                color=discord.Color.green()
            )
        else:
            embed = discord.Embed(
                title="Error Removing SoundCloud Notifications",
                description=message,
                color=discord.Color.red()
            )
            
        await ctx.send(embed=embed)
    
    @soundcloud.group(name="message", invoke_without_command=True)
    @commands.has_permissions(manage_guild=True)
    async def soundcloud_message(self, ctx, username: str, *, message: str):
        """Set a message for SoundCloud notifications"""
        # Find all channels with this username
        guild_id = str(ctx.guild.id)
        if guild_id not in self.notifications:
            await ctx.send(f"No notifications set up for {username} in this server.")
            return
            
        success = False
        channels_updated = []
        
        for channel_id, channel_data in self.notifications[guild_id].items():
            if username.lower() in channel_data:
                channel = ctx.guild.get_channel(int(channel_id))
                if channel:
                    success, _ = await self.set_notification_message(guild_id, channel_id, username, message)
                    if success:
                        channels_updated.append(channel.mention)
        
        if channels_updated:
            embed = discord.Embed(
                title="SoundCloud Notification Message Updated",
                description=f"Updated message for {username} in {len(channels_updated)} channels:\n{', '.join(channels_updated)}",
                color=discord.Color.green()
            )
            embed.add_field(name="New Message", value=message, inline=False)
            embed.add_field(
                name="Available Variables", 
                value="{username} - The SoundCloud username\n{title} - The track title\n{url} - The track URL", 
                inline=False
            )
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"No notifications found for {username} in any channel.")
    
    @soundcloud_message.command(name="view")
    @commands.has_permissions(manage_guild=True)
    async def soundcloud_message_view(self, ctx, username: str):
        """View SoundCloud message for new posts"""
        guild_id = str(ctx.guild.id)
        if guild_id not in self.notifications:
            await ctx.send(f"No notifications set up for {username} in this server.")
            return
            
        messages_found = False
        embed = discord.Embed(
            title=f"Notification Messages for {username}",
            color=0xFF7700
        )
        
        for channel_id, channel_data in self.notifications[guild_id].items():
            if username.lower() in channel_data:
                channel = ctx.guild.get_channel(int(channel_id))
                if channel:
                    message = channel_data[username.lower()].get('message', "New track from {username}! 🎵")
                    embed.add_field(
                        name=f"#{channel.name}",
                        value=f"```\n{message}\n```",
                        inline=False
                    )
                    messages_found = True
        
        if messages_found:
            embed.add_field(
                name="Available Variables", 
                value="{username} - The SoundCloud username\n{title} - The track title\n{url} - The track URL", 
                inline=False
            )
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"No notifications found for {username} in any channel.")

async def setup(bot):
    await bot.add_cog(SoundCloud(bot)) 