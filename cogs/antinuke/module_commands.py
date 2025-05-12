import discord
from discord.ext import commands
import logging
from datetime import datetime

logger = logging.getLogger('bot')

class ModuleCommands(commands.Cog):
    """Commands for managing individual AntiNuke modules"""
    
    def __init__(self, bot, antinuke_cog):
        self.bot = bot
        self.antinuke = antinuke_cog
    
    @commands.command(name="kick")
    @commands.has_permissions(send_messages=True)
    async def antinuke_kick(self, ctx, status: str = None):
        """Prevent mass member kick"""
        # Check if user can manage antinuke
        if not self.antinuke._can_manage_antinuke(ctx.guild, ctx.author):
            await ctx.send("❌ Only the server owner and authorized admins can use AntiNuke commands.")
            return
            
        settings = self.antinuke._get_guild_settings(ctx.guild.id)
        
        if status is None:
            # Show current status
            embed = discord.Embed(
                title="AntiNuke Kick Module",
                description="Prevents mass member kicks by one user",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            
            status = "✅ Enabled" if settings["modules"]["kick"] else "❌ Disabled"
            embed.add_field(name="Status", value=status, inline=True)
            embed.add_field(name="Threshold", value=f"{settings['thresholds']['kick']} kicks", inline=True)
            embed.add_field(name="Timeframe", value=f"{settings['timeframe']} seconds", inline=True)
            
            await ctx.send(embed=embed)
            return
            
        # Update status
        if status.lower() in ["enable", "on", "true", "yes"]:
            settings["modules"]["kick"] = True
            await ctx.send("✅ Kick protection is now **enabled**.")
            
        elif status.lower() in ["disable", "off", "false", "no"]:
            settings["modules"]["kick"] = False
            await ctx.send("✅ Kick protection is now **disabled**.")
            
        else:
            await ctx.send("❌ Invalid status. Use `enable` or `disable`.")
            return
            
        self.antinuke._save_settings()
    
    @commands.command(name="ban")
    @commands.has_permissions(send_messages=True)
    async def antinuke_ban(self, ctx, status: str = None, *, flags=None):
        """Prevent mass member ban"""
        # Check if user can manage antinuke
        if not self.antinuke._can_manage_antinuke(ctx.guild, ctx.author):
            await ctx.send("❌ Only the server owner and authorized admins can use AntiNuke commands.")
            return
            
        settings = self.antinuke._get_guild_settings(ctx.guild.id)
        
        if status is None:
            # Show current status
            embed = discord.Embed(
                title="AntiNuke Ban Module",
                description="Prevents mass member bans by one user",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            
            status = "✅ Enabled" if settings["modules"]["ban"] else "❌ Disabled"
            embed.add_field(name="Status", value=status, inline=True)
            embed.add_field(name="Threshold", value=f"{settings['thresholds']['ban']} bans", inline=True)
            embed.add_field(name="Timeframe", value=f"{settings['timeframe']} seconds", inline=True)
            
            await ctx.send(embed=embed)
            return
            
        # Update status
        if status.lower() in ["enable", "on", "true", "yes"]:
            settings["modules"]["ban"] = True
            await ctx.send("✅ Ban protection is now **enabled**.")
            
        elif status.lower() in ["disable", "off", "false", "no"]:
            settings["modules"]["ban"] = False
            await ctx.send("✅ Ban protection is now **disabled**.")
            
        elif status.lower() == "threshold" and flags is not None:
            try:
                threshold = int(flags)
                if threshold < 1:
                    await ctx.send("❌ Threshold must be at least 1.")
                    return
                    
                settings["thresholds"]["ban"] = threshold
                await ctx.send(f"✅ Ban threshold set to **{threshold}**.")
                
            except ValueError:
                await ctx.send("❌ Invalid threshold value. Please provide a number.")
                return
                
        else:
            await ctx.send("❌ Invalid status. Use `enable`, `disable`, or `threshold <number>`.")
            return
            
        self.antinuke._save_settings()
    
    @commands.command(name="channel")
    @commands.has_permissions(send_messages=True)
    async def antinuke_channel(self, ctx, status: str = None, *, flags=None):
        """Prevent mass channel create and delete"""
        # Check if user can manage antinuke
        if not self.antinuke._can_manage_antinuke(ctx.guild, ctx.author):
            await ctx.send("❌ Only the server owner and authorized admins can use AntiNuke commands.")
            return
            
        settings = self.antinuke._get_guild_settings(ctx.guild.id)
        
        if status is None:
            # Show current status
            embed = discord.Embed(
                title="AntiNuke Channel Module",
                description="Prevents mass channel creation and deletion by one user",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            
            status = "✅ Enabled" if settings["modules"]["channel"] else "❌ Disabled"
            embed.add_field(name="Status", value=status, inline=True)
            embed.add_field(name="Create Threshold", value=f"{settings['thresholds']['channel_create']} channels", inline=True)
            embed.add_field(name="Delete Threshold", value=f"{settings['thresholds']['channel_delete']} channels", inline=True)
            embed.add_field(name="Timeframe", value=f"{settings['timeframe']} seconds", inline=True)
            
            await ctx.send(embed=embed)
            return
            
        # Update status
        if status.lower() in ["enable", "on", "true", "yes"]:
            settings["modules"]["channel"] = True
            await ctx.send("✅ Channel protection is now **enabled**.")
            
        elif status.lower() in ["disable", "off", "false", "no"]:
            settings["modules"]["channel"] = False
            await ctx.send("✅ Channel protection is now **disabled**.")
            
        elif status.lower() == "create" and flags is not None:
            try:
                threshold = int(flags)
                if threshold < 1:
                    await ctx.send("❌ Threshold must be at least 1.")
                    return
                    
                settings["thresholds"]["channel_create"] = threshold
                await ctx.send(f"✅ Channel creation threshold set to **{threshold}**.")
                
            except ValueError:
                await ctx.send("❌ Invalid threshold value. Please provide a number.")
                return
                
        elif status.lower() == "delete" and flags is not None:
            try:
                threshold = int(flags)
                if threshold < 1:
                    await ctx.send("❌ Threshold must be at least 1.")
                    return
                    
                settings["thresholds"]["channel_delete"] = threshold
                await ctx.send(f"✅ Channel deletion threshold set to **{threshold}**.")
                
            except ValueError:
                await ctx.send("❌ Invalid threshold value. Please provide a number.")
                return
                
        else:
            await ctx.send("❌ Invalid status. Use `enable`, `disable`, `create <number>`, or `delete <number>`.")
            return
            
        self.antinuke._save_settings()
    
    @commands.command(name="webhook")
    @commands.has_permissions(send_messages=True)
    async def antinuke_webhook(self, ctx, status: str = None, *, flags=None):
        """Prevent mass webhook creation"""
        # Check if user can manage antinuke
        if not self.antinuke._can_manage_antinuke(ctx.guild, ctx.author):
            await ctx.send("❌ Only the server owner and authorized admins can use AntiNuke commands.")
            return
            
        settings = self.antinuke._get_guild_settings(ctx.guild.id)
        
        if status is None:
            # Show current status
            embed = discord.Embed(
                title="AntiNuke Webhook Module",
                description="Prevents mass webhook creation by one user",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            
            status = "✅ Enabled" if settings["modules"]["webhook"] else "❌ Disabled"
            embed.add_field(name="Status", value=status, inline=True)
            embed.add_field(name="Threshold", value=f"{settings['thresholds']['webhook_create']} webhooks", inline=True)
            embed.add_field(name="Timeframe", value=f"{settings['timeframe']} seconds", inline=True)
            
            await ctx.send(embed=embed)
            return
            
        # Update status
        if status.lower() in ["enable", "on", "true", "yes"]:
            settings["modules"]["webhook"] = True
            await ctx.send("✅ Webhook protection is now **enabled**.")
            
        elif status.lower() in ["disable", "off", "false", "no"]:
            settings["modules"]["webhook"] = False
            await ctx.send("✅ Webhook protection is now **disabled**.")
            
        elif status.lower() == "threshold" and flags is not None:
            try:
                threshold = int(flags)
                if threshold < 1:
                    await ctx.send("❌ Threshold must be at least 1.")
                    return
                    
                settings["thresholds"]["webhook_create"] = threshold
                await ctx.send(f"✅ Webhook creation threshold set to **{threshold}**.")
                
            except ValueError:
                await ctx.send("❌ Invalid threshold value. Please provide a number.")
                return
                
        else:
            await ctx.send("❌ Invalid status. Use `enable`, `disable`, or `threshold <number>`.")
            return
            
        self.antinuke._save_settings()
    
    @commands.command(name="role")
    @commands.has_permissions(send_messages=True)
    async def antinuke_role(self, ctx, status: str = None, *, flags=None):
        """Prevent mass role delete"""
        # Check if user can manage antinuke
        if not self.antinuke._can_manage_antinuke(ctx.guild, ctx.author):
            await ctx.send("❌ Only the server owner and authorized admins can use AntiNuke commands.")
            return
            
        settings = self.antinuke._get_guild_settings(ctx.guild.id)
        
        if status is None:
            # Show current status
            embed = discord.Embed(
                title="AntiNuke Role Module",
                description="Prevents mass role deletion by one user",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            
            status = "✅ Enabled" if settings["modules"]["role"] else "❌ Disabled"
            embed.add_field(name="Status", value=status, inline=True)
            embed.add_field(name="Threshold", value=f"{settings['thresholds']['role_delete']} roles", inline=True)
            embed.add_field(name="Timeframe", value=f"{settings['timeframe']} seconds", inline=True)
            
            await ctx.send(embed=embed)
            return
            
        # Update status
        if status.lower() in ["enable", "on", "true", "yes"]:
            settings["modules"]["role"] = True
            await ctx.send("✅ Role protection is now **enabled**.")
            
        elif status.lower() in ["disable", "off", "false", "no"]:
            settings["modules"]["role"] = False
            await ctx.send("✅ Role protection is now **disabled**.")
            
        elif status.lower() == "threshold" and flags is not None:
            try:
                threshold = int(flags)
                if threshold < 1:
                    await ctx.send("❌ Threshold must be at least 1.")
                    return
                    
                settings["thresholds"]["role_delete"] = threshold
                await ctx.send(f"✅ Role deletion threshold set to **{threshold}**.")
                
            except ValueError:
                await ctx.send("❌ Invalid threshold value. Please provide a number.")
                return
                
        else:
            await ctx.send("❌ Invalid status. Use `enable`, `disable`, or `threshold <number>`.")
            return
            
        self.antinuke._save_settings()
    
    @commands.command(name="emoji")
    @commands.has_permissions(send_messages=True)
    async def antinuke_emoji(self, ctx, status: str = None, *, flags=None):
        """Prevent mass emoji delete"""
        # Check if user can manage antinuke
        if not self.antinuke._can_manage_antinuke(ctx.guild, ctx.author):
            await ctx.send("❌ Only the server owner and authorized admins can use AntiNuke commands.")
            return
            
        settings = self.antinuke._get_guild_settings(ctx.guild.id)
        
        if status is None:
            # Show current status
            embed = discord.Embed(
                title="AntiNuke Emoji Module",
                description="Prevents mass emoji deletion by one user\n⚠️ Warning: This module may be unstable due to Discord's rate limit",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            
            status = "✅ Enabled" if settings["modules"]["emoji"] else "❌ Disabled"
            embed.add_field(name="Status", value=status, inline=True)
            embed.add_field(name="Threshold", value=f"{settings['thresholds']['emoji_delete']} emojis", inline=True)
            embed.add_field(name="Timeframe", value=f"{settings['timeframe']} seconds", inline=True)
            
            await ctx.send(embed=embed)
            return
            
        # Update status
        if status.lower() in ["enable", "on", "true", "yes"]:
            settings["modules"]["emoji"] = True
            await ctx.send("✅ Emoji protection is now **enabled**. ⚠️ Note: This module may be unstable due to Discord's rate limit.")
            
        elif status.lower() in ["disable", "off", "false", "no"]:
            settings["modules"]["emoji"] = False
            await ctx.send("✅ Emoji protection is now **disabled**.")
            
        elif status.lower() == "threshold" and flags is not None:
            try:
                threshold = int(flags)
                if threshold < 1:
                    await ctx.send("❌ Threshold must be at least 1.")
                    return
                    
                settings["thresholds"]["emoji_delete"] = threshold
                await ctx.send(f"✅ Emoji deletion threshold set to **{threshold}**.")
                
            except ValueError:
                await ctx.send("❌ Invalid threshold value. Please provide a number.")
                return
                
        else:
            await ctx.send("❌ Invalid status. Use `enable`, `disable`, or `threshold <number>`.")
            return
            
        self.antinuke._save_settings()
    
    @commands.command(name="botadd")
    @commands.has_permissions(send_messages=True)
    async def antinuke_botadd(self, ctx, status: str = None, *, flags=None):
        """Prevent new bot additions"""
        # Check if user can manage antinuke
        if not self.antinuke._can_manage_antinuke(ctx.guild, ctx.author):
            await ctx.send("❌ Only the server owner and authorized admins can use AntiNuke commands.")
            return
            
        settings = self.antinuke._get_guild_settings(ctx.guild.id)
        
        if status is None:
            # Show current status
            embed = discord.Embed(
                title="AntiNuke Bot Add Module",
                description="Prevents unauthorized bot additions to the server",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            
            status = "✅ Enabled" if settings["modules"]["botadd"] else "❌ Disabled"
            embed.add_field(name="Status", value=status, inline=True)
            embed.add_field(name="Threshold", value=f"{settings['thresholds']['bot_add']} bots", inline=True)
            embed.add_field(name="Timeframe", value=f"{settings['timeframe']} seconds", inline=True)
            
            # Add whitelisted bots list
            bot_whitelist_text = ""
            for bot_id in settings["bot_whitelist"]:
                bot_user = self.bot.get_user(int(bot_id))
                bot_whitelist_text += f"• {bot_user.mention if bot_user else f'Unknown Bot ({bot_id})'}\n"
                
            embed.add_field(
                name="Whitelisted Bots",
                value=bot_whitelist_text or "No bots whitelisted",
                inline=False
            )
            
            await ctx.send(embed=embed)
            return
            
        # Update status
        if status.lower() in ["enable", "on", "true", "yes"]:
            settings["modules"]["botadd"] = True
            await ctx.send("✅ Bot addition protection is now **enabled**.")
            
        elif status.lower() in ["disable", "off", "false", "no"]:
            settings["modules"]["botadd"] = False
            await ctx.send("✅ Bot addition protection is now **disabled**.")
            
        elif status.lower() == "threshold" and flags is not None:
            try:
                threshold = int(flags)
                if threshold < 1:
                    await ctx.send("❌ Threshold must be at least 1.")
                    return
                    
                settings["thresholds"]["bot_add"] = threshold
                await ctx.send(f"✅ Bot addition threshold set to **{threshold}**.")
                
            except ValueError:
                await ctx.send("❌ Invalid threshold value. Please provide a number.")
                return
                
        else:
            await ctx.send("❌ Invalid status. Use `enable`, `disable`, or `threshold <number>`.")
            return
            
        self.antinuke._save_settings()
        
    @commands.command(name="permissions")
    @commands.has_permissions(send_messages=True)
    async def antinuke_permissions(self, ctx, option: str = None, permission: str = None, *, flags=None):
        """Watch for dangerous permissions being granted or removed"""
        # Check if user can manage antinuke
        if not self.antinuke._can_manage_antinuke(ctx.guild, ctx.author):
            await ctx.send("❌ Only the server owner and authorized admins can use AntiNuke commands.")
            return
            
        settings = self.antinuke._get_guild_settings(ctx.guild.id)
        
        if option is None:
            # Show current status
            embed = discord.Embed(
                title="AntiNuke Permissions Module",
                description="Monitors and prevents dangerous permission changes",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            
            status = "✅ Enabled" if settings["modules"]["permissions"]["enabled"] else "❌ Disabled"
            embed.add_field(name="Status", value=status, inline=True)
            
            # Add monitored permissions
            perms_text = ""
            for perm in settings["modules"]["permissions"]["monitored"]:
                perms_text += f"• {perm.replace('_', ' ').title()}\n"
                
            embed.add_field(
                name="Monitored Permissions",
                value=perms_text or "No permissions monitored",
                inline=False
            )
            
            embed.add_field(
                name="Available Options",
                value=(
                    "`antinuke permissions enable` - Enable permission monitoring\n"
                    "`antinuke permissions disable` - Disable permission monitoring\n"
                    "`antinuke permissions add <permission>` - Add a permission to monitor\n"
                    "`antinuke permissions remove <permission>` - Remove a permission from monitoring\n"
                ),
                inline=False
            )
            
            await ctx.send(embed=embed)
            return
            
        # Update options
        if option.lower() in ["enable", "on", "true", "yes"]:
            settings["modules"]["permissions"]["enabled"] = True
            await ctx.send("✅ Permission monitoring is now **enabled**.")
            
        elif option.lower() in ["disable", "off", "false", "no"]:
            settings["modules"]["permissions"]["enabled"] = False
            await ctx.send("✅ Permission monitoring is now **disabled**.")
            
        elif option.lower() == "add" and permission is not None:
            # Format permission to snake_case
            perm = permission.lower().replace(" ", "_")
            
            # Validate permission
            valid_perms = [
                "administrator", "ban_members", "kick_members", "manage_guild",
                "manage_roles", "manage_channels", "manage_webhooks", "manage_emojis",
                "mention_everyone", "manage_messages"
            ]
            
            if perm not in valid_perms:
                await ctx.send(f"❌ Invalid permission. Valid permissions are: {', '.join(valid_perms)}")
                return
                
            # Check if already monitored
            if perm in settings["modules"]["permissions"]["monitored"]:
                await ctx.send(f"❌ `{perm.replace('_', ' ').title()}` is already being monitored.")
                return
                
            # Add to monitored permissions
            settings["modules"]["permissions"]["monitored"].append(perm)
            await ctx.send(f"✅ Now monitoring `{perm.replace('_', ' ').title()}` permission changes.")
            
        elif option.lower() == "remove" and permission is not None:
            # Format permission to snake_case
            perm = permission.lower().replace(" ", "_")
            
            # Check if being monitored
            if perm not in settings["modules"]["permissions"]["monitored"]:
                await ctx.send(f"❌ `{perm.replace('_', ' ').title()}` is not being monitored.")
                return
                
            # Remove from monitored permissions
            settings["modules"]["permissions"]["monitored"].remove(perm)
            await ctx.send(f"✅ Stopped monitoring `{perm.replace('_', ' ').title()}` permission changes.")
            
        else:
            await ctx.send("❌ Invalid option. Use `enable`, `disable`, `add <permission>`, or `remove <permission>`.")
            return
            
        self.antinuke._save_settings()

async def setup(bot, antinuke_cog):
    await bot.add_cog(ModuleCommands(bot, antinuke_cog)) 