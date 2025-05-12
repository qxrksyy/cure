import discord
from discord.ext import commands
import logging
import datetime
import os
import asyncio
import math
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import typing

from .levels_db import LevelsDB

logger = logging.getLogger('bot')

class Levels(commands.Cog):
    """Leveling system for Discord servers"""
    
    def __init__(self, bot):
        self.bot = bot
        self.db = LevelsDB()
        
    async def cog_load(self):
        """Initialize the cog on load"""
        await self.db.initialize()
    
    @commands.Cog.listener()
    async def on_message(self, message):
        """Process messages for XP gain"""
        # Ignore bots, DMs, and commands
        if message.author.bot or not message.guild or message.content.startswith(self.bot.command_prefix):
            return
            
        # Process message for XP
        member_role_ids = [str(role.id) for role in message.author.roles]
        level_up = await self.db.process_message(
            str(message.guild.id),
            str(message.author.id),
            str(message.channel.id),
            member_role_ids
        )
        
        # Handle level up
        if level_up:
            await self._handle_level_up(message.guild, message.author, message.channel, level_up)
    
    async def _handle_level_up(self, guild, member, channel, new_level):
        """Handle a user leveling up"""
        # Get guild settings
        settings = await self.db.get_guild_settings(str(guild.id))
        if not settings:
            return
            
        # Check if user wants to see level up messages
        show_messages = await self.db.should_show_level_messages(str(guild.id), str(member.id))
        if not show_messages:
            return
            
        # Handle level up based on message mode
        message_mode = settings.get('message_mode', 'channel')
        if message_mode == 'off':
            return
            
        # Format level up message
        level_up_message = settings.get('level_up_message', 'Congratulations {user}, you reached level {level}!')
        formatted_message = level_up_message.format(
            user=member.mention,
            level=new_level,
            username=member.name,
            server=guild.name
        )
        
        # Send message
        try:
            if message_mode == 'dm':
                await member.send(formatted_message)
            else:
                await channel.send(formatted_message)
        except discord.Forbidden:
            pass
            
        # Assign roles
        await self._update_roles(guild, member, new_level)
    
    async def _update_roles(self, guild, member, level):
        """Update a member's roles based on their level"""
        # Get roles to assign
        roles_to_assign = await self.db.get_roles_to_assign(str(guild.id), level)
        if not roles_to_assign:
            return
            
        # Get settings
        settings = await self.db.get_guild_settings(str(guild.id))
        if not settings:
            return
            
        # Get all level roles
        all_level_roles = await self.db.get_level_roles(str(guild.id))
        all_role_ids = [role_id for _, role_id in all_level_roles]
        
        try:
            # Get role objects
            roles_to_add = []
            roles_to_remove = []
            
            for role_id in roles_to_assign:
                role = guild.get_role(int(role_id))
                if role:
                    roles_to_add.append(role)
            
            if not settings.get('stack_roles', False):
                # Get roles to remove (roles that are not in roles_to_assign)
                for role_id in all_role_ids:
                    if role_id not in roles_to_assign:
                        role = guild.get_role(int(role_id))
                        if role and role in member.roles:
                            roles_to_remove.append(role)
            
            # Update member's roles
            await member.add_roles(*roles_to_add, reason="Level up reward")
            
            if roles_to_remove:
                await member.remove_roles(*roles_to_remove, reason="Level change")
        except discord.Forbidden:
            pass
        except Exception as e:
            logger.error(f"Error updating roles: {e}")
    
    @commands.group(name="levels", aliases=["level", "rank", "lvl"], invoke_without_command=True)
    async def levels(self, ctx, member: discord.Member = None):
        """View your level or someone else's level"""
        target = member or ctx.author
        
        # Get level info
        level_info = await self.db.get_user_level(str(ctx.guild.id), str(target.id))
        if not level_info:
            await ctx.send(f"No level data found for {target.mention}.")
            return
        
        # Calculate progress to next level
        current_level = level_info['level']
        current_xp = level_info['xp']
        xp_for_current = self.db.xp_for_level(current_level)
        xp_for_next = self.db.xp_for_level(current_level + 1)
        progress = (current_xp - xp_for_current) / (xp_for_next - xp_for_current) if xp_for_next > xp_for_current else 1.0
        
        # Create embed
        embed = discord.Embed(
            title=f"{target.name}'s Level",
            description=f"Level: **{current_level}**\nXP: **{current_xp}** / **{xp_for_next}**",
            color=target.color or discord.Color.blue()
        )
        
        # Add progress bar
        progress_bar = self._create_progress_bar(progress)
        embed.add_field(name="Progress to Next Level", value=progress_bar, inline=False)
        
        # Get rank on leaderboard
        leaderboard = await self.db.get_leaderboard(str(ctx.guild.id))
        rank = next((i for i, entry in enumerate(leaderboard, 1) if entry['user_id'] == str(target.id)), None)
        if rank:
            embed.add_field(name="Rank", value=f"#{rank} / {len(leaderboard)}", inline=True)
        
        # Add user avatar
        embed.set_thumbnail(url=target.display_avatar.url)
        
        await ctx.send(embed=embed)
    
    def _create_progress_bar(self, progress, length=10):
        """Create a text progress bar"""
        filled = int(progress * length)
        bar = "▓" * filled + "░" * (length - filled)
        percent = int(progress * 100)
        return f"{bar} {percent}%"
    
    @levels.command(name="leaderboard", aliases=["lb", "top"])
    async def leaderboard(self, ctx):
        """View the highest ranking members"""
        leaderboard = await self.db.get_leaderboard(str(ctx.guild.id), limit=10)
        if not leaderboard:
            await ctx.send("No level data found for this server.")
            return
        
        embed = discord.Embed(
            title=f"{ctx.guild.name} Leaderboard",
            color=discord.Color.blue()
        )
        
        for i, entry in enumerate(leaderboard, 1):
            user_id = entry['user_id']
            level = entry['level']
            xp = entry['xp']
            
            member = ctx.guild.get_member(int(user_id))
            name = member.name if member else f"User {user_id}"
            
            embed.add_field(
                name=f"#{i} {name}",
                value=f"Level: {level} | XP: {xp}",
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    @levels.command(name="roles")
    async def roles(self, ctx):
        """Show all level rewards"""
        roles = await self.db.get_level_roles(str(ctx.guild.id))
        if not roles:
            await ctx.send("No level rewards set up for this server.")
            return
        
        embed = discord.Embed(
            title="Level Rewards",
            color=discord.Color.blue()
        )
        
        for level, role_id in sorted(roles, key=lambda x: x[0]):
            role = ctx.guild.get_role(int(role_id))
            if role:
                embed.add_field(
                    name=f"Level {level}",
                    value=role.mention,
                    inline=True
                )
        
        # Add settings info
        settings = await self.db.get_guild_settings(str(ctx.guild.id))
        if settings:
            stack_roles = "Yes" if settings.get('stack_roles', False) else "No"
            embed.set_footer(text=f"Role Stacking: {stack_roles}")
        
        await ctx.send(embed=embed)
    
    @levels.command(name="add")
    @commands.has_permissions(manage_guild=True)
    async def add_role(self, ctx, role: discord.Role, level: int):
        """Create level role"""
        if level < 1:
            await ctx.send("Level must be at least 1.")
            return
        
        success = await self.db.add_level_role(str(ctx.guild.id), level, str(role.id))
        if success:
            await ctx.send(f"Successfully added {role.mention} as a reward for level {level}.")
        else:
            await ctx.send("Failed to add level reward. Please try again.")
    
    @levels.command(name="remove")
    @commands.has_permissions(manage_guild=True)
    async def remove_role(self, ctx, level: int):
        """Remove a level role"""
        roles = await self.db.get_level_roles(str(ctx.guild.id))
        role_at_level = next((role_id for lvl, role_id in roles if lvl == level), None)
        
        if not role_at_level:
            await ctx.send(f"No role found for level {level}.")
            return
        
        success = await self.db.remove_level_role(str(ctx.guild.id), level)
        if success:
            role = ctx.guild.get_role(int(role_at_level))
            role_name = role.name if role else f"role {role_at_level}"
            await ctx.send(f"Successfully removed {role_name} as a reward for level {level}.")
        else:
            await ctx.send("Failed to remove level reward. Please try again.")
    
    @levels.command(name="stackroles")
    @commands.has_permissions(manage_guild=True)
    async def stackroles(self, ctx, option: str):
        """Enable or disable stacking of roles"""
        option = option.lower()
        if option not in ["on", "off", "enable", "disable", "true", "false"]:
            await ctx.send("Please use 'on' or 'off' to enable or disable role stacking.")
            return
        
        enabled = option in ["on", "enable", "true"]
        success = await self.db.set_stack_roles(str(ctx.guild.id), enabled)
        
        if success:
            if enabled:
                await ctx.send("Role stacking enabled. Users will keep all previous level roles when leveling up.")
            else:
                await ctx.send("Role stacking disabled. Users will only have the role for their current level.")
        else:
            await ctx.send("Failed to update role stacking setting. Please try again.")
    
    @levels.group(name="message", invoke_without_command=True)
    @commands.has_permissions(manage_guild=True)
    async def set_message(self, ctx, *, message: str = None):
        """Set a message for leveling up"""
        if message is None:
            await ctx.invoke(self.message_view)
            return
        
        success = await self.db.set_level_up_message(str(ctx.guild.id), message)
        if success:
            await ctx.send(f"Level up message set to: {message}")
        else:
            await ctx.send("Failed to update level up message. Please try again.")

    @set_message.command(name="view")
    @commands.has_permissions(manage_guild=True)
    async def message_view(self, ctx):
        """View the level up message for the server"""
        settings = await self.db.get_guild_settings(str(ctx.guild.id))
        if not settings:
            await ctx.send("No settings found for this server.")
            return
        
        message = settings.get('level_up_message', 'Congratulations {user}, you reached level {level}!')
        await ctx.send(f"Current level up message: {message}")
    
    @levels.command(name="messagemode")
    @commands.has_permissions(manage_guild=True)
    async def messagemode(self, ctx, mode: str):
        """Set up where level up messages will be sent"""
        mode = mode.lower()
        valid_modes = ["channel", "dm", "off"]
        if mode not in valid_modes:
            await ctx.send("Valid modes are: channel, dm, off")
            return
        
        success = await self.db.set_message_mode(str(ctx.guild.id), mode)
        if success:
            if mode == "channel":
                await ctx.send("Level up messages will now be sent in the channel where the user leveled up.")
            elif mode == "dm":
                await ctx.send("Level up messages will now be sent as DMs to the user.")
            else:  # mode == "off"
                await ctx.send("Level up messages are now disabled.")
        else:
            await ctx.send("Failed to update message mode. Please try again.")
    
    @levels.command(name="ignore")
    @commands.has_permissions(manage_guild=True)
    async def ignore(self, ctx, target: typing.Union[discord.TextChannel, discord.Role]):
        """Ignore a channel or role for XP"""
        entity_type = "channel" if isinstance(target, discord.TextChannel) else "role"
        
        # Check if already ignored
        is_ignored = await self.db.is_entity_ignored(str(ctx.guild.id), str(target.id))
        if is_ignored:
            await ctx.send(f"The {entity_type} {target.mention} is already ignored for XP gain.")
            return
        
        success = await self.db.ignore_entity(str(ctx.guild.id), str(target.id), entity_type)
        if success:
            await ctx.send(f"The {entity_type} {target.mention} will now be ignored for XP gain.")
        else:
            await ctx.send(f"Failed to ignore the {entity_type}. Please try again.")
    
    @levels.command(name="unignore")
    @commands.has_permissions(manage_guild=True)
    async def unignore(self, ctx, target: typing.Union[discord.TextChannel, discord.Role]):
        """Unignore a channel or role for XP"""
        # Check if ignored
        is_ignored = await self.db.is_entity_ignored(str(ctx.guild.id), str(target.id))
        if not is_ignored:
            entity_type = "channel" if isinstance(target, discord.TextChannel) else "role"
            await ctx.send(f"The {entity_type} {target.mention} is not ignored for XP gain.")
            return
        
        success = await self.db.unignore_entity(str(ctx.guild.id), str(target.id))
        if success:
            entity_type = "channel" if isinstance(target, discord.TextChannel) else "role"
            await ctx.send(f"The {entity_type} {target.mention} will now grant XP again.")
        else:
            await ctx.send("Failed to unignore the entity. Please try again.")
    
    @levels.command(name="list")
    @commands.has_permissions(manage_guild=True)
    async def list_ignored(self, ctx):
        """View all ignored channels and roles"""
        entities = await self.db.get_ignored_entities(str(ctx.guild.id))
        if not entities:
            await ctx.send("No ignored channels or roles found.")
            return
        
        embed = discord.Embed(
            title="Ignored Channels and Roles",
            color=discord.Color.blue()
        )
        
        channels = []
        roles = []
        
        for entity_id, entity_type in entities:
            if entity_type == "channel":
                channel = ctx.guild.get_channel(int(entity_id))
                if channel:
                    channels.append(channel.mention)
            else:  # entity_type == "role"
                role = ctx.guild.get_role(int(entity_id))
                if role:
                    roles.append(role.mention)
        
        if channels:
            embed.add_field(name="Ignored Channels", value="\n".join(channels), inline=False)
        
        if roles:
            embed.add_field(name="Ignored Roles", value="\n".join(roles), inline=False)
        
        await ctx.send(embed=embed)
    
    @levels.command(name="setrate")
    @commands.has_permissions(manage_guild=True)
    async def setrate(self, ctx, multiplier: float):
        """Set multiplier for XP gain"""
        if multiplier <= 0:
            await ctx.send("XP rate multiplier must be greater than 0.")
            return
        
        success = await self.db.set_xp_rate(str(ctx.guild.id), multiplier)
        if success:
            await ctx.send(f"XP rate multiplier set to {multiplier}x.")
        else:
            await ctx.send("Failed to update XP rate multiplier. Please try again.")
    
    @levels.command(name="messages")
    async def toggle_messages(self, ctx, setting: str):
        """Toggle level up messages for yourself"""
        setting = setting.lower()
        if setting not in ["on", "off", "enable", "disable", "true", "false"]:
            await ctx.send("Please use 'on' or 'off' to enable or disable level up messages.")
            return
        
        show = setting in ["on", "enable", "true"]
        success = await self.db.toggle_level_messages(str(ctx.guild.id), str(ctx.author.id), show)
        
        if success:
            if show:
                await ctx.send("You will now receive level up messages.")
            else:
                await ctx.send("You will no longer receive level up messages.")
        else:
            await ctx.send("Failed to update your message setting. Please try again.")
    
    @levels.command(name="reset")
    @commands.has_permissions(manage_guild=True)
    async def reset(self, ctx):
        """Reset all levels and configurations"""
        # Ask for confirmation
        embed = discord.Embed(
            title="Confirmation",
            description="Are you sure you want to reset all levels and configurations? This action cannot be undone.",
            color=discord.Color.red()
        )
        confirmation_message = await ctx.send(embed=embed)
        
        # Add reactions
        await confirmation_message.add_reaction("✅")
        await confirmation_message.add_reaction("❌")
        
        # Wait for reaction
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == confirmation_message.id
        
        try:
            reaction, user = await self.bot.wait_for("reaction_add", timeout=30, check=check)
            
            if str(reaction.emoji) == "✅":
                success = await self.db.reset_levels(str(ctx.guild.id))
                if success:
                    await ctx.send("All levels and configurations have been reset.")
                else:
                    await ctx.send("Failed to reset levels and configurations. Please try again.")
            else:
                await ctx.send("Reset canceled.")
        except asyncio.TimeoutError:
            await ctx.send("Reset canceled due to timeout.")
    
    @levels.command(name="lock")
    @commands.has_permissions(manage_guild=True)
    async def lock(self, ctx):
        """Disable leveling system"""
        success = await self.db.enable_leveling(str(ctx.guild.id), False)
        if success:
            await ctx.send("Leveling system has been disabled.")
        else:
            await ctx.send("Failed to disable leveling system. Please try again.")
    
    @levels.command(name="unlock")
    @commands.has_permissions(manage_guild=True)
    async def unlock(self, ctx):
        """Enable leveling system"""
        success = await self.db.enable_leveling(str(ctx.guild.id), True)
        if success:
            await ctx.send("Leveling system has been enabled.")
        else:
            await ctx.send("Failed to enable leveling system. Please try again.")
    
    @levels.command(name="cleanup")
    @commands.has_permissions(manage_guild=True)
    async def cleanup(self, ctx):
        """Reset level & XP for absent members"""
        # Get all members in the guild
        member_ids = [str(member.id) for member in ctx.guild.members]
        
        count = await self.db.cleanup_absent_members(str(ctx.guild.id), member_ids)
        await ctx.send(f"Cleaned up {count} absent members from the levels database.")
    
    @levels.command(name="sync")
    @commands.has_permissions(manage_guild=True)
    async def sync(self, ctx):
        """Sync your level roles for your members"""
        # Get all level roles
        roles = await self.db.get_level_roles(str(ctx.guild.id))
        if not roles:
            await ctx.send("No level roles found. Set up level roles first with `!levels add`.")
            return
        
        # Get all users in the database
        async with ctx.typing():
            for member in ctx.guild.members:
                # Skip bots
                if member.bot:
                    continue
                
                # Get user level
                user_level = await self.db.get_user_level(str(ctx.guild.id), str(member.id))
                if not user_level:
                    continue
                
                # Update roles
                await self._update_roles(ctx.guild, member, user_level['level'])
        
        await ctx.send("Synced level roles for all members.")
    
    @levels.command(name="config")
    @commands.has_permissions(manage_guild=True)
    async def config(self, ctx):
        """View server configuration for Leveling system"""
        settings = await self.db.get_guild_settings(str(ctx.guild.id))
        if not settings:
            await ctx.send("No settings found for this server.")
            return
        
        embed = discord.Embed(
            title="Leveling System Configuration",
            color=discord.Color.blue()
        )
        
        embed.add_field(name="Enabled", value="Yes" if settings['enabled'] else "No", inline=True)
        embed.add_field(name="XP Rate", value=f"{settings['xp_rate']}x", inline=True)
        embed.add_field(name="Role Stacking", value="Yes" if settings['stack_roles'] else "No", inline=True)
        
        message_mode = settings['message_mode']
        if message_mode == "channel":
            embed.add_field(name="Message Mode", value="Channel", inline=True)
        elif message_mode == "dm":
            embed.add_field(name="Message Mode", value="DM", inline=True)
        else:  # message_mode == "off"
            embed.add_field(name="Message Mode", value="Off", inline=True)
        
        embed.add_field(name="Level Up Message", value=settings['level_up_message'], inline=False)
        
        # Add role count
        roles = await self.db.get_level_roles(str(ctx.guild.id))
        embed.add_field(name="Level Roles", value=f"{len(roles)} roles configured", inline=True)
        
        # Add ignored entities count
        entities = await self.db.get_ignored_entities(str(ctx.guild.id))
        channels = sum(1 for _, type in entities if type == "channel")
        roles = sum(1 for _, type in entities if type == "role")
        embed.add_field(name="Ignored Entities", value=f"{channels} channels, {roles} roles", inline=True)
        
        await ctx.send(embed=embed)

    @commands.command(name="setlevel")
    @commands.has_permissions(manage_guild=True)
    async def setlevel(self, ctx, member: discord.Member, level: int):
        """Set a user's level"""
        if level < 1:
            await ctx.send("Level must be at least 1.")
            return
        
        success = await self.db.set_user_level(str(ctx.guild.id), str(member.id), level)
        if success:
            await ctx.send(f"{member.mention}'s level has been set to {level}.")
            await self._update_roles(ctx.guild, member, level)
        else:
            await ctx.send(f"Failed to set {member.mention}'s level. Please try again.")
    
    @commands.command(name="setxp")
    @commands.has_permissions(manage_guild=True)
    async def setxp(self, ctx, member: discord.Member, xp: int):
        """Set a user's experience"""
        if xp < 0:
            await ctx.send("XP must be at least 0.")
            return
        
        success = await self.db.set_user_xp(str(ctx.guild.id), str(member.id), xp)
        if success:
            # Get the new level for this XP
            level = self.db.level_for_xp(xp)
            await ctx.send(f"{member.mention}'s XP has been set to {xp} (Level {level}).")
            await self._update_roles(ctx.guild, member, level)
        else:
            await ctx.send(f"Failed to set {member.mention}'s XP. Please try again.")
    
    @commands.command(name="removexp")
    @commands.has_permissions(manage_guild=True)
    async def removexp(self, ctx, member: discord.Member, xp: int):
        """Remove experience from a user"""
        if xp <= 0:
            await ctx.send("XP to remove must be greater than 0.")
            return
        
        # Get current level and XP
        user_level = await self.db.get_user_level(str(ctx.guild.id), str(member.id))
        if not user_level:
            await ctx.send(f"No level data found for {member.mention}.")
            return
        
        old_level = user_level['level']
        old_xp = user_level['xp']
        
        success = await self.db.remove_user_xp(str(ctx.guild.id), str(member.id), xp)
        if success:
            # Get updated info
            updated_level = await self.db.get_user_level(str(ctx.guild.id), str(member.id))
            new_level = updated_level['level']
            new_xp = updated_level['xp']
            
            await ctx.send(f"Removed {xp} XP from {member.mention}. New XP: {new_xp} (Level {new_level}).")
            
            # Update roles if level changed
            if new_level != old_level:
                await self._update_roles(ctx.guild, member, new_level)
        else:
            await ctx.send(f"Failed to remove XP from {member.mention}. Please try again.")

async def setup(bot):
    """Load the Levels cog"""
    await bot.add_cog(Levels(bot)) 