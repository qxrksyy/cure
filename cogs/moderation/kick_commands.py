import discord
from discord.ext import commands, tasks
import json
import os
import logging
import aiohttp
import asyncio
from datetime import datetime

logger = logging.getLogger('bot')

class KickCommands(commands.Cog):
    """Commands for Kick.com stream notifications"""
    
    def __init__(self, bot):
        self.bot = bot
        self.data_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'data')
        self.config_file = os.path.join(self.data_folder, 'kick_config.json')
        self.kick_config = self.load_config()
        
        # Stream check settings
        self.check_interval = 5 * 60  # 5 minutes
        self.user_stream_status = {}  # username -> {is_live, last_checked}
        
        # Start the background task
        self.check_live_streams.start()
        
    def load_config(self):
        """Load the kick configuration from file"""
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
        """Save the kick configuration to file"""
        with open(self.config_file, 'w') as f:
            json.dump(self.kick_config, f, indent=4)
            
    def cog_unload(self):
        """Clean up when the cog is unloaded"""
        self.check_live_streams.cancel()
        
    async def check_stream_status(self, username):
        """Check if a Kick.com user is currently streaming"""
        try:
            # Kick.com API endpoint (unofficial)
            url = f"https://kick.com/api/v1/channels/{username}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status != 200:
                        logger.warning(f"Failed to get stream status for {username}. Status code: {response.status}")
                        return None
                    
                    try:
                        data = await response.json()
                        is_live = data.get('livestream') is not None
                        
                        return {
                            'is_live': is_live,
                            'title': data.get('livestream', {}).get('session_title', 'No Title') if is_live else None,
                            'game': data.get('livestream', {}).get('categories', [{}])[0].get('name', 'No Game') if is_live else None,
                            'viewer_count': data.get('livestream', {}).get('viewer_count', 0) if is_live else 0,
                            'thumbnail': data.get('livestream', {}).get('thumbnail', {}).get('url') if is_live else None,
                            'started_at': data.get('livestream', {}).get('created_at') if is_live else None,
                            'streamer_name': data.get('user', {}).get('username', username),
                            'avatar': data.get('user', {}).get('profile_pic')
                        }
                    except (KeyError, ValueError, json.JSONDecodeError) as e:
                        logger.error(f"Error parsing JSON response for {username}: {str(e)}")
                        return None
        except asyncio.TimeoutError:
            logger.warning(f"Timeout while checking stream status for {username}")
            return None
        except aiohttp.ClientError as e:
            logger.error(f"HTTP client error checking stream status for {username}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error checking stream status for {username}: {str(e)}")
            return None
    
    @tasks.loop(minutes=5)
    async def check_live_streams(self):
        """Check for live streams and send notifications"""
        logger.info("Checking for Kick.com live streams...")
        
        try:
            all_usernames = set()
            
            # Collect all usernames across all guilds and channels
            for guild_id, guild_data in self.kick_config.items():
                if "channels" in guild_data:
                    for channel_id, usernames in guild_data["channels"].items():
                        all_usernames.update([u.lower() for u in usernames])
            
            if not all_usernames:
                logger.info("No Kick.com channels to check.")
                return
                
            logger.info(f"Checking {len(all_usernames)} Kick.com channels...")
            
            for username in all_usernames:
                try:
                    # Check if user is streaming
                    stream_info = await self.check_stream_status(username)
                    
                    if not stream_info:
                        logger.debug(f"Could not get stream info for {username}")
                        continue
                        
                    was_live = self.user_stream_status.get(username, {}).get('is_live', False)
                    currently_live = stream_info['is_live']
                    
                    # Only notify if stream just started (changed from offline to online)
                    if currently_live and not was_live:
                        logger.info(f"{username} just went live! Sending notifications...")
                        await self.send_stream_notifications(username, stream_info)
                    elif currently_live and was_live:
                        logger.debug(f"{username} is still live with {stream_info.get('viewer_count', 0)} viewers")
                    elif not currently_live and was_live:
                        logger.info(f"{username} just went offline")
                    
                    # Update status cache
                    self.user_stream_status[username] = {
                        'is_live': currently_live,
                        'last_checked': datetime.now().isoformat(),
                        'viewer_count': stream_info.get('viewer_count', 0) if currently_live else 0
                    }
                    
                    # Small delay between API calls to avoid rate limits
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    logger.error(f"Error processing stream status for {username}: {str(e)}")
                    # Continue checking other streamers even if one fails
                    continue
        except Exception as e:
            logger.error(f"Critical error in check_live_streams task: {str(e)}")
            # Don't let the task die, just report the error
    
    @check_live_streams.before_loop
    async def before_check_live_streams(self):
        """Wait until the bot is ready before starting the task"""
        await self.bot.wait_until_ready()
        logger.info("Starting Kick.com stream check task")
    
    async def send_stream_notifications(self, username, stream_info):
        """Send notifications for a live stream"""
        username_lower = username.lower()
        
        for guild_id, guild_data in self.kick_config.items():
            if "channels" not in guild_data:
                continue
                
            for channel_id, usernames in guild_data["channels"].items():
                if username_lower not in [u.lower() for u in usernames]:
                    continue
                    
                # Get the channel
                try:
                    channel = self.bot.get_channel(int(channel_id))
                    if not channel:
                        guild = self.bot.get_guild(int(guild_id))
                        if guild:
                            # Try to fetch the channel if it's not in cache
                            try:
                                channel = await guild.fetch_channel(int(channel_id))
                            except discord.NotFound:
                                logger.warning(f"Channel {channel_id} not found in guild {guild_id}, skipping")
                                continue
                            except Exception as e:
                                logger.error(f"Error fetching channel {channel_id}: {str(e)}")
                                continue
                        else:
                            logger.warning(f"Guild {guild_id} not found, skipping")
                            continue
                    
                    # Get custom message if set
                    custom_message = None
                    if "messages" in guild_data and username_lower in guild_data["messages"]:
                        custom_message = guild_data["messages"][username_lower]
                    
                    # Create embed
                    embed = discord.Embed(
                        title=stream_info['title'] or "Live Stream",
                        url=f"https://kick.com/{username}",
                        description=f"**{stream_info['streamer_name']}** is now live on Kick.com!",
                        color=discord.Color.purple(),
                        timestamp=datetime.now()
                    )
                    
                    if stream_info['game']:
                        embed.add_field(name="Game", value=stream_info['game'], inline=True)
                        
                    embed.add_field(name="Viewers", value=f"{stream_info['viewer_count']:,}", inline=True)
                    
                    if stream_info['thumbnail']:
                        embed.set_image(url=stream_info['thumbnail'])
                        
                    if stream_info['avatar']:
                        embed.set_author(
                            name=stream_info['streamer_name'],
                            icon_url=stream_info['avatar'],
                            url=f"https://kick.com/{username}"
                        )
                    
                    embed.set_footer(text="Kick.com", icon_url="https://assets.kick.com/images/favicon/apple-touch-icon.png")
                    
                    # Format the message content with stream information
                    content = self.format_message(custom_message, stream_info) if custom_message else f"🔴 **{stream_info['streamer_name']}** is now live on Kick.com!"
                    
                    # Send notification with retry logic
                    max_retries = 3
                    for attempt in range(max_retries):
                        try:
                            await channel.send(content=content, embed=embed)
                            logger.info(f"Sent stream notification for {username} in guild {guild_id}, channel {channel_id}")
                            break
                        except discord.Forbidden:
                            logger.error(f"No permission to send messages in channel {channel_id} of guild {guild_id}")
                            break  # Don't retry permission errors
                        except Exception as e:
                            if attempt < max_retries - 1:
                                retry_delay = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                                logger.warning(f"Error sending notification, retrying in {retry_delay}s: {str(e)}")
                                await asyncio.sleep(retry_delay)
                            else:
                                logger.error(f"Failed to send notification after {max_retries} attempts: {str(e)}")
                    
                except Exception as e:
                    logger.error(f"Unexpected error processing notification for channel {channel_id}: {str(e)}")
                
                # Small delay between notifications
                await asyncio.sleep(1)
            
    def format_message(self, message_template, stream_info):
        """Format a message with stream information"""
        try:
            # Replace placeholders with stream information
            return message_template.format(
                username=stream_info['streamer_name'],
                title=stream_info['title'] or "Live Stream",
                game=stream_info['game'] or "No Game",
                viewers=stream_info['viewer_count'],
                url=f"https://kick.com/{stream_info['streamer_name'].lower()}"
            )
        except KeyError as e:
            logger.error(f"Missing key in stream_info: {str(e)}")
            return f"🔴 **{stream_info.get('streamer_name', 'Unknown')}** is now live on Kick.com!"
        except (ValueError, IndexError) as e:
            logger.error(f"Error formatting message template: {str(e)}")
            return f"🔴 **{stream_info.get('streamer_name', 'Unknown')}** is now live on Kick.com!"
        except Exception as e:
            logger.error(f"Unexpected error formatting message: {str(e)}")
            return f"🔴 Live stream started on Kick.com!"
            
    @commands.group(name="kick", invoke_without_command=True)
    async def kick_group(self, ctx):
        """Group of Kick.com commands for stream notifications"""
        embed = discord.Embed(
            title="Kick Commands",
            description="Manage Kick.com stream notifications",
            color=discord.Color.purple()
        )
        
        embed.add_field(
            name="!kick add [channel] [username]",
            value="Add stream notifications to channel",
            inline=False
        )
        
        embed.add_field(
            name="!kick remove [channel] [username]",
            value="Remove stream notifications from a channel",
            inline=False
        )
        
        embed.add_field(
            name="!kick list",
            value="View all Kick stream notifications",
            inline=False
        )
        
        embed.add_field(
            name="!kick message [username] [message]",
            value="Set a message for Kick notifications",
            inline=False
        )
        
        embed.add_field(
            name="!kick message view [username]",
            value="View Kick message for new streams",
            inline=False
        )
        
        await ctx.send(embed=embed)
            
    @kick_group.command(name="add")
    @commands.has_permissions(manage_guild=True)
    async def kick_add(self, ctx, channel: discord.TextChannel, username: str):
        """Add stream notifications to channel"""
        guild_id = str(ctx.guild.id)
        
        if guild_id not in self.kick_config:
            self.kick_config[guild_id] = {}
            
        if "channels" not in self.kick_config[guild_id]:
            self.kick_config[guild_id]["channels"] = {}
            
        channel_id = str(channel.id)
        if channel_id not in self.kick_config[guild_id]["channels"]:
            self.kick_config[guild_id]["channels"][channel_id] = []
            
        if username.lower() not in [name.lower() for name in self.kick_config[guild_id]["channels"][channel_id]]:
            self.kick_config[guild_id]["channels"][channel_id].append(username)
            await ctx.send(f"Added Kick.com notifications for `{username}` in {channel.mention}")
        else:
            await ctx.send(f"Kick.com notifications for `{username}` already exist in {channel.mention}")
            
        self.save_config()

    @kick_group.command(name="remove")
    @commands.has_permissions(manage_guild=True)
    async def kick_remove(self, ctx, channel: discord.TextChannel, username: str):
        """Remove stream notifications from a channel"""
        guild_id = str(ctx.guild.id)
        channel_id = str(channel.id)
        
        if (guild_id in self.kick_config and 
            "channels" in self.kick_config[guild_id] and 
            channel_id in self.kick_config[guild_id]["channels"]):
            
            usernames = self.kick_config[guild_id]["channels"][channel_id]
            for i, name in enumerate(usernames):
                if name.lower() == username.lower():
                    self.kick_config[guild_id]["channels"][channel_id].pop(i)
                    await ctx.send(f"Removed Kick.com notifications for `{name}` from {channel.mention}")
                    
                    # Clean up empty entries
                    if not self.kick_config[guild_id]["channels"][channel_id]:
                        del self.kick_config[guild_id]["channels"][channel_id]
                    if not self.kick_config[guild_id]["channels"]:
                        del self.kick_config[guild_id]["channels"]
                    if not self.kick_config[guild_id]:
                        del self.kick_config[guild_id]
                        
                    self.save_config()
                    return
                    
            await ctx.send(f"No Kick.com notifications for `{username}` found in {channel.mention}")
        else:
            await ctx.send(f"No Kick.com notifications found in {channel.mention}")

    @kick_group.command(name="list")
    @commands.has_permissions(manage_guild=True)
    async def kick_list(self, ctx):
        """View all Kick stream notifications"""
        guild_id = str(ctx.guild.id)
        
        if (guild_id not in self.kick_config or 
            "channels" not in self.kick_config[guild_id] or 
            not self.kick_config[guild_id]["channels"]):
            await ctx.send("No Kick.com notifications set up in this server.")
            return
            
        embed = discord.Embed(
            title="Kick.com Stream Notifications", 
            color=discord.Color.purple(),
            description="List of channels with Kick.com stream notifications"
        )
        
        for channel_id, usernames in self.kick_config[guild_id]["channels"].items():
            channel = self.bot.get_channel(int(channel_id))
            if channel:
                usernames_formatted = ", ".join([f"`{name}`" for name in usernames]) if usernames else "None"
                embed.add_field(
                    name=f"#{channel.name}", 
                    value=usernames_formatted, 
                    inline=False
                )
                
        await ctx.send(embed=embed)

    @kick_group.group(name="message", invoke_without_command=True)
    @commands.has_permissions(manage_guild=True)
    async def kick_message(self, ctx, username: str = None, *, message: str = None):
        """Set a message for Kick notifications"""
        if username is None or message is None:
            embed = discord.Embed(
                title="Kick Message Commands",
                description="Commands for managing Kick.com notification messages",
                color=discord.Color.purple()
            )
            
            embed.add_field(
                name="!kick message [username] [message]",
                value="Set a custom message for a streamer's notifications",
                inline=False
            )
            
            embed.add_field(
                name="!kick message view [username]",
                value="View the custom message for a streamer",
                inline=False
            )
            
            await ctx.send(embed=embed)
            return
            
        guild_id = str(ctx.guild.id)
        
        if guild_id not in self.kick_config:
            self.kick_config[guild_id] = {}
            
        if "messages" not in self.kick_config[guild_id]:
            self.kick_config[guild_id]["messages"] = {}
            
        self.kick_config[guild_id]["messages"][username.lower()] = message
        self.save_config()
        
        await ctx.send(f"Set custom notification message for `{username}` streams")
        
    @kick_message.command(name="view")
    @commands.has_permissions(manage_guild=True)
    async def kick_message_view(self, ctx, username: str):
        """View Kick message for new streams"""
        guild_id = str(ctx.guild.id)
        username = username.lower()
        
        if (guild_id in self.kick_config and 
            "messages" in self.kick_config[guild_id] and 
            username in self.kick_config[guild_id]["messages"]):
            
            message = self.kick_config[guild_id]["messages"][username]
            embed = discord.Embed(
                title=f"Notification Message for {username}",
                description=message,
                color=discord.Color.purple()
            )
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"No custom message set for `{username}`")

async def setup(bot):
    await bot.add_cog(KickCommands(bot)) 