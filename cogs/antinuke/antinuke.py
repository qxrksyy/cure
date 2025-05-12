import discord
from discord.ext import commands
import json
import os
import logging
from datetime import datetime, timedelta
import asyncio

logger = logging.getLogger('bot')

# Action types for auditing
ACTIONS = {
    "KICK": "kick",
    "BAN": "ban",
    "CHANNEL_DELETE": "channel_delete",
    "CHANNEL_CREATE": "channel_create",
    "ROLE_DELETE": "role_delete",
    "EMOJI_DELETE": "emoji_delete",
    "WEBHOOK_CREATE": "webhook_create",
    "BOT_ADD": "bot_add",
    "PERMISSION_CHANGE": "permission_change"
}

class AntiNuke(commands.Cog):
    """Commands to protect your server against nuking and mass destructive actions"""
    
    def __init__(self, bot):
        self.bot = bot
        self.config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'data', 'antinuke')
        self.settings = {}
        self.action_counters = {}
        self.recently_punished = set()
        
        # Create directory if it doesn't exist
        os.makedirs(self.config_path, exist_ok=True)
        
        # Load settings
        self._load_settings()
        
        # Start cleanup task
        self.cleanup_task = bot.loop.create_task(self._cleanup_counters())
    
    def cog_unload(self):
        """Called when the cog is unloaded"""
        self.cleanup_task.cancel()
    
    def _load_settings(self):
        """Load antinuke settings from file"""
        try:
            filepath = f"{self.config_path}/settings.json"
            if os.path.exists(filepath):
                with open(filepath, "r") as f:
                    self.settings = json.load(f)
        except Exception as e:
            logger.error(f"Error loading antinuke settings: {str(e)}")
    
    def _save_settings(self):
        """Save antinuke settings to file"""
        try:
            filepath = f"{self.config_path}/settings.json"
            with open(filepath, "w") as f:
                json.dump(self.settings, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving antinuke settings: {str(e)}")
    
    def _get_guild_settings(self, guild_id):
        """Get antinuke settings for a guild"""
        guild_id = str(guild_id)
        if guild_id not in self.settings:
            self.settings[guild_id] = {
                "modules": {
                    "kick": False,
                    "ban": False,
                    "channel": False,
                    "role": False,
                    "emoji": False,
                    "webhook": False,
                    "botadd": False,
                    "permissions": {
                        "enabled": False,
                        "monitored": [
                            "administrator",
                            "ban_members",
                            "kick_members",
                            "manage_guild",
                            "manage_roles",
                            "manage_channels",
                            "manage_webhooks"
                        ]
                    }
                },
                "thresholds": {
                    "kick": 3,
                    "ban": 3,
                    "channel_delete": 3,
                    "channel_create": 5,
                    "role_delete": 3,
                    "emoji_delete": 5,
                    "webhook_create": 3,
                    "bot_add": 2
                },
                "timeframe": 10,  # seconds
                "whitelist": [],
                "bot_whitelist": [],
                "admins": [],
                "punishment": "ban"  # can be 'kick', 'ban', or 'remove_roles'
            }
            self._save_settings()
        return self.settings[guild_id]
    
    def _can_manage_antinuke(self, guild, member):
        """Check if a member can manage antinuke settings"""
        if member.id == guild.owner_id:
            return True
            
        settings = self._get_guild_settings(guild.id)
        if str(member.id) in settings["admins"]:
            return True
            
        return False
    
    def _is_whitelisted(self, guild_id, user_id):
        """Check if a user is whitelisted"""
        settings = self._get_guild_settings(guild_id)
        return str(user_id) in settings["whitelist"]
    
    def _is_bot_whitelisted(self, guild_id, bot_id):
        """Check if a bot is whitelisted"""
        settings = self._get_guild_settings(guild_id)
        return str(bot_id) in settings["bot_whitelist"]
    
    async def _increment_counter(self, guild_id, user_id, action_type):
        """Increment action counter for a user"""
        guild_id = str(guild_id)
        user_id = str(user_id)
        
        if guild_id not in self.action_counters:
            self.action_counters[guild_id] = {}
            
        if user_id not in self.action_counters[guild_id]:
            self.action_counters[guild_id][user_id] = {}
            
        if action_type not in self.action_counters[guild_id][user_id]:
            self.action_counters[guild_id][user_id][action_type] = {
                "count": 0,
                "first_action": datetime.utcnow()
            }
        
        # Update counter
        self.action_counters[guild_id][user_id][action_type]["count"] += 1
        
        # Check if we need to reset the counter based on timeframe
        settings = self._get_guild_settings(guild_id)
        timeframe = settings["timeframe"]
        first_action = self.action_counters[guild_id][user_id][action_type]["first_action"]
        
        if (datetime.utcnow() - first_action).total_seconds() > timeframe:
            # Reset counter if outside timeframe
            self.action_counters[guild_id][user_id][action_type] = {
                "count": 1,
                "first_action": datetime.utcnow()
            }
    
    def _check_threshold_exceeded(self, guild_id, user_id, action_type):
        """Check if a user has exceeded the threshold for an action"""
        guild_id = str(guild_id)
        user_id = str(user_id)
        
        if guild_id not in self.action_counters:
            return False
            
        if user_id not in self.action_counters[guild_id]:
            return False
            
        if action_type not in self.action_counters[guild_id][user_id]:
            return False
        
        settings = self._get_guild_settings(guild_id)
        threshold = settings["thresholds"].get(action_type, 3)
        timeframe = settings["timeframe"]
        counter = self.action_counters[guild_id][user_id][action_type]
        
        # Check if counter is within timeframe
        if (datetime.utcnow() - counter["first_action"]).total_seconds() <= timeframe:
            return counter["count"] >= threshold
            
        return False
    
    async def _cleanup_counters(self):
        """Periodically clean up old counters"""
        while not self.bot.is_closed():
            try:
                now = datetime.utcnow()
                for guild_id in list(self.action_counters.keys()):
                    for user_id in list(self.action_counters[guild_id].keys()):
                        for action_type in list(self.action_counters[guild_id][user_id].keys()):
                            counter = self.action_counters[guild_id][user_id][action_type]
                            timeframe = self.settings[guild_id]["timeframe"] if guild_id in self.settings else 10
                            
                            if (now - counter["first_action"]).total_seconds() > timeframe:
                                del self.action_counters[guild_id][user_id][action_type]
                                
                        # Clean up empty user entries
                        if not self.action_counters[guild_id][user_id]:
                            del self.action_counters[guild_id][user_id]
                            
                    # Clean up empty guild entries
                    if not self.action_counters[guild_id]:
                        del self.action_counters[guild_id]
            except Exception as e:
                logger.error(f"Error cleaning up counters: {str(e)}")
                
            # Clear recently punished set after 5 minutes
            now = datetime.utcnow()
            new_recently_punished = set()
            for entry in self.recently_punished:
                if isinstance(entry, tuple) and len(entry) == 2:
                    user_id, timestamp = entry
                    if now - timestamp < timedelta(minutes=5):
                        new_recently_punished.add(entry)
            self.recently_punished = new_recently_punished
            
            await asyncio.sleep(60)  # Run cleanup every minute
    
    async def _take_antinuke_action(self, guild, user_id, action_type, reason):
        """Take action against a user who triggered antinuke"""
        try:
            # Skip if already punished recently
            for punished in self.recently_punished:
                if punished[0] == user_id and (datetime.utcnow() - punished[1]) < timedelta(minutes=5):
                    return
            
            # If punishment has already been applied within 5 minutes, don't apply again
            punish_key = (user_id, guild.id, action_type)
            if punish_key in self.recently_punished:
                return
                
            settings = self._get_guild_settings(guild.id)
            punishment = settings["punishment"]
            
            # Get the user
            user = await self.bot.fetch_user(int(user_id))
            if not user:
                return
                
            # Get the member
            member = guild.get_member(int(user_id))
            if not member:
                # If member not found but user exists, they might have left
                if punishment == "ban":
                    await guild.ban(user, reason=f"AntiNuke: {reason}")
                    logger.warning(f"AntiNuke banned user {user.name} ({user.id}) from {guild.name}: {reason}")
                return
            
            # Take action based on punishment setting
            if punishment == "ban":
                await member.ban(reason=f"AntiNuke: {reason}")
                logger.warning(f"AntiNuke banned {member.name} ({member.id}) from {guild.name}: {reason}")
            elif punishment == "kick":
                await member.kick(reason=f"AntiNuke: {reason}")
                logger.warning(f"AntiNuke kicked {member.name} ({member.id}) from {guild.name}: {reason}")
            elif punishment == "remove_roles":
                # Save current roles
                roles_to_remove = [role for role in member.roles if role.permissions.value > 0 and role != guild.default_role]
                
                if roles_to_remove:
                    await member.remove_roles(*roles_to_remove, reason=f"AntiNuke: {reason}")
                    logger.warning(f"AntiNuke removed roles from {member.name} ({member.id}) in {guild.name}: {reason}")
            
            # Mark as recently punished
            self.recently_punished.add((user_id, datetime.utcnow()))
            
            # Send alert to system channel if available
            if guild.system_channel:
                embed = discord.Embed(
                    title="⚠️ AntiNuke Triggered",
                    description=f"Action has been taken against a user for suspicious activity.",
                    color=discord.Color.red(),
                    timestamp=datetime.utcnow()
                )
                
                embed.add_field(name="User", value=f"{user.mention} ({user.name})", inline=True)
                embed.add_field(name="Action Type", value=action_type.replace("_", " ").title(), inline=True)
                embed.add_field(name="Punishment", value=punishment.replace("_", " ").title(), inline=True)
                embed.add_field(name="Reason", value=reason, inline=False)
                
                await guild.system_channel.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error taking antinuke action: {str(e)}")
    
    @commands.group(name="antinuke", invoke_without_command=True)
    @commands.has_permissions(send_messages=True)
    async def antinuke(self, ctx):
        """Antinuke to protect your server"""
        embed = discord.Embed(
            title="AntiNuke Protection",
            description="Protect your server against mass nuking and destructive actions",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        # Only continue if command invoker is server owner or antinuke admin
        if not self._can_manage_antinuke(ctx.guild, ctx.author):
            embed.add_field(
                name="❌ Access Denied",
                value="Only the server owner or authorized admins can manage AntiNuke settings.",
                inline=False
            )
            await ctx.send(embed=embed)
            return
        
        settings = self._get_guild_settings(ctx.guild.id)
        
        # Create module status text
        module_status = []
        modules = settings["modules"]
        
        for module, enabled in modules.items():
            if module != "permissions":  # Handle permissions separately
                status = "✅ Enabled" if enabled else "❌ Disabled"
                module_status.append(f"**{module.title()}**: {status}")
        
        # Handle permissions module separately
        perm_module = modules["permissions"]
        perm_status = "✅ Enabled" if perm_module["enabled"] else "❌ Disabled"
        module_status.append(f"**Permissions**: {perm_status}")
        
        embed.add_field(
            name="Module Status",
            value="\n".join(module_status),
            inline=False
        )
        
        # Add command list
        embed.add_field(
            name="Available Commands",
            value=(
                "`antinuke kick <status>` - Prevent mass member kick\n"
                "`antinuke ban <status>` - Prevent mass member ban\n"
                "`antinuke channel <status>` - Prevent mass channel delete/create\n"
                "`antinuke role <status>` - Prevent mass role delete\n"
                "`antinuke emoji <status>` - Prevent mass emoji delete\n"
                "`antinuke webhook <status>` - Prevent mass webhook creation\n"
                "`antinuke botadd <status>` - Prevent new bot additions\n"
                "`antinuke permissions <option> <permission>` - Watch for dangerous permissions\n"
                "`antinuke admin <member>` - Give a member permission to edit settings\n"
                "`antinuke admins` - View all antinuke admins\n"
                "`antinuke whitelist <member>` - Whitelist a member or bot\n"
                "`antinuke list` - View all enabled modules and whitelisted users\n"
                "`antinuke config` - View detailed server configuration"
            ),
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @antinuke.command(name="list")
    @commands.has_permissions(send_messages=True)
    async def antinuke_list(self, ctx):
        """View all enabled modules along with whitelisted members & bots"""
        # Check if user can manage antinuke
        if not self._can_manage_antinuke(ctx.guild, ctx.author):
            await ctx.send("❌ Only the server owner and authorized admins can use AntiNuke commands.")
            return
        
        settings = self._get_guild_settings(ctx.guild.id)
        
        embed = discord.Embed(
            title="AntiNuke Configuration",
            description="Current AntiNuke settings for this server",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        # Add enabled modules
        modules_text = ""
        for module, enabled in settings["modules"].items():
            if module == "permissions":
                status = "✅ Enabled" if settings["modules"]["permissions"]["enabled"] else "❌ Disabled"
                modules_text += f"**Permissions**: {status}\n"
            else:
                status = "✅ Enabled" if enabled else "❌ Disabled"
                modules_text += f"**{module.title()}**: {status}\n"
                
        embed.add_field(
            name="Enabled Modules",
            value=modules_text or "No modules enabled",
            inline=False
        )
        
        # Add whitelisted members
        whitelist_text = ""
        for user_id in settings["whitelist"]:
            user = self.bot.get_user(int(user_id))
            whitelist_text += f"• {user.mention if user else f'Unknown User ({user_id})'}\n"
            
        embed.add_field(
            name="Whitelisted Members",
            value=whitelist_text or "No members whitelisted",
            inline=True
        )
        
        # Add whitelisted bots
        bot_whitelist_text = ""
        for bot_id in settings["bot_whitelist"]:
            bot_user = self.bot.get_user(int(bot_id))
            bot_whitelist_text += f"• {bot_user.mention if bot_user else f'Unknown Bot ({bot_id})'}\n"
            
        embed.add_field(
            name="Whitelisted Bots",
            value=bot_whitelist_text or "No bots whitelisted",
            inline=True
        )
        
        await ctx.send(embed=embed)
    
    @antinuke.command(name="config")
    @commands.has_permissions(send_messages=True)
    async def antinuke_config(self, ctx):
        """View server configuration for Antinuke"""
        # Check if user can manage antinuke
        if not self._can_manage_antinuke(ctx.guild, ctx.author):
            await ctx.send("❌ Only the server owner and authorized admins can use AntiNuke commands.")
            return
        
        settings = self._get_guild_settings(ctx.guild.id)
        
        embed = discord.Embed(
            title="AntiNuke Detailed Configuration",
            description="Complete configuration of AntiNuke for this server",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        # Add general settings
        embed.add_field(
            name="General Settings",
            value=(
                f"**Timeframe**: {settings['timeframe']} seconds\n"
                f"**Punishment**: {settings['punishment'].replace('_', ' ').title()}"
            ),
            inline=False
        )
        
        # Add module thresholds
        thresholds_text = ""
        for action, threshold in settings["thresholds"].items():
            thresholds_text += f"**{action.replace('_', ' ').title()}**: {threshold}\n"
            
        embed.add_field(
            name="Action Thresholds",
            value=thresholds_text,
            inline=False
        )
        
        # Add monitored permissions if enabled
        if settings["modules"]["permissions"]["enabled"]:
            perms_text = ""
            for perm in settings["modules"]["permissions"]["monitored"]:
                perms_text += f"• {perm.replace('_', ' ').title()}\n"
                
            embed.add_field(
                name="Monitored Permissions",
                value=perms_text or "No permissions monitored",
                inline=False
            )
        
        await ctx.send(embed=embed)

async def setup(bot):
    antinuke_cog = AntiNuke(bot)
    await bot.add_cog(antinuke_cog)
    
    # Import and load module_commands with antinuke_cog reference
    try:
        from . import module_commands
        await module_commands.setup(bot, antinuke_cog)
        logger.info("Loaded antinuke module_commands extension")
    except Exception as e:
        logger.error(f"Error loading antinuke module_commands: {str(e)}") 