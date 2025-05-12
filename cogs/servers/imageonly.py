import discord
from discord.ext import commands
import json
import os
import logging
from datetime import datetime

logger = logging.getLogger('bot')

class ImageOnly(commands.Cog):
    """
    Image-only channel management for gallery channels
    """
    
    def __init__(self, bot):
        self.bot = bot
        self.config_path = "data/servers"
        self.image_config = {}
        
        # Create directory if it doesn't exist
        os.makedirs(self.config_path, exist_ok=True)
        
        # Load settings
        self._load_image_config()
        
    def _load_image_config(self):
        """Load image channel settings from file"""
        try:
            filepath = f"{self.config_path}/image_channels.json"
            if os.path.exists(filepath):
                with open(filepath, "r") as f:
                    self.image_config = json.load(f)
        except Exception as e:
            logger.error(f"Error loading image channel settings: {str(e)}")
            self.image_config = {}
    
    def _save_image_config(self):
        """Save image channel settings to file"""
        try:
            filepath = f"{self.config_path}/image_channels.json"
            with open(filepath, "w") as f:
                json.dump(self.image_config, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving image channel settings: {str(e)}")
    
    def _get_guild_image_config(self, guild_id):
        """Get image channel config for a guild"""
        guild_id = str(guild_id)
        if guild_id not in self.image_config:
            self.image_config[guild_id] = {
                "channels": []
            }
            self._save_image_config()
        return self.image_config[guild_id]
    
    def is_image_channel(self, guild_id, channel_id):
        """Check if a channel is configured as image-only"""
        guild_config = self._get_guild_image_config(guild_id)
        return str(channel_id) in guild_config.get("channels", [])
    
    @commands.group(name="imageonly", invoke_without_command=True)
    async def imageonly(self, ctx):
        """Set up image + caption only channels"""
        embed = discord.Embed(
            title="Image-Only Channels",
            description="Set up gallery channels that only allow images with captions",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        guild_config = self._get_guild_image_config(ctx.guild.id)
        
        # List configured channels
        channels_text = ""
        for channel_id in guild_config.get("channels", []):
            channel = ctx.guild.get_channel(int(channel_id))
            if channel:
                channels_text += f"• {channel.mention}\n"
                
        if channels_text:
            embed.add_field(
                name="Configured Gallery Channels",
                value=channels_text,
                inline=False
            )
        else:
            embed.add_field(
                name="No Gallery Channels Configured",
                value="Use `imageonly add #channel` to set up a gallery channel",
                inline=False
            )
        
        embed.add_field(
            name="Available Commands",
            value=(
                "`imageonly add #channel` - Add a gallery channel\n"
                "`imageonly remove #channel` - Remove a gallery channel\n"
                "`imageonly list` - View all gallery channels"
            ),
            inline=False
        )
        
        await ctx.send(embed=embed)
        
    @imageonly.command(name="add")
    @commands.has_permissions(manage_guild=True)
    async def imageonly_add(self, ctx, channel: discord.TextChannel = None):
        """Add a gallery channel"""
        if channel is None:
            await ctx.send("❌ Please specify a channel to set as a gallery channel.")
            return
            
        guild_config = self._get_guild_image_config(ctx.guild.id)
        
        if str(channel.id) in guild_config.get("channels", []):
            await ctx.send(f"❌ {channel.mention} is already configured as a gallery channel.")
            return
            
        if "channels" not in guild_config:
            guild_config["channels"] = []
            
        guild_config["channels"].append(str(channel.id))
        self._save_image_config()
        
        await ctx.send(f"✅ {channel.mention} has been set as a gallery channel. Only images with captions will be allowed.")
        
    @imageonly.command(name="remove")
    @commands.has_permissions(manage_guild=True)
    async def imageonly_remove(self, ctx, channel: discord.TextChannel = None):
        """Remove a gallery channel"""
        if channel is None:
            await ctx.send("❌ Please specify a channel to remove from gallery channels.")
            return
            
        guild_config = self._get_guild_image_config(ctx.guild.id)
        
        if str(channel.id) not in guild_config.get("channels", []):
            await ctx.send(f"❌ {channel.mention} is not configured as a gallery channel.")
            return
            
        guild_config["channels"].remove(str(channel.id))
        self._save_image_config()
        
        await ctx.send(f"✅ {channel.mention} has been removed from gallery channels.")
        
    @imageonly.command(name="list")
    @commands.has_permissions(manage_guild=True)
    async def imageonly_list(self, ctx):
        """View all gallery channels"""
        guild_config = self._get_guild_image_config(ctx.guild.id)
        
        embed = discord.Embed(
            title="Gallery Channels",
            description="Channels configured to only allow images with captions",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        # List configured channels
        channels_text = ""
        for channel_id in guild_config.get("channels", []):
            channel = ctx.guild.get_channel(int(channel_id))
            if channel:
                channels_text += f"• {channel.mention} (ID: {channel.id})\n"
            else:
                channels_text += f"• Unknown Channel (ID: {channel_id})\n"
                
        if channels_text:
            embed.add_field(
                name="Configured Gallery Channels",
                value=channels_text,
                inline=False
            )
        else:
            embed.add_field(
                name="No Gallery Channels",
                value="No channels are currently configured as gallery channels.",
                inline=False
            )
            
        await ctx.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_message(self, message):
        """Ensure only images with captions are sent in gallery channels"""
        # Skip if not in a guild or if message is from a bot
        if not message.guild or message.author.bot:
            return
            
        # Check if the channel is a gallery channel
        if not self.is_image_channel(message.guild.id, message.channel.id):
            return
            
        # Allow messages from users with manage messages permission
        member = message.guild.get_member(message.author.id)
        if member and member.guild_permissions.manage_messages:
            return
            
        # Check if the message has attachments and content
        has_image = False
        
        # Check for image attachments
        for attachment in message.attachments:
            content_type = attachment.content_type
            if content_type and content_type.startswith('image/'):
                has_image = True
                break
                
        # Check for embeds with images (for link previews)
        if not has_image and message.embeds:
            for embed in message.embeds:
                if embed.type == 'image' or embed.image or embed.thumbnail:
                    has_image = True
                    break
                    
        # Check for message content (caption)
        has_caption = bool(message.content.strip())
        
        # Delete messages that don't meet criteria
        if not has_image or not has_caption:
            reason = []
            if not has_image:
                reason.append("an image")
            if not has_caption:
                reason.append("a caption")
                
            reason_str = " and ".join(reason)
            
            try:
                await message.delete()
                
                # Send a temporary warning message
                warning = await message.channel.send(
                    f"⚠️ {message.author.mention}, your message was removed because it didn't include {reason_str}. "
                    f"This channel requires both an image and caption."
                )
                
                # Delete the warning after 5 seconds
                await warning.delete(delay=5)
                
            except discord.Forbidden:
                logger.error(f"Missing permissions to delete message in gallery channel {message.channel.id}")
            except Exception as e:
                logger.error(f"Error enforcing image-only channel: {str(e)}")

async def setup(bot):
    await bot.add_cog(ImageOnly(bot)) 