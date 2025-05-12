import discord
from discord.ext import commands
import asyncio
import json
import os
import logging
from datetime import datetime

logger = logging.getLogger('bot')

# Default starboard settings
DEFAULT_SETTINGS = {
    "channel_id": None,
    "emoji": "⭐",
    "threshold": 3,
    "selfstar": False,
    "locked": False,
    "ignored_channels": [],
    "ignored_members": [],
    "ignored_roles": [],
    "show_attachments": True,
    "show_timestamp": True,
    "show_jumpurl": True,
    "color": 0xFFAC33  # Gold color
}

class Starboard(commands.Cog):
    """Starboard feature for highlighting the best messages in your server"""
    
    def __init__(self, bot):
        self.bot = bot
        self.data_dir = "data/starboard"
        self.settings = {}
        self.cached_messages = {}
        
        # Create data directory if it doesn't exist
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Load settings for all guilds
        self.bot.loop.create_task(self.load_all_settings())
        
    async def load_all_settings(self):
        """Load settings for all guilds"""
        await self.bot.wait_until_ready()
        
        for guild in self.bot.guilds:
            await self.get_guild_settings(guild.id)
            
    async def get_guild_settings(self, guild_id):
        """Get settings for a specific guild, creating them if they don't exist"""
        if guild_id in self.settings:
            return self.settings[guild_id]
            
        guild_settings = DEFAULT_SETTINGS.copy()
        settings_file = os.path.join(self.data_dir, f"{guild_id}.json")
        
        if os.path.exists(settings_file):
            try:
                with open(settings_file, 'r') as f:
                    stored_settings = json.load(f)
                    guild_settings.update(stored_settings)
            except Exception as e:
                logger.error(f"Error loading starboard settings for guild {guild_id}: {e}")
                
        self.settings[guild_id] = guild_settings
        await self.save_guild_settings(guild_id)
        return guild_settings
        
    async def save_guild_settings(self, guild_id):
        """Save settings for a specific guild"""
        if guild_id not in self.settings:
            return
            
        settings_file = os.path.join(self.data_dir, f"{guild_id}.json")
        
        try:
            with open(settings_file, 'w') as f:
                json.dump(self.settings[guild_id], f, indent=4)
        except Exception as e:
            logger.error(f"Error saving starboard settings for guild {guild_id}: {e}")
    
    def is_ignored(self, guild_id, channel_id=None, member_id=None, role_ids=None):
        """Check if a channel, member, or any roles are ignored"""
        settings = self.settings.get(guild_id, DEFAULT_SETTINGS.copy())
        
        if channel_id and channel_id in settings["ignored_channels"]:
            return True
            
        if member_id and member_id in settings["ignored_members"]:
            return True
            
        if role_ids:
            for role_id in role_ids:
                if role_id in settings["ignored_roles"]:
                    return True
                    
        return False
    
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        """Handle reactions for the starboard"""
        # Ignore reactions from the bot itself
        if payload.user_id == self.bot.user.id:
            return
            
        # Get guild settings
        guild_id = payload.guild_id
        settings = await self.get_guild_settings(guild_id)
        
        # Check if starboard is set up and not locked
        if settings["channel_id"] is None or settings["locked"]:
            return
            
        # Check if the emoji matches the starboard emoji
        if str(payload.emoji) != settings["emoji"]:
            return
            
        # Get the guild, channel, and message objects
        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return
            
        channel = guild.get_channel(payload.channel_id)
        if not channel:
            return
        
        # Check if the channel is ignored
        if self.is_ignored(guild_id, channel_id=channel.id):
            return
            
        try:
            message = await channel.fetch_message(payload.message_id)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            return
            
        # Check if the message author is ignored
        author = message.author
        if self.is_ignored(guild_id, member_id=author.id, role_ids=[role.id for role in author.roles]):
            return
            
        # Get the reaction count for the starboard emoji
        reaction_count = 0
        for reaction in message.reactions:
            if str(reaction.emoji) == settings["emoji"]:
                reaction_count = reaction.count
                break
                
        # Check if threshold is met
        if reaction_count < settings["threshold"]:
            return
            
        # If selfstar is disabled, check if the author reacted to their own message
        if not settings["selfstar"]:
            users = [user async for user in reaction.users()]
            if author in users:
                reaction_count -= 1
                if reaction_count < settings["threshold"]:
                    return
                    
        # Post or update the message on the starboard
        await self.post_to_starboard(message, reaction_count, settings)
    
    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        """Handle reaction removals for the starboard"""
        # Similar logic to on_raw_reaction_add but handles reaction removal
        guild_id = payload.guild_id
        settings = await self.get_guild_settings(guild_id)
        
        if settings["channel_id"] is None or settings["locked"]:
            return
            
        if str(payload.emoji) != settings["emoji"]:
            return
            
        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return
            
        channel = guild.get_channel(payload.channel_id)
        if not channel:
            return
            
        try:
            message = await channel.fetch_message(payload.message_id)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            return
            
        reaction_count = 0
        for reaction in message.reactions:
            if str(reaction.emoji) == settings["emoji"]:
                reaction_count = reaction.count
                break
                
        # Check if message needs to be removed from starboard
        if reaction_count < settings["threshold"]:
            await self.remove_from_starboard(message.id, guild_id, settings)
        else:
            # Update the count
            await self.post_to_starboard(message, reaction_count, settings)
            
    async def post_to_starboard(self, message, stars, settings):
        """Post or update a message on the starboard"""
        starboard_channel = self.bot.get_channel(settings["channel_id"])
        if not starboard_channel:
            return
            
        # Create embed for starboard message
        embed = discord.Embed(
            description=message.content,
            color=settings["color"],
            timestamp=message.created_at if settings["show_timestamp"] else None
        )
        
        # Add author info
        embed.set_author(
            name=message.author.display_name,
            icon_url=message.author.display_avatar.url
        )
        
        # Add footer with message ID and star count
        embed.set_footer(text=f"{settings['emoji']} {stars} | Message ID: {message.id}")
        
        # Add attachments if enabled
        if settings["show_attachments"] and message.attachments:
            attachment = message.attachments[0]
            if attachment.width and attachment.height:  # It's an image
                embed.set_image(url=attachment.url)
            elif len(message.attachments) > 0:
                embed.add_field(name="Attachments", value=f"[{attachment.filename}]({attachment.url})", inline=False)
                
        # Add jump URL if enabled
        if settings["show_jumpurl"]:
            embed.add_field(name="Source", value=f"[Jump to Message]({message.jump_url})", inline=False)
            
        # Check if the message is already in the starboard
        starboard_msg_id = None
        for key, value in self.cached_messages.items():
            if value["original_id"] == message.id and value["guild_id"] == message.guild.id:
                starboard_msg_id = key
                break
                
        try:
            if starboard_msg_id:
                # Update existing starboard message
                try:
                    starboard_msg = await starboard_channel.fetch_message(starboard_msg_id)
                    await starboard_msg.edit(embed=embed)
                except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                    # Message was deleted, create a new one
                    new_msg = await starboard_channel.send(embed=embed)
                    self.cached_messages[new_msg.id] = {
                        "original_id": message.id,
                        "guild_id": message.guild.id
                    }
            else:
                # Create new starboard message
                new_msg = await starboard_channel.send(embed=embed)
                self.cached_messages[new_msg.id] = {
                    "original_id": message.id,
                    "guild_id": message.guild.id
                }
        except Exception as e:
            logger.error(f"Error posting to starboard: {e}")
            
    async def remove_from_starboard(self, message_id, guild_id, settings):
        """Remove a message from the starboard"""
        starboard_channel = self.bot.get_channel(settings["channel_id"])
        if not starboard_channel:
            return
            
        # Find the starboard message
        starboard_msg_id = None
        for key, value in self.cached_messages.items():
            if value["original_id"] == message_id and value["guild_id"] == guild_id:
                starboard_msg_id = key
                break
                
        if starboard_msg_id:
            try:
                # Delete the starboard message
                starboard_msg = await starboard_channel.fetch_message(starboard_msg_id)
                await starboard_msg.delete()
                del self.cached_messages[starboard_msg_id]
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                pass
    
    @commands.group(name="starboard", invoke_without_command=True)
    @commands.has_permissions(manage_guild=True)
    async def starboard(self, ctx):
        """Showcase the best messages in your server"""
        await ctx.send_help(ctx.command)
    
    @starboard.command(name="set")
    @commands.has_permissions(manage_guild=True)
    async def starboard_set(self, ctx, channel: discord.TextChannel, emoji: str = "⭐"):
        """Set the channel for the starboard"""
        # Check bot permissions in the channel
        permissions = channel.permissions_for(ctx.guild.me)
        if not (permissions.send_messages and permissions.embed_links):
            return await ctx.send(f"I need permissions to send messages and embed links in {channel.mention}")
            
        # Get guild settings
        settings = await self.get_guild_settings(ctx.guild.id)
        
        # Update settings
        settings["channel_id"] = channel.id
        settings["emoji"] = emoji
        await self.save_guild_settings(ctx.guild.id)
        
        await ctx.send(f"Starboard channel set to {channel.mention} with emoji {emoji}")
    
    @starboard.command(name="ignore")
    @commands.has_permissions(manage_guild=True)
    async def starboard_ignore(self, ctx, target: discord.abc.Snowflake):
        """Ignore a channel, member, or role for reactions"""
        settings = await self.get_guild_settings(ctx.guild.id)
        
        if isinstance(target, discord.TextChannel):
            if target.id in settings["ignored_channels"]:
                settings["ignored_channels"].remove(target.id)
                await ctx.send(f"Channel {target.mention} is no longer ignored for starboard")
            else:
                settings["ignored_channels"].append(target.id)
                await ctx.send(f"Channel {target.mention} is now ignored for starboard")
                
        elif isinstance(target, discord.Member):
            if target.id in settings["ignored_members"]:
                settings["ignored_members"].remove(target.id)
                await ctx.send(f"Member {target.mention} is no longer ignored for starboard")
            else:
                settings["ignored_members"].append(target.id)
                await ctx.send(f"Member {target.mention} is now ignored for starboard")
                
        elif isinstance(target, discord.Role):
            if target.id in settings["ignored_roles"]:
                settings["ignored_roles"].remove(target.id)
                await ctx.send(f"Role {target.mention} is no longer ignored for starboard")
            else:
                settings["ignored_roles"].append(target.id)
                await ctx.send(f"Role {target.mention} is now ignored for starboard")
                
        else:
            await ctx.send("Invalid target. Please specify a channel, member, or role")
            return
            
        await self.save_guild_settings(ctx.guild.id)
    
    @starboard.command(name="ignore_list")
    @commands.has_permissions(manage_guild=True)
    async def starboard_ignore_list(self, ctx):
        """View ignored roles, members and channels for Starboard"""
        settings = await self.get_guild_settings(ctx.guild.id)
        
        embed = discord.Embed(
            title="Starboard Ignored Items",
            color=discord.Color.gold(),
            timestamp=datetime.utcnow()
        )
        
        # Channels
        ignored_channels = []
        for channel_id in settings["ignored_channels"]:
            channel = ctx.guild.get_channel(channel_id)
            if channel:
                ignored_channels.append(channel.mention)
        
        if ignored_channels:
            embed.add_field(name="Ignored Channels", value="\n".join(ignored_channels), inline=False)
        else:
            embed.add_field(name="Ignored Channels", value="None", inline=False)
            
        # Members
        ignored_members = []
        for member_id in settings["ignored_members"]:
            member = ctx.guild.get_member(member_id)
            if member:
                ignored_members.append(member.mention)
                
        if ignored_members:
            embed.add_field(name="Ignored Members", value="\n".join(ignored_members), inline=False)
        else:
            embed.add_field(name="Ignored Members", value="None", inline=False)
            
        # Roles
        ignored_roles = []
        for role_id in settings["ignored_roles"]:
            role = ctx.guild.get_role(role_id)
            if role:
                ignored_roles.append(role.mention)
                
        if ignored_roles:
            embed.add_field(name="Ignored Roles", value="\n".join(ignored_roles), inline=False)
        else:
            embed.add_field(name="Ignored Roles", value="None", inline=False)
            
        await ctx.send(embed=embed)
    
    @starboard.command(name="threshold")
    @commands.has_permissions(manage_guild=True)
    async def starboard_threshold(self, ctx, number: int):
        """Sets the default amount stars needed to post"""
        if number < 1:
            return await ctx.send("Threshold must be at least 1")
            
        settings = await self.get_guild_settings(ctx.guild.id)
        settings["threshold"] = number
        await self.save_guild_settings(ctx.guild.id)
        
        await ctx.send(f"Starboard threshold set to {number} {settings['emoji']}")
    
    @starboard.command(name="emoji")
    @commands.has_permissions(manage_guild=True)
    async def starboard_emoji(self, ctx, emoji: str):
        """Sets the emoji that triggers the starboard messages"""
        settings = await self.get_guild_settings(ctx.guild.id)
        settings["emoji"] = emoji
        await self.save_guild_settings(ctx.guild.id)
        
        await ctx.send(f"Starboard emoji set to {emoji}")
    
    @starboard.command(name="selfstar")
    @commands.has_permissions(manage_guild=True)
    async def starboard_selfstar(self, ctx, option: bool):
        """Allow an author to star their own message"""
        settings = await self.get_guild_settings(ctx.guild.id)
        settings["selfstar"] = option
        await self.save_guild_settings(ctx.guild.id)
        
        if option:
            await ctx.send("Authors can now star their own messages")
        else:
            await ctx.send("Authors can no longer star their own messages")
    
    @starboard.command(name="lock")
    @commands.has_permissions(manage_guild=True)
    async def starboard_lock(self, ctx):
        """Disables/locks the starboard from operating"""
        settings = await self.get_guild_settings(ctx.guild.id)
        settings["locked"] = True
        await self.save_guild_settings(ctx.guild.id)
        
        await ctx.send("Starboard is now locked. No new messages will be added.")
    
    @starboard.command(name="unlock")
    @commands.has_permissions(manage_guild=True)
    async def starboard_unlock(self, ctx):
        """Enables/unlocks the starboard from operating"""
        settings = await self.get_guild_settings(ctx.guild.id)
        settings["locked"] = False
        await self.save_guild_settings(ctx.guild.id)
        
        await ctx.send("Starboard is now unlocked. New messages can be added.")
    
    @starboard.command(name="jumpurl")
    @commands.has_permissions(manage_guild=True)
    async def starboard_jumpurl(self, ctx, option: bool):
        """Allow the jump URL to appear on a Starboard post"""
        settings = await self.get_guild_settings(ctx.guild.id)
        settings["show_jumpurl"] = option
        await self.save_guild_settings(ctx.guild.id)
        
        if option:
            await ctx.send("Jump URLs will now appear on starboard posts")
        else:
            await ctx.send("Jump URLs will no longer appear on starboard posts")
    
    @starboard.command(name="attachments")
    @commands.has_permissions(manage_guild=True)
    async def starboard_attachments(self, ctx, option: bool):
        """Allow attachments to appear on Starboard posts"""
        settings = await self.get_guild_settings(ctx.guild.id)
        settings["show_attachments"] = option
        await self.save_guild_settings(ctx.guild.id)
        
        if option:
            await ctx.send("Attachments will now appear on starboard posts")
        else:
            await ctx.send("Attachments will no longer appear on starboard posts")
    
    @starboard.command(name="timestamp")
    @commands.has_permissions(manage_guild=True)
    async def starboard_timestamp(self, ctx, option: bool):
        """Allow a timestamp to appear on a Starboard post"""
        settings = await self.get_guild_settings(ctx.guild.id)
        settings["show_timestamp"] = option
        await self.save_guild_settings(ctx.guild.id)
        
        if option:
            await ctx.send("Timestamps will now appear on starboard posts")
        else:
            await ctx.send("Timestamps will no longer appear on starboard posts")
    
    @starboard.command(name="settings")
    @commands.has_permissions(manage_guild=True)
    async def starboard_settings(self, ctx):
        """Display your current starboard settings"""
        settings = await self.get_guild_settings(ctx.guild.id)
        
        embed = discord.Embed(
            title="Starboard Settings",
            color=discord.Color(settings["color"]),
            timestamp=datetime.utcnow()
        )
        
        # Channel info
        channel = None
        if settings["channel_id"]:
            channel = ctx.guild.get_channel(settings["channel_id"])
            
        embed.add_field(
            name="Channel", 
            value=channel.mention if channel else "Not set", 
            inline=True
        )
        
        # Basic settings
        embed.add_field(name="Emoji", value=settings["emoji"], inline=True)
        embed.add_field(name="Threshold", value=settings["threshold"], inline=True)
        embed.add_field(name="Status", value="Locked 🔒" if settings["locked"] else "Unlocked 🔓", inline=True)
        
        # Feature settings
        features = []
        features.append(f"Self-starring: {'Enabled ✅' if settings['selfstar'] else 'Disabled ❌'}")
        features.append(f"Show Jump URL: {'Enabled ✅' if settings['show_jumpurl'] else 'Disabled ❌'}")
        features.append(f"Show Attachments: {'Enabled ✅' if settings['show_attachments'] else 'Disabled ❌'}")
        features.append(f"Show Timestamps: {'Enabled ✅' if settings['show_timestamp'] else 'Disabled ❌'}")
        
        embed.add_field(name="Features", value="\n".join(features), inline=False)
        
        # Ignored items summary
        ignored_summary = []
        ignored_summary.append(f"Ignored Channels: {len(settings['ignored_channels'])}")
        ignored_summary.append(f"Ignored Members: {len(settings['ignored_members'])}")
        ignored_summary.append(f"Ignored Roles: {len(settings['ignored_roles'])}")
        
        embed.add_field(name="Ignored Items", value="\n".join(ignored_summary), inline=False)
        
        embed.set_footer(text=f"Use '{ctx.prefix}starboard ignore_list' to see ignored items")
        
        await ctx.send(embed=embed)
    
    @starboard.command(name="color")
    @commands.has_permissions(manage_guild=True)
    async def starboard_color(self, ctx, color: discord.Color):
        """Set the starboard embed color"""
        settings = await self.get_guild_settings(ctx.guild.id)
        settings["color"] = color.value
        await self.save_guild_settings(ctx.guild.id)
        
        embed = discord.Embed(
            title="Starboard Color Updated",
            description="This is how your starboard embeds will look",
            color=color,
            timestamp=datetime.utcnow()
        )
        
        await ctx.send(embed=embed)
    
    @starboard.command(name="reset")
    @commands.has_permissions(manage_guild=True)
    async def starboard_reset(self, ctx):
        """Reset the guild's starboard configuration"""
        # Confirm with the user
        confirm_msg = await ctx.send("Are you sure you want to reset starboard settings? This will delete all ignore lists and configuration. Type `yes` to confirm.")
        
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() == "yes"
            
        try:
            await self.bot.wait_for("message", check=check, timeout=30.0)
        except asyncio.TimeoutError:
            return await confirm_msg.edit(content="Reset cancelled due to timeout.")
            
        # Reset settings
        self.settings[ctx.guild.id] = DEFAULT_SETTINGS.copy()
        await self.save_guild_settings(ctx.guild.id)
        
        await ctx.send("Starboard settings have been reset to default.")

async def setup(bot):
    await bot.add_cog(Starboard(bot)) 