import discord
from discord.ext import commands
import json
import os
import logging
from datetime import datetime
import asyncio
import time

logger = logging.getLogger('bot')

class UserHistory(commands.Cog):
    """
    Commands for tracking user history like names, avatars, and activity
    """
    
    def __init__(self, bot):
        self.bot = bot
        self.config_path = "data/miscellaneous/history"
        self.name_history = {}  # User ID -> list of name changes
        self.avatar_history = {}  # User ID -> list of avatar changes
        self.guild_name_history = {}  # Guild ID -> list of name changes
        self.user_seen = {}  # User ID -> last seen timestamp
        self.user_screentime = {}  # User ID -> status statistics
        
        # Create directories if they don't exist
        os.makedirs(os.path.join(self.config_path, "names"), exist_ok=True)
        os.makedirs(os.path.join(self.config_path, "avatars"), exist_ok=True)
        os.makedirs(os.path.join(self.config_path, "guilds"), exist_ok=True)
        os.makedirs(os.path.join(self.config_path, "seen"), exist_ok=True)
        os.makedirs(os.path.join(self.config_path, "screentime"), exist_ok=True)
        
        # Load data
        self._load_data()
        
    def _load_data(self):
        """Load history data from files"""
        # This is a simplified version. In a full implementation,
        # you would load all the data from files.
        pass
        
    def _save_name_history(self, user_id):
        """Save name history for a user to file"""
        user_id_str = str(user_id)
        if user_id_str in self.name_history:
            try:
                with open(os.path.join(self.config_path, "names", f"{user_id_str}.json"), 'w') as f:
                    json.dump(self.name_history[user_id_str], f, indent=4)
            except Exception as e:
                logger.error(f"Error saving name history for user {user_id}: {str(e)}")
    
    def _save_avatar_history(self, user_id):
        """Save avatar history for a user to file"""
        user_id_str = str(user_id)
        if user_id_str in self.avatar_history:
            try:
                with open(os.path.join(self.config_path, "avatars", f"{user_id_str}.json"), 'w') as f:
                    json.dump(self.avatar_history[user_id_str], f, indent=4)
            except Exception as e:
                logger.error(f"Error saving avatar history for user {user_id}: {str(e)}")
    
    def _save_guild_name_history(self, guild_id):
        """Save name history for a guild to file"""
        guild_id_str = str(guild_id)
        if guild_id_str in self.guild_name_history:
            try:
                with open(os.path.join(self.config_path, "guilds", f"{guild_id_str}.json"), 'w') as f:
                    json.dump(self.guild_name_history[guild_id_str], f, indent=4)
            except Exception as e:
                logger.error(f"Error saving guild name history for guild {guild_id}: {str(e)}")
    
    def _save_user_seen(self, user_id):
        """Save last seen timestamp for a user"""
        user_id_str = str(user_id)
        if user_id_str in self.user_seen:
            try:
                with open(os.path.join(self.config_path, "seen", f"{user_id_str}.json"), 'w') as f:
                    json.dump({"timestamp": self.user_seen[user_id_str]}, f)
            except Exception as e:
                logger.error(f"Error saving last seen for user {user_id}: {str(e)}")
    
    def _save_user_screentime(self, user_id):
        """Save screentime statistics for a user"""
        user_id_str = str(user_id)
        if user_id_str in self.user_screentime:
            try:
                with open(os.path.join(self.config_path, "screentime", f"{user_id_str}.json"), 'w') as f:
                    json.dump(self.user_screentime[user_id_str], f, indent=4)
            except Exception as e:
                logger.error(f"Error saving screentime for user {user_id}: {str(e)}")
    
    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        """Track member updates for history"""
        # Track name changes
        if before.name != after.name or before.nick != after.nick:
            user_id = str(after.id)
            timestamp = int(time.time())
            
            if user_id not in self.name_history:
                self.name_history[user_id] = []
                
            # Record the change
            self.name_history[user_id].append({
                "timestamp": timestamp,
                "old_name": before.name,
                "new_name": after.name,
                "old_nick": before.nick,
                "new_nick": after.nick,
                "guild_id": after.guild.id
            })
            
            # Limit history to last 50 changes
            self.name_history[user_id] = self.name_history[user_id][-50:]
            
            # Save to file
            self._save_name_history(user_id)
            
        # Track avatar changes
        if before.avatar != after.avatar:
            user_id = str(after.id)
            timestamp = int(time.time())
            
            if user_id not in self.avatar_history:
                self.avatar_history[user_id] = []
                
            # Record the change
            self.avatar_history[user_id].append({
                "timestamp": timestamp,
                "old_avatar": str(before.avatar.url) if before.avatar else None,
                "new_avatar": str(after.avatar.url) if after.avatar else None
            })
            
            # Limit history to last 20 avatar changes
            self.avatar_history[user_id] = self.avatar_history[user_id][-20:]
            
            # Save to file
            self._save_avatar_history(user_id)
            
        # Track status changes for screentime
        if before.status != after.status:
            user_id = str(after.id)
            timestamp = int(time.time())
            
            # Update last seen
            self.user_seen[user_id] = timestamp
            self._save_user_seen(user_id)
            
            # Initialize screentime tracking if needed
            if user_id not in self.user_screentime:
                self.user_screentime[user_id] = {
                    "online": 0,
                    "idle": 0,
                    "dnd": 0,
                    "offline": 0,
                    "last_status": str(after.status),
                    "last_change": timestamp
                }
            
            # Update screentime
            last_status = self.user_screentime[user_id]["last_status"]
            last_change = self.user_screentime[user_id]["last_change"]
            duration = timestamp - last_change
            
            # Only count reasonable durations (prevent issues with reconnections)
            if 0 < duration < 86400:  # Less than a day
                self.user_screentime[user_id][last_status] += duration
                
            # Update tracking info
            self.user_screentime[user_id]["last_status"] = str(after.status)
            self.user_screentime[user_id]["last_change"] = timestamp
            
            # Save to file
            self._save_user_screentime(user_id)
    
    @commands.Cog.listener()
    async def on_guild_update(self, before, after):
        """Track guild name changes"""
        if before.name != after.name:
            guild_id = str(after.id)
            timestamp = int(time.time())
            
            if guild_id not in self.guild_name_history:
                self.guild_name_history[guild_id] = []
                
            # Record the change
            self.guild_name_history[guild_id].append({
                "timestamp": timestamp,
                "old_name": before.name,
                "new_name": after.name
            })
            
            # Limit history to last 30 changes
            self.guild_name_history[guild_id] = self.guild_name_history[guild_id][-30:]
            
            # Save to file
            self._save_guild_name_history(guild_id)
    
    @commands.command()
    async def names(self, ctx, member: discord.Member = None):
        """View username and nickname history of a member or yourself"""
        # Default to the command author if no member is specified
        if member is None:
            member = ctx.author
            
        user_id = str(member.id)
        
        # Check if we have history for this user
        if user_id not in self.name_history or not self.name_history[user_id]:
            await ctx.send(f"❌ No name history found for {member.display_name}.")
            return
            
        # Create an embed to display the history
        embed = discord.Embed(
            title=f"Name History for {member.display_name}",
            color=member.color,
            timestamp=datetime.utcnow()
        )
        
        # Add user info
        embed.set_thumbnail(url=member.display_avatar.url)
        
        # Add current names
        embed.add_field(
            name="Current",
            value=f"Username: {member.name}\nNickname: {member.nick or 'None'}",
            inline=False
        )
        
        # Add history (most recent 10 entries)
        history_entries = []
        for entry in reversed(self.name_history[user_id][-10:]):
            timestamp = datetime.fromtimestamp(entry["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
            
            # Determine what changed
            if entry["old_name"] != entry["new_name"] and entry["old_nick"] != entry["new_nick"]:
                change = f"Username: {entry['old_name']} → {entry['new_name']}\nNickname: {entry['old_nick'] or 'None'} → {entry['new_nick'] or 'None'}"
            elif entry["old_name"] != entry["new_name"]:
                change = f"Username: {entry['old_name']} → {entry['new_name']}"
            else:
                change = f"Nickname: {entry['old_nick'] or 'None'} → {entry['new_nick'] or 'None'}"
                
            history_entries.append(f"**{timestamp}**\n{change}")
            
        # If there are entries, add them to the embed
        if history_entries:
            embed.add_field(
                name="History (Recent Changes)",
                value="\n\n".join(history_entries),
                inline=False
            )
            
        await ctx.send(embed=embed)
    
    @commands.command()
    async def clearnames(self, ctx):
        """Reset your name history"""
        user_id = str(ctx.author.id)
        
        # Check if we have history for this user
        if user_id not in self.name_history or not self.name_history[user_id]:
            await ctx.send("❌ You don't have any recorded name history to clear.")
            return
            
        # Confirm the action
        confirm_msg = await ctx.send("⚠️ Are you sure you want to clear your name history? This action cannot be undone. React with ✅ to confirm or ❌ to cancel.")
        
        # Add reactions
        await confirm_msg.add_reaction('✅')
        await confirm_msg.add_reaction('❌')
        
        # Wait for user's reaction
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ['✅', '❌'] and reaction.message.id == confirm_msg.id
            
        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=check)
            
            if str(reaction.emoji) == '✅':
                # Clear the history
                self.name_history[user_id] = []
                self._save_name_history(user_id)
                
                # Delete the file if it exists
                file_path = os.path.join(self.config_path, "names", f"{user_id}.json")
                if os.path.exists(file_path):
                    os.remove(file_path)
                    
                await ctx.send("✅ Your name history has been cleared.")
            else:
                await ctx.send("❌ Operation cancelled.")
                
        except asyncio.TimeoutError:
            await ctx.send("❌ Timed out. No changes were made.")
    
    @commands.command()
    async def avatarhistory(self, ctx, member: discord.Member = None):
        """Get a user's avatar changes that have been recorded by the bot"""
        # Default to the command author if no member is specified
        if member is None:
            member = ctx.author
            
        user_id = str(member.id)
        
        # Check if we have history for this user
        if user_id not in self.avatar_history or not self.avatar_history[user_id]:
            await ctx.send(f"❌ No avatar history found for {member.display_name}.")
            return
            
        # Create an embed to display the history
        embed = discord.Embed(
            title=f"Avatar History for {member.display_name}",
            color=member.color,
            timestamp=datetime.utcnow()
        )
        
        # Add current avatar
        embed.set_thumbnail(url=member.display_avatar.url)
        
        # Show the most recent avatar change
        if self.avatar_history[user_id]:
            latest = self.avatar_history[user_id][-1]
            timestamp = datetime.fromtimestamp(latest["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
            
            embed.add_field(
                name=f"Latest Change ({timestamp})",
                value="Avatar updated",
                inline=False
            )
            
            if latest["new_avatar"]:
                embed.set_image(url=latest["new_avatar"])
            
        # Add note about full history
        embed.add_field(
            name="Note",
            value=f"Found {len(self.avatar_history[user_id])} recorded avatar changes. The bot only shows the most recent change to avoid spam.",
            inline=False
        )
            
        await ctx.send(embed=embed)
    
    @commands.command()
    async def clearavatars(self, ctx):
        """Reset your recorded avatar changes"""
        user_id = str(ctx.author.id)
        
        # Check if we have history for this user
        if user_id not in self.avatar_history or not self.avatar_history[user_id]:
            await ctx.send("❌ You don't have any recorded avatar history to clear.")
            return
            
        # Confirm the action
        confirm_msg = await ctx.send("⚠️ Are you sure you want to clear your avatar history? This action cannot be undone. React with ✅ to confirm or ❌ to cancel.")
        
        # Add reactions
        await confirm_msg.add_reaction('✅')
        await confirm_msg.add_reaction('❌')
        
        # Wait for user's reaction
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ['✅', '❌'] and reaction.message.id == confirm_msg.id
            
        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=check)
            
            if str(reaction.emoji) == '✅':
                # Clear the history
                self.avatar_history[user_id] = []
                self._save_avatar_history(user_id)
                
                # Delete the file if it exists
                file_path = os.path.join(self.config_path, "avatars", f"{user_id}.json")
                if os.path.exists(file_path):
                    os.remove(file_path)
                    
                await ctx.send("✅ Your avatar history has been cleared.")
            else:
                await ctx.send("❌ Operation cancelled.")
                
        except asyncio.TimeoutError:
            await ctx.send("❌ Timed out. No changes were made.")
    
    @commands.command()
    async def guildnames(self, ctx, guild_id: int = None):
        """View guild name changes"""
        # Default to the current guild if no ID is specified
        if guild_id is None:
            guild_id = ctx.guild.id
            
        guild_id_str = str(guild_id)
        
        # Try to get the guild
        guild = self.bot.get_guild(guild_id)
        guild_name = guild.name if guild else f"Unknown Guild ({guild_id})"
        
        # Check if we have history for this guild
        if guild_id_str not in self.guild_name_history or not self.guild_name_history[guild_id_str]:
            await ctx.send(f"❌ No name history found for {guild_name}.")
            return
            
        # Create an embed to display the history
        embed = discord.Embed(
            title=f"Name History for {guild_name}",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        # Add guild icon if available
        if guild and guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        
        # Add history (most recent 15 entries)
        history_entries = []
        for entry in reversed(self.guild_name_history[guild_id_str][-15:]):
            timestamp = datetime.fromtimestamp(entry["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
            change = f"{entry['old_name']} → {entry['new_name']}"
            history_entries.append(f"**{timestamp}**\n{change}")
            
        # If there are entries, add them to the embed
        if history_entries:
            embed.add_field(
                name="History (Recent Changes)",
                value="\n\n".join(history_entries),
                inline=False
            )
            
        await ctx.send(embed=embed)
    
    @commands.command()
    async def cleargnames(self, ctx):
        """Reset your guild's name history"""
        # Check if user is guild owner
        if ctx.author.id != ctx.guild.owner_id:
            await ctx.send("❌ Only the server owner can clear the guild name history.")
            return
            
        guild_id = str(ctx.guild.id)
        
        # Check if we have history for this guild
        if guild_id not in self.guild_name_history or not self.guild_name_history[guild_id]:
            await ctx.send("❌ This server doesn't have any recorded name history to clear.")
            return
            
        # Confirm the action
        confirm_msg = await ctx.send("⚠️ Are you sure you want to clear this server's name history? This action cannot be undone. React with ✅ to confirm or ❌ to cancel.")
        
        # Add reactions
        await confirm_msg.add_reaction('✅')
        await confirm_msg.add_reaction('❌')
        
        # Wait for user's reaction
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ['✅', '❌'] and reaction.message.id == confirm_msg.id
            
        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=check)
            
            if str(reaction.emoji) == '✅':
                # Clear the history
                self.guild_name_history[guild_id] = []
                self._save_guild_name_history(guild_id)
                
                # Delete the file if it exists
                file_path = os.path.join(self.config_path, "guilds", f"{guild_id}.json")
                if os.path.exists(file_path):
                    os.remove(file_path)
                    
                await ctx.send("✅ This server's name history has been cleared.")
            else:
                await ctx.send("❌ Operation cancelled.")
                
        except asyncio.TimeoutError:
            await ctx.send("❌ Timed out. No changes were made.")
    
    @commands.command()
    async def seen(self, ctx, member: discord.Member = None):
        """View when a user was last seen by the bot"""
        if member is None:
            await ctx.send("❌ Please specify a member to check.")
            return
            
        user_id = str(member.id)
        
        # Check if we have seen this user
        if user_id not in self.user_seen:
            await ctx.send(f"❌ I haven't seen {member.display_name} change status since I started tracking.")
            return
            
        # Get the timestamp
        last_seen = self.user_seen[user_id]
        time_diff = int(time.time()) - last_seen
        
        # Format the timestamp
        timestamp = datetime.fromtimestamp(last_seen).strftime("%Y-%m-%d %H:%M:%S")
        
        # Format the time difference
        if time_diff < 60:
            time_str = f"{time_diff} seconds ago"
        elif time_diff < 3600:
            minutes = time_diff // 60
            time_str = f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        elif time_diff < 86400:
            hours = time_diff // 3600
            time_str = f"{hours} hour{'s' if hours != 1 else ''} ago"
        else:
            days = time_diff // 86400
            time_str = f"{days} day{'s' if days != 1 else ''} ago"
        
        # Create an embed
        embed = discord.Embed(
            title=f"Last Seen: {member.display_name}",
            description=f"{member.mention} was last seen {time_str}",
            color=member.color,
            timestamp=datetime.utcnow()
        )
        
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Timestamp", value=timestamp, inline=False)
        
        await ctx.send(embed=embed)
    
    @commands.command()
    async def screentime(self, ctx, member: discord.Member = None):
        """View the status statistics of a user"""
        # Default to the command author if no member is specified
        if member is None:
            member = ctx.author
            
        user_id = str(member.id)
        
        # Check if we have stats for this user
        if user_id not in self.user_screentime:
            await ctx.send(f"❌ No status statistics found for {member.display_name}.")
            return
            
        # Get the stats
        stats = self.user_screentime[user_id]
        
        # Calculate totals
        total_time = stats.get("online", 0) + stats.get("idle", 0) + stats.get("dnd", 0)
        
        # Skip if total time is too small
        if total_time < 3600:  # Less than an hour
            await ctx.send(f"❌ Not enough status history collected for {member.display_name} yet.")
            return
            
        # Calculate percentages
        if total_time > 0:
            online_percent = (stats.get("online", 0) / total_time) * 100
            idle_percent = (stats.get("idle", 0) / total_time) * 100
            dnd_percent = (stats.get("dnd", 0) / total_time) * 100
        else:
            online_percent = idle_percent = dnd_percent = 0
            
        # Format times
        format_time = lambda seconds: f"{seconds // 3600}h {(seconds % 3600) // 60}m"
        
        # Create an embed
        embed = discord.Embed(
            title=f"Status Statistics for {member.display_name}",
            color=member.color,
            timestamp=datetime.utcnow()
        )
        
        embed.set_thumbnail(url=member.display_avatar.url)
        
        # Add current status
        embed.add_field(
            name="Current Status",
            value=f"{str(member.status).capitalize()}",
            inline=False
        )
        
        # Add time statistics
        embed.add_field(
            name="Online",
            value=f"{format_time(stats.get('online', 0))} ({online_percent:.1f}%)",
            inline=True
        )
        
        embed.add_field(
            name="Idle",
            value=f"{format_time(stats.get('idle', 0))} ({idle_percent:.1f}%)",
            inline=True
        )
        
        embed.add_field(
            name="Do Not Disturb",
            value=f"{format_time(stats.get('dnd', 0))} ({dnd_percent:.1f}%)",
            inline=True
        )
        
        # Add note
        embed.set_footer(text="Statistics are approximations based on observed status changes")
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(UserHistory(bot)) 