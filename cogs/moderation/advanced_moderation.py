import discord
from discord.ext import commands
import json
import os
import logging
import asyncio
import re
from datetime import datetime, timedelta

# Import custom check for has_any_of
from custom_checks import has_any_of

logger = logging.getLogger('bot')

class AdvancedModeration(commands.Cog):
    """Advanced moderation commands"""
    
    def __init__(self, bot):
        self.bot = bot
        self.data_folder = 'data/moderation'
        self.hardbans_file = os.path.join(self.data_folder, 'hardbans.json')
        self.temproles_file = os.path.join(self.data_folder, 'temproles.json')
        # Create data directory if it doesn't exist
        os.makedirs(self.data_folder, exist_ok=True)
        # Load data
        self.hardbans = self.load_hardbans()
        self.temproles = self.load_temproles()
        # Active tasks
        self.unban_all_tasks = {}
        self.purge_tasks = {}
        # Start background tasks
        self.check_temproles_task = self.bot.loop.create_task(self.check_temproles())
    
    def load_hardbans(self):
        """Load the hardbans from file"""
        try:
            if os.path.exists(self.hardbans_file):
                with open(self.hardbans_file, 'r') as f:
                    return json.load(f)
            else:
                return {}
        except json.JSONDecodeError:
            logger.error(f"Error decoding {self.hardbans_file}. Using empty config.")
            return {}
    
    def save_hardbans(self):
        """Save the hardbans to file"""
        with open(self.hardbans_file, 'w') as f:
            json.dump(self.hardbans, f, indent=4)
    
    def load_temproles(self):
        """Load the temporary roles from file"""
        try:
            if os.path.exists(self.temproles_file):
                with open(self.temproles_file, 'r') as f:
                    return json.load(f)
            else:
                return {}
        except json.JSONDecodeError:
            logger.error(f"Error decoding {self.temproles_file}. Using empty config.")
            return {}
    
    def save_temproles(self):
        """Save the temporary roles to file"""
        with open(self.temproles_file, 'w') as f:
            json.dump(self.temproles, f, indent=4)

    @commands.command(name="hardban")
    @has_any_of(commands.has_permissions(administrator=True), commands.has_role("Antinuke Admin"))
    async def hardban(self, ctx, user_id: int, *, reason="No reason provided"):
        """Keep a member banned"""
        try:
            # Get the user
            try:
                user = await self.bot.fetch_user(user_id)
            except discord.NotFound:
                await ctx.send(f"❌ User with ID {user_id} not found.")
                return
            
            # Check if the user is already banned
            try:
                ban_entry = await ctx.guild.fetch_ban(user)
                already_banned = True
            except discord.NotFound:
                already_banned = False
            
            # Ban the user if they're not already banned
            if not already_banned:
                await ctx.guild.ban(user, reason=f"{reason} | Hardbanned by {ctx.author}")
            
            # Add to hardbans
            guild_id = str(ctx.guild.id)
            if guild_id not in self.hardbans:
                self.hardbans[guild_id] = {}
            
            self.hardbans[guild_id][str(user_id)] = {
                "user_name": f"{user.name}#{user.discriminator}",
                "reason": reason,
                "banned_by": ctx.author.id,
                "banned_at": datetime.utcnow().isoformat(),
            }
            
            self.save_hardbans()
            
            # Create an embed for the hardban confirmation
            embed = discord.Embed(
                title="Member Hardbanned",
                description=f"{user.mention} has been hardbanned from the server.",
                color=discord.Color.dark_red(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Reason", value=reason)
            embed.add_field(name="Hardbanned by", value=ctx.author.mention)
            embed.set_thumbnail(url=user.display_avatar.url)
            embed.set_footer(text=f"User ID: {user.id}")
            
            await ctx.send(embed=embed)
            
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to ban that user.")
        except Exception as e:
            logger.error(f"Error when hardbanning user: {str(e)}")
            await ctx.send(f"❌ An error occurred: {str(e)}")
    
    @commands.command(name="hardban_list", aliases=["hardbanlist"])
    @has_any_of(commands.has_permissions(administrator=True), commands.has_role("Antinuke Admin"))
    async def hardban_list(self, ctx):
        """View list of hardbanned members"""
        guild_id = str(ctx.guild.id)
        
        if guild_id not in self.hardbans or not self.hardbans[guild_id]:
            await ctx.send("❌ There are no hardbanned users in this server.")
            return
        
        # Create embed
        embed = discord.Embed(
            title="Hardbanned Members",
            description=f"Total: {len(self.hardbans[guild_id])} hardbanned members",
            color=discord.Color.dark_red(),
            timestamp=datetime.utcnow()
        )
        
        # Add each hardbanned user to the embed
        for user_id, data in self.hardbans[guild_id].items():
            banned_by = await self.bot.fetch_user(data["banned_by"])
            banned_at = datetime.fromisoformat(data["banned_at"])
            
            embed.add_field(
                name=f"{data['user_name']} (ID: {user_id})",
                value=(
                    f"**Reason:** {data['reason']}\n"
                    f"**Banned by:** {banned_by.mention}\n"
                    f"**Banned at:** <t:{int(banned_at.timestamp())}:R>"
                ),
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    @commands.command(name="clearinvites")
    @commands.has_permissions(manage_guild=True)
    async def clearinvites(self, ctx):
        """Remove all existing invites in guild"""
        try:
            # Get all invites for the guild
            invites = await ctx.guild.invites()
            
            if not invites:
                await ctx.send("❌ This server has no active invites to clear.")
                return
            
            # Create a confirmation message
            confirm_msg = await ctx.send(
                f"⚠️ Are you sure you want to delete all {len(invites)} invites? "
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
                    await confirm_msg.edit(content="❌ Invite clearing cancelled.")
                    return
                
                # Create a status message
                status_msg = await ctx.send(f"🔄 Deleting {len(invites)} invites... This may take a moment.")
                
                # Delete all invites
                deleted_count = 0
                failed_count = 0
                
                for invite in invites:
                    try:
                        await invite.delete(reason=f"Cleared by {ctx.author}")
                        deleted_count += 1
                    except:
                        failed_count += 1
                
                # Update the status message
                await status_msg.edit(
                    content=f"✅ Successfully deleted {deleted_count} invites. Failed to delete {failed_count} invites."
                )
                
            except asyncio.TimeoutError:
                await confirm_msg.edit(content="❌ Invite clearing timed out. No invites were deleted.")
                
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to manage invites for this server.")
        except Exception as e:
            logger.error(f"Error clearing invites: {str(e)}")
            await ctx.send(f"❌ An error occurred while clearing invites: {str(e)}")
    
    @commands.command(name="drag")
    @commands.has_permissions(moderate_members=True)
    async def drag(self, ctx, members: commands.Greedy[discord.Member], *, channel: discord.VoiceChannel):
        """Drag member(s) to the specified Voice Channel"""
        if not members:
            await ctx.send("❌ Please specify at least one member to drag.")
            return
        
        success = []
        failed = []
        
        for member in members:
            # Check if the member is in a voice channel
            if not member.voice:
                failed.append(f"{member.mention} - Not in a voice channel")
                continue
            
            try:
                # Move the member to the specified voice channel
                await member.move_to(channel, reason=f"Dragged by {ctx.author}")
                success.append(member.mention)
            except discord.Forbidden:
                failed.append(f"{member.mention} - Missing permissions")
            except Exception as e:
                failed.append(f"{member.mention} - Error: {str(e)}")
        
        # Create embed for the results
        embed = discord.Embed(
            title="Drag Results",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        if success:
            embed.add_field(
                name=f"✅ Successfully dragged {len(success)} member(s) to {channel.name}",
                value=", ".join(success),
                inline=False
            )
        
        if failed:
            embed.add_field(
                name=f"❌ Failed to drag {len(failed)} member(s)",
                value="\n".join(failed),
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    @commands.command(name="unbanall")
    @commands.has_permissions(administrator=True)
    async def unbanall(self, ctx):
        """Unbans every member in a guild"""
        # Check if a task is already running
        if ctx.guild.id in self.unban_all_tasks:
            await ctx.send("❌ An unban all task is already running for this server. Use `unbanall cancel` to cancel it.")
            return
        
        try:
            # Fetch all bans
            bans = [entry async for entry in ctx.guild.bans()]
            
            if not bans:
                await ctx.send("❌ There are no banned users in this server.")
                return
            
            # Create a confirmation message
            confirm_msg = await ctx.send(
                f"⚠️ Are you sure you want to unban all {len(bans)} banned users? "
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
                    await confirm_msg.edit(content="❌ Unban all operation cancelled.")
                    return
                
                # Create a status message
                status_msg = await ctx.send(f"🔄 Unbanning {len(bans)} users... This may take a while.")
                
                # Create and start the unban all task
                async def unban_all_task():
                    unbanned = 0
                    failed = 0
                    
                    for ban_entry in bans:
                        try:
                            # Skip hardbanned users
                            guild_id = str(ctx.guild.id)
                            if (guild_id in self.hardbans and 
                                str(ban_entry.user.id) in self.hardbans[guild_id]):
                                failed += 1
                                continue
                            
                            await ctx.guild.unban(ban_entry.user, reason=f"Mass unban by {ctx.author}")
                            unbanned += 1
                            
                            # Update status every 10 unbans
                            if unbanned % 10 == 0:
                                await status_msg.edit(
                                    content=f"🔄 Unbanned {unbanned}/{len(bans)} users..."
                                )
                            
                            # Sleep briefly to avoid rate limits
                            await asyncio.sleep(0.5)
                            
                        except Exception as e:
                            logger.error(f"Error unbanning user {ban_entry.user.id}: {str(e)}")
                            failed += 1
                    
                    # Final update
                    await status_msg.edit(
                        content=f"✅ Unban all operation completed! Unbanned {unbanned} users. Failed to unban {failed} users."
                    )
                    
                    # Remove from active tasks
                    del self.unban_all_tasks[ctx.guild.id]
                
                # Start the task
                task = self.bot.loop.create_task(unban_all_task())
                self.unban_all_tasks[ctx.guild.id] = task
                
            except asyncio.TimeoutError:
                await confirm_msg.edit(content="❌ Unban all operation timed out. No users were unbanned.")
                
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to manage bans for this server.")
        except Exception as e:
            logger.error(f"Error in unban all: {str(e)}")
            await ctx.send(f"❌ An error occurred during the unban all operation: {str(e)}")
    
    @commands.command(name="unbanall_cancel", aliases=["unbanallcancel"])
    @commands.has_permissions(administrator=True)
    async def unbanall_cancel(self, ctx):
        """Cancels a unban all task running"""
        if ctx.guild.id not in self.unban_all_tasks:
            await ctx.send("❌ There is no unban all task running for this server.")
            return
        
        # Cancel the task
        self.unban_all_tasks[ctx.guild.id].cancel()
        del self.unban_all_tasks[ctx.guild.id]
        
        await ctx.send("✅ Unban all task cancelled.")
    
    @commands.command(name="temprole")
    @commands.has_permissions(manage_roles=True)
    async def temprole(self, ctx, member: discord.Member, duration: str, *, role: discord.Role):
        """Temporarily give a role to a member"""
        # Check if the role is manageable
        if not role.is_assignable():
            await ctx.send("❌ I cannot assign that role. It might be higher than my highest role or managed by an integration.")
            return
        
        # Parse the duration
        duration_seconds = 0
        time_units = {"s": 1, "m": 60, "h": 3600, "d": 86400}
        
        duration_parts = duration.lower().split()
        for part in duration_parts:
            if part[-1] in time_units and part[:-1].isdigit():
                duration_seconds += int(part[:-1]) * time_units[part[-1]]
            elif part.isdigit():
                # Default to minutes if no unit specified
                duration_seconds += int(part) * 60
        
        if duration_seconds <= 0:
            await ctx.send("❌ Invalid duration. Please use format like '1d 2h 3m 4s'.")
            return
        
        # Format readable duration
        days, remainder = divmod(duration_seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        duration_str = ""
        if days > 0:
            duration_str += f"{days} day{'s' if days != 1 else ''} "
        if hours > 0:
            duration_str += f"{hours} hour{'s' if hours != 1 else ''} "
        if minutes > 0:
            duration_str += f"{minutes} minute{'s' if minutes != 1 else ''} "
        if seconds > 0:
            duration_str += f"{seconds} second{'s' if seconds != 1 else ''}"
            
        duration_str = duration_str.strip()
        expiry_time = datetime.utcnow() + timedelta(seconds=duration_seconds)
        
        try:
            # Add the role to the member
            if role not in member.roles:
                await member.add_roles(role, reason=f"Temporary role by {ctx.author} for {duration_str}")
            
            # Store in the temproles dict
            guild_id = str(ctx.guild.id)
            if guild_id not in self.temproles:
                self.temproles[guild_id] = {}
            
            member_id = str(member.id)
            if member_id not in self.temproles[guild_id]:
                self.temproles[guild_id][member_id] = {}
            
            self.temproles[guild_id][member_id][str(role.id)] = {
                "expires": expiry_time.isoformat(),
                "added_by": ctx.author.id,
                "added_at": datetime.utcnow().isoformat(),
                "duration": duration_seconds
            }
            
            self.save_temproles()
            
            # Create an embed for the temprole confirmation
            embed = discord.Embed(
                title="Temporary Role Added",
                description=f"{role.mention} has been temporarily added to {member.mention}.",
                color=role.color,
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Duration", value=duration_str)
            embed.add_field(name="Expires", value=f"<t:{int(expiry_time.timestamp())}:R>")
            embed.add_field(name="Added by", value=ctx.author.mention)
            embed.set_thumbnail(url=member.display_avatar.url)
            
            await ctx.send(embed=embed)
            
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to manage roles for that member.")
        except Exception as e:
            logger.error(f"Error adding temporary role: {str(e)}")
            await ctx.send(f"❌ An error occurred: {str(e)}")
    
    @commands.command(name="temprole_list", aliases=["temprolelist"])
    @commands.has_permissions(manage_roles=True)
    async def temprole_list(self, ctx):
        """List all active temporary roles"""
        guild_id = str(ctx.guild.id)
        
        if guild_id not in self.temproles or not self.temproles[guild_id]:
            await ctx.send("❌ There are no active temporary roles in this server.")
            return
        
        # Create embed
        embed = discord.Embed(
            title="Active Temporary Roles",
            description="List of all active temporary roles in this server",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        # Add each temprole to the embed
        for member_id, roles in self.temproles[guild_id].items():
            member = ctx.guild.get_member(int(member_id)) or await self.bot.fetch_user(int(member_id))
            
            if not roles:  # Skip if no roles
                continue
            
            role_details = []
            for role_id, data in roles.items():
                role = ctx.guild.get_role(int(role_id))
                if not role:
                    continue
                
                expires = datetime.fromisoformat(data["expires"])
                added_by = await self.bot.fetch_user(data["added_by"])
                
                role_details.append(
                    f"**Role:** {role.mention}\n"
                    f"**Expires:** <t:{int(expires.timestamp())}:R>\n"
                    f"**Added by:** {added_by.mention}"
                )
            
            if role_details:
                embed.add_field(
                    name=f"{member.display_name} ({member.id})",
                    value="\n\n".join(role_details),
                    inline=False
                )
        
        await ctx.send(embed=embed)
    
    async def check_temproles(self):
        """Background task to check and remove expired temporary roles"""
        await self.bot.wait_until_ready()
        
        while not self.bot.is_closed():
            try:
                current_time = datetime.utcnow()
                guilds_to_update = []
                
                for guild_id, members in self.temproles.items():
                    guild = self.bot.get_guild(int(guild_id))
                    if not guild:
                        continue
                    
                    for member_id, roles in members.items():
                        member = guild.get_member(int(member_id))
                        if not member:
                            continue
                        
                        roles_to_remove = []
                        for role_id, data in roles.items():
                            expires = datetime.fromisoformat(data["expires"])
                            
                            if current_time >= expires:
                                role = guild.get_role(int(role_id))
                                if role and role in member.roles:
                                    try:
                                        await member.remove_roles(role, reason="Temporary role expired")
                                        logger.info(f"Removed temporary role {role.name} from {member.display_name}")
                                    except Exception as e:
                                        logger.error(f"Error removing temporary role: {str(e)}")
                                
                                roles_to_remove.append(role_id)
                        
                        # Remove expired roles from the dict
                        for role_id in roles_to_remove:
                            del self.temproles[guild_id][member_id][role_id]
                        
                        # If the member has no more temproles, mark for removal
                        if not self.temproles[guild_id][member_id]:
                            roles_to_remove.append(member_id)
                    
                    # Remove members with no temproles
                    for member_id in roles_to_remove:
                        if member_id in self.temproles[guild_id]:
                            del self.temproles[guild_id][member_id]
                    
                    # If the guild has no more temproles, mark for removal
                    if not self.temproles[guild_id]:
                        guilds_to_update.append(guild_id)
                
                # Remove guilds with no temproles
                for guild_id in guilds_to_update:
                    del self.temproles[guild_id]
                
                # Save changes if any were made
                if guilds_to_update or any(roles_to_remove):
                    self.save_temproles()
                
            except Exception as e:
                logger.error(f"Error in check_temproles task: {str(e)}")
            
            # Check every minute
            await asyncio.sleep(60)
    
    def cog_unload(self):
        """Clean up when the cog is unloaded"""
        self.check_temproles_task.cancel()

    # Event to maintain hardbans
    @commands.Cog.listener()
    async def on_member_unban(self, guild, user):
        guild_id = str(guild.id)
        user_id = str(user.id)
        
        # Check if the user is hardbanned
        if (guild_id in self.hardbans and 
            user_id in self.hardbans[guild_id]):
            # Re-ban the user
            try:
                reason = self.hardbans[guild_id][user_id]["reason"]
                await guild.ban(user, reason=f"Hardbanned: {reason}")
                logger.info(f"Re-banned hardbanned user {user.name}#{user.discriminator} ({user.id}) in {guild.name}")
            except Exception as e:
                logger.error(f"Failed to re-ban hardbanned user: {str(e)}")

async def setup(bot):
    await bot.add_cog(AdvancedModeration(bot)) 