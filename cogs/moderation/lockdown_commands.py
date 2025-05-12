import discord
from discord.ext import commands
import json
import os
import asyncio
import logging
from datetime import datetime, timedelta

# Import custom check for has_any_of
from custom_checks import has_any_of

logger = logging.getLogger('bot')

class LockdownCommands(commands.Cog):
    """Commands for locking down channels and other channel management"""
    
    def __init__(self, bot):
        self.bot = bot
        self.data_folder = 'data/moderation'
        self.lockdown_file = os.path.join(self.data_folder, 'lockdown_settings.json')
        # Create directory if it doesn't exist
        os.makedirs(self.data_folder, exist_ok=True)
        # Load data
        self.lockdown_settings = self.load_settings()
    
    def load_settings(self):
        """Load lockdown settings from file"""
        try:
            if os.path.exists(self.lockdown_file):
                with open(self.lockdown_file, 'r') as f:
                    return json.load(f)
            else:
                return {}
        except json.JSONDecodeError:
            logger.error(f"Error decoding {self.lockdown_file}. Using empty settings.")
            return {}
    
    def save_settings(self):
        """Save lockdown settings to file"""
        with open(self.lockdown_file, 'w') as f:
            json.dump(self.lockdown_settings, f, indent=4)
    
    @commands.command(name="lockdown")
    @commands.has_permissions(manage_channels=True)
    async def lockdown(self, ctx, channel: discord.TextChannel = None, *, reason="No reason provided"):
        """Prevent regular members from typing"""
        # Default to current channel if none specified
        channel = channel or ctx.channel
        
        try:
            # Get the @everyone role
            everyone_role = ctx.guild.default_role
            
            # Check if the channel is already locked
            current_perms = channel.overwrites_for(everyone_role)
            if current_perms.send_messages is False:
                await ctx.send(f"❌ {channel.mention} is already locked.")
                return
            
            # Store the original permissions for later unlock
            guild_id = str(ctx.guild.id)
            channel_id = str(channel.id)
            
            if guild_id not in self.lockdown_settings:
                self.lockdown_settings[guild_id] = {}
                
            self.lockdown_settings[guild_id][channel_id] = {
                "original_send": current_perms.send_messages,
                "locked_by": ctx.author.id,
                "locked_at": datetime.utcnow().isoformat(),
                "reason": reason
            }
            
            self.save_settings()
            
            # Update permissions
            overwrite = discord.PermissionOverwrite(**{k: v for k, v in current_perms})
            overwrite.send_messages = False
            
            await channel.set_permissions(
                everyone_role, 
                overwrite=overwrite,
                reason=f"Channel locked by {ctx.author.name}: {reason}"
            )
            
            # Create the lockdown message
            embed = discord.Embed(
                title="🔒 Channel Locked",
                description=f"This channel has been locked by {ctx.author.mention}.",
                color=discord.Color.red(),
                timestamp=datetime.utcnow()
            )
            
            embed.add_field(name="Reason", value=reason)
            embed.add_field(name="Unlock Command", value=f"`!unlockdown {channel.mention}`")
            embed.set_footer(text="Only users with 'Manage Channels' permission can send messages")
            
            await channel.send(embed=embed)
            
            # Confirm in the command channel if different
            if channel.id != ctx.channel.id:
                await ctx.send(f"✅ {channel.mention} has been locked.")
            
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to manage channel permissions.")
        except Exception as e:
            logger.error(f"Error when locking channel: {str(e)}")
            await ctx.send(f"❌ An error occurred: {str(e)}")
    
    @commands.group(name="lockdown_ignore", invoke_without_command=True, aliases=["lockdownignore"])
    @commands.has_permissions(manage_channels=True)
    async def lockdown_ignore(self, ctx):
        """Prevent channels from being altered during lockdown all"""
        # Display current ignored channels
        await ctx.invoke(self.bot.get_command("lockdown_ignore list"))
    
    @lockdown_ignore.command(name="add")
    @commands.has_permissions(manage_channels=True)
    async def lockdown_ignore_add(self, ctx, channel: discord.TextChannel):
        """Add a channel to the ignore list"""
        guild_id = str(ctx.guild.id)
        
        if guild_id not in self.lockdown_settings:
            self.lockdown_settings[guild_id] = {}
            
        if "ignored_channels" not in self.lockdown_settings[guild_id]:
            self.lockdown_settings[guild_id]["ignored_channels"] = []
            
        channel_id = str(channel.id)
        
        if channel_id in self.lockdown_settings[guild_id]["ignored_channels"]:
            await ctx.send(f"❌ {channel.mention} is already in the ignore list.")
            return
            
        self.lockdown_settings[guild_id]["ignored_channels"].append(channel_id)
        self.save_settings()
        
        await ctx.send(f"✅ Added {channel.mention} to the lockdown ignore list.")
    
    @lockdown_ignore.command(name="remove")
    @commands.has_permissions(manage_channels=True)
    async def lockdown_ignore_remove(self, ctx, channel: discord.TextChannel):
        """Remove a channel from the ignore list"""
        guild_id = str(ctx.guild.id)
        channel_id = str(channel.id)
        
        if (guild_id not in self.lockdown_settings or 
            "ignored_channels" not in self.lockdown_settings[guild_id] or
            channel_id not in self.lockdown_settings[guild_id]["ignored_channels"]):
            await ctx.send(f"❌ {channel.mention} is not in the ignore list.")
            return
            
        self.lockdown_settings[guild_id]["ignored_channels"].remove(channel_id)
        self.save_settings()
        
        await ctx.send(f"✅ Removed {channel.mention} from the lockdown ignore list.")
    
    @lockdown_ignore.command(name="list")
    @commands.has_permissions(manage_channels=True)
    async def lockdown_ignore_list(self, ctx):
        """List all ignored channels"""
        guild_id = str(ctx.guild.id)
        
        if (guild_id not in self.lockdown_settings or 
            "ignored_channels" not in self.lockdown_settings[guild_id] or
            not self.lockdown_settings[guild_id]["ignored_channels"]):
            await ctx.send("❌ There are no channels in the lockdown ignore list.")
            return
            
        ignored_channels = []
        for channel_id in self.lockdown_settings[guild_id]["ignored_channels"]:
            channel = ctx.guild.get_channel(int(channel_id))
            if channel:
                ignored_channels.append(channel.mention)
                
        if not ignored_channels:
            await ctx.send("❌ There are no valid channels in the lockdown ignore list.")
            return
            
        embed = discord.Embed(
            title="Lockdown Ignored Channels",
            description="These channels will not be affected by the `lockdown all` command.",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(
            name=f"Ignored Channels ({len(ignored_channels)})",
            value=", ".join(ignored_channels) or "None",
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @commands.command(name="lockdown_all", aliases=["lockdownall"])
    @commands.has_permissions(manage_channels=True)
    async def lockdown_all(self, ctx, *, reason="No reason provided"):
        """Prevent regular members from typing in all channels"""
        try:
            # Get the @everyone role
            everyone_role = ctx.guild.default_role
            
            # Get text channels
            text_channels = [c for c in ctx.guild.text_channels if isinstance(c, discord.TextChannel)]
            
            # Get ignore list
            guild_id = str(ctx.guild.id)
            ignored_channels = []
            
            if (guild_id in self.lockdown_settings and 
                "ignored_channels" in self.lockdown_settings[guild_id]):
                ignored_channels = self.lockdown_settings[guild_id]["ignored_channels"]
            
            # Initialize counters
            locked = 0
            already_locked = 0
            failed = 0
            ignored = 0
            
            # Create initial status message
            status_msg = await ctx.send(f"🔄 Locking all text channels... 0/{len(text_channels)} completed")
            
            # Initialize server lockdown status
            if guild_id not in self.lockdown_settings:
                self.lockdown_settings[guild_id] = {}
                
            if "server_lockdown" not in self.lockdown_settings[guild_id]:
                self.lockdown_settings[guild_id]["server_lockdown"] = {
                    "active": False,
                    "channels": {}
                }
                
            server_lockdown = self.lockdown_settings[guild_id]["server_lockdown"]
            server_lockdown["active"] = True
            server_lockdown["locked_by"] = ctx.author.id
            server_lockdown["locked_at"] = datetime.utcnow().isoformat()
            server_lockdown["reason"] = reason
            
            # Lock all channels
            for i, channel in enumerate(text_channels):
                channel_id = str(channel.id)
                
                # Skip ignored channels
                if channel_id in ignored_channels:
                    ignored += 1
                    continue
                
                try:
                    # Get current permissions
                    current_perms = channel.overwrites_for(everyone_role)
                    
                    # Skip if already locked
                    if current_perms.send_messages is False:
                        already_locked += 1
                        continue
                    
                    # Store original permissions
                    server_lockdown["channels"][channel_id] = {
                        "original_send": current_perms.send_messages
                    }
                    
                    # Update permissions
                    overwrite = discord.PermissionOverwrite(**{k: v for k, v in current_perms})
                    overwrite.send_messages = False
                    
                    await channel.set_permissions(
                        everyone_role, 
                        overwrite=overwrite,
                        reason=f"Server-wide lockdown by {ctx.author.name}: {reason}"
                    )
                    
                    locked += 1
                    
                    # Send lockdown notice in the channel
                    embed = discord.Embed(
                        title="🔒 Server Lockdown",
                        description=f"This channel has been locked due to a server-wide lockdown.",
                        color=discord.Color.red(),
                        timestamp=datetime.utcnow()
                    )
                    
                    embed.add_field(name="Locked by", value=ctx.author.mention)
                    embed.add_field(name="Reason", value=reason)
                    
                    try:
                        await channel.send(embed=embed)
                    except:
                        # Can't send message, but the channel is still locked
                        pass
                    
                except:
                    failed += 1
                
                # Update status every 5 channels
                if (i + 1) % 5 == 0 or i + 1 == len(text_channels):
                    await status_msg.edit(
                        content=f"🔄 Locking all text channels... {i+1}/{len(text_channels)} completed"
                    )
            
            # Save changes
            self.save_settings()
            
            # Final update
            embed = discord.Embed(
                title="🔒 Server Lockdown Complete",
                description=f"Server-wide lockdown has been activated.",
                color=discord.Color.red(),
                timestamp=datetime.utcnow()
            )
            
            embed.add_field(name="Locked by", value=ctx.author.mention)
            embed.add_field(name="Reason", value=reason)
            embed.add_field(name="Channels Locked", value=str(locked), inline=True)
            embed.add_field(name="Already Locked", value=str(already_locked), inline=True)
            embed.add_field(name="Ignored", value=str(ignored), inline=True)
            embed.add_field(name="Failed", value=str(failed), inline=True)
            embed.add_field(
                name="Unlock Command", 
                value="`!unlockdown_all`", 
                inline=False
            )
            
            await status_msg.edit(content=None, embed=embed)
            
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to manage channel permissions.")
        except Exception as e:
            logger.error(f"Error during server-wide lockdown: {str(e)}")
            await ctx.send(f"❌ An error occurred: {str(e)}")
    
    @commands.command(name="unlockdown")
    @commands.has_permissions(manage_channels=True)
    async def unlockdown(self, ctx, channel: discord.TextChannel = None, *, reason="No reason provided"):
        """Allow regular members to type"""
        # Default to current channel if none specified
        channel = channel or ctx.channel
        
        try:
            # Get the @everyone role
            everyone_role = ctx.guild.default_role
            
            # Check if the channel is locked
            current_perms = channel.overwrites_for(everyone_role)
            if current_perms.send_messages is not False:
                await ctx.send(f"❌ {channel.mention} is not locked.")
                return
            
            # Get the original permissions if available
            guild_id = str(ctx.guild.id)
            channel_id = str(channel.id)
            original_send = None
            
            if (guild_id in self.lockdown_settings and 
                channel_id in self.lockdown_settings[guild_id]):
                original_send = self.lockdown_settings[guild_id][channel_id].get("original_send")
                del self.lockdown_settings[guild_id][channel_id]
                
                # Clean up empty entries
                if not self.lockdown_settings[guild_id]:
                    del self.lockdown_settings[guild_id]
                    
                self.save_settings()
            
            # Also check server-wide lockdown
            if (guild_id in self.lockdown_settings and 
                "server_lockdown" in self.lockdown_settings[guild_id] and
                "channels" in self.lockdown_settings[guild_id]["server_lockdown"] and
                channel_id in self.lockdown_settings[guild_id]["server_lockdown"]["channels"]):
                
                if original_send is None:  # Don't override if we already have a value
                    original_send = self.lockdown_settings[guild_id]["server_lockdown"]["channels"][channel_id].get("original_send")
                
                del self.lockdown_settings[guild_id]["server_lockdown"]["channels"][channel_id]
                
                # Update server lockdown status if all channels are unlocked
                if not self.lockdown_settings[guild_id]["server_lockdown"]["channels"]:
                    self.lockdown_settings[guild_id]["server_lockdown"]["active"] = False
                    
                self.save_settings()
            
            # Update permissions
            overwrite = discord.PermissionOverwrite(**{k: v for k, v in current_perms})
            overwrite.send_messages = original_send  # None = revert to role defaults, True/False = explicit allow/deny
            
            # If all permissions are None (default), remove the override entirely
            if all(getattr(overwrite, attr) is None for attr in dir(overwrite) if not attr.startswith('_')):
                await channel.set_permissions(
                    everyone_role, 
                    overwrite=None,
                    reason=f"Channel unlocked by {ctx.author.name}: {reason}"
                )
            else:
                await channel.set_permissions(
                    everyone_role, 
                    overwrite=overwrite,
                    reason=f"Channel unlocked by {ctx.author.name}: {reason}"
                )
            
            # Create the unlock message
            embed = discord.Embed(
                title="🔓 Channel Unlocked",
                description=f"This channel has been unlocked by {ctx.author.mention}.",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            
            embed.add_field(name="Reason", value=reason)
            embed.set_footer(text="Everyone can now send messages in this channel again")
            
            await channel.send(embed=embed)
            
            # Confirm in the command channel if different
            if channel.id != ctx.channel.id:
                await ctx.send(f"✅ {channel.mention} has been unlocked.")
            
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to manage channel permissions.")
        except Exception as e:
            logger.error(f"Error when unlocking channel: {str(e)}")
            await ctx.send(f"❌ An error occurred: {str(e)}")
    
    @commands.command(name="unlockdown_all", aliases=["unlockdownall"])
    @commands.has_permissions(manage_channels=True)
    async def unlockdown_all(self, ctx, *, reason="No reason provided"):
        """Allow regular members to type in all channels"""
        guild_id = str(ctx.guild.id)
        
        # Check if server-wide lockdown is active
        if (guild_id not in self.lockdown_settings or
            "server_lockdown" not in self.lockdown_settings[guild_id] or
            not self.lockdown_settings[guild_id]["server_lockdown"].get("active", False)):
            await ctx.send("❌ There is no active server-wide lockdown.")
            return
        
        try:
            # Get the @everyone role
            everyone_role = ctx.guild.default_role
            
            # Get locked channels
            locked_channels = self.lockdown_settings[guild_id]["server_lockdown"]["channels"]
            
            if not locked_channels:
                await ctx.send("❌ There are no locked channels in the server-wide lockdown.")
                return
            
            # Initialize counters
            unlocked = 0
            failed = 0
            
            # Create initial status message
            status_msg = await ctx.send(f"🔄 Unlocking all locked channels... 0/{len(locked_channels)} completed")
            
            # Unlock all channels
            for i, (channel_id, data) in enumerate(list(locked_channels.items())):
                channel = ctx.guild.get_channel(int(channel_id))
                if not channel:
                    failed += 1
                    continue
                
                try:
                    # Get current permissions
                    current_perms = channel.overwrites_for(everyone_role)
                    
                    # Update permissions
                    overwrite = discord.PermissionOverwrite(**{k: v for k, v in current_perms})
                    overwrite.send_messages = data.get("original_send")  # None, True, or False based on original state
                    
                    # If all permissions are None (default), remove the override entirely
                    if all(getattr(overwrite, attr) is None for attr in dir(overwrite) if not attr.startswith('_')):
                        await channel.set_permissions(
                            everyone_role, 
                            overwrite=None,
                            reason=f"Server-wide unlock by {ctx.author.name}: {reason}"
                        )
                    else:
                        await channel.set_permissions(
                            everyone_role, 
                            overwrite=overwrite,
                            reason=f"Server-wide unlock by {ctx.author.name}: {reason}"
                        )
                    
                    unlocked += 1
                    
                    # Send unlock notice in the channel
                    embed = discord.Embed(
                        title="🔓 Server Lockdown Lifted",
                        description=f"This channel has been unlocked as the server-wide lockdown has ended.",
                        color=discord.Color.green(),
                        timestamp=datetime.utcnow()
                    )
                    
                    embed.add_field(name="Unlocked by", value=ctx.author.mention)
                    embed.add_field(name="Reason", value=reason)
                    
                    try:
                        await channel.send(embed=embed)
                    except:
                        # Can't send message, but the channel is still unlocked
                        pass
                    
                except:
                    failed += 1
                
                # Update status every 5 channels
                if (i + 1) % 5 == 0 or i + 1 == len(locked_channels):
                    await status_msg.edit(
                        content=f"🔄 Unlocking channels... {i+1}/{len(locked_channels)} completed"
                    )
            
            # Reset server lockdown
            self.lockdown_settings[guild_id]["server_lockdown"] = {
                "active": False,
                "channels": {}
            }
            
            # Save changes
            self.save_settings()
            
            # Final update
            embed = discord.Embed(
                title="🔓 Server Lockdown Lifted",
                description=f"Server-wide lockdown has been deactivated.",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            
            embed.add_field(name="Unlocked by", value=ctx.author.mention)
            embed.add_field(name="Reason", value=reason)
            embed.add_field(name="Channels Unlocked", value=str(unlocked), inline=True)
            embed.add_field(name="Failed", value=str(failed), inline=True)
            
            await status_msg.edit(content=None, embed=embed)
            
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to manage channel permissions.")
        except Exception as e:
            logger.error(f"Error during server-wide unlock: {str(e)}")
            await ctx.send(f"❌ An error occurred: {str(e)}")

    @commands.command(name="hide")
    @commands.has_permissions(manage_channels=True)
    async def hide(self, ctx, channel: discord.TextChannel = None, *, target: discord.Role = None):
        """Hide a channel from a role or member"""
        # Default to current channel if none specified
        channel = channel or ctx.channel
        
        # Default to @everyone if no role specified
        target = target or ctx.guild.default_role
        
        try:
            # Check current permissions
            current_perms = channel.overwrites_for(target)
            if current_perms.view_channel is False:
                await ctx.send(f"❌ {channel.mention} is already hidden from {target.mention}.")
                return
            
            # Update permissions
            overwrite = discord.PermissionOverwrite(**{k: v for k, v in current_perms})
            overwrite.view_channel = False
            
            await channel.set_permissions(
                target, 
                overwrite=overwrite,
                reason=f"Channel hidden by {ctx.author.name}"
            )
            
            await ctx.send(f"✅ {channel.mention} has been hidden from {target.mention}.")
            
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to manage channel permissions.")
        except Exception as e:
            logger.error(f"Error when hiding channel: {str(e)}")
            await ctx.send(f"❌ An error occurred: {str(e)}")
    
    @commands.command(name="unhide")
    @commands.has_permissions(manage_channels=True)
    async def unhide(self, ctx, channel: discord.TextChannel = None, *, target: discord.Role = None):
        """Unhide a channel from a role or member"""
        # Default to current channel if none specified
        channel = channel or ctx.channel
        
        # Default to @everyone if no role specified
        target = target or ctx.guild.default_role
        
        try:
            # Check current permissions
            current_perms = channel.overwrites_for(target)
            if current_perms.view_channel is not False:
                await ctx.send(f"❌ {channel.mention} is not hidden from {target.mention}.")
                return
            
            # Update permissions
            overwrite = discord.PermissionOverwrite(**{k: v for k, v in current_perms})
            overwrite.view_channel = None  # Reset to role default
            
            # If all permissions are None (default), remove the override entirely
            if all(getattr(overwrite, attr) is None for attr in dir(overwrite) if not attr.startswith('_')):
                await channel.set_permissions(
                    target, 
                    overwrite=None,
                    reason=f"Channel unhidden by {ctx.author.name}"
                )
            else:
                await channel.set_permissions(
                    target, 
                    overwrite=overwrite,
                    reason=f"Channel unhidden by {ctx.author.name}"
                )
            
            await ctx.send(f"✅ {channel.mention} has been unhidden from {target.mention}.")
            
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to manage channel permissions.")
        except Exception as e:
            logger.error(f"Error when unhiding channel: {str(e)}")
            await ctx.send(f"❌ An error occurred: {str(e)}")

    @commands.command(name="nuke")
    @has_any_of(commands.has_permissions(administrator=True), commands.has_role("Antinuke Admin"))
    async def nuke(self, ctx):
        """Clone the current channel"""
        channel = ctx.channel
        
        try:
            # Create a confirmation message
            confirm_msg = await ctx.send(
                f"⚠️ Are you sure you want to nuke {channel.mention}? This will clone the channel and delete the original. "
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
                    await ctx.send("❌ Nuke operation cancelled.")
                    return
                
                # Get channel information
                position = channel.position
                category = channel.category
                overwrites = channel.overwrites
                topic = channel.topic
                slowmode_delay = channel.slowmode_delay
                nsfw = channel.is_nsfw()
                
                # Clone the channel
                new_channel = await channel.clone(
                    name=channel.name,
                    reason=f"Channel nuked by {ctx.author.name}"
                )
                
                # Set the positions
                await new_channel.edit(
                    position=position,
                    topic=topic,
                    slowmode_delay=slowmode_delay,
                    nsfw=nsfw
                )
                
                # Delete the old channel
                await channel.delete(reason=f"Channel nuked by {ctx.author.name}")
                
                # Send a confirmation message in the new channel
                embed = discord.Embed(
                    title="💥 Channel Nuked",
                    description=f"This channel has been nuked by {ctx.author.mention}.",
                    color=discord.Color.orange(),
                    timestamp=datetime.utcnow()
                )
                
                embed.set_image(url="https://media.giphy.com/media/HhTXt43pk1I1W/giphy.gif")
                
                await new_channel.send(embed=embed)
                
            except asyncio.TimeoutError:
                await ctx.send("❌ Nuke operation timed out.")
                
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to manage channels.")
        except Exception as e:
            logger.error(f"Error when nuking channel: {str(e)}")
            await ctx.send(f"❌ An error occurred: {str(e)}")

async def setup(bot):
    await bot.add_cog(LockdownCommands(bot)) 