import discord
from discord.ext import commands
import asyncio
import logging
from datetime import datetime, timedelta
import json
import os

logger = logging.getLogger('bot')

class RaidProtection(commands.Cog):
    """Commands for protecting against raids and mass banning recent members"""
    
    def __init__(self, bot):
        self.bot = bot
        # Active tasks
        self.raid_tasks = {}
        self.recentban_tasks = {}
    
    @commands.command(name="raid")
    @commands.has_permissions(administrator=True)
    async def raid(self, ctx, time: str, action: str = "kick", *, reason="Raid cleanup"):
        """Remove all members that joined in the time provided in the event of a raid"""
        # Check if a task is already running for this guild
        if ctx.guild.id in self.raid_tasks:
            await ctx.send("❌ A raid cleanup task is already running for this server. Use `raid cancel` to cancel it.")
            return
            
        # Parse the time string (e.g., 5m, 1h, 30m, etc.)
        try:
            time_value = ""
            unit = ""
            
            for char in time:
                if char.isdigit():
                    time_value += char
                else:
                    unit += char
                    
            time_value = int(time_value)
            
            if unit.lower() in ['s', 'sec', 'second', 'seconds']:
                seconds = time_value
            elif unit.lower() in ['m', 'min', 'minute', 'minutes']:
                seconds = time_value * 60
            elif unit.lower() in ['h', 'hour', 'hours']:
                seconds = time_value * 3600
            elif unit.lower() in ['d', 'day', 'days']:
                seconds = time_value * 86400
            else:
                raise ValueError(f"Invalid time unit: {unit}")
                
            cutoff_time = datetime.utcnow() - timedelta(seconds=seconds)
            
        except (ValueError, IndexError):
            await ctx.send("❌ Invalid time format. Use format like '5m', '1h', '30m', etc.")
            return
            
        # Validate the action
        valid_actions = ["kick", "ban"]
        if action.lower() not in valid_actions:
            await ctx.send(f"❌ Invalid action. Must be one of: {', '.join(valid_actions)}")
            return
            
        action = action.lower()
        
        # Create a confirmation message
        members_to_process = []
        
        # Get members who joined within the specified time
        for member in ctx.guild.members:
            if member.joined_at and member.joined_at > cutoff_time:
                # Skip bots, members with roles, and moderators
                if member.bot or len(member.roles) > 1 or member.guild_permissions.kick_members:
                    continue
                    
                members_to_process.append(member)
                
        if not members_to_process:
            await ctx.send(f"❌ No members found who joined within the last {time}.")
            return
            
        confirm_msg = await ctx.send(
            f"⚠️ This will {action} {len(members_to_process)} members who joined in the last {time}. "
            f"React with ✅ to confirm or ❌ to cancel."
        )
        
        await confirm_msg.add_reaction('✅')
        await confirm_msg.add_reaction('❌')
        
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ['✅', '❌'] and reaction.message.id == confirm_msg.id
        
        try:
            # Wait for the user's reaction
            reaction, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=check)
            
            if str(reaction.emoji) == '❌':
                await confirm_msg.edit(content="❌ Raid cleanup cancelled.")
                return
                
            # Create a status message
            status_msg = await ctx.send(
                f"🔄 Processing raid cleanup... 0/{len(members_to_process)} members processed."
            )
            
            # Define the task
            async def process_raid_members():
                processed = 0
                success = 0
                failed = 0
                
                for i, member in enumerate(members_to_process):
                    try:
                        if action == "kick":
                            await member.kick(reason=f"{reason} | Raid cleanup by {ctx.author}")
                        else:  # ban
                            await member.ban(reason=f"{reason} | Raid cleanup by {ctx.author}")
                            
                        success += 1
                    except Exception as e:
                        logger.error(f"Error processing member in raid cleanup: {str(e)}")
                        failed += 1
                        
                    processed += 1
                    
                    # Update status every few members
                    if (i + 1) % 5 == 0 or i + 1 == len(members_to_process):
                        await status_msg.edit(
                            content=f"🔄 Processing raid cleanup... {processed}/{len(members_to_process)} members processed."
                        )
                        
                    # Sleep briefly to avoid rate limits
                    await asyncio.sleep(0.5)
                    
                # Final update
                final_action = "kicked" if action == "kick" else "banned"
                await status_msg.edit(
                    content=f"✅ Raid cleanup complete! Successfully {final_action} {success} members. Failed: {failed}"
                )
                
                # Remove from active tasks
                del self.raid_tasks[ctx.guild.id]
                
            # Start the task
            task = self.bot.loop.create_task(process_raid_members())
            self.raid_tasks[ctx.guild.id] = task
            
        except asyncio.TimeoutError:
            await confirm_msg.edit(content="❌ Raid cleanup timed out.")
    
    @commands.command(name="raid_cancel", aliases=["raidcancel"])
    @commands.has_permissions(administrator=True)
    async def raid_cancel(self, ctx):
        """End a chunkban of raid members"""
        if ctx.guild.id not in self.raid_tasks:
            await ctx.send("❌ There is no active raid cleanup task for this server.")
            return
            
        # Cancel the task
        self.raid_tasks[ctx.guild.id].cancel()
        del self.raid_tasks[ctx.guild.id]
        
        await ctx.send("✅ Raid cleanup task cancelled.")
    
    @commands.command(name="recentban")
    @commands.has_permissions(ban_members=True)
    async def recentban(self, ctx, count: int = 10, *, reason="Mass ban of recent joins"):
        """Chunk ban recently joined members"""
        # Check if a task is already running for this guild
        if ctx.guild.id in self.recentban_tasks:
            await ctx.send("❌ A recent member ban task is already running for this server. Use `recentban cancel` to cancel it.")
            return
            
        # Validate the count
        if count <= 0:
            await ctx.send("❌ Count must be greater than 0.")
            return
            
        if count > 100:
            await ctx.send("⚠️ For safety, the maximum number of members to ban at once is 100. Setting to 100.")
            count = 100
            
        # Get the most recently joined members
        members = sorted(
            [m for m in ctx.guild.members if not m.bot and len(m.roles) <= 1],
            key=lambda m: m.joined_at if m.joined_at else discord.utils.utcnow(),
            reverse=True
        )[:count]
        
        if not members:
            await ctx.send("❌ No eligible members found to ban.")
            return
            
        # Create a confirmation message with member details
        member_list = "\n".join([
            f"{m.name}#{m.discriminator} ({m.id}) - Joined: {m.joined_at.strftime('%Y-%m-%d %H:%M:%S') if m.joined_at else 'Unknown'}"
            for m in members[:10]  # Show only the first 10 for brevity
        ])
        
        if len(members) > 10:
            member_list += f"\n... and {len(members) - 10} more."
            
        confirm_msg = await ctx.send(
            f"⚠️ This will ban the {len(members)} most recently joined members:\n"
            f"```\n{member_list}\n```\n"
            f"React with ✅ to confirm or ❌ to cancel."
        )
        
        await confirm_msg.add_reaction('✅')
        await confirm_msg.add_reaction('❌')
        
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ['✅', '❌'] and reaction.message.id == confirm_msg.id
        
        try:
            # Wait for the user's reaction
            reaction, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=check)
            
            if str(reaction.emoji) == '❌':
                await confirm_msg.edit(content="❌ Recent member ban cancelled.")
                return
                
            # Create a status message
            status_msg = await ctx.send(
                f"🔄 Banning recent members... 0/{len(members)} members processed."
            )
            
            # Define the task
            async def process_recent_bans():
                processed = 0
                success = 0
                failed = 0
                
                for i, member in enumerate(members):
                    try:
                        await member.ban(reason=f"{reason} | Recent member ban by {ctx.author}")
                        success += 1
                    except Exception as e:
                        logger.error(f"Error banning member in recentban: {str(e)}")
                        failed += 1
                        
                    processed += 1
                    
                    # Update status every few members
                    if (i + 1) % 5 == 0 or i + 1 == len(members):
                        await status_msg.edit(
                            content=f"🔄 Banning recent members... {processed}/{len(members)} members processed."
                        )
                        
                    # Sleep briefly to avoid rate limits
                    await asyncio.sleep(0.5)
                    
                # Final update
                await status_msg.edit(
                    content=f"✅ Recent member ban complete! Successfully banned {success} members. Failed: {failed}"
                )
                
                # Remove from active tasks
                del self.recentban_tasks[ctx.guild.id]
                
            # Start the task
            task = self.bot.loop.create_task(process_recent_bans())
            self.recentban_tasks[ctx.guild.id] = task
            
        except asyncio.TimeoutError:
            await confirm_msg.edit(content="❌ Recent member ban timed out.")
    
    @commands.command(name="recentban_cancel", aliases=["recentbancancel"])
    @commands.has_permissions(ban_members=True)
    async def recentban_cancel(self, ctx):
        """Stop a chunk banning task"""
        if ctx.guild.id not in self.recentban_tasks:
            await ctx.send("❌ There is no active recent member ban task for this server.")
            return
            
        # Cancel the task
        self.recentban_tasks[ctx.guild.id].cancel()
        del self.recentban_tasks[ctx.guild.id]
        
        await ctx.send("✅ Recent member ban task cancelled.")
    
    @commands.command(name="newusers")
    async def newusers(self, ctx, count: int = 10):
        """View list of recently joined members"""
        # Validate the count
        if count <= 0:
            await ctx.send("❌ Count must be greater than 0.")
            return
            
        if count > 50:
            await ctx.send("⚠️ For readability, the maximum number of members to display is 50. Setting to 50.")
            count = 50
            
        # Get the most recently joined members
        members = sorted(
            [m for m in ctx.guild.members],
            key=lambda m: m.joined_at if m.joined_at else discord.utils.utcnow(),
            reverse=True
        )[:count]
        
        if not members:
            await ctx.send("❌ No members found.")
            return
            
        # Create an embed with the member list
        embed = discord.Embed(
            title=f"Recently Joined Members",
            description=f"Showing the {len(members)} most recently joined members",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        # Add member entries
        for i, member in enumerate(members):
            joined_at = member.joined_at.strftime("%Y-%m-%d %H:%M:%S") if member.joined_at else "Unknown"
            created_at = member.created_at.strftime("%Y-%m-%d %H:%M:%S")
            
            # Calculate account age
            if member.created_at:
                account_age = (datetime.utcnow() - member.created_at).days
                account_age_str = f"{account_age} days old"
            else:
                account_age_str = "Unknown age"
                
            roles = len(member.roles) - 1  # Subtract the @everyone role
            
            embed.add_field(
                name=f"{i+1}. {member.name}#{member.discriminator}",
                value=(
                    f"**ID:** {member.id}\n"
                    f"**Joined:** {joined_at}\n"
                    f"**Created:** {created_at} ({account_age_str})\n"
                    f"**Roles:** {roles}"
                ),
                inline=False
            )
            
        await ctx.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Log when a member joins to help track potential raids"""
        logger.info(f"Member joined: {member.name}#{member.discriminator} ({member.id}) in {member.guild.name}")

async def setup(bot):
    await bot.add_cog(RaidProtection(bot)) 