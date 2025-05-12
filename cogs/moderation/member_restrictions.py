import discord
from discord.ext import commands
import asyncio
import logging
from datetime import datetime, timedelta
import json
import os

logger = logging.getLogger('bot')

class MemberRestrictions(commands.Cog):
    """Commands for restricting members in various ways"""
    
    def __init__(self, bot):
        self.bot = bot
        self.data_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'data', 'moderation')
        self.jail_file = os.path.join(self.data_folder, 'jail.json')
        self.stfu_file = os.path.join(self.data_folder, 'stfu.json')
        self.forcenick_file = os.path.join(self.data_folder, 'forcenick.json')
        # Create data directory if it doesn't exist
        os.makedirs(self.data_folder, exist_ok=True)
        # Load data
        self.jail_data = self.load_data(self.jail_file)
        self.stfu_data = self.load_data(self.stfu_file)
        self.forcenick_data = self.load_data(self.forcenick_file)
        # Background task for checking jail timeouts
        self.check_jail_task = self.bot.loop.create_task(self.check_jail_timeouts())
    
    def load_data(self, file_path):
        """Load data from file"""
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    return json.load(f)
            else:
                return {}
        except json.JSONDecodeError:
            logger.error(f"Error decoding {file_path}. Using empty config.")
            return {}
    
    def save_data(self, data, file_path):
        """Save data to file"""
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=4)
    
    @commands.command(name="jail")
    @commands.has_permissions(manage_messages=True)
    async def jail(self, ctx, member: discord.Member, duration: str = None, *, reason="No reason provided"):
        """Jails the mentioned user"""
        # Check permissions
        if member.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
            await ctx.send("❌ You cannot jail a member with a role higher than or equal to yours.")
            return
            
        guild_id = str(ctx.guild.id)
        
        # Parse duration if provided
        expires = None
        duration_seconds = 0
        duration_str = "indefinitely"
        
        if duration:
            time_units = {"s": 1, "m": 60, "h": 3600, "d": 86400}
            
            # Simple duration parsing
            duration_parts = duration.lower().split()
            for part in duration_parts:
                if part[-1] in time_units and part[:-1].isdigit():
                    duration_seconds += int(part[:-1]) * time_units[part[-1]]
                elif part.isdigit():
                    # Default to minutes if no unit specified
                    duration_seconds += int(part) * 60
                    
            if duration_seconds > 0:
                expires = datetime.utcnow() + timedelta(seconds=duration_seconds)
                
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
        
        try:
            # Find or create the jail role
            jail_role = discord.utils.get(ctx.guild.roles, name="Jailed")
            if not jail_role:
                # Create the jail role if it doesn't exist
                jail_role = await ctx.guild.create_role(
                    name="Jailed",
                    color=discord.Color.dark_gray(),
                    reason="Creating jail role"
                )
                
                # Set permissions for the jail role in all text channels
                for channel in ctx.guild.text_channels:
                    try:
                        await channel.set_permissions(
                            jail_role,
                            send_messages=False,
                            add_reactions=False,
                            reason="Setting up jail role permissions"
                        )
                    except:
                        continue
                        
                # Set permissions for the jail role in all voice channels
                for channel in ctx.guild.voice_channels:
                    try:
                        await channel.set_permissions(
                            jail_role,
                            connect=False,
                            speak=False,
                            reason="Setting up jail role permissions"
                        )
                    except:
                        continue
            
            # Store the member's roles before jailing
            stored_roles = [role.id for role in member.roles if role.id != ctx.guild.default_role.id]
            
            # Remove all roles and add the jail role
            await member.edit(roles=[jail_role], reason=f"Jailed by {ctx.author}: {reason}")
            
            # Initialize the guild in jail data if it doesn't exist
            if guild_id not in self.jail_data:
                self.jail_data[guild_id] = {}
                
            # Store the jail information
            self.jail_data[guild_id][str(member.id)] = {
                "roles": stored_roles,
                "jailed_by": ctx.author.id,
                "jailed_at": datetime.utcnow().isoformat(),
                "reason": reason,
                "expires": expires.isoformat() if expires else None
            }
            
            self.save_data(self.jail_data, self.jail_file)
            
            # Create an embed for the jail confirmation
            embed = discord.Embed(
                title="Member Jailed",
                description=f"{member.mention} has been jailed for {duration_str}.",
                color=discord.Color.dark_gray(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Reason", value=reason)
            embed.add_field(name="Jailed by", value=ctx.author.mention)
            if expires:
                embed.add_field(name="Expires", value=f"<t:{int(expires.timestamp())}:R>")
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(text=f"User ID: {member.id}")
            
            await ctx.send(embed=embed)
            
            # Try to DM the member about being jailed
            try:
                dm_embed = discord.Embed(
                    title="You have been jailed",
                    description=f"You have been jailed in {ctx.guild.name} for {duration_str}.",
                    color=discord.Color.dark_gray(),
                    timestamp=datetime.utcnow()
                )
                dm_embed.add_field(name="Reason", value=reason)
                dm_embed.add_field(name="Jailed by", value=ctx.author.name)
                if expires:
                    dm_embed.add_field(name="Expires", value=f"<t:{int(expires.timestamp())}:R>")
                
                await member.send(embed=dm_embed)
            except:
                # Member might have DMs disabled
                pass
                
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to manage roles for that member.")
        except Exception as e:
            logger.error(f"Error jailing member: {str(e)}")
            await ctx.send(f"❌ An error occurred: {str(e)}")
    
    @commands.command(name="jaillist")
    @commands.has_permissions(manage_messages=True)
    async def jaillist(self, ctx):
        """View a list of every current jailed member"""
        guild_id = str(ctx.guild.id)
        
        if guild_id not in self.jail_data or not self.jail_data[guild_id]:
            await ctx.send("❌ There are no jailed members in this server.")
            return
            
        embed = discord.Embed(
            title="Jailed Members",
            description=f"Total: {len(self.jail_data[guild_id])} jailed members",
            color=discord.Color.dark_gray(),
            timestamp=datetime.utcnow()
        )
        
        for member_id, data in self.jail_data[guild_id].items():
            try:
                member = ctx.guild.get_member(int(member_id))
                if not member:
                    member = await self.bot.fetch_user(int(member_id))
                    
                jailed_by = ctx.guild.get_member(data["jailed_by"]) or await self.bot.fetch_user(data["jailed_by"])
                jailed_at = datetime.fromisoformat(data["jailed_at"])
                expires_str = "Never (permanent)"
                
                if data["expires"]:
                    expires = datetime.fromisoformat(data["expires"])
                    expires_str = f"<t:{int(expires.timestamp())}:R>"
                
                embed.add_field(
                    name=f"{member.display_name} ({member.id})",
                    value=(
                        f"**Reason:** {data['reason']}\n"
                        f"**Jailed by:** {jailed_by.mention}\n"
                        f"**Jailed at:** <t:{int(jailed_at.timestamp())}:R>\n"
                        f"**Expires:** {expires_str}"
                    ),
                    inline=False
                )
            except Exception as e:
                logger.error(f"Error displaying jailed member: {str(e)}")
                continue
                
        if not embed.fields:
            await ctx.send("❌ Failed to retrieve information about jailed members.")
            return
            
        await ctx.send(embed=embed)
    
    @commands.command(name="unjail")
    @commands.has_permissions(manage_messages=True)
    async def unjail(self, ctx, member: discord.Member):
        """Unjails the mentioned user"""
        guild_id = str(ctx.guild.id)
        member_id = str(member.id)
        
        # Check if the member is jailed
        if (guild_id not in self.jail_data or
            member_id not in self.jail_data[guild_id]):
            await ctx.send(f"❌ {member.mention} is not jailed.")
            return
            
        try:
            # Get the stored roles
            stored_role_ids = self.jail_data[guild_id][member_id]["roles"]
            roles_to_add = []
            
            for role_id in stored_role_ids:
                role = ctx.guild.get_role(int(role_id))
                if role:
                    roles_to_add.append(role)
            
            # Remove the jail role by setting the roles back to the stored ones
            await member.edit(roles=roles_to_add, reason=f"Unjailed by {ctx.author}")
            
            # Remove the member from jail data
            del self.jail_data[guild_id][member_id]
            
            # Remove guild from data if empty
            if not self.jail_data[guild_id]:
                del self.jail_data[guild_id]
                
            self.save_data(self.jail_data, self.jail_file)
            
            # Create an embed for the unjail confirmation
            embed = discord.Embed(
                title="Member Unjailed",
                description=f"{member.mention} has been released from jail.",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Unjailed by", value=ctx.author.mention)
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(text=f"User ID: {member.id}")
            
            await ctx.send(embed=embed)
            
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to manage roles for that member.")
        except Exception as e:
            logger.error(f"Error unjailing member: {str(e)}")
            await ctx.send(f"❌ An error occurred: {str(e)}")
    
    @commands.command(name="tempban")
    @commands.has_permissions(ban_members=True)
    async def tempban(self, ctx, member: discord.Member, duration: str, *, reason="No reason provided"):
        """Temporarily ban members"""
        # Check permissions
        if member.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
            await ctx.send("❌ You cannot ban a member with a role higher than or equal to yours.")
            return
            
        # Parse duration
        duration_seconds = 0
        time_units = {"s": 1, "m": 60, "h": 3600, "d": 86400}
        
        # Simple duration parsing
        duration_parts = duration.lower().split()
        for part in duration_parts:
            if part[-1] in time_units and part[:-1].isdigit():
                duration_seconds += int(part[:-1]) * time_units[part[-1]]
            elif part.isdigit():
                # Default to minutes if no unit specified
                duration_seconds += int(part) * 60
                
        if duration_seconds <= 0:
            await ctx.send("❌ Please provide a valid duration (e.g., '1h 30m', '2d', etc.)")
            return
            
        expires = datetime.utcnow() + timedelta(seconds=duration_seconds)
        
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
        
        try:
            # Try to send a DM to the user being banned
            try:
                dm_embed = discord.Embed(
                    title="You have been temporarily banned",
                    description=f"You have been banned from {ctx.guild.name} for {duration_str}.",
                    color=discord.Color.red(),
                    timestamp=datetime.utcnow()
                )
                dm_embed.add_field(name="Reason", value=reason)
                dm_embed.add_field(name="Banned by", value=ctx.author.name)
                dm_embed.add_field(name="Expires", value=f"<t:{int(expires.timestamp())}:R>")
                
                await member.send(embed=dm_embed)
            except:
                # Member might have DMs disabled
                pass
                
            # Execute the ban
            await member.ban(delete_message_days=1, reason=f"{reason} | Temp banned by {ctx.author} for {duration_str}")
            
            # Create an embed for the tempban confirmation
            embed = discord.Embed(
                title="Member Temporarily Banned",
                description=f"{member.mention} has been banned for {duration_str}.",
                color=discord.Color.red(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Reason", value=reason)
            embed.add_field(name="Banned by", value=ctx.author.mention)
            embed.add_field(name="Expires", value=f"<t:{int(expires.timestamp())}:R>")
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(text=f"User ID: {member.id}")
            
            await ctx.send(embed=embed)
            
            # Schedule unban task
            async def unban_later():
                await asyncio.sleep(duration_seconds)
                try:
                    # Check if the guild still exists
                    if ctx.guild in self.bot.guilds:
                        # Get the ban entry
                        banned_users = [entry async for entry in ctx.guild.bans()]
                        for ban_entry in banned_users:
                            if ban_entry.user.id == member.id:
                                await ctx.guild.unban(ban_entry.user, reason=f"Temporary ban for {duration_str} expired")
                                logger.info(f"Unbanned {member.name} ({member.id}) in {ctx.guild.name} - temporary ban expired")
                                
                                # Try to send notification to mod log channel or original channel
                                try:
                                    user_mention = f"<@{member.id}>"  # Use direct mention format instead of member.mention
                                    notification = discord.Embed(
                                        title="Temporary Ban Expired",
                                        description=f"The temporary ban for {user_mention} has expired.",
                                        color=discord.Color.green(),
                                        timestamp=datetime.utcnow()
                                    )
                                    notification.add_field(name="Originally banned by", value=ctx.author.mention)
                                    notification.add_field(name="Original reason", value=reason)
                                    notification.add_field(name="Ban duration", value=duration_str)
                                    notification.set_footer(text=f"User ID: {member.id}")
                                    
                                    await ctx.channel.send(embed=notification)
                                except:
                                    pass
                                break
                except Exception as e:
                    logger.error(f"Error during scheduled unban: {str(e)}")
                    
            # Start the unban task
            self.bot.loop.create_task(unban_later())
            
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to ban that member.")
        except Exception as e:
            logger.error(f"Error when temp banning user: {str(e)}")
            await ctx.send(f"❌ An error occurred: {str(e)}")
            
    async def check_jail_timeouts(self):
        """Background task to check and release expired jails"""
        await self.bot.wait_until_ready()
        
        while not self.bot.is_closed():
            try:
                current_time = datetime.utcnow()
                guilds_to_update = []
                
                for guild_id, members in self.jail_data.items():
                    guild = self.bot.get_guild(int(guild_id))
                    if not guild:
                        continue
                        
                    members_to_unjail = []
                    
                    for member_id, data in members.items():
                        if data["expires"]:
                            expires = datetime.fromisoformat(data["expires"])
                            
                            if current_time >= expires:
                                # Time to unjail
                                member = guild.get_member(int(member_id))
                                if member:
                                    try:
                                        # Get the stored roles
                                        stored_role_ids = data["roles"]
                                        roles_to_add = []
                                        
                                        for role_id in stored_role_ids:
                                            role = guild.get_role(int(role_id))
                                            if role and role.is_assignable():
                                                roles_to_add.append(role)
                                        
                                        # Remove the jail role by setting the roles back to the stored ones
                                        await member.edit(roles=roles_to_add, reason="Jail period expired")
                                        logger.info(f"Unjailed {member.name} in {guild.name} - jail period expired")
                                        
                                        # Add to the list of members to remove from jail data
                                        members_to_unjail.append(member_id)
                                        
                                    except Exception as e:
                                        logger.error(f"Error auto-unjailing member: {str(e)}")
                    
                    # Remove unjailed members from data
                    for member_id in members_to_unjail:
                        del self.jail_data[guild_id][member_id]
                        
                    # If the guild has no more jailed members, mark it for removal
                    if not self.jail_data[guild_id]:
                        guilds_to_update.append(guild_id)
                
                # Remove empty guilds
                for guild_id in guilds_to_update:
                    del self.jail_data[guild_id]
                    
                # Save if changes were made
                if guilds_to_update or any(members_to_unjail):
                    self.save_data(self.jail_data, self.jail_file)
                    
            except Exception as e:
                logger.error(f"Error in check_jail_timeouts task: {str(e)}")
                
            # Check every minute
            await asyncio.sleep(60)
    
    @commands.command(name="stfu")
    @commands.has_permissions(manage_messages=True)
    async def stfu(self, ctx, user: discord.Member):
        """Toggle deletion of a user's messages anytime they send one"""
        guild_id = str(ctx.guild.id)
        user_id = str(user.id)
        
        # Initialize the guild in stfu data if it doesn't exist
        if guild_id not in self.stfu_data:
            self.stfu_data[guild_id] = []
            
        # Toggle the user's stfu status
        if user_id in self.stfu_data[guild_id]:
            self.stfu_data[guild_id].remove(user_id)
            status_msg = f"✅ {user.mention} can now talk freely again."
            color = discord.Color.green()
        else:
            self.stfu_data[guild_id].append(user_id)
            status_msg = f"🤐 {user.mention} has been told to STFU. Their messages will be deleted."
            color = discord.Color.red()
            
        self.save_data(self.stfu_data, self.stfu_file)
        
        embed = discord.Embed(
            title="STFU Status Updated",
            description=status_msg,
            color=color,
            timestamp=datetime.utcnow()
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_footer(text=f"Toggled by {ctx.author.name}")
        
        await ctx.send(embed=embed)
    
    @commands.command(name="imute")
    @commands.has_permissions(moderate_members=True)
    async def imute(self, ctx, member: discord.Member, *, reason="No reason provided"):
        """Remove a member's attach files & embed links permission"""
        # Get the default role
        default_role = ctx.guild.default_role
        
        try:
            # Get the channel permissions
            for channel in ctx.guild.text_channels:
                # Get current permissions
                overwrites = channel.overwrites_for(member)
                
                # Update permissions
                overwrites.attach_files = False
                overwrites.embed_links = False
                
                await channel.set_permissions(
                    member,
                    overwrite=overwrites,
                    reason=f"Image muted by {ctx.author}: {reason}"
                )
                
            embed = discord.Embed(
                title="Member Image Muted",
                description=f"{member.mention} can no longer send images or embeds.",
                color=discord.Color.orange(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Reason", value=reason)
            embed.add_field(name="Muted by", value=ctx.author.mention)
            embed.set_thumbnail(url=member.display_avatar.url)
            
            await ctx.send(embed=embed)
            
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to manage channel permissions.")
        except Exception as e:
            logger.error(f"Error image muting member: {str(e)}")
            await ctx.send(f"❌ An error occurred: {str(e)}")
    
    @commands.command(name="iunmute")
    @commands.has_permissions(moderate_members=True)
    async def iunmute(self, ctx, member: discord.Member, *, reason="No reason provided"):
        """Restores a member's attach files & embed links permission"""
        try:
            # Get the channel permissions
            for channel in ctx.guild.text_channels:
                # Get current permissions
                overwrites = channel.overwrites_for(member)
                
                # Update permissions
                overwrites.attach_files = None
                overwrites.embed_links = None
                
                # If all permissions are now none, remove the overwrite completely
                if all(getattr(overwrites, attr) is None for attr in dir(overwrites) if not attr.startswith('_')):
                    await channel.set_permissions(
                        member,
                        overwrite=None,
                        reason=f"Image unmuted by {ctx.author}: {reason}"
                    )
                else:
                    await channel.set_permissions(
                        member,
                        overwrite=overwrites,
                        reason=f"Image unmuted by {ctx.author}: {reason}"
                    )
                
            embed = discord.Embed(
                title="Member Image Unmuted",
                description=f"{member.mention} can now send images and embeds again.",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Reason", value=reason)
            embed.add_field(name="Unmuted by", value=ctx.author.mention)
            embed.set_thumbnail(url=member.display_avatar.url)
            
            await ctx.send(embed=embed)
            
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to manage channel permissions.")
        except Exception as e:
            logger.error(f"Error image unmuting member: {str(e)}")
            await ctx.send(f"❌ An error occurred: {str(e)}")
    
    @commands.command(name="rmute")
    @commands.has_permissions(moderate_members=True)
    async def rmute(self, ctx, member: discord.Member, *, reason="No reason provided"):
        """Remove a member's add reactions & use external emotes permission"""
        try:
            # Get the channel permissions
            for channel in ctx.guild.text_channels:
                # Get current permissions
                overwrites = channel.overwrites_for(member)
                
                # Update permissions
                overwrites.add_reactions = False
                overwrites.use_external_emojis = False
                
                await channel.set_permissions(
                    member,
                    overwrite=overwrites,
                    reason=f"Reaction muted by {ctx.author}: {reason}"
                )
                
            embed = discord.Embed(
                title="Member Reaction Muted",
                description=f"{member.mention} can no longer add reactions or use external emojis.",
                color=discord.Color.orange(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Reason", value=reason)
            embed.add_field(name="Muted by", value=ctx.author.mention)
            embed.set_thumbnail(url=member.display_avatar.url)
            
            await ctx.send(embed=embed)
            
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to manage channel permissions.")
        except Exception as e:
            logger.error(f"Error reaction muting member: {str(e)}")
            await ctx.send(f"❌ An error occurred: {str(e)}")
    
    @commands.command(name="runmute")
    @commands.has_permissions(moderate_members=True)
    async def runmute(self, ctx, member: discord.Member, *, reason="No reason provided"):
        """Restores a member's add reactions & use external emotes permission"""
        try:
            # Get the channel permissions
            for channel in ctx.guild.text_channels:
                # Get current permissions
                overwrites = channel.overwrites_for(member)
                
                # Update permissions
                overwrites.add_reactions = None
                overwrites.use_external_emojis = None
                
                # If all permissions are now none, remove the overwrite completely
                if all(getattr(overwrites, attr) is None for attr in dir(overwrites) if not attr.startswith('_')):
                    await channel.set_permissions(
                        member,
                        overwrite=None,
                        reason=f"Reaction unmuted by {ctx.author}: {reason}"
                    )
                else:
                    await channel.set_permissions(
                        member,
                        overwrite=overwrites,
                        reason=f"Reaction unmuted by {ctx.author}: {reason}"
                    )
                
            embed = discord.Embed(
                title="Member Reaction Unmuted",
                description=f"{member.mention} can now add reactions and use external emojis again.",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Reason", value=reason)
            embed.add_field(name="Unmuted by", value=ctx.author.mention)
            embed.set_thumbnail(url=member.display_avatar.url)
            
            await ctx.send(embed=embed)
            
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to manage channel permissions.")
        except Exception as e:
            logger.error(f"Error reaction unmuting member: {str(e)}")
            await ctx.send(f"❌ An error occurred: {str(e)}")
    
    @commands.group(name="forcenickname", aliases=["forcenick"], invoke_without_command=True)
    @commands.has_permissions(manage_nicknames=True)
    async def forcenickname(self, ctx, member: discord.Member, *, name: str):
        """Force a member's current nickname"""
        guild_id = str(ctx.guild.id)
        member_id = str(member.id)
        
        try:
            # Set the nickname
            old_nick = member.display_name
            await member.edit(nick=name, reason=f"Nickname forced by {ctx.author}")
            
            # Store the forced nickname
            if guild_id not in self.forcenick_data:
                self.forcenick_data[guild_id] = {}
                
            self.forcenick_data[guild_id][member_id] = {
                "nickname": name,
                "forced_by": ctx.author.id,
                "forced_at": datetime.utcnow().isoformat()
            }
            
            self.save_data(self.forcenick_data, self.forcenick_file)
            
            embed = discord.Embed(
                title="Nickname Forced",
                description=f"{member.mention}'s nickname has been forcefully changed.",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Old Nickname", value=old_nick)
            embed.add_field(name="New Nickname", value=name)
            embed.add_field(name="Forced by", value=ctx.author.mention)
            embed.set_thumbnail(url=member.display_avatar.url)
            
            await ctx.send(embed=embed)
            
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to change that member's nickname.")
        except Exception as e:
            logger.error(f"Error forcing nickname: {str(e)}")
            await ctx.send(f"❌ An error occurred: {str(e)}")
    
    @forcenickname.command(name="list")
    @commands.has_permissions(manage_nicknames=True)
    async def forcenickname_list(self, ctx):
        """View a list of all forced nicknames"""
        guild_id = str(ctx.guild.id)
        
        if guild_id not in self.forcenick_data or not self.forcenick_data[guild_id]:
            await ctx.send("❌ There are no forced nicknames in this server.")
            return
            
        embed = discord.Embed(
            title="Forced Nicknames",
            description=f"Total: {len(self.forcenick_data[guild_id])} forced nicknames",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        for member_id, data in self.forcenick_data[guild_id].items():
            try:
                member = ctx.guild.get_member(int(member_id))
                if not member:
                    continue
                    
                forced_by = ctx.guild.get_member(data["forced_by"]) or await self.bot.fetch_user(data["forced_by"])
                forced_at = datetime.fromisoformat(data["forced_at"])
                
                embed.add_field(
                    name=f"{member.mention} ({member.id})",
                    value=(
                        f"**Nickname:** {data['nickname']}\n"
                        f"**Forced by:** {forced_by.mention}\n"
                        f"**Forced at:** <t:{int(forced_at.timestamp())}:R>"
                    ),
                    inline=False
                )
            except Exception as e:
                logger.error(f"Error displaying forced nickname: {str(e)}")
                continue
                
        if not embed.fields:
            await ctx.send("❌ Failed to retrieve information about forced nicknames.")
            return
            
        await ctx.send(embed=embed)
    
    # Event listeners to enforce restrictions
    @commands.Cog.listener()
    async def on_message(self, message):
        """Check for STFU users and delete their messages"""
        if message.author.bot or not message.guild:
            return
            
        guild_id = str(message.guild.id)
        user_id = str(message.author.id)
        
        # Check if the user is muted via STFU
        if (guild_id in self.stfu_data and 
            user_id in self.stfu_data[guild_id]):
            try:
                await message.delete()
                logger.info(f"Deleted message from STFU user {message.author.name} in {message.guild.name}")
            except:
                # Message might already be deleted or we don't have permissions
                pass
    
    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        """Check for nickname changes and enforce forced nicknames"""
        if before.nick == after.nick:
            return
            
        guild_id = str(after.guild.id)
        member_id = str(after.id)
        
        # Check if the member has a forced nickname
        if (guild_id in self.forcenick_data and 
            member_id in self.forcenick_data[guild_id]):
            forced_nick = self.forcenick_data[guild_id][member_id]["nickname"]
            
            if after.nick != forced_nick:
                try:
                    await after.edit(nick=forced_nick, reason="Enforcing forced nickname")
                    logger.info(f"Enforced forced nickname for {after.name} in {after.guild.name}")
                except:
                    # We might not have permissions
                    pass
    
    def cog_unload(self):
        """Clean up when the cog is unloaded"""
        self.check_jail_task.cancel()

async def setup(bot):
    await bot.add_cog(MemberRestrictions(bot)) 