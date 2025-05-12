import discord
from discord.ext import commands
import json
import os
import logging
from datetime import datetime
import asyncio

logger = logging.getLogger('bot')

class PinArchive(commands.Cog):
    """
    Pin Archival System for archiving pinned messages
    """
    
    def __init__(self, bot):
        self.bot = bot
        self.config_path = "data/servers"
        self.pin_config = {}
        
        # Create directory if it doesn't exist
        os.makedirs(self.config_path, exist_ok=True)
        
        # Load settings
        self._load_pin_config()
        
    def _load_pin_config(self):
        """Load pin settings from file"""
        try:
            filepath = f"{self.config_path}/pin_config.json"
            if os.path.exists(filepath):
                with open(filepath, "r") as f:
                    self.pin_config = json.load(f)
        except Exception as e:
            logger.error(f"Error loading pin settings: {str(e)}")
            self.pin_config = {}
    
    def _save_pin_config(self):
        """Save pin settings to file"""
        try:
            filepath = f"{self.config_path}/pin_config.json"
            with open(filepath, "w") as f:
                json.dump(self.pin_config, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving pin settings: {str(e)}")
    
    def _get_guild_pin_config(self, guild_id):
        """Get pin config for a guild"""
        guild_id = str(guild_id)
        if guild_id not in self.pin_config:
            self.pin_config[guild_id] = {
                "enabled": False,
                "archive_channel": None,
                "unpin_after_archive": False
            }
            self._save_pin_config()
        return self.pin_config[guild_id]
        
    @commands.group(name="pins", invoke_without_command=True)
    async def pins(self, ctx):
        """Pin archival system commands"""
        embed = discord.Embed(
            title="Pin Archival System",
            description="Archive pinned messages to keep your pin list clean",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        guild_config = self._get_guild_pin_config(ctx.guild.id)
        
        status = "Disabled"
        if guild_config.get("enabled", False):
            status = "Enabled"
            
        embed.add_field(
            name="Status",
            value=status,
            inline=False
        )
        
        archive_channel_id = guild_config.get("archive_channel")
        if archive_channel_id:
            channel = ctx.guild.get_channel(int(archive_channel_id))
            if channel:
                embed.add_field(
                    name="Archive Channel",
                    value=channel.mention,
                    inline=False
                )
        
        embed.add_field(
            name="Unpin After Archive",
            value="Yes" if guild_config.get("unpin_after_archive", False) else "No",
            inline=False
        )
        
        embed.add_field(
            name="Available Commands",
            value=(
                "`pins set` - Enable or disable the pin archival system\n"
                "`pins channel` - Set the pin archival channel\n"
                "`pins archive` - Archive the pins in the current channel\n"
                "`pins unpin` - Enable or disable unpinning of messages during archival\n"
                "`pins config` - View the pin archival config\n"
                "`pins reset` - Reset the pin archival config"
            ),
            inline=False
        )
        
        await ctx.send(embed=embed)
        
    @pins.command(name="set")
    @commands.has_permissions(manage_guild=True)
    async def pins_set(self, ctx, option: str = None):
        """Enable or disable the pin archival system"""
        if option is None:
            await ctx.send("❌ Please specify either `on` or `off`.")
            return
            
        option = option.lower()
        if option not in ["on", "off", "enable", "disable", "true", "false", "yes", "no"]:
            await ctx.send("❌ Invalid option. Please use `on` or `off`.")
            return
            
        enabled = option in ["on", "enable", "true", "yes"]
        
        guild_config = self._get_guild_pin_config(ctx.guild.id)
        guild_config["enabled"] = enabled
        self._save_pin_config()
        
        status = "enabled" if enabled else "disabled"
        await ctx.send(f"✅ Pin archival system has been {status}.")
        
    @pins.command(name="channel")
    @commands.has_permissions(manage_guild=True)
    async def pins_channel(self, ctx, channel: discord.TextChannel = None):
        """Set the pin archival channel"""
        if channel is None:
            await ctx.send("❌ Please specify a channel to set as the pin archive.")
            return
            
        guild_config = self._get_guild_pin_config(ctx.guild.id)
        guild_config["archive_channel"] = str(channel.id)
        self._save_pin_config()
        
        await ctx.send(f"✅ Pin archive channel has been set to {channel.mention}.")
        
    @pins.command(name="archive")
    @commands.has_permissions(manage_guild=True)
    async def pins_archive(self, ctx):
        """Archive the pins in the current channel"""
        guild_config = self._get_guild_pin_config(ctx.guild.id)
        
        if not guild_config.get("enabled", False):
            await ctx.send("❌ Pin archival system is not enabled. Use `pins set on` to enable it.")
            return
            
        archive_channel_id = guild_config.get("archive_channel")
        if not archive_channel_id:
            await ctx.send("❌ No archive channel has been set. Use `pins channel #channel` to set one.")
            return
            
        archive_channel = ctx.guild.get_channel(int(archive_channel_id))
        if not archive_channel:
            await ctx.send("❌ The configured archive channel no longer exists. Please set a new one.")
            return
            
        # Get all pinned messages in the current channel
        pins = await ctx.channel.pins()
        
        if not pins:
            await ctx.send("ℹ️ There are no pinned messages in this channel.")
            return
            
        # Create summary embed
        embed = discord.Embed(
            title=f"Archived Pins from #{ctx.channel.name}",
            description=f"{len(pins)} pins archived on {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        # Send the summary embed to archive channel
        archive_message = await archive_channel.send(embed=embed)
        
        # Process each pinned message
        count = 0
        for pinned_msg in pins:
            try:
                # Create embed for the pinned message
                pin_embed = discord.Embed(
                    description=pinned_msg.content if pinned_msg.content else "*No content*",
                    color=discord.Color.blue(),
                    timestamp=pinned_msg.created_at
                )
                
                # Add author info
                pin_embed.set_author(
                    name=f"{pinned_msg.author.display_name}",
                    icon_url=pinned_msg.author.display_avatar.url
                )
                
                # Add message link
                pin_embed.add_field(
                    name="Source",
                    value=f"[Jump to message]({pinned_msg.jump_url})",
                    inline=False
                )
                
                # Handle attachments
                if pinned_msg.attachments:
                    attachment = pinned_msg.attachments[0]
                    if attachment.content_type and attachment.content_type.startswith('image/'):
                        pin_embed.set_image(url=attachment.url)
                    else:
                        pin_embed.add_field(
                            name="Attachment",
                            value=f"[{attachment.filename}]({attachment.url})",
                            inline=False
                        )
                
                # Send the pinned message to archive channel
                await archive_channel.send(embed=pin_embed)
                count += 1
                
                # Unpin if configured
                if guild_config.get("unpin_after_archive", False):
                    await pinned_msg.unpin(reason="Archived to pin archive channel")
                    # Add a slight delay to avoid rate limits
                    await asyncio.sleep(1)
                    
            except Exception as e:
                logger.error(f"Error archiving pin: {str(e)}")
                continue
        
        # Update summary with count
        embed.description = f"{count} pins archived on {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}"
        await archive_message.edit(embed=embed)
        
        action = "archived and unpinned" if guild_config.get("unpin_after_archive", False) else "archived"
        await ctx.send(f"✅ Successfully {action} {count} pinned messages to {archive_channel.mention}.")
        
    @pins.command(name="unpin")
    @commands.has_permissions(manage_guild=True)
    async def pins_unpin(self, ctx, option: str = None):
        """Enable or disable the unpinning of messages during archival"""
        if option is None:
            await ctx.send("❌ Please specify either `on` or `off`.")
            return
            
        option = option.lower()
        if option not in ["on", "off", "enable", "disable", "true", "false", "yes", "no"]:
            await ctx.send("❌ Invalid option. Please use `on` or `off`.")
            return
            
        unpin = option in ["on", "enable", "true", "yes"]
        
        guild_config = self._get_guild_pin_config(ctx.guild.id)
        guild_config["unpin_after_archive"] = unpin
        self._save_pin_config()
        
        status = "enabled" if unpin else "disabled"
        await ctx.send(f"✅ Automatic unpinning after archival has been {status}.")
        
    @pins.command(name="config")
    @commands.has_permissions(manage_guild=True)
    async def pins_config(self, ctx):
        """View the pin archival config"""
        guild_config = self._get_guild_pin_config(ctx.guild.id)
        
        embed = discord.Embed(
            title="Pin Archival Configuration",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        status = "Enabled" if guild_config.get("enabled", False) else "Disabled"
        embed.add_field(
            name="Status",
            value=status,
            inline=False
        )
        
        archive_channel_id = guild_config.get("archive_channel")
        channel_value = "Not set"
        if archive_channel_id:
            channel = ctx.guild.get_channel(int(archive_channel_id))
            if channel:
                channel_value = channel.mention
            else:
                channel_value = f"Invalid Channel (ID: {archive_channel_id})"
                
        embed.add_field(
            name="Archive Channel",
            value=channel_value,
            inline=False
        )
        
        unpin_value = "Yes" if guild_config.get("unpin_after_archive", False) else "No"
        embed.add_field(
            name="Unpin After Archive",
            value=unpin_value,
            inline=False
        )
        
        await ctx.send(embed=embed)
        
    @pins.command(name="reset")
    @commands.has_permissions(manage_guild=True)
    async def pins_reset(self, ctx):
        """Reset the pin archival config"""
        if str(ctx.guild.id) in self.pin_config:
            del self.pin_config[str(ctx.guild.id)]
            self._save_pin_config()
        
        await ctx.send("✅ Pin archival configuration has been reset.")
        
    @commands.Cog.listener()
    async def on_guild_channel_pins_update(self, channel, last_pin):
        """Event listener for when pins are updated in a channel"""
        # We will add auto-archiving logic here in the future if needed
        pass 

async def setup(bot):
    await bot.add_cog(PinArchive(bot)) 