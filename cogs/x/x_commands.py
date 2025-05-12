import discord
from discord.ext import commands, tasks
import json
import os
import logging
import aiohttp
import asyncio
from datetime import datetime, timedelta

logger = logging.getLogger('bot')

class XCommands(commands.Cog):
    """Commands for X (Twitter) feed notifications"""
    
    def __init__(self, bot):
        self.bot = bot
        self.data_folder = 'data'
        self.config_file = os.path.join(self.data_folder, 'x_config.json')
        self.x_config = self.load_config()
        
        # Check interval for new posts (default: 15 minutes)
        self.check_interval = 15 * 60  
        self.last_post_data = {}  # username -> {post_ids: []}
        
        # Start the background task
        self.check_new_posts.start()
        
    def load_config(self):
        """Load the X configuration from file"""
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
        """Save the X configuration to file"""
        with open(self.config_file, 'w') as f:
            json.dump(self.x_config, f, indent=4)
            
    def cog_unload(self):
        """Clean up when the cog is unloaded"""
        self.check_new_posts.cancel()
        
    async def get_user_info(self, username):
        """Get the X user info for a username"""
        # In a real implementation, this would use the X API
        # For now, we'll return mock data
        
        # Remove '@' from the username if present
        if username.startswith('@'):
            username = username[1:]
            
        return {
            'id': f"user_{username}",
            'username': username,
            'display_name': username.capitalize(),
            'profile_image': f"https://xprofile.example.com/{username}/profile.jpg",
            'bio': f"This is {username}'s bio on X",
            'following_count': 500,
            'followers_count': 1000,
            'verified': username.lower() in ['elonmusk', 'twitter', 'x'],
        }
    
    async def get_latest_posts(self, username, limit=10):
        """Get the latest posts for an X user"""
        # In a real implementation, this would use the X API
        # For now we'll return mock data
        
        # Remove '@' from the username if present
        if username.startswith('@'):
            username = username[1:]
            
        # Example mock response
        mock_posts = [
            {
                'id': f"{username}_post_{i}",
                'text': f"This is a mock post #{i} from {username}",
                'url': f"https://x.com/{username}/status/{i}",
                'created_at': (datetime.now() - timedelta(hours=i)).isoformat(),
                'media': [] if i % 3 != 0 else [f"https://x.example.com/{username}/media/{i}.jpg"],
                'like_count': 100 - i * 10,
                'repost_count': 50 - i * 5,
                'reply_count': 20 - i * 2,
                'is_reply': i % 4 == 0,
                'is_repost': i % 5 == 0,
            }
            for i in range(1, limit+1)
        ]
        
        return mock_posts
        
    @tasks.loop(minutes=15)
    async def check_new_posts(self):
        """Check for new posts and send notifications"""
        logger.info("Checking for new X posts...")
        
        all_users = set()
        
        # Collect all X users across all guilds
        for guild_id, guild_data in self.x_config.items():
            if "channels" in guild_data:
                for discord_channel_id, x_users in guild_data["channels"].items():
                    all_users.update([u.lower() for u in x_users])
        
        if not all_users:
            return
            
        for x_user in all_users:
            try:
                # Remove '@' from the username if present
                clean_username = x_user[1:] if x_user.startswith('@') else x_user
                
                latest_posts = await self.get_latest_posts(clean_username, limit=5)
                
                # Initialize if this is a new user
                if clean_username not in self.last_post_data:
                    self.last_post_data[clean_username] = {
                        'post_ids': [post['id'] for post in latest_posts]
                    }
                    continue
                
                # Get previously seen post IDs
                known_post_ids = self.last_post_data[clean_username]['post_ids']
                
                # Find new posts
                for post in latest_posts:
                    if post['id'] not in known_post_ids:
                        await self.send_post_notifications(clean_username, post)
                        known_post_ids.append(post['id'])
                
                # Update last post data (keep only last 20 posts to prevent unlimited growth)
                self.last_post_data[clean_username]['post_ids'] = known_post_ids[:20]
                
                # Small delay between API calls to avoid rate limits
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.error(f"Error checking posts for {x_user}: {str(e)}")
    
    @check_new_posts.before_loop
    async def before_check_new_posts(self):
        """Wait until the bot is ready before starting the task"""
        await self.bot.wait_until_ready()
        logger.info("Starting X post check task")
    
    async def send_post_notifications(self, username, post):
        """Send notifications for a new post"""
        username_lower = username.lower()
        
        for guild_id, guild_data in self.x_config.items():
            if "channels" not in guild_data:
                continue
                
            for discord_channel_id, x_users in guild_data["channels"].items():
                if username_lower not in [u.lower() for u in x_users]:
                    continue
                    
                # Get the Discord channel
                channel = self.bot.get_channel(int(discord_channel_id))
                if not channel:
                    logger.warning(f"Channel {discord_channel_id} not found, skipping")
                    continue
                
                # Create embed
                embed = discord.Embed(
                    title=f"New post from @{username}",
                    url=post['url'],
                    description=post['text'],
                    color=discord.Color.blue(),
                    timestamp=datetime.fromisoformat(post['created_at'])
                )
                
                user_info = await self.get_user_info(username)
                
                # Set author with profile image
                embed.set_author(
                    name=f"{user_info['display_name']} (@{username})",
                    icon_url=user_info['profile_image'],
                    url=f"https://x.com/{username}"
                )
                
                # Add stats to the footer
                embed.set_footer(
                    text=f"❤️ {post['like_count']} | 🔁 {post['repost_count']} | 💬 {post['reply_count']}",
                    icon_url="https://abs.twimg.com/responsive-web/client-web/icon-default.522d363a.png"
                )
                
                # Add media if available
                if post['media'] and len(post['media']) > 0:
                    embed.set_image(url=post['media'][0])
                
                # Get custom message if set
                custom_message = None
                if "messages" in guild_data and username_lower in guild_data["messages"]:
                    custom_message = guild_data["messages"][username_lower]
                
                # Format the message content
                content = custom_message or f"🔔 New post from **@{username}**"
                
                # Send notification
                try:
                    await channel.send(content=content, embed=embed)
                    logger.info(f"Sent post notification for @{username} in guild {guild_id}, channel {discord_channel_id}")
                except Exception as e:
                    logger.error(f"Error sending notification: {str(e)}")
                
                # Small delay between notifications
                await asyncio.sleep(1)
            
    @commands.group(name="x", invoke_without_command=True)
    async def x_group(self, ctx, username: str = None):
        """Lookup an X user or follow their timeline"""
        if username is None:
            embed = discord.Embed(
                title="X Commands",
                description="Manage X feed notifications",
                color=discord.Color.blue()
            )
            
            embed.add_field(
                name="!x [username]",
                value="Lookup an X user",
                inline=False
            )
            
            embed.add_field(
                name="!x add [username] [channel]",
                value="Add X user to feed posts into a channel",
                inline=False
            )
            
            embed.add_field(
                name="!x remove [username] [channel]",
                value="Remove a user from a channel's X feed",
                inline=False
            )
            
            embed.add_field(
                name="!x list",
                value="List X feed channels",
                inline=False
            )
            
            embed.add_field(
                name="!x clear",
                value="Reset all X feeds that have been setup",
                inline=False
            )
            
            await ctx.send(embed=embed)
            return
            
        # If username is provided, look up the user
        try:
            # Remove '@' from the username if present
            clean_username = username[1:] if username.startswith('@') else username
            
            user_info = await self.get_user_info(clean_username)
            latest_posts = await self.get_latest_posts(clean_username, limit=3)
            
            # Create main user info embed
            embed = discord.Embed(
                title=f"{user_info['display_name']} (@{user_info['username']})",
                url=f"https://x.com/{user_info['username']}",
                description=user_info['bio'],
                color=discord.Color.blue()
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
                text="X (formerly Twitter)",
                icon_url="https://abs.twimg.com/responsive-web/client-web/icon-default.522d363a.png"
            )
            
            await ctx.send(embed=embed)
            
            # Send a few recent posts
            for post in latest_posts[:3]:
                post_embed = discord.Embed(
                    description=post['text'],
                    color=discord.Color.blue(),
                    timestamp=datetime.fromisoformat(post['created_at'])
                )
                
                # Add media if available
                if post['media'] and len(post['media']) > 0:
                    post_embed.set_image(url=post['media'][0])
                
                # Add stats to the footer
                post_embed.set_footer(
                    text=f"❤️ {post['like_count']} | 🔁 {post['repost_count']} | 💬 {post['reply_count']}",
                    icon_url="https://abs.twimg.com/responsive-web/client-web/icon-default.522d363a.png"
                )
                
                await ctx.send(embed=post_embed)
            
        except Exception as e:
            await ctx.send(f"Error looking up X user: {str(e)}")
            logger.error(f"Error looking up X user {username}: {str(e)}")

    @x_group.command(name="add")
    @commands.has_permissions(manage_channels=True)
    async def x_add(self, ctx, user: str, channel: discord.TextChannel):
        """Add an X user to feed posts into a channel"""
        guild_id = str(ctx.guild.id)
        
        # Remove '@' from the username if present
        clean_username = user[1:] if user.startswith('@') else user
        
        if guild_id not in self.x_config:
            self.x_config[guild_id] = {}
            
        if "channels" not in self.x_config[guild_id]:
            self.x_config[guild_id]["channels"] = {}
            
        channel_id = str(channel.id)
        if channel_id not in self.x_config[guild_id]["channels"]:
            self.x_config[guild_id]["channels"][channel_id] = []
            
        if clean_username.lower() not in [name.lower() for name in self.x_config[guild_id]["channels"][channel_id]]:
            self.x_config[guild_id]["channels"][channel_id].append(clean_username)
            await ctx.send(f"✅ Added X feed for `@{clean_username}` in {channel.mention}")
        else:
            await ctx.send(f"X feed for `@{clean_username}` already exists in {channel.mention}")
            
        self.save_config()

    @x_group.command(name="remove")
    @commands.has_permissions(manage_channels=True)
    async def x_remove(self, ctx, username: str, channel: discord.TextChannel):
        """Remove a user from a channel's X feed"""
        guild_id = str(ctx.guild.id)
        channel_id = str(channel.id)
        
        # Remove '@' from the username if present
        clean_username = username[1:] if username.startswith('@') else username
        
        if (guild_id in self.x_config and 
            "channels" in self.x_config[guild_id] and 
            channel_id in self.x_config[guild_id]["channels"]):
            
            x_users = self.x_config[guild_id]["channels"][channel_id]
            for i, name in enumerate(x_users):
                if name.lower() == clean_username.lower():
                    self.x_config[guild_id]["channels"][channel_id].pop(i)
                    await ctx.send(f"✅ Removed X feed for `@{name}` from {channel.mention}")
                    
                    # Clean up empty entries
                    if not self.x_config[guild_id]["channels"][channel_id]:
                        del self.x_config[guild_id]["channels"][channel_id]
                    if not self.x_config[guild_id]["channels"]:
                        del self.x_config[guild_id]["channels"]
                    if not self.x_config[guild_id]:
                        del self.x_config[guild_id]
                        
                    self.save_config()
                    return
                    
            await ctx.send(f"No X feed for `@{clean_username}` found in {channel.mention}")
        else:
            await ctx.send(f"No X feeds found in {channel.mention}")

    @x_group.command(name="list")
    @commands.has_permissions(manage_channels=True)
    async def x_list(self, ctx):
        """List X feed channels"""
        guild_id = str(ctx.guild.id)
        
        if (guild_id not in self.x_config or 
            "channels" not in self.x_config[guild_id] or 
            not self.x_config[guild_id]["channels"]):
            await ctx.send("No X feeds set up in this server.")
            return
            
        embed = discord.Embed(
            title="X Feed Notifications", 
            color=discord.Color.blue(),
            description="List of channels with X feed notifications"
        )
        
        for channel_id, x_users in self.x_config[guild_id]["channels"].items():
            channel = self.bot.get_channel(int(channel_id))
            if channel:
                users_formatted = ", ".join([f"`@{name}`" for name in x_users]) if x_users else "None"
                embed.add_field(
                    name=f"#{channel.name}", 
                    value=users_formatted, 
                    inline=False
                )
                
        await ctx.send(embed=embed)

    @x_group.command(name="clear")
    @commands.has_permissions(manage_channels=True)
    async def x_clear(self, ctx):
        """Reset all X feeds that have been setup"""
        guild_id = str(ctx.guild.id)
        
        if guild_id in self.x_config:
            del self.x_config[guild_id]
            self.save_config()
            await ctx.send("✅ All X feed configurations have been reset.")
        else:
            await ctx.send("No X feed configurations found for this server.")

async def setup(bot):
    await bot.add_cog(XCommands(bot)) 