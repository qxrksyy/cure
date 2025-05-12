import discord
from discord.ext import commands, tasks
import json
import os
import asyncio
import datetime
import random
import logging
import re
from typing import Dict, List, Optional, Union, Set

logger = logging.getLogger('bot')

# Constants
REACTION_EMOJI = "🎉"
DEFAULT_GIVEAWAY_COLOR = 0x1ABC9C  # Turquoise
ERROR_COLOR = 0xE74C3C  # Red
SUCCESS_COLOR = 0x2ECC71  # Green
MAX_ACTIVE_GIVEAWAYS = 25  # Maximum number of active giveaways per guild

class Giveaway(commands.Cog):
    """Giveaway commands for creating and managing giveaways"""
    
    def __init__(self, bot):
        self.bot = bot
        self.data_dir = "data/giveaways"
        self.active_giveaways = {}  # guild_id -> {message_id -> giveaway_data}
        self.ended_giveaways = {}  # guild_id -> {message_id -> giveaway_data}
        
        # Create data directory if it doesn't exist
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Start the background tasks
        self.load_active_giveaways.start()
        self.check_ended_giveaways.start()
        
    def cog_unload(self):
        """Cleanup when cog is unloaded"""
        self.check_ended_giveaways.cancel()
        self.load_active_giveaways.cancel()
        
        # Save all active giveaways when unloaded
        for guild_id in self.active_giveaways:
            self.save_giveaways(guild_id)
    
    @tasks.loop(seconds=1, count=1)
    async def load_active_giveaways(self):
        """Load all active giveaways on startup"""
        logger.info("Loading active giveaways...")
        
        # Get all guild data files
        for filename in os.listdir(self.data_dir):
            if filename.endswith(".json"):
                try:
                    guild_id = int(filename[:-5])  # Remove .json extension
                    filepath = os.path.join(self.data_dir, filename)
                    
                    with open(filepath, 'r') as f:
                        data = json.load(f)
                        
                    # Initialize guild dictionary if not exists
                    if guild_id not in self.active_giveaways:
                        self.active_giveaways[guild_id] = {}
                        
                    if guild_id not in self.ended_giveaways:
                        self.ended_giveaways[guild_id] = {}
                        
                    # Load active giveaways
                    for message_id, giveaway in data.get("active", {}).items():
                        self.active_giveaways[guild_id][message_id] = giveaway
                        
                    # Load ended giveaways
                    for message_id, giveaway in data.get("ended", {}).items():
                        self.ended_giveaways[guild_id][message_id] = giveaway
                        
                    logger.info(f"Loaded {len(self.active_giveaways.get(guild_id, {}))} active giveaways for guild {guild_id}")
                        
                except Exception as e:
                    logger.error(f"Error loading giveaways for file {filename}: {e}")
    
    @load_active_giveaways.before_loop
    async def before_load_active_giveaways(self):
        """Wait for the bot to be ready before loading giveaways"""
        await self.bot.wait_until_ready()
    
    @tasks.loop(seconds=60)  # Check every minute
    async def check_ended_giveaways(self):
        """Check for giveaways that have ended"""
        current_time = datetime.datetime.utcnow().timestamp()
        
        for guild_id, giveaways in list(self.active_giveaways.items()):
            guild = self.bot.get_guild(guild_id)
            if not guild:
                continue
                
            for message_id, giveaway in list(giveaways.items()):
                # Check if the giveaway has ended
                if giveaway["end_time"] <= current_time:
                    try:
                        # Get the channel and message
                        channel_id = giveaway["channel_id"]
                        channel = guild.get_channel(channel_id)
                        
                        if channel:
                            # Try to end the giveaway
                            await self.end_giveaway(guild, channel, message_id, giveaway)
                    except Exception as e:
                        logger.error(f"Error processing ended giveaway in guild {guild_id}, message {message_id}: {e}")
    
    @check_ended_giveaways.before_loop
    async def before_check_ended_giveaways(self):
        """Wait for giveaways to be loaded before checking for ended ones"""
        await self.load_active_giveaways.wait()
    
    def save_giveaways(self, guild_id: int):
        """Save active and ended giveaways for a guild"""
        filepath = os.path.join(self.data_dir, f"{guild_id}.json")
        
        data = {
            "active": self.active_giveaways.get(guild_id, {}),
            "ended": self.ended_giveaways.get(guild_id, {})
        }
        
        try:
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=4)
            logger.debug(f"Saved giveaways for guild {guild_id}")
        except Exception as e:
            logger.error(f"Error saving giveaways for guild {guild_id}: {e}")
    
    def parse_duration(self, duration_str: str) -> Optional[int]:
        """
        Parse a duration string into seconds.
        Format: 1d2h3m4s (days, hours, minutes, seconds)
        """
        total_seconds = 0
        pattern = r'(\d+)([dhms])'
        
        matches = re.findall(pattern, duration_str.lower())
        if not matches:
            return None
            
        for value, unit in matches:
            value = int(value)
            if unit == 'd':
                total_seconds += value * 86400  # days to seconds
            elif unit == 'h':
                total_seconds += value * 3600   # hours to seconds
            elif unit == 'm':
                total_seconds += value * 60     # minutes to seconds
            elif unit == 's':
                total_seconds += value          # seconds
                
        return total_seconds
    
    def format_time(self, seconds: int) -> str:
        """Format seconds into a readable time string"""
        if seconds < 60:
            return f"{seconds} seconds"
            
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)
        
        parts = []
        if days > 0:
            parts.append(f"{days} day{'s' if days != 1 else ''}")
        if hours > 0:
            parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
        if minutes > 0:
            parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
        if seconds > 0:
            parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")
            
        return ", ".join(parts)
    
    def time_remaining(self, end_time: float) -> str:
        """Calculate and format the time remaining for a giveaway"""
        now = datetime.datetime.utcnow().timestamp()
        remaining = max(0, end_time - now)
        
        return self.format_time(int(remaining))
    
    def create_giveaway_embed(self, giveaway: dict, is_ended: bool = False) -> discord.Embed:
        """Create an embed for a giveaway"""
        prize = giveaway["prize"]
        description = giveaway.get("description", "React with 🎉 to enter!")
        host_ids = giveaway.get("host_ids", [])
        thumbnail_url = giveaway.get("thumbnail_url")
        image_url = giveaway.get("image_url")
        winners_count = giveaway["winners_count"]
        
        # Choose color based on state
        if is_ended:
            color = discord.Color.light_grey()
        else:
            color = discord.Color(DEFAULT_GIVEAWAY_COLOR)
            
        # Create embed
        embed = discord.Embed(
            title=f"🎉 GIVEAWAY: {prize}",
            description=description,
            color=color,
            timestamp=datetime.datetime.utcnow()
        )
        
        # Add host information
        host_mentions = []
        for host_id in host_ids:
            host_mentions.append(f"<@{host_id}>")
            
        if host_mentions:
            embed.add_field(name="Hosted by", value=", ".join(host_mentions), inline=True)
            
        # Add winners count
        embed.add_field(
            name="Winners", 
            value=f"{winners_count} {'winner' if winners_count == 1 else 'winners'}", 
            inline=True
        )
        
        # Add time info
        if is_ended:
            embed.add_field(name="Status", value="🎊 Giveaway Ended! 🎊", inline=True)
        else:
            time_left = self.time_remaining(giveaway["end_time"])
            embed.add_field(name="Time Remaining", value=time_left, inline=True)
            
            # End time timestamp for Discord to display
            end_time_datetime = datetime.datetime.fromtimestamp(giveaway["end_time"])
            embed.add_field(
                name="Ends At", 
                value=f"<t:{int(giveaway['end_time'])}:F> (<t:{int(giveaway['end_time'])}:R>)", 
                inline=True
            )
        
        # Add entry requirements if any
        requirements = []
        
        min_account_age = giveaway.get("min_account_age")
        if min_account_age:
            requirements.append(f"• Account Age: At least {self.format_time(min_account_age)}")
            
        min_server_stay = giveaway.get("min_server_stay") 
        if min_server_stay:
            requirements.append(f"• Server Stay: At least {min_server_stay} days")
            
        min_level = giveaway.get("min_level")
        if min_level:
            requirements.append(f"• Minimum Level: {min_level}")
            
        max_level = giveaway.get("max_level")
        if max_level:
            requirements.append(f"• Maximum Level: {max_level}")
            
        required_role_ids = giveaway.get("required_role_ids", [])
        if required_role_ids:
            role_mentions = [f"<@&{role_id}>" for role_id in required_role_ids]
            requirements.append(f"• Required Roles: {', '.join(role_mentions)}")
            
        if requirements:
            embed.add_field(
                name="Entry Requirements", 
                value="\n".join(requirements), 
                inline=False
            )
            
        # Add reward roles if any
        reward_role_ids = giveaway.get("reward_role_ids", [])
        if reward_role_ids:
            role_mentions = [f"<@&{role_id}>" for role_id in reward_role_ids]
            embed.add_field(
                name="Reward Roles", 
                value=", ".join(role_mentions), 
                inline=False
            )
            
        # Add winners section if ended
        if is_ended and "winner_ids" in giveaway:
            winner_ids = giveaway["winner_ids"]
            if winner_ids:
                winners_text = ", ".join([f"<@{winner_id}>" for winner_id in winner_ids])
                embed.add_field(
                    name=f"🏆 {'Winner' if len(winner_ids) == 1 else 'Winners'}", 
                    value=winners_text, 
                    inline=False
                )
            else:
                embed.add_field(
                    name="Winners", 
                    value="No valid winners could be determined.", 
                    inline=False
                )
                
        # Add footer
        entries = giveaway.get("entries", [])
        footer_text = f"{len(entries)} {'entry' if len(entries) == 1 else 'entries'}"
        if not is_ended:
            footer_text += " • React with 🎉 to enter!"
            
        embed.set_footer(text=footer_text)
        
        # Add thumbnail and image if provided
        if thumbnail_url:
            embed.set_thumbnail(url=thumbnail_url)
            
        if image_url:
            embed.set_image(url=image_url)
            
        return embed
    
    async def end_giveaway(self, guild: discord.Guild, channel: discord.TextChannel, 
                          message_id: str, giveaway: dict) -> bool:
        """End a giveaway and select winners"""
        try:
            # Get the message
            try:
                message = await channel.fetch_message(int(message_id))
            except (discord.NotFound, discord.HTTPException):
                logger.warning(f"Could not find giveaway message {message_id} in channel {channel.id}")
                # Remove from active giveaways since the message is gone
                if guild.id in self.active_giveaways and message_id in self.active_giveaways[guild.id]:
                    del self.active_giveaways[guild.id][message_id]
                    self.save_giveaways(guild.id)
                return False
            
            # Get all the entries (users who reacted)
            entries = []
            for reaction in message.reactions:
                if str(reaction.emoji) == REACTION_EMOJI:
                    async for user in reaction.users():
                        if not user.bot:  # Skip bots
                            entries.append(user.id)
                            
            # Update entries in the giveaway data
            giveaway["entries"] = entries
            
            # Get valid entries (apply restrictions)
            valid_entries = await self.filter_valid_entries(guild, giveaway, entries)
            
            # Select winners
            winners_count = giveaway["winners_count"]
            winner_ids = []
            
            if valid_entries:
                # Ensure we don't try to pick more winners than there are valid entries
                winners_count = min(winners_count, len(valid_entries))
                winner_ids = random.sample(valid_entries, winners_count)
                
            # Update giveaway data with winners
            giveaway["winner_ids"] = winner_ids
            giveaway["valid_entries"] = valid_entries
            giveaway["ended_at"] = datetime.datetime.utcnow().timestamp()
            
            # Move from active to ended giveaways
            if guild.id in self.active_giveaways and message_id in self.active_giveaways[guild.id]:
                del self.active_giveaways[guild.id][message_id]
                
                # Initialize the ended_giveaways dictionary for this guild if it doesn't exist
                if guild.id not in self.ended_giveaways:
                    self.ended_giveaways[guild.id] = {}
                    
                self.ended_giveaways[guild.id][message_id] = giveaway
                self.save_giveaways(guild.id)
                
            # Update the giveaway message
            embed = self.create_giveaway_embed(giveaway, is_ended=True)
            await message.edit(embed=embed)
            
            # Send winner announcement
            if winner_ids:
                winners_mention = ", ".join([f"<@{winner_id}>" for winner_id in winner_ids])
                prize = giveaway["prize"]
                
                announcement = f"🎊 Congratulations {winners_mention}! You won the **{prize}**!"
                
                # If there are reward roles, apply them
                reward_role_ids = giveaway.get("reward_role_ids", [])
                if reward_role_ids:
                    reward_roles = [guild.get_role(role_id) for role_id in reward_role_ids if guild.get_role(role_id)]
                    if reward_roles:
                        # Add roles to winners
                        for winner_id in winner_ids:
                            member = guild.get_member(winner_id)
                            if member:
                                for role in reward_roles:
                                    try:
                                        await member.add_roles(role, reason=f"Giveaway prize: {prize}")
                                    except discord.Forbidden:
                                        logger.warning(f"Could not add role {role.name} to {member.display_name}")
                        
                        # Add roles info to the announcement
                        role_names = ", ".join([role.mention for role in reward_roles])
                        announcement += f"\n\nYou have been given the following role(s): {role_names}"
                
                await channel.send(announcement, reference=message)
            else:
                await channel.send(f"No valid winners could be determined for the **{giveaway['prize']}** giveaway.", 
                                  reference=message)
                
            return True
            
        except Exception as e:
            logger.error(f"Error ending giveaway {message_id}: {e}")
            return False
            
    async def filter_valid_entries(self, guild: discord.Guild, giveaway: dict, entries: List[int]) -> List[int]:
        """Filter the list of entries based on giveaway requirements"""
        valid_entries = []
        
        # Get all filter requirements
        min_account_age = giveaway.get("min_account_age", 0)
        min_server_stay = giveaway.get("min_server_stay", 0)
        min_level = giveaway.get("min_level")
        max_level = giveaway.get("max_level")
        required_role_ids = giveaway.get("required_role_ids", [])
        
        # If there are no requirements, all entries are valid
        if not (min_account_age or min_server_stay or min_level or max_level or required_role_ids):
            return entries
            
        # Current time for age calculations
        now = datetime.datetime.utcnow()
        min_creation_time = None
        min_join_time = None
        
        if min_account_age:
            min_creation_time = now - datetime.timedelta(seconds=min_account_age)
            
        if min_server_stay:
            min_join_time = now - datetime.timedelta(days=min_server_stay)
        
        # Check each entry against requirements
        for user_id in entries:
            member = guild.get_member(user_id)
            if not member:
                continue
                
            # Check account age
            if min_creation_time and member.created_at > min_creation_time:
                continue
                
            # Check server stay duration
            if min_join_time and member.joined_at and member.joined_at > min_join_time:
                continue
                
            # Check roles
            if required_role_ids and not any(role.id in required_role_ids for role in member.roles):
                continue
                
            # Check levels if implemented
            if min_level or max_level:
                user_level = await self.get_user_level(member)
                if min_level and (user_level is None or user_level < min_level):
                    continue
                if max_level and (user_level is not None and user_level > max_level):
                    continue
                    
            # If passed all checks, this entry is valid
            valid_entries.append(user_id)
            
        return valid_entries
    
    async def get_user_level(self, member: discord.Member) -> Optional[int]:
        """
        Get a user's level if a levels cog is present
        Returns None if levels cog is not found or user has no level
        """
        levels_cog = self.bot.get_cog("Levels")
        if not levels_cog:
            return None
            
        # This assumes the Levels cog has a get_user_level method
        try:
            if hasattr(levels_cog, "get_user_level"):
                return await levels_cog.get_user_level(member.guild.id, member.id)
            return None
        except Exception:
            return None

async def setup(bot):
    await bot.add_cog(Giveaway(bot)) 