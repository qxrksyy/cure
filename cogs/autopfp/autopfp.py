import discord
from discord.ext import commands
import json
import os
import logging
from datetime import datetime
import random
import aiohttp
import asyncio

logger = logging.getLogger('bot')

class AutoPfp(commands.Cog):
    """Commands to set up automatic profile picture and banner channels"""
    
    def __init__(self, bot):
        self.bot = bot
        self.config_path = "data/autopfp"
        self.pfp_config = {}
        self.banner_config = {}
        self.update_task = None
        
        # Create directory if it doesn't exist
        os.makedirs(self.config_path, exist_ok=True)
        
        # Load settings
        self._load_pfp_config()
        self._load_banner_config()
        
        # Start update task
        self.update_task = self.bot.loop.create_task(self._update_channels_loop())
    
    def cog_unload(self):
        """Called when the cog is unloaded"""
        if self.update_task:
            self.update_task.cancel()
    
    def _load_pfp_config(self):
        """Load profile picture settings from file"""
        try:
            filepath = f"{self.config_path}/pfp_channels.json"
            if os.path.exists(filepath):
                with open(filepath, "r") as f:
                    self.pfp_config = json.load(f)
        except Exception as e:
            logger.error(f"Error loading profile picture settings: {str(e)}")
            self.pfp_config = {}
    
    def _save_pfp_config(self):
        """Save profile picture settings to file"""
        try:
            filepath = f"{self.config_path}/pfp_channels.json"
            with open(filepath, "w") as f:
                json.dump(self.pfp_config, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving profile picture settings: {str(e)}")
    
    def _load_banner_config(self):
        """Load banner settings from file"""
        try:
            filepath = f"{self.config_path}/banner_channels.json"
            if os.path.exists(filepath):
                with open(filepath, "r") as f:
                    self.banner_config = json.load(f)
        except Exception as e:
            logger.error(f"Error loading banner settings: {str(e)}")
            self.banner_config = {}
    
    def _save_banner_config(self):
        """Save banner settings to file"""
        try:
            filepath = f"{self.config_path}/banner_channels.json"
            with open(filepath, "w") as f:
                json.dump(self.banner_config, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving banner settings: {str(e)}")
    
    def _get_guild_pfp_config(self, guild_id):
        """Get profile picture config for a guild"""
        guild_id = str(guild_id)
        if guild_id not in self.pfp_config:
            self.pfp_config[guild_id] = {"channels": {}}
            self._save_pfp_config()
        return self.pfp_config[guild_id]
    
    def _get_guild_banner_config(self, guild_id):
        """Get banner config for a guild"""
        guild_id = str(guild_id)
        if guild_id not in self.banner_config:
            self.banner_config[guild_id] = {"channels": {}}
            self._save_banner_config()
        return self.banner_config[guild_id]
    
    async def _update_channels_loop(self):
        """Loop to periodically fetch and post new images"""
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            try:
                # Update PFP channels
                for guild_id, guild_config in self.pfp_config.items():
                    for channel_id, channel_config in guild_config.get("channels", {}).items():
                        try:
                            guild = self.bot.get_guild(int(guild_id))
                            if not guild:
                                continue
                                
                            channel = guild.get_channel(int(channel_id))
                            if not channel:
                                continue
                                
                            # Post a new profile picture
                            await self._post_new_pfp(channel, channel_config.get("categories", ["anime"]))
                        except Exception as e:
                            logger.error(f"Error updating pfp channel {channel_id}: {str(e)}")
                
                # Update banner channels
                for guild_id, guild_config in self.banner_config.items():
                    for channel_id, channel_config in guild_config.get("channels", {}).items():
                        try:
                            guild = self.bot.get_guild(int(guild_id))
                            if not guild:
                                continue
                                
                            channel = guild.get_channel(int(channel_id))
                            if not channel:
                                continue
                                
                            # Post a new banner
                            await self._post_new_banner(channel, channel_config.get("categories", ["nature"]))
                        except Exception as e:
                            logger.error(f"Error updating banner channel {channel_id}: {str(e)}")
                
            except Exception as e:
                logger.error(f"Error in update channels loop: {str(e)}")
                
            # Wait for next update (30 minutes)
            await asyncio.sleep(1800)  # 30 min = 1800 seconds
    
    async def _post_new_pfp(self, channel, categories=None):
        """Post a new profile picture in the channel"""
        if not categories:
            categories = ["anime"]
            
        try:
            # Choose a random category
            category = random.choice(categories)
            
            # Get a random image URL 
            async with aiohttp.ClientSession() as session:
                # Using a placeholder API for demo purposes
                # In real implementation, you'd use a proper API service
                async with session.get(f"https://source.unsplash.com/random/512x512/?{category}") as resp:
                    if resp.status == 200:
                        # Create an embed with the image
                        embed = discord.Embed(
                            title=f"Random {category.capitalize()} Profile Picture",
                            color=discord.Color.blue(),
                            timestamp=datetime.utcnow()
                        )
                        embed.set_image(url=str(resp.url))
                        embed.set_footer(text=f"Category: {category.capitalize()}")
                        
                        # Send the embed
                        await channel.send(embed=embed)
                    else:
                        logger.error(f"Failed to fetch profile picture: {resp.status}")
        except Exception as e:
            logger.error(f"Error posting new profile picture: {str(e)}")
    
    async def _post_new_banner(self, channel, categories=None):
        """Post a new banner in the channel"""
        if not categories:
            categories = ["nature"]
            
        try:
            # Choose a random category
            category = random.choice(categories)
            
            # Get a random image URL
            async with aiohttp.ClientSession() as session:
                # Using a placeholder API for demo purposes
                # In real implementation, you'd use a proper API service
                async with session.get(f"https://source.unsplash.com/random/1500x500/?{category}") as resp:
                    if resp.status == 200:
                        # Create an embed with the image
                        embed = discord.Embed(
                            title=f"Random {category.capitalize()} Banner",
                            color=discord.Color.blue(),
                            timestamp=datetime.utcnow()
                        )
                        embed.set_image(url=str(resp.url))
                        embed.set_footer(text=f"Category: {category.capitalize()}")
                        
                        # Send the embed
                        await channel.send(embed=embed)
                    else:
                        logger.error(f"Failed to fetch banner: {resp.status}")
        except Exception as e:
            logger.error(f"Error posting new banner: {str(e)}")

    # AutoPfp Commands
    @commands.group(name="autopfp", invoke_without_command=True)
    @commands.has_permissions(manage_guild=True)
    async def autopfp(self, ctx):
        """Command group for managing auto profile picture channels"""
        embed = discord.Embed(
            title="AutoPfp Commands",
            description="Set up channels that automatically post profile pictures",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(
            name="Available Commands",
            value=(
                "`autopfp setup` - Show setup instructions\n"
                "`autopfp set <channel> [categories]` - Set a channel for profile pictures\n"
                "`autopfp reset` - Reset all auto profile picture settings\n"
            ),
            inline=False
        )
        
        # Add current configuration if any
        guild_config = self._get_guild_pfp_config(ctx.guild.id)
        if guild_config.get("channels"):
            config_text = ""
            for channel_id, channel_data in guild_config["channels"].items():
                channel = ctx.guild.get_channel(int(channel_id))
                if channel:
                    categories = ", ".join(channel_data.get("categories", ["anime"]))
                    config_text += f"• {channel.mention} - Categories: {categories}\n"
            
            if config_text:
                embed.add_field(
                    name="Current Configuration",
                    value=config_text,
                    inline=False
                )
        
        await ctx.send(embed=embed)
    
    @autopfp.command(name="setup")
    @commands.has_permissions(manage_guild=True)
    async def autopfp_setup(self, ctx):
        """Setup auto pfp channels"""
        embed = discord.Embed(
            title="AutoPfp Setup",
            description="Learn how to set up automatic profile picture channels",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(
            name="Step 1: Create a Channel",
            value="Create a dedicated text channel for profile pictures",
            inline=False
        )
        
        embed.add_field(
            name="Step 2: Set the Channel",
            value=(
                "Use the following command to set a channel for auto profile pictures:\n"
                "`autopfp set #channel category1 category2 ...`\n\n"
                "Available categories: anime, gaming, art, meme, aesthetic, etc.\n"
                "If no categories are specified, anime is used by default."
            ),
            inline=False
        )
        
        embed.add_field(
            name="Step 3: Enjoy!",
            value="The bot will post new profile pictures every 30 minutes",
            inline=False
        )
        
        embed.add_field(
            name="Note",
            value="You can set multiple channels with different categories",
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @autopfp.command(name="set")
    @commands.has_permissions(manage_guild=True)
    async def autopfp_set(self, ctx, channel: discord.TextChannel = None, *categories):
        """Set the pfp categories for a channel"""
        if not channel:
            await ctx.send("❌ Please specify a channel to set up")
            return
        
        # Default categories if none specified
        if not categories:
            categories = ["anime"]
        
        # Save the configuration
        guild_config = self._get_guild_pfp_config(ctx.guild.id)
        
        # Add or update the channel configuration
        guild_config["channels"][str(channel.id)] = {
            "categories": list(categories),
            "set_by": str(ctx.author.id),
            "set_at": datetime.utcnow().isoformat()
        }
        
        self._save_pfp_config()
        
        # Immediately post a profile picture
        await self._post_new_pfp(channel, list(categories))
        
        # Send confirmation
        categories_str = ", ".join(categories)
        await ctx.send(f"✅ Set {channel.mention} as an auto profile picture channel with categories: {categories_str}")
    
    @autopfp.command(name="reset")
    @commands.has_permissions(manage_guild=True)
    async def autopfp_reset(self, ctx):
        """Reset autopfp configuration"""
        guild_id = str(ctx.guild.id)
        
        # Check if there's any configuration to reset
        if guild_id not in self.pfp_config or not self.pfp_config[guild_id].get("channels"):
            await ctx.send("❌ No auto profile picture channels are configured")
            return
        
        # Ask for confirmation
        channel_count = len(self.pfp_config[guild_id]["channels"])
        confirm_msg = await ctx.send(f"⚠️ Are you sure you want to remove all {channel_count} auto profile picture channels? (yes/no)")
        
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and \
                   m.content.lower() in ['yes', 'no', 'y', 'n']
        
        try:
            msg = await self.bot.wait_for('message', check=check, timeout=30.0)
            
            if msg.content.lower() in ['yes', 'y']:
                # Reset the configuration
                self.pfp_config[guild_id] = {"channels": {}}
                self._save_pfp_config()
                await ctx.send("✅ All auto profile picture channels have been reset")
            else:
                await ctx.send("❌ Operation cancelled")
                
        except asyncio.TimeoutError:
            await ctx.send("❌ Timed out waiting for confirmation")

    # AutoBanner Commands
    @commands.group(name="autobanner", invoke_without_command=True)
    @commands.has_permissions(manage_guild=True)
    async def autobanner(self, ctx):
        """Command group for managing auto banner channels"""
        embed = discord.Embed(
            title="AutoBanner Commands",
            description="Set up channels that automatically post banner images",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(
            name="Available Commands",
            value=(
                "`autobanner setup` - Show setup instructions\n"
                "`autobanner set <channel> [categories]` - Set a channel for banners\n"
                "`autobanner reset` - Reset all auto banner settings\n"
            ),
            inline=False
        )
        
        # Add current configuration if any
        guild_config = self._get_guild_banner_config(ctx.guild.id)
        if guild_config.get("channels"):
            config_text = ""
            for channel_id, channel_data in guild_config["channels"].items():
                channel = ctx.guild.get_channel(int(channel_id))
                if channel:
                    categories = ", ".join(channel_data.get("categories", ["nature"]))
                    config_text += f"• {channel.mention} - Categories: {categories}\n"
            
            if config_text:
                embed.add_field(
                    name="Current Configuration",
                    value=config_text,
                    inline=False
                )
        
        await ctx.send(embed=embed)
    
    @autobanner.command(name="setup")
    @commands.has_permissions(manage_guild=True)
    async def autobanner_setup(self, ctx):
        """Setup auto banner channels"""
        embed = discord.Embed(
            title="AutoBanner Setup",
            description="Learn how to set up automatic banner channels",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(
            name="Step 1: Create a Channel",
            value="Create a dedicated text channel for banner images",
            inline=False
        )
        
        embed.add_field(
            name="Step 2: Set the Channel",
            value=(
                "Use the following command to set a channel for auto banners:\n"
                "`autobanner set #channel category1 category2 ...`\n\n"
                "Available categories: nature, city, abstract, gaming, space, etc.\n"
                "If no categories are specified, nature is used by default."
            ),
            inline=False
        )
        
        embed.add_field(
            name="Step 3: Enjoy!",
            value="The bot will post new banners every 30 minutes",
            inline=False
        )
        
        embed.add_field(
            name="Note",
            value="You can set multiple channels with different categories",
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @autobanner.command(name="set")
    @commands.has_permissions(manage_guild=True)
    async def autobanner_set(self, ctx, channel: discord.TextChannel = None, *categories):
        """Set the banner categories for a channel"""
        if not channel:
            await ctx.send("❌ Please specify a channel to set up")
            return
        
        # Default categories if none specified
        if not categories:
            categories = ["nature"]
        
        # Save the configuration
        guild_config = self._get_guild_banner_config(ctx.guild.id)
        
        # Add or update the channel configuration
        guild_config["channels"][str(channel.id)] = {
            "categories": list(categories),
            "set_by": str(ctx.author.id),
            "set_at": datetime.utcnow().isoformat()
        }
        
        self._save_banner_config()
        
        # Immediately post a banner
        await self._post_new_banner(channel, list(categories))
        
        # Send confirmation
        categories_str = ", ".join(categories)
        await ctx.send(f"✅ Set {channel.mention} as an auto banner channel with categories: {categories_str}")
    
    @autobanner.command(name="reset")
    @commands.has_permissions(manage_guild=True)
    async def autobanner_reset(self, ctx):
        """Reset autobanner configuration"""
        guild_id = str(ctx.guild.id)
        
        # Check if there's any configuration to reset
        if guild_id not in self.banner_config or not self.banner_config[guild_id].get("channels"):
            await ctx.send("❌ No auto banner channels are configured")
            return
        
        # Ask for confirmation
        channel_count = len(self.banner_config[guild_id]["channels"])
        confirm_msg = await ctx.send(f"⚠️ Are you sure you want to remove all {channel_count} auto banner channels? (yes/no)")
        
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and \
                   m.content.lower() in ['yes', 'no', 'y', 'n']
        
        try:
            msg = await self.bot.wait_for('message', check=check, timeout=30.0)
            
            if msg.content.lower() in ['yes', 'y']:
                # Reset the configuration
                self.banner_config[guild_id] = {"channels": {}}
                self._save_banner_config()
                await ctx.send("✅ All auto banner channels have been reset")
            else:
                await ctx.send("❌ Operation cancelled")
                
        except asyncio.TimeoutError:
            await ctx.send("❌ Timed out waiting for confirmation")

async def setup(bot):
    await bot.add_cog(AutoPfp(bot)) 