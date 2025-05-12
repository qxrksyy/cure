import discord
from discord.ext import commands
import asyncio
import json
import os
import logging
from typing import Optional, Union

logger = logging.getLogger('bot')

class VoiceChannel:
    """Represents a temporary voice channel"""
    
    def __init__(self, channel_id, owner_id):
        self.channel_id = channel_id
        self.owner_id = owner_id
        self.locked = False
        self.hidden = False
        self.permitted_users = set()
        self.rejected_users = set()
        self.permitted_roles = set()
        self.rejected_roles = set()
        
    def to_dict(self):
        """Convert to dictionary for saving to JSON"""
        return {
            'channel_id': self.channel_id,
            'owner_id': self.owner_id,
            'locked': self.locked,
            'hidden': self.hidden,
            'permitted_users': list(self.permitted_users),
            'rejected_users': list(self.rejected_users),
            'permitted_roles': list(self.permitted_roles),
            'rejected_roles': list(self.rejected_roles)
        }
        
    @classmethod
    def from_dict(cls, data):
        """Create from dictionary loaded from JSON"""
        channel = cls(data['channel_id'], data['owner_id'])
        channel.locked = data.get('locked', False)
        channel.hidden = data.get('hidden', False)
        channel.permitted_users = set(data.get('permitted_users', []))
        channel.rejected_users = set(data.get('rejected_users', []))
        channel.permitted_roles = set(data.get('permitted_roles', []))
        channel.rejected_roles = set(data.get('rejected_roles', []))
        return channel

class VoiceMaster(commands.Cog):
    """Commands for creating temporary voice channels"""
    
    def __init__(self, bot):
        self.bot = bot
        # Use absolute path for data folder
        self.data_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
        self.data_file = os.path.join(self.data_folder, 'voicemaster.json')
        self.active_channels = {}  # channel_id -> VoiceChannel
        self.voice_create_channels = {}  # guild_id -> channel_id
        self.guild_settings = {}  # guild_id -> settings dict
        self.load_data()
        
    def load_data(self):
        """Load voicemaster data from JSON file"""
        if not os.path.exists(self.data_folder):
            os.makedirs(self.data_folder)
            
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                    
                    # Load active channels
                    for channel_id, channel_data in data.get('active_channels', {}).items():
                        self.active_channels[int(channel_id)] = VoiceChannel.from_dict(channel_data)
                        
                    # Load voice create channels
                    for guild_id, channel_id in data.get('voice_create_channels', {}).items():
                        self.voice_create_channels[int(guild_id)] = int(channel_id)
                        
                    # Load guild settings
                    for guild_id, settings in data.get('guild_settings', {}).items():
                        self.guild_settings[int(guild_id)] = settings
            else:
                self.active_channels = {}
                self.voice_create_channels = {}
                self.guild_settings = {}
        except Exception as e:
            logger.error(f"Error loading voicemaster data: {e}")
            self.active_channels = {}
            self.voice_create_channels = {}
            self.guild_settings = {}
            
    def save_data(self):
        """Save voicemaster data to JSON file"""
        try:
            with open(self.data_file, 'w') as f:
                # Convert active channels to dict of dicts
                active_channels_dict = {
                    str(channel_id): channel.to_dict() 
                    for channel_id, channel in self.active_channels.items()
                }
                
                # Convert other dictionaries to use string keys
                voice_create_dict = {
                    str(guild_id): channel_id
                    for guild_id, channel_id in self.voice_create_channels.items()
                }
                
                guild_settings_dict = {
                    str(guild_id): settings
                    for guild_id, settings in self.guild_settings.items()
                }
                
                data = {
                    'active_channels': active_channels_dict,
                    'voice_create_channels': voice_create_dict,
                    'guild_settings': guild_settings_dict
                }
                
                json.dump(data, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving voicemaster data: {e}")

    def get_default_settings(self):
        """Get default settings for a guild"""
        return {
            'category_id': None,
            'default_bitrate': 64000,  # 64 kbps
            'default_region': None,
            'default_role_id': None,
            'channel_limit': 0  # No limit
        }
        
    def get_guild_settings(self, guild_id):
        """Get settings for a specific guild"""
        guild_id = int(guild_id)
        if guild_id not in self.guild_settings:
            self.guild_settings[guild_id] = self.get_default_settings()
            
        return self.guild_settings[guild_id]
        
    async def setup(self, ctx):
        """Initial setup for VoiceMaster"""
        guild_id = ctx.guild.id
        
        # Create category for voice channels
        category = await ctx.guild.create_category("Voice Channels")
        
        # Create "Create Voice Channel" voice channel
        create_channel = await ctx.guild.create_voice_channel("➕ Create Voice Channel", category=category)
        
        # Save settings
        self.voice_create_channels[guild_id] = create_channel.id
        
        settings = self.get_default_settings()
        settings['category_id'] = category.id
        self.guild_settings[guild_id] = settings
        
        self.save_data()
        
        return category, create_channel

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """Handle voice channel joins and leaves"""
        if before.channel == after.channel:
            return  # No channel change
            
        if after.channel and after.channel.id in self.voice_create_channels.values():
            # User joined a create channel, create a new voice channel for them
            await self.create_voice_channel(member, after.channel)
            
        if before.channel and before.channel.id in self.active_channels:
            # Check if channel should be deleted (empty)
            if len(before.channel.members) == 0:
                try:
                    # Get the channel data
                    channel_data = self.active_channels[before.channel.id]
                    
                    # Delete the channel
                    await before.channel.delete(reason="Temporary voice channel empty")
                    
                    # Remove from active channels
                    del self.active_channels[before.channel.id]
                    self.save_data()
                except (discord.Forbidden, discord.HTTPException, discord.NotFound):
                    pass
                    
        # Apply settings for newly joined channels
        if after.channel and after.channel.id in self.active_channels:
            channel_data = self.active_channels[after.channel.id]
            
            # Apply permissions if the channel is locked or hidden
            await self.apply_voice_permissions(after.channel, member, channel_data)
            
            # Apply default role if set
            guild_settings = self.get_guild_settings(member.guild.id)
            default_role_id = guild_settings.get('default_role_id')
            
            if default_role_id:
                try:
                    role = member.guild.get_role(default_role_id)
                    if role:
                        await member.add_roles(role, reason="Joined voice channel with default role")
                except (discord.Forbidden, discord.HTTPException):
                    pass
                    
        # Remove default role if left a managed channel
        if before.channel and before.channel.id in self.active_channels:
            guild_settings = self.get_guild_settings(member.guild.id)
            default_role_id = guild_settings.get('default_role_id')
            
            if default_role_id:
                try:
                    role = member.guild.get_role(default_role_id)
                    if role:
                        # Check if the member is in any other managed voice channels
                        in_other_channel = False
                        for channel_id in self.active_channels.keys():
                            channel = self.bot.get_channel(channel_id)
                            if channel and member in channel.members:
                                in_other_channel = True
                                break
                                
                        if not in_other_channel:
                            await member.remove_roles(role, reason="Left all voice channels with default role")
                except (discord.Forbidden, discord.HTTPException):
                    pass
            
    async def create_voice_channel(self, member, create_channel):
        """Create a new voice channel for a member"""
        guild = member.guild
        guild_id = guild.id
        
        # Get settings
        settings = self.get_guild_settings(guild_id)
        category_id = settings.get('category_id')
        
        # If no category is set, use the create channel's category
        if not category_id:
            category = create_channel.category
        else:
            category = guild.get_channel(category_id)
            if not category:
                category = create_channel.category
                
        # Create the channel
        channel_name = f"{member.display_name}'s Channel"
        
        try:
            new_channel = await guild.create_voice_channel(
                name=channel_name,
                category=category,
                bitrate=settings.get('default_bitrate', 64000),
                user_limit=settings.get('channel_limit', 0),
                rtc_region=settings.get('default_region')
            )
            
            # Set permissions for the owner
            await new_channel.set_permissions(member, connect=True, manage_channels=True)
            
            # Create and store the channel data
            channel_data = VoiceChannel(new_channel.id, member.id)
            self.active_channels[new_channel.id] = channel_data
            
            # Save data
            self.save_data()
            
            # Move the member to the new channel
            await member.move_to(new_channel)
            
            # Apply default role if set
            default_role_id = settings.get('default_role_id')
            if default_role_id:
                try:
                    role = guild.get_role(default_role_id)
                    if role:
                        await member.add_roles(role, reason="Joined voice channel with default role")
                except (discord.Forbidden, discord.HTTPException):
                    pass
                    
            return new_channel
        except (discord.Forbidden, discord.HTTPException) as e:
            logger.error(f"Error creating voice channel: {e}")
            return None

    async def apply_voice_permissions(self, channel, member, channel_data):
        """Apply voice channel permissions based on settings"""
        # Skip if it's the owner
        if member.id == channel_data.owner_id:
            return
            
        # Base permissions
        can_connect = True
        
        # Check if user is rejected
        if member.id in channel_data.rejected_users:
            can_connect = False
            
        # Check if user has a rejected role
        for role in member.roles:
            if role.id in channel_data.rejected_roles:
                can_connect = False
                break
                
        # Check if user is permitted (overrides rejection)
        if member.id in channel_data.permitted_users:
            can_connect = True
            
        # Check if user has a permitted role (overrides rejection)
        for role in member.roles:
            if role.id in channel_data.permitted_roles:
                can_connect = True
                break
                
        # Apply locked status (only if not permitted)
        if channel_data.locked and not can_connect:
            can_connect = False
            
        # Set permissions
        try:
            await channel.set_permissions(member, connect=can_connect)
            
            # If can't connect and in channel, disconnect them
            if not can_connect and member in channel.members:
                await member.move_to(None)
        except (discord.Forbidden, discord.HTTPException) as e:
            logger.error(f"Error setting voice permissions: {e}")

    def get_member_voice_channel(self, member):
        """Get a member's owned voice channel"""
        for channel_id, channel_data in self.active_channels.items():
            if channel_data.owner_id == member.id:
                channel = self.bot.get_channel(channel_id)
                if channel:
                    return channel, channel_data
        return None, None

    def can_manage_channel(self, channel_id, member):
        """Check if a member can manage a voice channel"""
        # Check if channel is an active voice channel
        if channel_id not in self.active_channels:
            return False
            
        # Get channel data
        channel_data = self.active_channels[channel_id]
        
        # Check if member is the owner
        if member.id == channel_data.owner_id:
            return True
            
        # Check if member has manage server permission
        if member.guild_permissions.manage_guild:
            return True
            
        return False
        
    @commands.group(invoke_without_command=True)
    async def voicemaster(self, ctx):
        """Make temporary voice channels in your server!"""
        channel, channel_data = self.get_member_voice_channel(ctx.author)
        
        if not channel:
            embed = discord.Embed(
                title="VoiceMaster",
                description="You don't have an active voice channel!\nJoin the \"Create Voice Channel\" to make your own.",
                color=discord.Color.blue()
            )
        else:
            embed = discord.Embed(
                title="VoiceMaster",
                description=f"Your voice channel: {channel.name}",
                color=discord.Color.green()
            )
            
            status_list = []
            if channel_data.locked:
                status_list.append("🔒 Locked")
            else:
                status_list.append("🔓 Unlocked")
                
            if channel_data.hidden:
                status_list.append("👁️ Hidden")
            else:
                status_list.append("👁️ Visible")
                
            if channel.user_limit > 0:
                status_list.append(f"👥 Limit: {channel.user_limit}")
            else:
                status_list.append("👥 No User Limit")
                
            embed.add_field(name="Status", value=" | ".join(status_list), inline=False)
            
            embed.add_field(
                name="Commands", 
                value="`name` - Rename your channel\n"
                      "`lock/unlock` - Lock/unlock your channel\n"
                      "`ghost/unghost` - Hide/reveal your channel\n"
                      "`limit` - Set user limit\n"
                      "`permit/reject` - Allow/deny users or roles\n"
                      "`transfer` - Transfer ownership\n"
                      "`bitrate` - Change bitrate\n"
                      "`claim` - Claim an inactive channel",
                inline=False
            )
            
        await ctx.send(embed=embed)
        
    @voicemaster.command(name="setup")
    @commands.has_permissions(manage_guild=True)
    async def voicemaster_setup(self, ctx):
        """Begin VoiceMaster server configuration setup"""
        guild_id = ctx.guild.id
        
        # Check if already set up
        if guild_id in self.voice_create_channels:
            channel_id = self.voice_create_channels[guild_id]
            channel = ctx.guild.get_channel(channel_id)
            
            if channel:
                embed = discord.Embed(
                    title="VoiceMaster Already Set Up",
                    description=f"VoiceMaster is already set up with the \"Create Voice Channel\" at {channel.mention}.\n\nUse `{ctx.prefix}voicemaster reset` to reset the configuration if needed.",
                    color=discord.Color.orange()
                )
                await ctx.send(embed=embed)
                return
                
        # Begin setup
        embed = discord.Embed(
            title="VoiceMaster Setup",
            description="Setting up VoiceMaster...",
            color=discord.Color.blue()
        )
        message = await ctx.send(embed=embed)
        
        # Do the setup
        try:
            category, create_channel = await self.setup(ctx)
            
            embed = discord.Embed(
                title="VoiceMaster Setup Complete",
                description=f"Setup complete! Join {create_channel.mention} to create your own voice channel.",
                color=discord.Color.green()
            )
            embed.add_field(
                name="Configuration",
                value=f"Category: {category.name}\nCreate Channel: {create_channel.name}",
                inline=False
            )
            embed.add_field(
                name="Next Steps",
                value=f"Use `{ctx.prefix}voicemaster category` to change the category\n"
                      f"Use `{ctx.prefix}voicemaster defaultbitrate` to change the default bitrate\n"
                      f"Use `{ctx.prefix}voicemaster defaultregion` to change the default region\n"
                      f"Use `{ctx.prefix}voicemaster defaultrole` to set a role for voice channel users",
                inline=False
            )
            
            await message.edit(embed=embed)
        except Exception as e:
            logger.error(f"Error setting up VoiceMaster: {e}")
            embed = discord.Embed(
                title="VoiceMaster Setup Failed",
                description=f"Setup failed due to an error: {str(e)}",
                color=discord.Color.red()
            )
            await message.edit(embed=embed)
            
    @voicemaster.command(name="reset")
    @commands.has_permissions(manage_guild=True)
    async def voicemaster_reset(self, ctx):
        """Reset server configuration for VoiceMaster"""
        guild_id = ctx.guild.id
        
        # Check if set up
        if guild_id not in self.voice_create_channels:
            embed = discord.Embed(
                title="VoiceMaster Not Set Up",
                description=f"VoiceMaster is not set up in this server. Use `{ctx.prefix}voicemaster setup` to set it up.",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed)
            return
            
        # Confirm reset
        embed = discord.Embed(
            title="Confirm Reset",
            description="Are you sure you want to reset the VoiceMaster configuration? All active voice channels will be unmanaged but not deleted.",
            color=discord.Color.orange()
        )
        message = await ctx.send(embed=embed)
        
        # Add reaction confirmation
        await message.add_reaction("✅")
        await message.add_reaction("❌")
        
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == message.id
            
        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=check)
            
            if str(reaction.emoji) == "✅":
                # Remove active channels for this guild
                for channel_id in list(self.active_channels.keys()):
                    channel = self.bot.get_channel(channel_id)
                    if channel and channel.guild.id == guild_id:
                        del self.active_channels[channel_id]
                
                # Remove guild settings
                if guild_id in self.guild_settings:
                    del self.guild_settings[guild_id]
                    
                # Remove voice create channel
                if guild_id in self.voice_create_channels:
                    del self.voice_create_channels[guild_id]
                    
                # Save data
                self.save_data()
                
                embed = discord.Embed(
                    title="VoiceMaster Reset",
                    description="VoiceMaster configuration has been reset for this server.",
                    color=discord.Color.green()
                )
                await message.edit(embed=embed)
            else:
                embed = discord.Embed(
                    title="Reset Cancelled",
                    description="VoiceMaster configuration reset was cancelled.",
                    color=discord.Color.blue()
                )
                await message.edit(embed=embed)
        except asyncio.TimeoutError:
            embed = discord.Embed(
                title="Reset Cancelled",
                description="VoiceMaster configuration reset was cancelled due to timeout.",
                color=discord.Color.blue()
            )
            await message.edit(embed=embed)
            
    @voicemaster.command(name="category")
    @commands.has_permissions(manage_guild=True)
    async def voicemaster_category(self, ctx, *, channel: discord.CategoryChannel = None):
        """Redirect voice channels to custom category"""
        guild_id = ctx.guild.id
        
        # Check if set up
        if guild_id not in self.voice_create_channels:
            embed = discord.Embed(
                title="VoiceMaster Not Set Up",
                description=f"VoiceMaster is not set up in this server. Use `{ctx.prefix}voicemaster setup` to set it up.",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed)
            return
            
        settings = self.get_guild_settings(guild_id)
        
        if channel:
            # Update category
            settings['category_id'] = channel.id
            self.save_data()
            
            embed = discord.Embed(
                title="Category Updated",
                description=f"New voice channels will now be created in the category: {channel.name}",
                color=discord.Color.green()
            )
        else:
            # Show current category
            category_id = settings.get('category_id')
            category = None
            
            if category_id:
                category = ctx.guild.get_channel(category_id)
                
            if category:
                embed = discord.Embed(
                    title="Current Voice Channel Category",
                    description=f"New voice channels are being created in: {category.name}",
                    color=discord.Color.blue()
                )
            else:
                embed = discord.Embed(
                    title="No Category Set",
                    description=f"No custom category is set. Specify a category to update the setting.",
                    color=discord.Color.orange()
                )
                
        await ctx.send(embed=embed)
        
    @voicemaster.command(name="defaultbitrate")
    @commands.has_permissions(manage_guild=True)
    async def voicemaster_defaultbitrate(self, ctx, bitrate: int = None):
        """Edit default bitrate for new Voice Channels"""
        guild_id = ctx.guild.id
        
        # Check if set up
        if guild_id not in self.voice_create_channels:
            embed = discord.Embed(
                title="VoiceMaster Not Set Up",
                description=f"VoiceMaster is not set up in this server. Use `{ctx.prefix}voicemaster setup` to set it up.",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed)
            return
            
        settings = self.get_guild_settings(guild_id)
        
        if bitrate is not None:
            # Validate bitrate
            min_bitrate = 8000   # 8 kbps
            max_bitrate = ctx.guild.premium_tier * 128000 or 96000  # Based on guild premium tier
            
            if bitrate < min_bitrate:
                bitrate = min_bitrate
            elif bitrate > max_bitrate:
                bitrate = max_bitrate
                
            # Update bitrate
            settings['default_bitrate'] = bitrate
            self.save_data()
            
            embed = discord.Embed(
                title="Default Bitrate Updated",
                description=f"New voice channels will now be created with a bitrate of {bitrate//1000} kbps",
                color=discord.Color.green()
            )
        else:
            # Show current bitrate
            current_bitrate = settings.get('default_bitrate', 64000)
            
            embed = discord.Embed(
                title="Current Default Bitrate",
                description=f"New voice channels are being created with a bitrate of {current_bitrate//1000} kbps",
                color=discord.Color.blue()
            )
                
        await ctx.send(embed=embed)
        
    @voicemaster.command(name="defaultregion")
    @commands.has_permissions(manage_guild=True)
    async def voicemaster_defaultregion(self, ctx, region: str = None):
        """Edit default region for new Voice Channels"""
        guild_id = ctx.guild.id
        
        # Check if set up
        if guild_id not in self.voice_create_channels:
            embed = discord.Embed(
                title="VoiceMaster Not Set Up",
                description=f"VoiceMaster is not set up in this server. Use `{ctx.prefix}voicemaster setup` to set it up.",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed)
            return
            
        settings = self.get_guild_settings(guild_id)
        
        # Valid regions
        valid_regions = ['automatic', 'brazil', 'hongkong', 'india', 'japan', 'rotterdam', 'russia', 'singapore', 'southafrica', 'sydney', 'us-central', 'us-east', 'us-south', 'us-west']
        
        if region is not None:
            # Validate region
            if region.lower() not in valid_regions and region.lower() != 'none':
                embed = discord.Embed(
                    title="Invalid Region",
                    description=f"Invalid region specified. Valid regions are: {', '.join(valid_regions)}",
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed)
                return
                
            # Update region
            if region.lower() == 'none' or region.lower() == 'automatic':
                settings['default_region'] = None
            else:
                settings['default_region'] = region.lower()
                
            self.save_data()
            
            region_display = region.lower() if region.lower() != 'none' else 'Automatic'
            
            embed = discord.Embed(
                title="Default Region Updated",
                description=f"New voice channels will now be created with region: {region_display}",
                color=discord.Color.green()
            )
        else:
            # Show current region
            current_region = settings.get('default_region')
            
            if current_region:
                embed = discord.Embed(
                    title="Current Default Region",
                    description=f"New voice channels are being created with region: {current_region}",
                    color=discord.Color.blue()
                )
            else:
                embed = discord.Embed(
                    title="Current Default Region",
                    description=f"New voice channels are being created with automatic region selection",
                    color=discord.Color.blue()
                )
                
        await ctx.send(embed=embed)
        
    @voicemaster.command(name="defaultrole")
    @commands.has_permissions(manage_guild=True, manage_roles=True)
    async def voicemaster_defaultrole(self, ctx, *, role: discord.Role = None):
        """Set a role that members get for being in a VM channel"""
        guild_id = ctx.guild.id
        
        # Check if set up
        if guild_id not in self.voice_create_channels:
            embed = discord.Embed(
                title="VoiceMaster Not Set Up",
                description=f"VoiceMaster is not set up in this server. Use `{ctx.prefix}voicemaster setup` to set it up.",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed)
            return
            
        settings = self.get_guild_settings(guild_id)
        
        if role:
            # Validate role
            if role.is_default() or role.is_bot_managed() or role.is_integration() or role.is_premium_subscriber():
                embed = discord.Embed(
                    title="Invalid Role",
                    description="You cannot use this role as it is a system role.",
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed)
                return
                
            if role.position >= ctx.guild.me.top_role.position:
                embed = discord.Embed(
                    title="Invalid Role",
                    description="I cannot assign this role as it is higher than or equal to my highest role.",
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed)
                return
                
            # Update default role
            settings['default_role_id'] = role.id
            self.save_data()
            
            embed = discord.Embed(
                title="Default Role Updated",
                description=f"Members in voice channels will now be assigned the role: {role.mention}",
                color=discord.Color.green()
            )
        else:
            # Remove default role if it's currently set
            if 'default_role_id' in settings:
                current_role_id = settings.get('default_role_id')
                current_role = ctx.guild.get_role(current_role_id) if current_role_id else None
                
                settings['default_role_id'] = None
                self.save_data()
                
                if current_role:
                    embed = discord.Embed(
                        title="Default Role Removed",
                        description=f"Members will no longer be assigned the {current_role.mention} role when in voice channels.",
                        color=discord.Color.blue()
                    )
                else:
                    embed = discord.Embed(
                        title="Default Role Removed",
                        description="Default role setting has been cleared.",
                        color=discord.Color.blue()
                    )
            else:
                embed = discord.Embed(
                    title="No Default Role Set",
                    description="There is currently no default role configured.",
                    color=discord.Color.orange()
                )
                
        await ctx.send(embed=embed)
        
    @voicemaster.command(name="configuration")
    async def voicemaster_configuration(self, ctx):
        """See current configuration for current voice channel"""
        channel, channel_data = self.get_member_voice_channel(ctx.author)
        
        if not channel:
            embed = discord.Embed(
                title="No Voice Channel",
                description="You don't have an active voice channel to configure.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        embed = discord.Embed(
            title=f"Voice Channel Configuration: {channel.name}",
            color=discord.Color.blue()
        )
        
        # Basic settings
        embed.add_field(name="Owner", value=f"<@{channel_data.owner_id}>", inline=True)
        embed.add_field(name="Bitrate", value=f"{channel.bitrate//1000} kbps", inline=True)
        embed.add_field(name="User Limit", value=str(channel.user_limit) if channel.user_limit > 0 else "None", inline=True)
        
        # Status
        status_list = []
        status_list.append("🔒 Locked" if channel_data.locked else "🔓 Unlocked")
        status_list.append("👁️ Hidden" if channel_data.hidden else "👁️ Visible")
        
        embed.add_field(name="Status", value=" | ".join(status_list), inline=False)
        
        # Permitted users
        permitted_users = []
        for user_id in channel_data.permitted_users:
            permitted_users.append(f"<@{user_id}>")
            
        if permitted_users:
            embed.add_field(name="Permitted Users", value=", ".join(permitted_users), inline=False)
        
        # Permitted roles
        permitted_roles = []
        for role_id in channel_data.permitted_roles:
            role = ctx.guild.get_role(role_id)
            if role:
                permitted_roles.append(role.mention)
            
        if permitted_roles:
            embed.add_field(name="Permitted Roles", value=", ".join(permitted_roles), inline=False)
        
        # Rejected users
        rejected_users = []
        for user_id in channel_data.rejected_users:
            rejected_users.append(f"<@{user_id}>")
            
        if rejected_users:
            embed.add_field(name="Rejected Users", value=", ".join(rejected_users), inline=False)
        
        # Rejected roles
        rejected_roles = []
        for role_id in channel_data.rejected_roles:
            role = ctx.guild.get_role(role_id)
            if role:
                rejected_roles.append(role.mention)
            
        if rejected_roles:
            embed.add_field(name="Rejected Roles", value=", ".join(rejected_roles), inline=False)
            
        await ctx.send(embed=embed)
        
    @voicemaster.command(name="name")
    async def voicemaster_name(self, ctx, *, name: str):
        """Rename your voice channel"""
        channel, channel_data = self.get_member_voice_channel(ctx.author)
        
        if not channel:
            embed = discord.Embed(
                title="No Voice Channel",
                description="You don't have an active voice channel to rename.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        try:
            old_name = channel.name
            await channel.edit(name=name)
            
            embed = discord.Embed(
                title="Channel Renamed",
                description=f"Channel renamed from \"{old_name}\" to \"{name}\"",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
        except discord.Forbidden:
            embed = discord.Embed(
                title="Permission Error",
                description="I don't have permission to rename this channel.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
        except discord.HTTPException as e:
            embed = discord.Embed(
                title="Rename Failed",
                description=f"Failed to rename channel: {str(e)}",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            
    @voicemaster.command(name="lock")
    async def voicemaster_lock(self, ctx):
        """Lock your voice channel"""
        channel, channel_data = self.get_member_voice_channel(ctx.author)
        
        if not channel:
            embed = discord.Embed(
                title="No Voice Channel",
                description="You don't have an active voice channel to lock.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        if channel_data.locked:
            embed = discord.Embed(
                title="Already Locked",
                description="Your voice channel is already locked.",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed)
            return
            
        # Lock the channel
        channel_data.locked = True
        self.save_data()
        
        # Update channel permissions
        everyone_role = ctx.guild.default_role
        try:
            # Set permissions for @everyone to deny connect
            await channel.set_permissions(everyone_role, connect=False)
            
            # Set permissions for current members to allow connect
            for member in channel.members:
                if member.id != channel_data.owner_id and member.id not in channel_data.rejected_users:
                    await channel.set_permissions(member, connect=True)
                    
            embed = discord.Embed(
                title="Channel Locked",
                description="Your voice channel has been locked. Only you and current members can join now.",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
        except discord.Forbidden:
            embed = discord.Embed(
                title="Permission Error",
                description="I don't have permission to lock this channel.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
        except discord.HTTPException as e:
            embed = discord.Embed(
                title="Lock Failed",
                description=f"Failed to lock channel: {str(e)}",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            
    @voicemaster.command(name="unlock")
    async def voicemaster_unlock(self, ctx):
        """Unlock your voice channel"""
        channel, channel_data = self.get_member_voice_channel(ctx.author)
        
        if not channel:
            embed = discord.Embed(
                title="No Voice Channel",
                description="You don't have an active voice channel to unlock.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        if not channel_data.locked:
            embed = discord.Embed(
                title="Already Unlocked",
                description="Your voice channel is already unlocked.",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed)
            return
            
        # Unlock the channel
        channel_data.locked = False
        self.save_data()
        
        # Update channel permissions
        everyone_role = ctx.guild.default_role
        try:
            # Reset permissions for @everyone
            await channel.set_permissions(everyone_role, connect=None)
            
            # Keep other specific permissions (rejected users/roles)
            for user_id in channel_data.rejected_users:
                user = ctx.guild.get_member(user_id)
                if user:
                    await channel.set_permissions(user, connect=False)
                    
            for role_id in channel_data.rejected_roles:
                role = ctx.guild.get_role(role_id)
                if role:
                    await channel.set_permissions(role, connect=False)
                    
            for user_id in channel_data.permitted_users:
                user = ctx.guild.get_member(user_id)
                if user:
                    await channel.set_permissions(user, connect=True)
                    
            for role_id in channel_data.permitted_roles:
                role = ctx.guild.get_role(role_id)
                if role:
                    await channel.set_permissions(role, connect=True)
                    
            embed = discord.Embed(
                title="Channel Unlocked",
                description="Your voice channel has been unlocked. Anyone can join now.",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
        except discord.Forbidden:
            embed = discord.Embed(
                title="Permission Error",
                description="I don't have permission to unlock this channel.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
        except discord.HTTPException as e:
            embed = discord.Embed(
                title="Unlock Failed",
                description=f"Failed to unlock channel: {str(e)}",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            
    @voicemaster.command(name="ghost")
    async def voicemaster_ghost(self, ctx):
        """Hide your voice channel"""
        channel, channel_data = self.get_member_voice_channel(ctx.author)
        
        if not channel:
            embed = discord.Embed(
                title="No Voice Channel",
                description="You don't have an active voice channel to hide.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        if channel_data.hidden:
            embed = discord.Embed(
                title="Already Hidden",
                description="Your voice channel is already hidden.",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed)
            return
            
        # Hide the channel
        channel_data.hidden = True
        self.save_data()
        
        # Update channel permissions
        everyone_role = ctx.guild.default_role
        try:
            # Set permissions for @everyone to deny view channel
            await channel.set_permissions(everyone_role, view_channel=False)
            
            # Set permissions for current members to allow view
            for member in channel.members:
                if member.id != channel_data.owner_id:
                    await channel.set_permissions(member, view_channel=True)
                    
            embed = discord.Embed(
                title="Channel Hidden",
                description="Your voice channel has been hidden. Only you and current members can see it now.",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
        except discord.Forbidden:
            embed = discord.Embed(
                title="Permission Error",
                description="I don't have permission to hide this channel.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
        except discord.HTTPException as e:
            embed = discord.Embed(
                title="Hide Failed",
                description=f"Failed to hide channel: {str(e)}",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            
    @voicemaster.command(name="unghost")
    async def voicemaster_unghost(self, ctx):
        """Reveal your voice channel"""
        channel, channel_data = self.get_member_voice_channel(ctx.author)
        
        if not channel:
            embed = discord.Embed(
                title="No Voice Channel",
                description="You don't have an active voice channel to reveal.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        if not channel_data.hidden:
            embed = discord.Embed(
                title="Already Visible",
                description="Your voice channel is already visible.",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed)
            return
            
        # Reveal the channel
        channel_data.hidden = False
        self.save_data()
        
        # Update channel permissions
        everyone_role = ctx.guild.default_role
        try:
            # Reset permissions for @everyone
            await channel.set_permissions(everyone_role, view_channel=None)
            
            embed = discord.Embed(
                title="Channel Revealed",
                description="Your voice channel has been revealed. Everyone can see it now.",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
        except discord.Forbidden:
            embed = discord.Embed(
                title="Permission Error",
                description="I don't have permission to reveal this channel.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
        except discord.HTTPException as e:
            embed = discord.Embed(
                title="Reveal Failed",
                description=f"Failed to reveal channel: {str(e)}",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)

    @voicemaster.command(name="limit")
    async def voicemaster_limit(self, ctx, limit: int = None):
        """Edit user limit of your voice channel"""
        channel, channel_data = self.get_member_voice_channel(ctx.author)
        
        if not channel:
            embed = discord.Embed(
                title="No Voice Channel",
                description="You don't have an active voice channel to set a limit for.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        # Set or display the limit
        if limit is not None:
            # Validate limit
            if limit < 0:
                limit = 0
            elif limit > 99:
                limit = 99
                
            # Update the channel
            try:
                await channel.edit(user_limit=limit)
                
                if limit == 0:
                    description = "User limit removed. Anyone can join (up to Discord's limit)."
                else:
                    description = f"User limit set to {limit} members."
                    
                embed = discord.Embed(
                    title="User Limit Updated",
                    description=description,
                    color=discord.Color.green()
                )
                await ctx.send(embed=embed)
            except discord.Forbidden:
                embed = discord.Embed(
                    title="Permission Error",
                    description="I don't have permission to edit this channel.",
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed)
            except discord.HTTPException as e:
                embed = discord.Embed(
                    title="Update Failed",
                    description=f"Failed to update user limit: {str(e)}",
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed)
        else:
            # Display current limit
            current_limit = channel.user_limit
            
            if current_limit == 0:
                description = "There is currently no user limit set."
            else:
                description = f"The current user limit is {current_limit} members."
                
            embed = discord.Embed(
                title="Current User Limit",
                description=description,
                color=discord.Color.blue()
            )
            embed.add_field(
                name="Usage", 
                value=f"Use `{ctx.prefix}voicemaster limit <number>` to set a limit\n"
                      f"Use `{ctx.prefix}voicemaster limit 0` to remove the limit",
                inline=False
            )
            await ctx.send(embed=embed)
            
    @voicemaster.command(name="bitrate")
    async def voicemaster_bitrate(self, ctx, bitrate: int = None):
        """Edit bitrate of your voice channel"""
        channel, channel_data = self.get_member_voice_channel(ctx.author)
        
        if not channel:
            embed = discord.Embed(
                title="No Voice Channel",
                description="You don't have an active voice channel to set a bitrate for.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        # Set or display the bitrate
        if bitrate is not None:
            # Validate bitrate
            min_bitrate = 8000   # 8 kbps
            max_bitrate = ctx.guild.premium_tier * 128000 or 96000  # Based on guild premium tier
            
            if bitrate < min_bitrate:
                bitrate = min_bitrate
            elif bitrate > max_bitrate:
                bitrate = max_bitrate
                
            # Update the channel
            try:
                await channel.edit(bitrate=bitrate)
                
                embed = discord.Embed(
                    title="Bitrate Updated",
                    description=f"Bitrate set to {bitrate//1000} kbps.",
                    color=discord.Color.green()
                )
                await ctx.send(embed=embed)
            except discord.Forbidden:
                embed = discord.Embed(
                    title="Permission Error",
                    description="I don't have permission to edit this channel.",
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed)
            except discord.HTTPException as e:
                embed = discord.Embed(
                    title="Update Failed",
                    description=f"Failed to update bitrate: {str(e)}",
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed)
        else:
            # Display current bitrate
            current_bitrate = channel.bitrate
            
            embed = discord.Embed(
                title="Current Bitrate",
                description=f"The current bitrate is {current_bitrate//1000} kbps.",
                color=discord.Color.blue()
            )
            max_bitrate = ctx.guild.premium_tier * 128000 or 96000
            embed.add_field(
                name="Usage", 
                value=f"Use `{ctx.prefix}voicemaster bitrate <number>` to set a bitrate\n"
                      f"Your server can set up to {max_bitrate//1000} kbps based on boost level",
                inline=False
            )
            await ctx.send(embed=embed)
            
    @voicemaster.command(name="permit")
    async def voicemaster_permit(self, ctx, target: Union[discord.Member, discord.Role]):
        """Permit a member or role to join your VC"""
        channel, channel_data = self.get_member_voice_channel(ctx.author)
        
        if not channel:
            embed = discord.Embed(
                title="No Voice Channel",
                description="You don't have an active voice channel to set permissions for.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        try:
            # Permit the target
            if isinstance(target, discord.Member):
                # It's a member
                user_id = target.id
                
                # Remove from rejected if present
                if user_id in channel_data.rejected_users:
                    channel_data.rejected_users.remove(user_id)
                    
                # Add to permitted if not owner and not already permitted
                if user_id != channel_data.owner_id and user_id not in channel_data.permitted_users:
                    channel_data.permitted_users.add(user_id)
                    
                # Set permission
                await channel.set_permissions(target, connect=True)
                
                embed = discord.Embed(
                    title="Permission Granted",
                    description=f"{target.mention} can now join your voice channel.",
                    color=discord.Color.green()
                )
            else:
                # It's a role
                role_id = target.id
                
                # Don't permit @everyone
                if target.is_default():
                    embed = discord.Embed(
                        title="Invalid Role",
                        description="You cannot permit the @everyone role. Use `unlock` instead.",
                        color=discord.Color.red()
                    )
                    await ctx.send(embed=embed)
                    return
                    
                # Remove from rejected if present
                if role_id in channel_data.rejected_roles:
                    channel_data.rejected_roles.remove(role_id)
                    
                # Add to permitted if not already permitted
                if role_id not in channel_data.permitted_roles:
                    channel_data.permitted_roles.add(role_id)
                    
                # Set permission
                await channel.set_permissions(target, connect=True)
                
                embed = discord.Embed(
                    title="Permission Granted",
                    description=f"Members with the {target.mention} role can now join your voice channel.",
                    color=discord.Color.green()
                )
                
            # Save data
            self.save_data()
            
            await ctx.send(embed=embed)
        except discord.Forbidden:
            embed = discord.Embed(
                title="Permission Error",
                description="I don't have permission to edit this channel's permissions.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
        except discord.HTTPException as e:
            embed = discord.Embed(
                title="Update Failed",
                description=f"Failed to update permissions: {str(e)}",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            
    @voicemaster.command(name="reject")
    async def voicemaster_reject(self, ctx, target: Union[discord.Member, discord.Role]):
        """Reject a member or role from joining your VC"""
        channel, channel_data = self.get_member_voice_channel(ctx.author)
        
        if not channel:
            embed = discord.Embed(
                title="No Voice Channel",
                description="You don't have an active voice channel to set permissions for.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        try:
            # Reject the target
            if isinstance(target, discord.Member):
                # It's a member
                user_id = target.id
                
                # Can't reject owner
                if user_id == channel_data.owner_id:
                    embed = discord.Embed(
                        title="Invalid Target",
                        description="You cannot reject yourself from your own channel.",
                        color=discord.Color.red()
                    )
                    await ctx.send(embed=embed)
                    return
                    
                # Remove from permitted if present
                if user_id in channel_data.permitted_users:
                    channel_data.permitted_users.remove(user_id)
                    
                # Add to rejected if not already rejected
                if user_id not in channel_data.rejected_users:
                    channel_data.rejected_users.add(user_id)
                    
                # Set permission
                await channel.set_permissions(target, connect=False)
                
                # Disconnect user if in channel
                if target in channel.members:
                    await target.move_to(None)
                    
                embed = discord.Embed(
                    title="Permission Denied",
                    description=f"{target.mention} can no longer join your voice channel.",
                    color=discord.Color.green()
                )
            else:
                # It's a role
                role_id = target.id
                
                # If it's @everyone role, lock the channel instead
                if target.is_default():
                    embed = discord.Embed(
                        title="Invalid Role",
                        description="To reject everyone, use the `lock` command instead.",
                        color=discord.Color.red()
                    )
                    await ctx.send(embed=embed)
                    return
                    
                # Remove from permitted if present
                if role_id in channel_data.permitted_roles:
                    channel_data.permitted_roles.remove(role_id)
                    
                # Add to rejected if not already rejected
                if role_id not in channel_data.rejected_roles:
                    channel_data.rejected_roles.add(role_id)
                    
                # Set permission
                await channel.set_permissions(target, connect=False)
                
                # Disconnect users with this role if in channel
                for member in channel.members:
                    if target in member.roles and member.id != channel_data.owner_id:
                        # Check if they don't have permitted individual access
                        if member.id not in channel_data.permitted_users:
                            await member.move_to(None)
                    
                embed = discord.Embed(
                    title="Permission Denied",
                    description=f"Members with the {target.mention} role can no longer join your voice channel.",
                    color=discord.Color.green()
                )
                
            # Save data
            self.save_data()
            
            await ctx.send(embed=embed)
        except discord.Forbidden:
            embed = discord.Embed(
                title="Permission Error",
                description="I don't have permission to edit this channel's permissions.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
        except discord.HTTPException as e:
            embed = discord.Embed(
                title="Update Failed",
                description=f"Failed to update permissions: {str(e)}",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            
    @voicemaster.command(name="claim")
    async def voicemaster_claim(self, ctx):
        """Claim an inactive voice channel"""
        # Check if the user is in a voice channel
        if not ctx.author.voice or not ctx.author.voice.channel:
            embed = discord.Embed(
                title="Not in Voice",
                description="You must be in a voice channel to claim it.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        current_channel = ctx.author.voice.channel
        
        # Check if the channel is a managed voice channel
        if current_channel.id not in self.active_channels:
            embed = discord.Embed(
                title="Not Claimable",
                description="This channel is not a VoiceMaster channel and cannot be claimed.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        channel_data = self.active_channels[current_channel.id]
        
        # Check if user is already the owner
        if channel_data.owner_id == ctx.author.id:
            embed = discord.Embed(
                title="Already Owner",
                description="You are already the owner of this voice channel.",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed)
            return
            
        # Check if owner is present in the channel
        owner_present = False
        owner_member = ctx.guild.get_member(channel_data.owner_id)
        
        if owner_member and owner_member in current_channel.members:
            owner_present = True
            
        # If owner is present, deny claim
        if owner_present:
            embed = discord.Embed(
                title="Cannot Claim",
                description="The owner is still in this channel. You cannot claim it.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        # Claim the channel
        old_owner_id = channel_data.owner_id
        channel_data.owner_id = ctx.author.id
        
        # Update permissions
        await current_channel.set_permissions(ctx.author, connect=True, manage_channels=True)
        
        # If old owner still has a permission override, remove it
        old_owner = ctx.guild.get_member(old_owner_id)
        if old_owner:
            current_overwrite = current_channel.overwrites_for(old_owner)
            if current_overwrite.manage_channels:
                await current_channel.set_permissions(old_owner, manage_channels=None)
        
        self.save_data()
        
        embed = discord.Embed(
            title="Channel Claimed",
            description="You are now the owner of this voice channel!",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
        
    @voicemaster.command(name="transfer")
    async def voicemaster_transfer(self, ctx, member: discord.Member):
        """Transfer ownership of your channel to another member"""
        channel, channel_data = self.get_member_voice_channel(ctx.author)
        
        if not channel:
            embed = discord.Embed(
                title="No Voice Channel",
                description="You don't have an active voice channel to transfer.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        # Can't transfer to yourself
        if member.id == ctx.author.id:
            embed = discord.Embed(
                title="Invalid Target",
                description="You can't transfer the channel to yourself.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        # Member must be in the channel
        if member not in channel.members:
            embed = discord.Embed(
                title="Member Not Present",
                description="The member must be in your voice channel to transfer ownership.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        # Transfer ownership
        try:
            old_owner_id = channel_data.owner_id
            channel_data.owner_id = member.id
            
            # Update permissions
            await channel.set_permissions(member, connect=True, manage_channels=True)
            await channel.set_permissions(ctx.author, manage_channels=None)
            
            self.save_data()
            
            embed = discord.Embed(
                title="Ownership Transferred",
                description=f"Ownership of the channel has been transferred to {member.mention}.",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
        except discord.Forbidden:
            embed = discord.Embed(
                title="Permission Error",
                description="I don't have permission to edit this channel's permissions.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
        except discord.HTTPException as e:
            embed = discord.Embed(
                title="Transfer Failed",
                description=f"Failed to transfer ownership: {str(e)}",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)

    def cleanup_non_existent_channels(self):
        """Clean up channels that no longer exist from the active channels list"""
        to_remove = []
        for channel_id in self.active_channels:
            channel = self.bot.get_channel(channel_id)
            if not channel:
                to_remove.append(channel_id)
                
        for channel_id in to_remove:
            logger.info(f"Removing non-existent channel {channel_id} from active channels")
            del self.active_channels[channel_id]
            
        # Also check that voice create channels still exist
        guild_ids_to_remove = []
        for guild_id, channel_id in self.voice_create_channels.items():
            channel = self.bot.get_channel(channel_id)
            if not channel:
                guild_ids_to_remove.append(guild_id)
                
        for guild_id in guild_ids_to_remove:
            logger.info(f"Removing non-existent create channel for guild {guild_id}")
            del self.voice_create_channels[guild_id]
            
        # Save if we made changes
        if to_remove or guild_ids_to_remove:
            self.save_data()
    
    # Run cleanup when bot is ready
    @commands.Cog.listener()
    async def on_ready(self):
        """Called when the bot is ready"""
        self.cleanup_non_existent_channels()
        logger.info("VoiceMaster cog is ready, data cleaned up")

async def setup(bot):
    cog = VoiceMaster(bot)
    await bot.add_cog(cog) 