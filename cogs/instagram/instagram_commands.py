import discord
from discord.ext import commands, tasks
import json
import os
import logging
import aiohttp
import asyncio
from datetime import datetime, timedelta

logger = logging.getLogger('bot')

class InstagramCommands(commands.Cog):
    """Commands for Instagram feed notifications"""
    
    def __init__(self, bot):
        self.bot = bot
        self.data_folder = 'data'
        self.config_file = os.path.join(self.data_folder, 'instagram_config.json')
        self.instagram_config = self.load_config()
        
        # Check interval for new posts (default: 30 minutes)
        self.check_interval = 30 * 60  
        self.last_post_data = {}  # username -> {post_ids: []}
        
        # Start the background task
        self.check_new_posts.start()
        
    def load_config(self):
        """Load the Instagram configuration from file"""
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
        """Save the Instagram configuration to file"""
        with open(self.config_file, 'w') as f:
            json.dump(self.instagram_config, f, indent=4)
            
    def cog_unload(self):
        """Clean up when the cog is unloaded"""
        self.check_new_posts.cancel()
        
    async def get_user_info(self, username):
        """Get the Instagram user info for a username"""
        # In a real implementation, this would use the Instagram API
        # For now, we'll return mock data
        
        # Remove '@' from the username if present
        if username.startswith('@'):
            username = username[1:]
            
        return {
            'id': f"user_{username}",
            'username': username,
            'full_name': username.capitalize(),
            'profile_pic_url': f"https://instagram.fbna1-1.fna.fbcdn.net/v/t51.2885-19/sample_profile_{username}.jpg",
            'biography': f"This is {username}'s bio on Instagram",
            'following_count': 800,
            'follower_count': 1500,
            'media_count': 120,
            'is_private': False,
            'is_verified': username.lower() in ['kimkardashian', 'therock', 'cristiano'],
            'external_url': f"https://www.{username}.com" if username.lower() not in ['instagram', 'facebook'] else None,
        }
    
    async def get_recent_posts(self, username, limit=10):
        """Get the recent posts for an Instagram user"""
        # In a real implementation, this would use the Instagram API
        # For now we'll return mock data
        
        # Remove '@' from the username if present
        if username.startswith('@'):
            username = username[1:]
            
        # Example mock response
        mock_posts = [
            {
                'id': f"{username}_post_{i}",
                'shortcode': f"B{i}X{username[:2].upper()}",
                'caption': f"Post #{i} by {username} 📸 #instagram #photography",
                'permalink': f"https://www.instagram.com/p/B{i}X{username[:2].upper()}/",
                'created_at': (datetime.now() - timedelta(days=i)).isoformat(),
                'image_url': f"https://instagram.fbna1-1.fna.fbcdn.net/v/t51.2885-15/sample_post_{username}_{i}.jpg",
                'thumbnail_url': f"https://instagram.fbna1-1.fna.fbcdn.net/v/t51.2885-15/sample_thumb_{username}_{i}.jpg",
                'like_count': 15000 - i * 1000,
                'comment_count': 1200 - i * 100,
                'is_video': i % 3 == 0,  # Every third post is a video
                'video_url': f"https://instagram.fbna1-1.fna.fbcdn.net/v/t50.16885-16/sample_video_{username}_{i}.mp4" if i % 3 == 0 else None,
                'location': {"name": f"Location {i}", "city": "Los Angeles", "country": "USA"} if i % 2 == 0 else None,
                'is_carousel': i % 5 == 0,  # Every fifth post is a carousel
                'carousel_media': [
                    {
                        'image_url': f"https://instagram.fbna1-1.fna.fbcdn.net/v/t51.2885-15/sample_carousel_{username}_{i}_{j}.jpg",
                        'is_video': False
                    } for j in range(1, 4)
                ] if i % 5 == 0 else None,
            }
            for i in range(1, limit+1)
        ]
        
        return mock_posts
        
    @tasks.loop(minutes=30)
    async def check_new_posts(self):
        """Check for new posts and send notifications"""
        logger.info("Checking for new Instagram posts...")
        
        all_users = set()
        
        # Collect all Instagram users across all guilds
        for guild_id, guild_data in self.instagram_config.items():
            if "channels" in guild_data:
                for discord_channel_id, instagram_users in guild_data["channels"].items():
                    all_users.update([u.lower() for u in instagram_users])
        
        if not all_users:
            return
            
        for instagram_user in all_users:
            try:
                # Remove '@' from the username if present
                clean_username = instagram_user[1:] if instagram_user.startswith('@') else instagram_user
                
                recent_posts = await self.get_recent_posts(clean_username, limit=5)
                
                # Initialize if this is a new user
                if clean_username not in self.last_post_data:
                    self.last_post_data[clean_username] = {
                        'post_ids': [post['id'] for post in recent_posts]
                    }
                    continue
                
                # Get previously seen post IDs
                known_post_ids = self.last_post_data[clean_username]['post_ids']
                
                # Find new posts
                for post in recent_posts:
                    if post['id'] not in known_post_ids:
                        await self.send_post_notifications(clean_username, post)
                        known_post_ids.append(post['id'])
                
                # Update last post data (keep only last 20 posts to prevent unlimited growth)
                self.last_post_data[clean_username]['post_ids'] = known_post_ids[:20]
                
                # Small delay between API calls to avoid rate limits
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.error(f"Error checking posts for {instagram_user}: {str(e)}")
    
    @check_new_posts.before_loop
    async def before_check_new_posts(self):
        """Wait until the bot is ready before starting the task"""
        await self.bot.wait_until_ready()
        logger.info("Starting Instagram post check task")
        
    async def send_post_notifications(self, username, post):
        """Send notifications for a new post"""
        username_lower = username.lower()
        
        for guild_id, guild_data in self.instagram_config.items():
            if "channels" not in guild_data:
                continue
                
            for discord_channel_id, instagram_users in guild_data["channels"].items():
                if username_lower not in [u.lower() for u in instagram_users]:
                    continue
                    
                # Get the Discord channel
                channel = self.bot.get_channel(int(discord_channel_id))
                if not channel:
                    logger.warning(f"Channel {discord_channel_id} not found, skipping")
                    continue
                
                # Create embed
                embed = discord.Embed(
                    title=f"New Instagram Post from @{username}",
                    url=post['permalink'],
                    description=post['caption'],
                    color=0xE1306C,  # Instagram pink
                    timestamp=datetime.fromisoformat(post['created_at'])
                )
                
                user_info = await self.get_user_info(username)
                
                # Set author with profile image
                embed.set_author(
                    name=f"{user_info['full_name']} (@{username})",
                    icon_url=user_info['profile_pic_url'],
                    url=f"https://www.instagram.com/{username}"
                )
                
                # Add stats to the footer
                embed.set_footer(
                    text=f"❤️ {post['like_count']:,} | 💬 {post['comment_count']:,}",
                    icon_url="https://www.instagram.com/static/images/ico/favicon-192.png/68d99ba29cc8.png"
                )
                
                # Add image or video thumbnail
                if post['is_carousel']:
                    embed.add_field(
                        name="📸 Type",
                        value="Multiple Photos/Videos",
                        inline=True
                    )
                    if post['carousel_media'] and len(post['carousel_media']) > 0:
                        embed.set_image(url=post['carousel_media'][0]['image_url'])
                elif post['is_video']:
                    embed.add_field(
                        name="📸 Type",
                        value="Video",
                        inline=True
                    )
                    embed.set_image(url=post['thumbnail_url'])
                else:
                    embed.add_field(
                        name="📸 Type",
                        value="Photo",
                        inline=True
                    )
                    embed.set_image(url=post['image_url'])
                
                # Add location if available
                if post['location']:
                    embed.add_field(
                        name="📍 Location",
                        value=f"{post['location']['name']}, {post['location']['city']}",
                        inline=True
                    )
                
                # Get custom message if set
                custom_message = None
                if "messages" in guild_data and username_lower in guild_data["messages"]:
                    custom_message = guild_data["messages"][username_lower]
                
                # Format the message content
                content = custom_message or f"📸 New Instagram post from **@{username}**"
                
                # Send notification
                try:
                    await channel.send(content=content, embed=embed)
                    logger.info(f"Sent Instagram notification for @{username} in guild {guild_id}, channel {discord_channel_id}")
                except Exception as e:
                    logger.error(f"Error sending notification: {str(e)}")
                
                # Small delay between notifications
                await asyncio.sleep(1) 

    @commands.command(name="instagram")
    async def instagram_user(self, ctx, username: str = None):
        """Lookup an Instagram user or follow their timeline"""
        if username is None:
            embed = discord.Embed(
                title="Instagram Commands",
                description="Manage Instagram feed notifications",
                color=0xE1306C  # Instagram pink
            )
            
            embed.add_field(
                name="!instagram [username]",
                value="Lookup an Instagram user",
                inline=False
            )
            
            embed.add_field(
                name="!starinstagram add [username] [channel]",
                value="Add Instagram user to have their posts feeded into a channel",
                inline=False
            )
            
            embed.add_field(
                name="!starinstagram remove [username] [channel]",
                value="Remove a user from a channel's Instagram feed",
                inline=False
            )
            
            embed.add_field(
                name="!starinstagram list",
                value="List Instagram feed channels",
                inline=False
            )
            
            embed.add_field(
                name="!starinstagram clear",
                value="Reset all Instagram feeds that have been setup",
                inline=False
            )
            
            await ctx.send(embed=embed)
            return
            
        # If username is provided, look up the user
        try:
            # Remove '@' from the username if present
            clean_username = username[1:] if username.startswith('@') else username
            
            user_info = await self.get_user_info(clean_username)
            recent_posts = await self.get_recent_posts(clean_username, limit=3)
            
            # Create main user info embed
            embed = discord.Embed(
                title=f"{user_info['full_name']} (@{user_info['username']})",
                url=f"https://www.instagram.com/{user_info['username']}",
                description=user_info['biography'],
                color=0xE1306C  # Instagram pink
            )
            
            # Stats
            embed.add_field(
                name="Posts",
                value=f"{user_info['media_count']:,}",
                inline=True
            )
            
            embed.add_field(
                name="Following",
                value=f"{user_info['following_count']:,}",
                inline=True
            )
            
            embed.add_field(
                name="Followers",
                value=f"{user_info['follower_count']:,}",
                inline=True
            )
            
            if user_info['is_verified']:
                embed.add_field(
                    name="Status",
                    value="✓ Verified",
                    inline=True
                )
                
            if user_info['is_private']:
                embed.add_field(
                    name="Privacy",
                    value="🔒 Private",
                    inline=True
                )
                
            if user_info['external_url']:
                embed.add_field(
                    name="Website",
                    value=user_info['external_url'],
                    inline=True
                )
            
            # Set thumbnail to profile image
            embed.set_thumbnail(url=user_info['profile_pic_url'])
            
            # Set footer
            embed.set_footer(
                text="Instagram",
                icon_url="https://www.instagram.com/static/images/ico/favicon-192.png/68d99ba29cc8.png"
            )
            
            await ctx.send(embed=embed)
            
            # Send a few recent posts
            for post in recent_posts[:3]:
                post_embed = discord.Embed(
                    title=f"Instagram Post",
                    url=post['permalink'],
                    description=post['caption'],
                    color=0xE1306C,  # Instagram pink
                    timestamp=datetime.fromisoformat(post['created_at'])
                )
                
                # Add image or video thumbnail
                if post['is_carousel']:
                    post_embed.add_field(
                        name="📸 Type",
                        value="Multiple Photos/Videos",
                        inline=True
                    )
                    if post['carousel_media'] and len(post['carousel_media']) > 0:
                        post_embed.set_image(url=post['carousel_media'][0]['image_url'])
                elif post['is_video']:
                    post_embed.add_field(
                        name="📸 Type",
                        value="Video",
                        inline=True
                    )
                    post_embed.set_image(url=post['thumbnail_url'])
                else:
                    post_embed.add_field(
                        name="📸 Type",
                        value="Photo",
                        inline=True
                    )
                    post_embed.set_image(url=post['image_url'])
                
                # Add location if available
                if post['location']:
                    post_embed.add_field(
                        name="📍 Location",
                        value=f"{post['location']['name']}, {post['location']['city']}",
                        inline=True
                    )
                
                # Add stats to the footer
                post_embed.set_footer(
                    text=f"❤️ {post['like_count']:,} | 💬 {post['comment_count']:,}",
                    icon_url="https://www.instagram.com/static/images/ico/favicon-192.png/68d99ba29cc8.png"
                )
                
                await ctx.send(embed=post_embed)
            
        except Exception as e:
            await ctx.send(f"Error looking up Instagram user: {str(e)}")
            logger.error(f"Error looking up Instagram user {username}: {str(e)}")

    @commands.group(name="starinstagram", invoke_without_command=True)
    async def instagram_group(self, ctx):
        """Group of Instagram commands for feed management"""
        embed = discord.Embed(
            title="Instagram Feed Commands",
            description="Manage Instagram feed notifications",
            color=0xE1306C  # Instagram pink
        )
        
        embed.add_field(
            name="!starinstagram add [username] [channel]",
            value="Add Instagram user to have their posts feeded into a channel",
            inline=False
        )
        
        embed.add_field(
            name="!starinstagram remove [username] [channel]",
            value="Remove a user from a channel's Instagram feed",
            inline=False
        )
        
        embed.add_field(
            name="!starinstagram list",
            value="List Instagram feed channels",
            inline=False
        )
        
        embed.add_field(
            name="!starinstagram clear",
            value="Reset all Instagram feeds that have been setup",
            inline=False
        )
        
        await ctx.send(embed=embed)

    @instagram_group.command(name="add")
    @commands.has_permissions(manage_channels=True)
    async def instagram_add(self, ctx, username: str, channel: discord.TextChannel):
        """Add an Instagram user to have their posts feeded into a channel"""
        guild_id = str(ctx.guild.id)
        
        # Remove '@' from the username if present
        clean_username = username[1:] if username.startswith('@') else username
        
        if guild_id not in self.instagram_config:
            self.instagram_config[guild_id] = {}
            
        if "channels" not in self.instagram_config[guild_id]:
            self.instagram_config[guild_id]["channels"] = {}
            
        channel_id = str(channel.id)
        if channel_id not in self.instagram_config[guild_id]["channels"]:
            self.instagram_config[guild_id]["channels"][channel_id] = []
            
        if clean_username.lower() not in [name.lower() for name in self.instagram_config[guild_id]["channels"][channel_id]]:
            self.instagram_config[guild_id]["channels"][channel_id].append(clean_username)
            await ctx.send(f"✅ Added Instagram feed for `@{clean_username}` in {channel.mention}")
        else:
            await ctx.send(f"Instagram feed for `@{clean_username}` already exists in {channel.mention}")
            
        self.save_config()

    @instagram_group.command(name="remove")
    @commands.has_permissions(manage_channels=True)
    async def instagram_remove(self, ctx, username: str, channel: discord.TextChannel):
        """Remove a user from a channel's Instagram feed"""
        guild_id = str(ctx.guild.id)
        channel_id = str(channel.id)
        
        # Remove '@' from the username if present
        clean_username = username[1:] if username.startswith('@') else username
        
        if (guild_id in self.instagram_config and 
            "channels" in self.instagram_config[guild_id] and 
            channel_id in self.instagram_config[guild_id]["channels"]):
            
            instagram_users = self.instagram_config[guild_id]["channels"][channel_id]
            for i, name in enumerate(instagram_users):
                if name.lower() == clean_username.lower():
                    self.instagram_config[guild_id]["channels"][channel_id].pop(i)
                    await ctx.send(f"✅ Removed Instagram feed for `@{name}` from {channel.mention}")
                    
                    # Clean up empty entries
                    if not self.instagram_config[guild_id]["channels"][channel_id]:
                        del self.instagram_config[guild_id]["channels"][channel_id]
                    if not self.instagram_config[guild_id]["channels"]:
                        del self.instagram_config[guild_id]["channels"]
                    if not self.instagram_config[guild_id]:
                        del self.instagram_config[guild_id]
                        
                    self.save_config()
                    return
                    
            await ctx.send(f"No Instagram feed for `@{clean_username}` found in {channel.mention}")
        else:
            await ctx.send(f"No Instagram feeds found in {channel.mention}")

    @instagram_group.command(name="list")
    @commands.has_permissions(manage_channels=True)
    async def instagram_list(self, ctx):
        """List Instagram feed channels"""
        guild_id = str(ctx.guild.id)
        
        if (guild_id not in self.instagram_config or 
            "channels" not in self.instagram_config[guild_id] or 
            not self.instagram_config[guild_id]["channels"]):
            await ctx.send("No Instagram feeds set up in this server.")
            return
            
        embed = discord.Embed(
            title="Instagram Feed Notifications", 
            color=0xE1306C,  # Instagram pink
            description="List of channels with Instagram feed notifications"
        )
        
        for channel_id, instagram_users in self.instagram_config[guild_id]["channels"].items():
            channel = self.bot.get_channel(int(channel_id))
            if channel:
                users_formatted = ", ".join([f"`@{name}`" for name in instagram_users]) if instagram_users else "None"
                embed.add_field(
                    name=f"#{channel.name}", 
                    value=users_formatted, 
                    inline=False
                )
                
        await ctx.send(embed=embed)

    @instagram_group.command(name="clear")
    @commands.has_permissions(manage_channels=True)
    async def instagram_clear(self, ctx):
        """Reset all Instagram feeds that have been setup"""
        guild_id = str(ctx.guild.id)
        
        if guild_id in self.instagram_config:
            del self.instagram_config[guild_id]
            self.save_config()
            await ctx.send("✅ All Instagram feed configurations have been reset.")
        else:
            await ctx.send("No Instagram feed configurations found for this server.")

async def setup(bot):
    await bot.add_cog(InstagramCommands(bot)) 