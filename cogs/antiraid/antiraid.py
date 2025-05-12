import discord
from discord.ext import commands
import asyncio
from datetime import datetime, timedelta
import logging
import json
import os
from .mass_join_handler import MassJoinHandler

logger = logging.getLogger('bot')

class AntiRaid(commands.Cog):
    """Commands for protecting against server raids"""
    
    def __init__(self, bot):
        self.bot = bot
        self.raid_settings = {}
        self.whitelist = {}
        self.raid_state = {}
        self.config_path = "data/antiraid"
        
        # Create directory if it doesn't exist
        os.makedirs(self.config_path, exist_ok=True)
        
        # Load settings
        self._load_settings()
        
        # Initialize mass join handler
        self.mass_join_handler = MassJoinHandler(self)
        
    def _load_settings(self):
        """Load antiraid settings from file"""
        try:
            if os.path.exists(f"{self.config_path}/settings.json"):
                with open(f"{self.config_path}/settings.json", "r") as f:
                    self.raid_settings = json.load(f)
            
            if os.path.exists(f"{self.config_path}/whitelist.json"):
                with open(f"{self.config_path}/whitelist.json", "r") as f:
                    self.whitelist = json.load(f)
                    
            if os.path.exists(f"{self.config_path}/raid_state.json"):
                with open(f"{self.config_path}/raid_state.json", "r") as f:
                    self.raid_state = json.load(f)
        except Exception as e:
            logger.error(f"Error loading antiraid settings: {str(e)}")
            
    def _save_settings(self):
        """Save antiraid settings to file"""
        try:
            with open(f"{self.config_path}/settings.json", "w") as f:
                json.dump(self.raid_settings, f, indent=4)
                
            with open(f"{self.config_path}/whitelist.json", "w") as f:
                json.dump(self.whitelist, f, indent=4)
                
            with open(f"{self.config_path}/raid_state.json", "w") as f:
                json.dump(self.raid_state, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving antiraid settings: {str(e)}")
    
    def _get_guild_settings(self, guild_id):
        """Get guild antiraid settings"""
        guild_id = str(guild_id)
        if guild_id not in self.raid_settings:
            self.raid_settings[guild_id] = {
                "newaccounts": {
                    "enabled": False,
                    "action": "kick",  # kick, ban, timeout
                    "min_age": 7,  # days
                    "timeout_duration": 24  # hours (if action is timeout)
                },
                "massjoin": {
                    "enabled": False,
                    "threshold": 5,  # number of joins
                    "timeframe": 10,  # seconds
                    "action": "lockdown"  # lockdown or verification
                },
                "avatar": {
                    "enabled": False,
                    "action": "kick"  # kick, ban, timeout
                }
            }
            self._save_settings()
        return self.raid_settings[guild_id]
        
    def _get_guild_whitelist(self, guild_id):
        """Get guild whitelist"""
        guild_id = str(guild_id)
        if guild_id not in self.whitelist:
            self.whitelist[guild_id] = []
            self._save_settings()
        return self.whitelist[guild_id]
        
    def _get_guild_raid_state(self, guild_id):
        """Get guild raid state"""
        guild_id = str(guild_id)
        if guild_id not in self.raid_state:
            self.raid_state[guild_id] = {
                "active": False,
                "started_at": None,
                "reason": None
            }
            self._save_settings()
        return self.raid_state[guild_id]
    
    @commands.group(name="antiraid", invoke_without_command=True)
    async def antiraid(self, ctx):
        """Configure protection against potential raids"""
        embed = discord.Embed(
            title="AntiRaid Configuration",
            description="Configure protection against potential raids",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(
            name="Available Commands",
            value=(
                "`antiraid newaccounts` - Punish new registered accounts\n"
                "`antiraid massjoin` - Protect server against mass bot raids\n"
                "`antiraid avatar` - Punish accounts without a profile picture\n"
                "`antiraid config` - View server antiraid configuration\n"
                "`antiraid state` - Turn off server's raid state\n"
                "`antiraid wl` - Create a one-time whitelist to allow a user to join\n"
                "`antiraid whitelist view` - View all current antinuke whitelists"
            ),
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @antiraid.command(name="newaccounts")
    @commands.has_permissions(manage_guild=True)
    async def antiraid_newaccounts(self, ctx, setting=None, *, flags=None):
        """Punish new registered accounts"""
        guild_id = str(ctx.guild.id)
        settings = self._get_guild_settings(guild_id)
        
        if setting is None:
            # Display current settings
            embed = discord.Embed(
                title="New Accounts Protection",
                description="Current settings for new account protection",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            
            status = "Enabled" if settings["newaccounts"]["enabled"] else "Disabled"
            action = settings["newaccounts"]["action"].capitalize()
            min_age = settings["newaccounts"]["min_age"]
            
            embed.add_field(name="Status", value=status, inline=True)
            embed.add_field(name="Action", value=action, inline=True)
            embed.add_field(name="Minimum Account Age", value=f"{min_age} days", inline=True)
            
            if settings["newaccounts"]["action"] == "timeout":
                embed.add_field(
                    name="Timeout Duration", 
                    value=f"{settings['newaccounts']['timeout_duration']} hours", 
                    inline=True
                )
                
            await ctx.send(embed=embed)
            return
            
        # Update settings
        if setting.lower() in ["enable", "on", "true", "yes"]:
            settings["newaccounts"]["enabled"] = True
            await ctx.send("✅ New accounts protection is now **enabled**.")
            
        elif setting.lower() in ["disable", "off", "false", "no"]:
            settings["newaccounts"]["enabled"] = False
            await ctx.send("✅ New accounts protection is now **disabled**.")
            
        elif setting.lower() == "action":
            if not flags or flags.lower() not in ["kick", "ban", "timeout"]:
                await ctx.send("❌ Invalid action. Choose from: `kick`, `ban`, `timeout`")
                return
                
            settings["newaccounts"]["action"] = flags.lower()
            await ctx.send(f"✅ Action for new accounts set to **{flags.lower()}**.")
            
        elif setting.lower() == "minage":
            try:
                min_age = int(flags)
                if min_age < 1:
                    await ctx.send("❌ Minimum age must be at least 1 day.")
                    return
                    
                settings["newaccounts"]["min_age"] = min_age
                await ctx.send(f"✅ Minimum account age set to **{min_age} days**.")
                
            except ValueError:
                await ctx.send("❌ Please provide a valid number of days.")
                return
                
        elif setting.lower() == "timeoutduration" and settings["newaccounts"]["action"] == "timeout":
            try:
                duration = int(flags)
                if duration < 1:
                    await ctx.send("❌ Timeout duration must be at least 1 hour.")
                    return
                    
                settings["newaccounts"]["timeout_duration"] = duration
                await ctx.send(f"✅ Timeout duration set to **{duration} hours**.")
                
            except ValueError:
                await ctx.send("❌ Please provide a valid number of hours.")
                return
        else:
            await ctx.send("❌ Invalid setting. Use `enable`, `disable`, `action`, `minage`, or `timeoutduration`.")
            return
            
        self._save_settings()

    @antiraid.command(name="massjoin")
    @commands.has_permissions(manage_guild=True)
    async def antiraid_massjoin(self, ctx, setting=None, *, flags=None):
        """Protect server against mass bot raids"""
        guild_id = str(ctx.guild.id)
        settings = self._get_guild_settings(guild_id)
        
        if setting is None:
            # Display current settings
            embed = discord.Embed(
                title="Mass Join Protection",
                description="Current settings for mass join protection",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            
            status = "Enabled" if settings["massjoin"]["enabled"] else "Disabled"
            threshold = settings["massjoin"]["threshold"]
            timeframe = settings["massjoin"]["timeframe"]
            action = settings["massjoin"]["action"].capitalize()
            
            embed.add_field(name="Status", value=status, inline=True)
            embed.add_field(name="Threshold", value=f"{threshold} joins", inline=True)
            embed.add_field(name="Timeframe", value=f"{timeframe} seconds", inline=True)
            embed.add_field(name="Action", value=action, inline=True)
                
            await ctx.send(embed=embed)
            return
            
        # Update settings
        if setting.lower() in ["enable", "on", "true", "yes"]:
            settings["massjoin"]["enabled"] = True
            await ctx.send("✅ Mass join protection is now **enabled**.")
            
        elif setting.lower() in ["disable", "off", "false", "no"]:
            settings["massjoin"]["enabled"] = False
            await ctx.send("✅ Mass join protection is now **disabled**.")
            
        elif setting.lower() == "action":
            if not flags or flags.lower() not in ["lockdown", "verification"]:
                await ctx.send("❌ Invalid action. Choose from: `lockdown`, `verification`")
                return
                
            settings["massjoin"]["action"] = flags.lower()
            await ctx.send(f"✅ Action for mass joins set to **{flags.lower()}**.")
            
        elif setting.lower() == "threshold":
            try:
                threshold = int(flags)
                if threshold < 2:
                    await ctx.send("❌ Threshold must be at least 2 joins.")
                    return
                    
                settings["massjoin"]["threshold"] = threshold
                await ctx.send(f"✅ Mass join threshold set to **{threshold} joins**.")
                
            except ValueError:
                await ctx.send("❌ Please provide a valid threshold number.")
                return
                
        elif setting.lower() == "timeframe":
            try:
                timeframe = int(flags)
                if timeframe < 1:
                    await ctx.send("❌ Timeframe must be at least 1 second.")
                    return
                    
                settings["massjoin"]["timeframe"] = timeframe
                await ctx.send(f"✅ Mass join timeframe set to **{timeframe} seconds**.")
                
            except ValueError:
                await ctx.send("❌ Please provide a valid number of seconds.")
                return
        else:
            await ctx.send("❌ Invalid setting. Use `enable`, `disable`, `action`, `threshold`, or `timeframe`.")
            return
            
        self._save_settings()

    @antiraid.command(name="avatar")
    @commands.has_permissions(manage_guild=True)
    async def antiraid_avatar(self, ctx, setting=None, *, flags=None):
        """Punish accounts without a profile picture"""
        guild_id = str(ctx.guild.id)
        settings = self._get_guild_settings(guild_id)
        
        if setting is None:
            # Display current settings
            embed = discord.Embed(
                title="No Avatar Protection",
                description="Current settings for accounts without profile pictures",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            
            status = "Enabled" if settings["avatar"]["enabled"] else "Disabled"
            action = settings["avatar"]["action"].capitalize()
            
            embed.add_field(name="Status", value=status, inline=True)
            embed.add_field(name="Action", value=action, inline=True)
                
            await ctx.send(embed=embed)
            return
            
        # Update settings
        if setting.lower() in ["enable", "on", "true", "yes"]:
            settings["avatar"]["enabled"] = True
            await ctx.send("✅ No avatar protection is now **enabled**.")
            
        elif setting.lower() in ["disable", "off", "false", "no"]:
            settings["avatar"]["enabled"] = False
            await ctx.send("✅ No avatar protection is now **disabled**.")
            
        elif setting.lower() == "action":
            if not flags or flags.lower() not in ["kick", "ban", "timeout"]:
                await ctx.send("❌ Invalid action. Choose from: `kick`, `ban`, `timeout`")
                return
                
            settings["avatar"]["action"] = flags.lower()
            await ctx.send(f"✅ Action for no avatar set to **{flags.lower()}**.")
        else:
            await ctx.send("❌ Invalid setting. Use `enable`, `disable`, or `action`.")
            return
            
        self._save_settings()

    @antiraid.command(name="config")
    @commands.has_permissions(manage_guild=True)
    async def antiraid_config(self, ctx):
        """View server antiraid configuration"""
        guild_id = str(ctx.guild.id)
        settings = self._get_guild_settings(guild_id)
        raid_state = self._get_guild_raid_state(guild_id)
        
        embed = discord.Embed(
            title="AntiRaid Configuration",
            description="Current antiraid settings for this server",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        # Raid State
        raid_status = "❌ Not Active"
        if raid_state["active"]:
            raid_status = f"⚠️ **ACTIVE** - {raid_state['reason']}"
            
        embed.add_field(name="Raid State", value=raid_status, inline=False)
        
        # New Accounts
        newaccount_status = "Disabled"
        if settings["newaccounts"]["enabled"]:
            newaccount_status = f"Enabled - {settings['newaccounts']['action'].capitalize()} accounts < {settings['newaccounts']['min_age']} days old"
            
        embed.add_field(name="New Account Protection", value=newaccount_status, inline=False)
        
        # Mass Join
        massjoin_status = "Disabled"
        if settings["massjoin"]["enabled"]:
            massjoin_status = f"Enabled - {settings['massjoin']['action'].capitalize()} on {settings['massjoin']['threshold']} joins in {settings['massjoin']['timeframe']}s"
            
        embed.add_field(name="Mass Join Protection", value=massjoin_status, inline=False)
        
        # No Avatar
        avatar_status = "Disabled"
        if settings["avatar"]["enabled"]:
            avatar_status = f"Enabled - {settings['avatar']['action'].capitalize()} accounts without avatars"
            
        embed.add_field(name="No Avatar Protection", value=avatar_status, inline=False)
        
        await ctx.send(embed=embed)

    @antiraid.command(name="state")
    @commands.has_permissions(manage_guild=True)
    async def antiraid_state(self, ctx):
        """Turn off server's raid state"""
        guild_id = str(ctx.guild.id)
        raid_state = self._get_guild_raid_state(guild_id)
        
        if not raid_state["active"]:
            await ctx.send("❌ Raid state is not currently active.")
            return
            
        raid_state["active"] = False
        raid_state["started_at"] = None
        raid_state["reason"] = None
        
        self._save_settings()
        
        embed = discord.Embed(
            title="Raid State Disabled",
            description="The server's raid state has been turned off.",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(name="Disabled by", value=ctx.author.mention, inline=False)
        embed.set_footer(text="You can now resume normal server operations.")
        
        await ctx.send(embed=embed)

    @antiraid.command(name="wl")
    @commands.has_permissions(manage_guild=True)
    async def antiraid_whitelist(self, ctx, member: discord.Member = None):
        """Create a one-time whitelist to allow a user to join"""
        if member is None:
            await ctx.send("❌ Please specify a member to whitelist.")
            return
            
        guild_id = str(ctx.guild.id)
        whitelist = self._get_guild_whitelist(guild_id)
        
        # Check if already whitelisted
        if str(member.id) in whitelist:
            await ctx.send(f"❌ {member.mention} is already whitelisted.")
            return
            
        # Add to whitelist
        whitelist.append(str(member.id))
        self._save_settings()
        
        embed = discord.Embed(
            title="Member Whitelisted",
            description=f"{member.mention} has been whitelisted from antiraid measures.",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(name="Whitelisted by", value=ctx.author.mention, inline=False)
        embed.set_thumbnail(url=member.display_avatar.url)
        
        await ctx.send(embed=embed)

    @antiraid.group(name="whitelist", invoke_without_command=True)
    @commands.has_permissions(manage_guild=True)
    async def antiraid_whitelist_group(self, ctx):
        """Whitelist management commands"""
        await ctx.send_help(ctx.command)

    @antiraid_whitelist_group.command(name="view")
    @commands.has_permissions(manage_guild=True)
    async def antiraid_whitelist_view(self, ctx):
        """View all current antinuke whitelists"""
        guild_id = str(ctx.guild.id)
        whitelist = self._get_guild_whitelist(guild_id)
        
        if not whitelist:
            await ctx.send("❌ No members are currently whitelisted.")
            return
            
        embed = discord.Embed(
            title="AntiRaid Whitelist",
            description="Members whitelisted from antiraid measures",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        whitelist_text = ""
        for user_id in whitelist:
            user = ctx.guild.get_member(int(user_id))
            if user:
                whitelist_text += f"• {user.mention} (ID: {user.id})\n"
            else:
                whitelist_text += f"• Unknown User (ID: {user_id})\n"
                
        if not whitelist_text:
            whitelist_text = "No valid whitelisted members found."
            
        embed.add_field(name="Whitelisted Members", value=whitelist_text, inline=False)
        
        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Check joining members against antiraid settings"""
        guild_id = str(member.guild.id)
        settings = self._get_guild_settings(guild_id)
        whitelist = self._get_guild_whitelist(guild_id)
        raid_state = self._get_guild_raid_state(guild_id)
        
        # Skip if member is whitelisted
        if str(member.id) in whitelist:
            # Remove from whitelist since it's one-time use
            whitelist.remove(str(member.id))
            self._save_settings()
            return
            
        # Check for active raid state
        if raid_state["active"]:
            try:
                # Send DM to user
                embed = discord.Embed(
                    title="Server in Raid Protection Mode",
                    description=f"Sorry, {member.guild.name} is currently in raid protection mode.",
                    color=discord.Color.red()
                )
                embed.add_field(
                    name="What this means", 
                    value="The server is currently experiencing or recently experienced a raid attack. " +
                          "New joins are temporarily restricted for security.",
                    inline=False
                )
                embed.add_field(
                    name="What to do", 
                    value="Please try joining again later or contact a server administrator.",
                    inline=False
                )
                await member.send(embed=embed)
            except:
                pass
                
            # Kick the member
            try:
                await member.kick(reason="Server in raid protection mode")
            except:
                pass
                
            return
                
        # Check for new account
        if settings["newaccounts"]["enabled"]:
            account_age = (datetime.utcnow() - member.created_at).days
            
            if account_age < settings["newaccounts"]["min_age"]:
                action = settings["newaccounts"]["action"]
                
                try:
                    # Send DM to user
                    embed = discord.Embed(
                        title="Account Too New",
                        description=f"Your account is too new to join {member.guild.name}.",
                        color=discord.Color.red()
                    )
                    embed.add_field(
                        name="Requirement", 
                        value=f"Accounts must be at least {settings['newaccounts']['min_age']} days old.",
                        inline=False
                    )
                    embed.add_field(
                        name="Your account age", 
                        value=f"{account_age} days",
                        inline=False
                    )
                    await member.send(embed=embed)
                except:
                    pass
                    
                # Take action based on settings
                if action == "kick":
                    try:
                        await member.kick(reason=f"Account too new ({account_age} days)")
                    except:
                        pass
                elif action == "ban":
                    try:
                        await member.ban(reason=f"Account too new ({account_age} days)")
                    except:
                        pass
                elif action == "timeout":
                    try:
                        # Set timeout duration
                        duration = timedelta(hours=settings["newaccounts"]["timeout_duration"])
                        await member.timeout_for(duration, reason=f"Account too new ({account_age} days)")
                    except:
                        pass
                        
        # Check for no avatar
        if settings["avatar"]["enabled"]:
            if member.avatar is None:
                action = settings["avatar"]["action"]
                
                try:
                    # Send DM to user
                    embed = discord.Embed(
                        title="Avatar Required",
                        description=f"You need a profile picture to join {member.guild.name}.",
                        color=discord.Color.red()
                    )
                    embed.add_field(
                        name="What to do", 
                        value="Please set a profile picture and try joining again.",
                        inline=False
                    )
                    await member.send(embed=embed)
                except:
                    pass
                    
                # Take action based on settings
                if action == "kick":
                    try:
                        await member.kick(reason="No profile picture")
                    except:
                        pass
                elif action == "ban":
                    try:
                        await member.ban(reason="No profile picture")
                    except:
                        pass
                elif action == "timeout":
                    try:
                        # Set timeout for 24 hours
                        duration = timedelta(hours=24)
                        await member.timeout_for(duration, reason="No profile picture")
                    except:
                        pass
                        
        # Process mass join detection
        await self.mass_join_handler.handle_member_join(member)

async def setup(bot):
    await bot.add_cog(AntiRaid(bot)) 