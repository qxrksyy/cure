import discord
from discord.ext import commands, tasks
import json
import os
import logging
import aiohttp
import asyncio
from datetime import datetime

logger = logging.getLogger('bot')

class TwitchCommands(commands.Cog):
    """Commands for Twitch stream notifications"""
    
    def __init__(self, bot):
        self.bot = bot
        self.data_folder = 'data'
        self.config_file = os.path.join(self.data_folder, 'twitch_config.json')
        self.twitch_config = self.load_config()
        
        # Stream check settings
        self.check_interval = 5 * 60  # 5 minutes
        self.streamer_status = {}  # username -> {is_live, last_checked, stream_data}
        
        # Start the background task
        self.check_live_streams.start()
        
    def load_config(self):
        """Load the Twitch configuration from file"""
        if not os.path.exists(self.data_folder):
            os.makedirs(self.data_folder)
            
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            else:
                return {}
        except json.JSONDecodeError:
            logger.error(f"Error decoding {self.config_file}. Using empty config.")
            return {}
            
    def save_config(self):
        """Save the Twitch configuration to file"""
        with open(self.config_file, 'w') as f:
            json.dump(self.twitch_config, f, indent=4)
            
    def cog_unload(self):
        """Clean up when the cog is unloaded"""
        self.check_live_streams.cancel()
        
    async def check_stream_status(self, username):
        """Check if a Twitch user is currently streaming"""
        try:
            # In a real implementation, this would use the Twitch API
            # For now, we'll return mock data
            
            # Simulate random live status based on username (for testing)
            import hashlib
            import time
            hash_val = int(hashlib.md5(f"{username}{int(time.time() / 3600)}".encode()).hexdigest(), 16)
            is_live = (hash_val % 5) == 0  # 20% chance of being live
            
            if is_live:
                return {
                    'is_live': True,
                    'title': f"{username}'s Awesome Stream",
                    'game': "Just Chatting",
                    'viewer_count': hash_val % 1000,
                    'thumbnail': f"https://static-cdn.jtvnw.net/previews-ttv/live_user_{username}-1280x720.jpg",
                    'started_at': datetime.now().isoformat(),
                    'username': username,
                    'display_name': username.capitalize(),
                    'profile_image': f"https://static-cdn.jtvnw.net/jtv_user_pictures/{username}_profile_image.png"
                }
            else:
                return {
                    'is_live': False,
                    'username': username,
                    'display_name': username.capitalize(),
                    'profile_image': f"https://static-cdn.jtvnw.net/jtv_user_pictures/{username}_profile_image.png"
                }
                
        except Exception as e:
            logger.error(f"Error checking stream status for {username}: {str(e)}")
            return None
    
    @tasks.loop(minutes=5)
    async def check_live_streams(self):
        """Check for live streams and send notifications"""
        logger.info("Checking for Twitch live streams...")
        
        all_streamers = set()
        
        # Collect all streamers across all guilds and channels
        for guild_id, guild_data in self.twitch_config.items():
            if "channels" in guild_data:
                for channel_id, streamers in guild_data["channels"].items():
                    all_streamers.update([s.lower() for s in streamers])
        
        if not all_streamers:
            return
            
        for streamer in all_streamers:
            try:
                # Check if streamer is live
                stream_info = await self.check_stream_status(streamer)
                
                if not stream_info:
                    continue
                    
                # Get previous status
                was_live = self.streamer_status.get(streamer, {}).get('is_live', False)
                currently_live = stream_info['is_live']
                
                # Only notify if stream just started (changed from offline to online)
                if currently_live and not was_live:
                    await self.send_stream_notifications(streamer, stream_info)
                
                # Update status cache
                self.streamer_status[streamer] = {
                    'is_live': currently_live,
                    'last_checked': datetime.now().isoformat(),
                    'stream_data': stream_info if currently_live else None
                }
                
                # Small delay between API calls to avoid rate limits
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.error(f"Error processing stream status for {streamer}: {str(e)}")
    
    @check_live_streams.before_loop
    async def before_check_live_streams(self):
        """Wait until the bot is ready before starting the task"""
        await self.bot.wait_until_ready()
        logger.info("Starting Twitch stream check task")
    
    async def send_stream_notifications(self, streamer, stream_info):
        """Send notifications for a live stream"""
        streamer_lower = streamer.lower()
        
        for guild_id, guild_data in self.twitch_config.items():
            if "channels" not in guild_data:
                continue
                
            for discord_channel_id, streamers in guild_data["channels"].items():
                if streamer_lower not in [s.lower() for s in streamers]:
                    continue
                    
                # Get the channel
                channel = self.bot.get_channel(int(discord_channel_id))
                if not channel:
                    logger.warning(f"Channel {discord_channel_id} not found, skipping")
                    continue
                
                # Get custom message if set
                custom_message = None
                if "messages" in guild_data and streamer_lower in guild_data["messages"]:
                    custom_message = guild_data["messages"][streamer_lower]
                
                # Create embed
                embed = discord.Embed(
                    title=stream_info['title'],
                    url=f"https://twitch.tv/{streamer}",
                    description=f"**{stream_info['display_name']}** is now live on Twitch!",
                    color=discord.Color.purple(),
                    timestamp=datetime.now()
                )
                
                if stream_info['game']:
                    embed.add_field(name="Game", value=stream_info['game'], inline=True)
                    
                embed.add_field(name="Viewers", value=f"{stream_info['viewer_count']:,}", inline=True)
                
                if stream_info['thumbnail']:
                    embed.set_image(url=stream_info['thumbnail'])
                    
                if stream_info['profile_image']:
                    embed.set_author(
                        name=stream_info['display_name'],
                        icon_url=stream_info['profile_image'],
                        url=f"https://twitch.tv/{streamer}"
                    )
                
                embed.set_footer(text="Twitch", icon_url="https://brand.twitch.tv/assets/images/favicon.png")
                
                # Format the message content with stream information
                content = self.format_message(custom_message, stream_info) if custom_message else f"🔴 **{stream_info['display_name']}** is now live on Twitch!"
                
                # Send notification
                try:
                    await channel.send(content=content, embed=embed)
                    logger.info(f"Sent stream notification for {streamer} in guild {guild_id}, channel {discord_channel_id}")
                except Exception as e:
                    logger.error(f"Error sending notification: {str(e)}")
                
                # Small delay between notifications
                await asyncio.sleep(1)
            
    def format_message(self, message_template, stream_info):
        """Format a message with stream information"""
        return message_template.format(
            username=stream_info['display_name'],
            title=stream_info['title'],
            game=stream_info['game'],
            viewers=stream_info['viewer_count'],
            url=f"https://twitch.tv/{stream_info['username'].lower()}"
        )
            
    @commands.group(name="twitch", invoke_without_command=True)
    async def twitch_group(self, ctx, username: str = None):
        """Lookup a channel or setup notifications for Twitch livestreams"""
        if username is None:
            embed = discord.Embed(
                title="Twitch Commands",
                description="Lookup or setup Twitch stream notifications",
                color=discord.Color.purple()
            )
            
            embed.add_field(
                name="!twitch [username]",
                value="Lookup a Twitch channel",
                inline=False
            )
            
            embed.add_field(
                name="!twitch add [username] [channel]",
                value="Add Twitch notifications to a channel",
                inline=False
            )
            
            embed.add_field(
                name="!twitch remove [username] [channel]",
                value="Remove Twitch notifications from a channel",
                inline=False
            )
            
            embed.add_field(
                name="!twitch list",
                value="List all Twitch notifications",
                inline=False
            )
            
            embed.add_field(
                name="!twitch clear",
                value="Reset all Twitch notifications",
                inline=False
            )
            
            await ctx.send(embed=embed)
            return
        
        # Lookup a Twitch channel
        try:
            stream_info = await self.check_stream_status(username)
            
            if not stream_info:
                await ctx.send(f"Error looking up Twitch channel: {username}")
                return
                
            status = "🔴 LIVE" if stream_info['is_live'] else "⚫ Offline"
            
            embed = discord.Embed(
                title=f"{stream_info['display_name']} ({status})",
                url=f"https://twitch.tv/{username}",
                description=stream_info.get('title', "Currently offline") if stream_info['is_live'] else "Currently offline",
                color=discord.Color.purple()
            )
            
            if stream_info['is_live']:
                embed.add_field(name="Game", value=stream_info.get('game', "Unknown"), inline=True)
                embed.add_field(name="Viewers", value=f"{stream_info.get('viewer_count', 0):,}", inline=True)
            
            # This is a mock implementation
            embed.add_field(name="Followers", value=f"{1000:,}", inline=True)
            
            if stream_info.get('profile_image'):
                embed.set_thumbnail(url=stream_info['profile_image'])
                
            embed.set_footer(text="Twitch", icon_url="https://brand.twitch.tv/assets/images/favicon.png")
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"Error looking up Twitch channel: {str(e)}")
            logger.error(f"Error looking up Twitch channel {username}: {str(e)}")

    @twitch_group.command(name="add")
    @commands.has_permissions(manage_channels=True)
    async def twitch_add(self, ctx, username: str, channel: discord.TextChannel):
        """Add Twitch notifications to a channel"""
        guild_id = str(ctx.guild.id)
        
        if guild_id not in self.twitch_config:
            self.twitch_config[guild_id] = {}
            
        if "channels" not in self.twitch_config[guild_id]:
            self.twitch_config[guild_id]["channels"] = {}
            
        channel_id = str(channel.id)
        if channel_id not in self.twitch_config[guild_id]["channels"]:
            self.twitch_config[guild_id]["channels"][channel_id] = []
            
        if username.lower() not in [name.lower() for name in self.twitch_config[guild_id]["channels"][channel_id]]:
            self.twitch_config[guild_id]["channels"][channel_id].append(username)
            await ctx.send(f"✅ Added Twitch notifications for `{username}` in {channel.mention}")
        else:
            await ctx.send(f"Twitch notifications for `{username}` already exist in {channel.mention}")
            
        self.save_config()

    @twitch_group.command(name="remove")
    @commands.has_permissions(manage_channels=True)
    async def twitch_remove(self, ctx, username: str, channel: discord.TextChannel):
        """Remove Twitch notifications from a channel"""
        guild_id = str(ctx.guild.id)
        channel_id = str(channel.id)
        
        if (guild_id in self.twitch_config and 
            "channels" in self.twitch_config[guild_id] and 
            channel_id in self.twitch_config[guild_id]["channels"]):
            
            streamers = self.twitch_config[guild_id]["channels"][channel_id]
            for i, name in enumerate(streamers):
                if name.lower() == username.lower():
                    self.twitch_config[guild_id]["channels"][channel_id].pop(i)
                    await ctx.send(f"✅ Removed Twitch notifications for `{name}` from {channel.mention}")
                    
                    # Clean up empty entries
                    if not self.twitch_config[guild_id]["channels"][channel_id]:
                        del self.twitch_config[guild_id]["channels"][channel_id]
                    if not self.twitch_config[guild_id]["channels"]:
                        del self.twitch_config[guild_id]["channels"]
                    if not self.twitch_config[guild_id]:
                        del self.twitch_config[guild_id]
                        
                    self.save_config()
                    return
                    
            await ctx.send(f"No Twitch notifications for `{username}` found in {channel.mention}")
        else:
            await ctx.send(f"No Twitch notifications found in {channel.mention}")

    @twitch_group.command(name="list")
    @commands.has_permissions(manage_channels=True)
    async def twitch_list(self, ctx):
        """List all Twitch notifications"""
        guild_id = str(ctx.guild.id)
        
        if (guild_id not in self.twitch_config or 
            "channels" not in self.twitch_config[guild_id] or 
            not self.twitch_config[guild_id]["channels"]):
            await ctx.send("No Twitch notifications set up in this server.")
            return
            
        embed = discord.Embed(
            title="Twitch Stream Notifications", 
            color=discord.Color.purple(),
            description="List of channels with Twitch stream notifications"
        )
        
        for channel_id, streamers in self.twitch_config[guild_id]["channels"].items():
            channel = self.bot.get_channel(int(channel_id))
            if channel:
                streamers_formatted = ", ".join([f"`{name}`" for name in streamers]) if streamers else "None"
                embed.add_field(
                    name=f"#{channel.name}", 
                    value=streamers_formatted, 
                    inline=False
                )
                
        await ctx.send(embed=embed)

    @twitch_group.command(name="clear")
    @commands.has_permissions(manage_channels=True)
    async def twitch_clear(self, ctx):
        """Reset all Twitch notifications"""
        guild_id = str(ctx.guild.id)
        
        if guild_id in self.twitch_config:
            del self.twitch_config[guild_id]
            self.save_config()
            await ctx.send("✅ All Twitch stream notifications have been reset.")
        else:
            await ctx.send("No Twitch stream notifications found for this server.")

    @twitch_group.command(name="message")
    @commands.has_permissions(manage_channels=True)
    async def twitch_message(self, ctx, username: str = None, *, message: str = None):
        """Set a message for Twitch notifications"""
        if username is None or message is None:
            embed = discord.Embed(
                title="Twitch Message Command",
                description="Set a custom message for a streamer's notifications\n\n"
                           "Available variables:\n"
                           "`{username}` - Streamer's username\n"
                           "`{title}` - Stream title\n"
                           "`{game}` - Game being played\n"
                           "`{viewers}` - Current viewer count\n"
                           "`{url}` - Stream URL",
                color=discord.Color.purple()
            )
            
            embed.add_field(
                name="Example",
                value="!twitch message ninja {username} is playing {game} with {viewers} viewers! {url}",
                inline=False
            )
            
            await ctx.send(embed=embed)
            return
            
        guild_id = str(ctx.guild.id)
        
        if guild_id not in self.twitch_config:
            self.twitch_config[guild_id] = {}
            
        if "messages" not in self.twitch_config[guild_id]:
            self.twitch_config[guild_id]["messages"] = {}
            
        self.twitch_config[guild_id]["messages"][username.lower()] = message
        self.save_config()
        
        await ctx.send(f"✅ Set custom notification message for `{username}` streams")
        
async def setup(bot):
    await bot.add_cog(TwitchCommands(bot)) 