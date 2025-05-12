import discord
from discord.ext import commands, tasks
import json
import os
import logging
import aiohttp
import asyncio
from datetime import datetime, timedelta

logger = logging.getLogger('bot')

class YouTubeCommands(commands.Cog):
    """Commands for YouTube feed notifications"""
    
    def __init__(self, bot):
        self.bot = bot
        self.data_folder = 'data'
        self.config_file = os.path.join(self.data_folder, 'youtube_config.json')
        self.youtube_config = self.load_config()
        
        # Check interval for new videos (default: 30 minutes)
        self.check_interval = 30 * 60  
        self.last_video_data = {}  # youtube_id -> {video_ids: []}
        
        # Start the background task
        self.check_new_videos.start()
        
    def load_config(self):
        """Load the YouTube configuration from file"""
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
        """Save the YouTube configuration to file"""
        with open(self.config_file, 'w') as f:
            json.dump(self.youtube_config, f, indent=4)
            
    def cog_unload(self):
        """Clean up when the cog is unloaded"""
        self.check_new_videos.cancel()
        
    async def get_channel_id(self, username):
        """Get the YouTube channel ID for a username or channel URL"""
        # Simplified version - in production this would use the YouTube API
        # For now, we'll just use the username as the ID
        return username.strip().lower()
    
    async def get_latest_videos(self, channel_id, limit=5):
        """Get the latest videos for a YouTube channel"""
        # In a real implementation, this would use the YouTube API
        # For now we'll return mock data
        
        # Example mock response
        mock_videos = [
            {
                'id': f"{channel_id}_video_{i}",
                'title': f"Video Title {i} for {channel_id}",
                'url': f"https://www.youtube.com/watch?v={channel_id}_video_{i}",
                'published_at': (datetime.now() - timedelta(days=i)).isoformat(),
                'thumbnail': f"https://img.youtube.com/vi/{channel_id}_video_{i}/maxresdefault.jpg"
            }
            for i in range(1, limit+1)
        ]
        
        return mock_videos
        
    @tasks.loop(minutes=30)
    async def check_new_videos(self):
        """Check for new videos and send notifications"""
        logger.info("Checking for new YouTube videos...")
        
        all_channels = set()
        
        # Collect all YouTube channels across all guilds
        for guild_id, guild_data in self.youtube_config.items():
            if "channels" in guild_data:
                for discord_channel_id, youtube_channels in guild_data["channels"].items():
                    all_channels.update(youtube_channels)
        
        if not all_channels:
            return
            
        for youtube_channel in all_channels:
            try:
                channel_id = await self.get_channel_id(youtube_channel)
                latest_videos = await self.get_latest_videos(channel_id, limit=3)
                
                # Initialize if this is a new channel
                if channel_id not in self.last_video_data:
                    self.last_video_data[channel_id] = {
                        'video_ids': [video['id'] for video in latest_videos]
                    }
                    continue
                
                # Get previously seen video IDs
                known_video_ids = self.last_video_data[channel_id]['video_ids']
                
                # Find new videos
                for video in latest_videos:
                    if video['id'] not in known_video_ids:
                        await self.send_video_notifications(youtube_channel, video)
                        known_video_ids.append(video['id'])
                
                # Update last video data (keep only last 20 videos to prevent unlimited growth)
                self.last_video_data[channel_id]['video_ids'] = known_video_ids[:20]
                
                # Small delay between API calls to avoid rate limits
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.error(f"Error checking videos for {youtube_channel}: {str(e)}")
    
    @check_new_videos.before_loop
    async def before_check_new_videos(self):
        """Wait until the bot is ready before starting the task"""
        await self.bot.wait_until_ready()
        logger.info("Starting YouTube video check task")
    
    async def send_video_notifications(self, youtube_channel, video):
        """Send notifications for a new video"""
        youtube_channel_lower = youtube_channel.lower()
        
        for guild_id, guild_data in self.youtube_config.items():
            if "channels" not in guild_data:
                continue
                
            for discord_channel_id, youtube_channels in guild_data["channels"].items():
                if youtube_channel_lower not in [c.lower() for c in youtube_channels]:
                    continue
                    
                # Get the Discord channel
                channel = self.bot.get_channel(int(discord_channel_id))
                if not channel:
                    logger.warning(f"Channel {discord_channel_id} not found, skipping")
                    continue
                
                # Create embed
                embed = discord.Embed(
                    title=video['title'],
                    url=video['url'],
                    description=f"**{youtube_channel}** has uploaded a new video!",
                    color=discord.Color.red(),
                    timestamp=datetime.now()
                )
                
                if video['thumbnail']:
                    embed.set_image(url=video['thumbnail'])
                    
                embed.set_footer(text="YouTube", icon_url="https://www.youtube.com/s/desktop/abfca16e/img/favicon_144x144.png")
                
                # Get custom message if set
                custom_message = None
                if "messages" in guild_data and youtube_channel_lower in guild_data["messages"]:
                    custom_message = guild_data["messages"][youtube_channel_lower]
                
                # Format the message content
                content = custom_message or f"🔴 **{youtube_channel}** has uploaded a new video!"
                
                # Send notification
                try:
                    await channel.send(content=content, embed=embed)
                    logger.info(f"Sent video notification for {youtube_channel} in guild {guild_id}, channel {discord_channel_id}")
                except Exception as e:
                    logger.error(f"Error sending notification: {str(e)}")
                
                # Small delay between notifications
                await asyncio.sleep(1)
            
    @commands.group(name="staryoutube", invoke_without_command=True)
    async def youtube_group(self, ctx, url: str = None):
        """Repost a YouTube post or follow a channel's post feed"""
        if url is None:
            embed = discord.Embed(
                title="YouTube Commands",
                description="Manage YouTube feed notifications",
                color=discord.Color.red()
            )
            
            embed.add_field(
                name="!staryoutube [url]",
                value="Repost a YouTube video",
                inline=False
            )
            
            embed.add_field(
                name="!staryoutube add [user] [channel]",
                value="Add YouTube user to feed posts into a channel",
                inline=False
            )
            
            embed.add_field(
                name="!staryoutube remove [username] [channel]",
                value="Remove a user from a channel's YouTube feed",
                inline=False
            )
            
            embed.add_field(
                name="!staryoutube list",
                value="List YouTube feed channels",
                inline=False
            )
            
            embed.add_field(
                name="!staryoutube clear",
                value="Reset all YouTube feeds that have been setup",
                inline=False
            )
            
            await ctx.send(embed=embed)
            return
            
        # If URL is provided, handle video reposting
        try:
            # This would be an actual YouTube API call in production
            # For now, just create a mock response
            
            video_info = {
                'title': "Example YouTube Video",
                'url': url,
                'thumbnail': "https://img.youtube.com/vi/example/maxresdefault.jpg",
                'channel': "Example Channel",
                'published_at': datetime.now().strftime("%Y-%m-%d")
            }
            
            embed = discord.Embed(
                title=video_info['title'],
                url=video_info['url'],
                description=f"Video by **{video_info['channel']}**",
                color=discord.Color.red()
            )
            
            embed.set_image(url=video_info['thumbnail'])
            embed.set_footer(text=f"Published on {video_info['published_at']} • YouTube")
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"Error processing YouTube URL: {str(e)}")
            logger.error(f"Error processing YouTube URL {url}: {str(e)}")

    @youtube_group.command(name="clear")
    @commands.has_permissions(manage_channels=True)
    async def youtube_clear(self, ctx):
        """Reset all YouTube feeds that have been setup"""
        guild_id = str(ctx.guild.id)
        
        if guild_id in self.youtube_config:
            del self.youtube_config[guild_id]
            self.save_config()
            await ctx.send("✅ All YouTube feed configurations have been reset.")
        else:
            await ctx.send("No YouTube feed configurations found for this server.")

    @youtube_group.command(name="add")
    @commands.has_permissions(manage_channels=True)
    async def youtube_add(self, ctx, user: str, channel: discord.TextChannel):
        """Add a YouTube user to feed posts into a channel"""
        guild_id = str(ctx.guild.id)
        
        if guild_id not in self.youtube_config:
            self.youtube_config[guild_id] = {}
            
        if "channels" not in self.youtube_config[guild_id]:
            self.youtube_config[guild_id]["channels"] = {}
            
        channel_id = str(channel.id)
        if channel_id not in self.youtube_config[guild_id]["channels"]:
            self.youtube_config[guild_id]["channels"][channel_id] = []
            
        if user.lower() not in [name.lower() for name in self.youtube_config[guild_id]["channels"][channel_id]]:
            self.youtube_config[guild_id]["channels"][channel_id].append(user)
            await ctx.send(f"✅ Added YouTube notifications for `{user}` in {channel.mention}")
        else:
            await ctx.send(f"YouTube notifications for `{user}` already exist in {channel.mention}")
            
        self.save_config()

    @youtube_group.command(name="remove")
    @commands.has_permissions(manage_channels=True)
    async def youtube_remove(self, ctx, username: str, channel: discord.TextChannel):
        """Remove a user from a channel's YouTube feed"""
        guild_id = str(ctx.guild.id)
        channel_id = str(channel.id)
        
        if (guild_id in self.youtube_config and 
            "channels" in self.youtube_config[guild_id] and 
            channel_id in self.youtube_config[guild_id]["channels"]):
            
            youtube_channels = self.youtube_config[guild_id]["channels"][channel_id]
            for i, name in enumerate(youtube_channels):
                if name.lower() == username.lower():
                    self.youtube_config[guild_id]["channels"][channel_id].pop(i)
                    await ctx.send(f"✅ Removed YouTube notifications for `{name}` from {channel.mention}")
                    
                    # Clean up empty entries
                    if not self.youtube_config[guild_id]["channels"][channel_id]:
                        del self.youtube_config[guild_id]["channels"][channel_id]
                    if not self.youtube_config[guild_id]["channels"]:
                        del self.youtube_config[guild_id]["channels"]
                    if not self.youtube_config[guild_id]:
                        del self.youtube_config[guild_id]
                        
                    self.save_config()
                    return
                    
            await ctx.send(f"No YouTube notifications for `{username}` found in {channel.mention}")
        else:
            await ctx.send(f"No YouTube notifications found in {channel.mention}")

    @youtube_group.command(name="list")
    @commands.has_permissions(manage_channels=True)
    async def youtube_list(self, ctx):
        """List YouTube feed channels"""
        guild_id = str(ctx.guild.id)
        
        if (guild_id not in self.youtube_config or 
            "channels" not in self.youtube_config[guild_id] or 
            not self.youtube_config[guild_id]["channels"]):
            await ctx.send("No YouTube notifications set up in this server.")
            return
            
        embed = discord.Embed(
            title="YouTube Feed Notifications", 
            color=discord.Color.red(),
            description="List of channels with YouTube feed notifications"
        )
        
        for channel_id, youtube_channels in self.youtube_config[guild_id]["channels"].items():
            channel = self.bot.get_channel(int(channel_id))
            if channel:
                channels_formatted = ", ".join([f"`{name}`" for name in youtube_channels]) if youtube_channels else "None"
                embed.add_field(
                    name=f"#{channel.name}", 
                    value=channels_formatted, 
                    inline=False
                )
                
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(YouTubeCommands(bot)) 