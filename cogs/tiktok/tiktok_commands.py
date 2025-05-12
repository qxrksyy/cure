import discord
from discord.ext import commands, tasks
import json
import os
import logging
import aiohttp
import asyncio
from datetime import datetime, timedelta

logger = logging.getLogger('bot')

class TikTokCommands(commands.Cog):
    """Commands for TikTok feed notifications"""
    
    def __init__(self, bot):
        self.bot = bot
        self.data_folder = 'data'
        self.config_file = os.path.join(self.data_folder, 'tiktok_config.json')
        self.tiktok_config = self.load_config()
        
        # Check interval for new posts (default: 30 minutes)
        self.check_interval = 30 * 60  
        self.last_video_data = {}  # username -> {video_ids: []}
        
        # Start the background task
        self.check_new_videos.start()
        
    def load_config(self):
        """Load the TikTok configuration from file"""
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
        """Save the TikTok configuration to file"""
        with open(self.config_file, 'w') as f:
            json.dump(self.tiktok_config, f, indent=4)
            
    def cog_unload(self):
        """Clean up when the cog is unloaded"""
        self.check_new_videos.cancel()
        
    async def get_user_info(self, username):
        """Get the TikTok user info for a username"""
        # In a real implementation, this would use the TikTok API
        # For now, we'll return mock data
        
        # Remove '@' from the username if present
        if username.startswith('@'):
            username = username[1:]
            
        return {
            'id': f"user_{username}",
            'username': username,
            'display_name': username.capitalize(),
            'profile_image': f"https://p16-sign.tiktokcdn-us.com/musically-maliva-obj/1594805258216454~c5_720x720.jpeg",
            'bio': f"This is {username}'s bio on TikTok",
            'following_count': 500,
            'followers_count': 1000,
            'likes_count': 5000,
            'verified': username.lower() in ['charlidamelio', 'khaby.lame', 'bellapoarch'],
        }
    
    async def get_latest_videos(self, username, limit=10):
        """Get the latest videos for a TikTok user"""
        # In a real implementation, this would use the TikTok API
        # For now we'll return mock data
        
        # Remove '@' from the username if present
        if username.startswith('@'):
            username = username[1:]
            
        # Example mock response
        mock_videos = [
            {
                'id': f"{username}_video_{i}",
                'desc': f"#{i} TikTok video by {username} #fyp #trend",
                'url': f"https://www.tiktok.com/@{username}/video/1000000000{i}",
                'created_at': (datetime.now() - timedelta(days=i)).isoformat(),
                'cover_image': f"https://p16-sign.tiktokcdn-us.com/obj/tos-useast5-p-0068-tx/sample_cover_{i}.jpg",
                'video_url': f"https://v16-webapp.tiktok.com/video/sample_{username}_{i}.mp4",
                'like_count': 10000 - i * 1000,
                'comment_count': 1000 - i * 100,
                'share_count': 500 - i * 50,
                'view_count': 100000 - i * 10000,
                'music': f"Original Sound - {username}",
                'duration': 15 + i % 15  # 15-30 seconds
            }
            for i in range(1, limit+1)
        ]
        
        return mock_videos
        
    @tasks.loop(minutes=30)
    async def check_new_videos(self):
        """Check for new videos and send notifications"""
        logger.info("Checking for new TikTok videos...")
        
        all_users = set()
        
        # Collect all TikTok users across all guilds
        for guild_id, guild_data in self.tiktok_config.items():
            if "channels" in guild_data:
                for discord_channel_id, tiktok_users in guild_data["channels"].items():
                    all_users.update([u.lower() for u in tiktok_users])
        
        if not all_users:
            return
            
        for tiktok_user in all_users:
            try:
                # Remove '@' from the username if present
                clean_username = tiktok_user[1:] if tiktok_user.startswith('@') else tiktok_user
                
                latest_videos = await self.get_latest_videos(clean_username, limit=5)
                
                # Initialize if this is a new user
                if clean_username not in self.last_video_data:
                    self.last_video_data[clean_username] = {
                        'video_ids': [video['id'] for video in latest_videos]
                    }
                    continue
                
                # Get previously seen video IDs
                known_video_ids = self.last_video_data[clean_username]['video_ids']
                
                # Find new videos
                for video in latest_videos:
                    if video['id'] not in known_video_ids:
                        await self.send_video_notifications(clean_username, video)
                        known_video_ids.append(video['id'])
                
                # Update last video data (keep only last 20 videos to prevent unlimited growth)
                self.last_video_data[clean_username]['video_ids'] = known_video_ids[:20]
                
                # Small delay between API calls to avoid rate limits
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.error(f"Error checking videos for {tiktok_user}: {str(e)}")
    
    @check_new_videos.before_loop
    async def before_check_new_videos(self):
        """Wait until the bot is ready before starting the task"""
        await self.bot.wait_until_ready()
        logger.info("Starting TikTok video check task")
    
    async def send_video_notifications(self, username, video):
        """Send notifications for a new video"""
        username_lower = username.lower()
        
        for guild_id, guild_data in self.tiktok_config.items():
            if "channels" not in guild_data:
                continue
                
            for discord_channel_id, tiktok_users in guild_data["channels"].items():
                if username_lower not in [u.lower() for u in tiktok_users]:
                    continue
                    
                # Get the Discord channel
                channel = self.bot.get_channel(int(discord_channel_id))
                if not channel:
                    logger.warning(f"Channel {discord_channel_id} not found, skipping")
                    continue
                
                # Create embed
                embed = discord.Embed(
                    title=f"New TikTok from @{username}",
                    url=video['url'],
                    description=video['desc'],
                    color=0xff0050,  # TikTok pink
                    timestamp=datetime.fromisoformat(video['created_at'])
                )
                
                user_info = await self.get_user_info(username)
                
                # Set author with profile image
                embed.set_author(
                    name=f"{user_info['display_name']} (@{username})",
                    icon_url=user_info['profile_image'],
                    url=f"https://www.tiktok.com/@{username}"
                )
                
                # Add stats to the footer
                embed.set_footer(
                    text=f"❤️ {video['like_count']:,} | 💬 {video['comment_count']:,} | 👁️ {video['view_count']:,}",
                    icon_url="https://sf16-scmcdn-sg.ibytedtos.com/goofy/tiktok/web/node/_next/static/images/logo-1d0074407.png"
                )
                
                # Add cover image
                if video['cover_image']:
                    embed.set_image(url=video['cover_image'])
                    
                # Add music field
                embed.add_field(
                    name="🎵 Music",
                    value=video['music'],
                    inline=True
                )
                
                # Add duration field
                embed.add_field(
                    name="⏱️ Duration",
                    value=f"{video['duration']} seconds",
                    inline=True
                )
                
                # Get custom message if set
                custom_message = None
                if "messages" in guild_data and username_lower in guild_data["messages"]:
                    custom_message = guild_data["messages"][username_lower]
                
                # Format the message content
                content = custom_message or f"🎵 New TikTok from **@{username}**"
                
                # Send notification
                try:
                    await channel.send(content=content, embed=embed)
                    logger.info(f"Sent TikTok notification for @{username} in guild {guild_id}, channel {discord_channel_id}")
                except Exception as e:
                    logger.error(f"Error sending notification: {str(e)}")
                
                # Small delay between notifications
                await asyncio.sleep(1)
            
    @commands.command(name="tiktok")
    async def tiktok_user(self, ctx, username: str = None):
        """Lookup a TikTok user or feed their posts into a channel"""
        if username is None:
            embed = discord.Embed(
                title="TikTok Commands",
                description="Manage TikTok feed notifications",
                color=0xff0050  # TikTok pink
            )
            
            embed.add_field(
                name="!tiktok [username]",
                value="Lookup a TikTok user",
                inline=False
            )
            
            embed.add_field(
                name="!startiktok add [username] [channel]",
                value="Add TikTok user to have their posts feeded into a channel",
                inline=False
            )
            
            embed.add_field(
                name="!startiktok remove [username] [channel]",
                value="Remove a user from a channel's TikTok feed",
                inline=False
            )
            
            embed.add_field(
                name="!startiktok list",
                value="List TikTok feed channels",
                inline=False
            )
            
            embed.add_field(
                name="!startiktok clear",
                value="Reset all TikTok feeds that have been setup",
                inline=False
            )
            
            await ctx.send(embed=embed)
            return
            
        # If username is provided, look up the user
        try:
            # Remove '@' from the username if present
            clean_username = username[1:] if username.startswith('@') else username
            
            user_info = await self.get_user_info(clean_username)
            latest_videos = await self.get_latest_videos(clean_username, limit=3)
            
            # Create main user info embed
            embed = discord.Embed(
                title=f"{user_info['display_name']} (@{user_info['username']})",
                url=f"https://www.tiktok.com/@{user_info['username']}",
                description=user_info['bio'],
                color=0xff0050  # TikTok pink
            )
            
            # Stats
            embed.add_field(
                name="Following",
                value=f"{user_info['following_count']:,}",
                inline=True
            )
            
            embed.add_field(
                name="Followers",
                value=f"{user_info['followers_count']:,}",
                inline=True
            )
            
            embed.add_field(
                name="Likes",
                value=f"{user_info['likes_count']:,}",
                inline=True
            )
            
            if user_info['verified']:
                embed.add_field(
                    name="Status",
                    value="✓ Verified",
                    inline=True
                )
            
            # Set thumbnail to profile image
            embed.set_thumbnail(url=user_info['profile_image'])
            
            # Set footer
            embed.set_footer(
                text="TikTok",
                icon_url="https://sf16-scmcdn-sg.ibytedtos.com/goofy/tiktok/web/node/_next/static/images/logo-1d0074407.png"
            )
            
            await ctx.send(embed=embed)
            
            # Send a few recent videos
            for video in latest_videos[:3]:
                video_embed = discord.Embed(
                    title=f"Video ({video['duration']} seconds)",
                    url=video['url'],
                    description=video['desc'],
                    color=0xff0050,  # TikTok pink
                    timestamp=datetime.fromisoformat(video['created_at'])
                )
                
                # Add cover image
                if video['cover_image']:
                    video_embed.set_image(url=video['cover_image'])
                
                # Add stats to the footer
                video_embed.set_footer(
                    text=f"❤️ {video['like_count']:,} | 💬 {video['comment_count']:,} | 👁️ {video['view_count']:,}",
                    icon_url="https://sf16-scmcdn-sg.ibytedtos.com/goofy/tiktok/web/node/_next/static/images/logo-1d0074407.png"
                )
                
                await ctx.send(embed=video_embed)
            
        except Exception as e:
            await ctx.send(f"Error looking up TikTok user: {str(e)}")
            logger.error(f"Error looking up TikTok user {username}: {str(e)}")

    @commands.group(name="startiktok", invoke_without_command=True)
    async def tiktok_group(self, ctx):
        """Group of TikTok commands for feed management"""
        embed = discord.Embed(
            title="TikTok Feed Commands",
            description="Manage TikTok feed notifications",
            color=0xff0050  # TikTok pink
        )
        
        embed.add_field(
            name="!startiktok add [username] [channel]",
            value="Add TikTok user to have their posts feeded into a channel",
            inline=False
        )
        
        embed.add_field(
            name="!startiktok remove [username] [channel]",
            value="Remove a user from a channel's TikTok feed",
            inline=False
        )
        
        embed.add_field(
            name="!startiktok list",
            value="List TikTok feed channels",
            inline=False
        )
        
        embed.add_field(
            name="!startiktok clear",
            value="Reset all TikTok feeds that have been setup",
            inline=False
        )
        
        await ctx.send(embed=embed)

    @tiktok_group.command(name="add")
    @commands.has_permissions(manage_channels=True)
    async def tiktok_add(self, ctx, username: str, channel: discord.TextChannel):
        """Add a TikTok user to have their posts feeded into a channel"""
        guild_id = str(ctx.guild.id)
        
        # Remove '@' from the username if present
        clean_username = username[1:] if username.startswith('@') else username
        
        if guild_id not in self.tiktok_config:
            self.tiktok_config[guild_id] = {}
            
        if "channels" not in self.tiktok_config[guild_id]:
            self.tiktok_config[guild_id]["channels"] = {}
            
        channel_id = str(channel.id)
        if channel_id not in self.tiktok_config[guild_id]["channels"]:
            self.tiktok_config[guild_id]["channels"][channel_id] = []
            
        if clean_username.lower() not in [name.lower() for name in self.tiktok_config[guild_id]["channels"][channel_id]]:
            self.tiktok_config[guild_id]["channels"][channel_id].append(clean_username)
            await ctx.send(f"✅ Added TikTok feed for `@{clean_username}` in {channel.mention}")
        else:
            await ctx.send(f"TikTok feed for `@{clean_username}` already exists in {channel.mention}")
            
        self.save_config()

    @tiktok_group.command(name="remove")
    @commands.has_permissions(manage_channels=True)
    async def tiktok_remove(self, ctx, username: str, channel: discord.TextChannel):
        """Remove a user from a channel's TikTok feed"""
        guild_id = str(ctx.guild.id)
        channel_id = str(channel.id)
        
        # Remove '@' from the username if present
        clean_username = username[1:] if username.startswith('@') else username
        
        if (guild_id in self.tiktok_config and 
            "channels" in self.tiktok_config[guild_id] and 
            channel_id in self.tiktok_config[guild_id]["channels"]):
            
            tiktok_users = self.tiktok_config[guild_id]["channels"][channel_id]
            for i, name in enumerate(tiktok_users):
                if name.lower() == clean_username.lower():
                    self.tiktok_config[guild_id]["channels"][channel_id].pop(i)
                    await ctx.send(f"✅ Removed TikTok feed for `@{name}` from {channel.mention}")
                    
                    # Clean up empty entries
                    if not self.tiktok_config[guild_id]["channels"][channel_id]:
                        del self.tiktok_config[guild_id]["channels"][channel_id]
                    if not self.tiktok_config[guild_id]["channels"]:
                        del self.tiktok_config[guild_id]["channels"]
                    if not self.tiktok_config[guild_id]:
                        del self.tiktok_config[guild_id]
                        
                    self.save_config()
                    return
                    
            await ctx.send(f"No TikTok feed for `@{clean_username}` found in {channel.mention}")
        else:
            await ctx.send(f"No TikTok feeds found in {channel.mention}")

    @tiktok_group.command(name="list")
    @commands.has_permissions(manage_channels=True)
    async def tiktok_list(self, ctx):
        """List TikTok feed channels"""
        guild_id = str(ctx.guild.id)
        
        if (guild_id not in self.tiktok_config or 
            "channels" not in self.tiktok_config[guild_id] or 
            not self.tiktok_config[guild_id]["channels"]):
            await ctx.send("No TikTok feeds set up in this server.")
            return
            
        embed = discord.Embed(
            title="TikTok Feed Notifications", 
            color=0xff0050,  # TikTok pink
            description="List of channels with TikTok feed notifications"
        )
        
        for channel_id, tiktok_users in self.tiktok_config[guild_id]["channels"].items():
            channel = self.bot.get_channel(int(channel_id))
            if channel:
                users_formatted = ", ".join([f"`@{name}`" for name in tiktok_users]) if tiktok_users else "None"
                embed.add_field(
                    name=f"#{channel.name}", 
                    value=users_formatted, 
                    inline=False
                )
                
        await ctx.send(embed=embed)

    @tiktok_group.command(name="clear")
    @commands.has_permissions(manage_channels=True)
    async def tiktok_clear(self, ctx):
        """Reset all TikTok feeds that have been setup"""
        guild_id = str(ctx.guild.id)
        
        if guild_id in self.tiktok_config:
            del self.tiktok_config[guild_id]
            self.save_config()
            await ctx.send("✅ All TikTok feed configurations have been reset.")
        else:
            await ctx.send("No TikTok feed configurations found for this server.")

async def setup(bot):
    await bot.add_cog(TikTokCommands(bot)) 