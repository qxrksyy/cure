import discord
from discord.ext import commands
import json
import os
import logging
from datetime import datetime

logger = logging.getLogger('bot')

# Available fake permissions
AVAILABLE_PERMISSIONS = {
    "manage_messages": "Manage Messages",
    "kick_members": "Kick Members",
    "ban_members": "Ban Members",
    "manage_nicknames": "Manage Nicknames",
    "manage_channels": "Manage Channels",
    "manage_roles": "Manage Roles",
    "manage_emojis": "Manage Emojis",
    "manage_webhooks": "Manage Webhooks",
    "manage_guild": "Manage Server",
    "mention_everyone": "Mention Everyone",
    "view_audit_log": "View Audit Log",
    "priority_speaker": "Priority Speaker",
    "mute_members": "Mute Members",
    "deafen_members": "Deafen Members",
    "move_members": "Move Members"
}

class FakePermissions(commands.Cog):
    """
    Fake permissions management for roles
    """
    
    def __init__(self, bot):
        self.bot = bot
        self.config_path = "data/servers"
        self.perm_config = {}
        
        # Create directory if it doesn't exist
        os.makedirs(self.config_path, exist_ok=True)
        
        # Load settings
        self._load_perm_config()
        
    def _load_perm_config(self):
        """Load permission settings from file"""
        try:
            filepath = f"{self.config_path}/fake_permissions.json"
            if os.path.exists(filepath):
                with open(filepath, "r") as f:
                    self.perm_config = json.load(f)
        except Exception as e:
            logger.error(f"Error loading permission settings: {str(e)}")
            self.perm_config = {}
    
    def _save_perm_config(self):
        """Save permission settings to file"""
        try:
            filepath = f"{self.config_path}/fake_permissions.json"
            with open(filepath, "w") as f:
                json.dump(self.perm_config, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving permission settings: {str(e)}")
    
    def _get_guild_perm_config(self, guild_id):
        """Get permission config for a guild"""
        guild_id = str(guild_id)
        if guild_id not in self.perm_config:
            self.perm_config[guild_id] = {
                "roles": {}  # Maps role_id -> list of permissions
            }
            self._save_perm_config()
        return self.perm_config[guild_id]
    
    def has_fake_permission(self, guild_id, member_id, permission):
        """Check if a member has a fake permission through role assignment"""
        guild_config = self._get_guild_perm_config(guild_id)
        guild = self.bot.get_guild(int(guild_id))
        
        if not guild:
            return False
            
        member = guild.get_member(int(member_id))
        if not member:
            return False
            
        # Check each of the member's roles
        for role in member.roles:
            role_id = str(role.id)
            if role_id in guild_config.get("roles", {}) and permission in guild_config["roles"][role_id]:
                return True
                
        return False
    
    @commands.group(name="fakepermissions", invoke_without_command=True)
    async def fakepermissions(self, ctx):
        """Set up fake permissions for role through the bot!"""
        embed = discord.Embed(
            title="Fake Permissions System",
            description="Grant roles permission to use bot commands without actual Discord permissions",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        guild_config = self._get_guild_perm_config(ctx.guild.id)
        
        # Add information about available permissions
        perms_text = "\n".join([f"• `{perm}`: {desc}" for perm, desc in AVAILABLE_PERMISSIONS.items()])
        embed.add_field(
            name="Available Permissions",
            value=perms_text or "No permissions available",
            inline=False
        )
        
        # Add information about commands
        embed.add_field(
            name="Available Commands",
            value=(
                "`fakepermissions add @role permission` - Grant a fake permission to a role\n"
                "`fakepermissions remove @role permission` - Remove a fake permission from a role\n"
                "`fakepermissions list [@role]` - List all fake permissions\n"
                "`fakepermissions reset` - Reset all fake permissions"
            ),
            inline=False
        )
        
        # Note on usage
        embed.add_field(
            name="📝 Note",
            value=(
                "These permissions only apply to bot commands, not actual Discord permissions.\n"
                "This allows you to grant specific bot functionality to roles without giving them "
                "potentially dangerous Discord permissions."
            ),
            inline=False
        )
        
        await ctx.send(embed=embed)
        
    @fakepermissions.command(name="add")
    @commands.has_permissions(administrator=True)
    async def fakepermissions_add(self, ctx, role: discord.Role = None, permission: str = None):
        """Grant a fake permission to a role"""
        if not ctx.author.id == ctx.guild.owner_id:
            await ctx.send("❌ Only the server owner can manage fake permissions.")
            return
            
        if role is None:
            await ctx.send("❌ Please specify a role to grant permission to.")
            return
            
        if permission is None:
            perms_text = ", ".join([f"`{perm}`" for perm in AVAILABLE_PERMISSIONS.keys()])
            await ctx.send(f"❌ Please specify a permission to grant. Available permissions: {perms_text}")
            return
            
        # Validate permission
        if permission.lower() not in AVAILABLE_PERMISSIONS:
            perms_text = ", ".join([f"`{perm}`" for perm in AVAILABLE_PERMISSIONS.keys()])
            await ctx.send(f"❌ Invalid permission. Available permissions: {perms_text}")
            return
            
        permission = permission.lower()
            
        guild_config = self._get_guild_perm_config(ctx.guild.id)
        
        # Initialize role entry if it doesn't exist
        if "roles" not in guild_config:
            guild_config["roles"] = {}
            
        if str(role.id) not in guild_config["roles"]:
            guild_config["roles"][str(role.id)] = []
            
        # Check if permission is already granted
        if permission in guild_config["roles"][str(role.id)]:
            await ctx.send(f"❌ {role.mention} already has the `{permission}` permission.")
            return
            
        # Grant permission
        guild_config["roles"][str(role.id)].append(permission)
        self._save_perm_config()
        
        await ctx.send(f"✅ Granted `{permission}` permission to {role.mention}.")
        
    @fakepermissions.command(name="remove")
    @commands.has_permissions(administrator=True)
    async def fakepermissions_remove(self, ctx, role: discord.Role = None, permission: str = None):
        """Remove a fake permission from a role"""
        if not ctx.author.id == ctx.guild.owner_id:
            await ctx.send("❌ Only the server owner can manage fake permissions.")
            return
            
        if role is None:
            await ctx.send("❌ Please specify a role to remove permission from.")
            return
            
        if permission is None:
            perms_text = ", ".join([f"`{perm}`" for perm in AVAILABLE_PERMISSIONS.keys()])
            await ctx.send(f"❌ Please specify a permission to remove. Available permissions: {perms_text}")
            return
            
        permission = permission.lower()
            
        guild_config = self._get_guild_perm_config(ctx.guild.id)
        
        # Check if role has permissions
        if str(role.id) not in guild_config.get("roles", {}):
            await ctx.send(f"❌ {role.mention} doesn't have any fake permissions.")
            return
            
        # Check if role has the specified permission
        if permission not in guild_config["roles"][str(role.id)]:
            await ctx.send(f"❌ {role.mention} doesn't have the `{permission}` permission.")
            return
            
        # Remove permission
        guild_config["roles"][str(role.id)].remove(permission)
        
        # If no permissions left, remove role entry
        if not guild_config["roles"][str(role.id)]:
            del guild_config["roles"][str(role.id)]
            
        self._save_perm_config()
        
        await ctx.send(f"✅ Removed `{permission}` permission from {role.mention}.")
        
    @fakepermissions.command(name="list")
    @commands.has_permissions(administrator=True)
    async def fakepermissions_list(self, ctx, role: discord.Role = None):
        """List all fake permissions"""
        if not ctx.author.id == ctx.guild.owner_id:
            await ctx.send("❌ Only the server owner can view fake permissions.")
            return
            
        guild_config = self._get_guild_perm_config(ctx.guild.id)
        
        embed = discord.Embed(
            title="Fake Permissions List",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        # If role specified, only show permissions for that role
        if role:
            role_id = str(role.id)
            if role_id not in guild_config.get("roles", {}):
                embed.description = f"{role.mention} does not have any fake permissions."
            else:
                perms = guild_config["roles"][role_id]
                perms_text = "\n".join([f"• `{perm}`: {AVAILABLE_PERMISSIONS.get(perm, 'Unknown')}" for perm in perms])
                embed.add_field(
                    name=f"Permissions for {role.name}",
                    value=perms_text or "No permissions",
                    inline=False
                )
        # Otherwise show all roles
        else:
            if not guild_config.get("roles", {}):
                embed.description = "No fake permissions have been configured."
            else:
                for role_id, perms in guild_config.get("roles", {}).items():
                    role_obj = ctx.guild.get_role(int(role_id))
                    if not role_obj:
                        continue
                        
                    perms_text = ", ".join([f"`{perm}`" for perm in perms])
                    embed.add_field(
                        name=f"{role_obj.name}",
                        value=perms_text or "No permissions",
                        inline=False
                    )
                    
        await ctx.send(embed=embed)
        
    @fakepermissions.command(name="reset")
    @commands.has_permissions(administrator=True)
    async def fakepermissions_reset(self, ctx):
        """Reset all fake permissions"""
        if not ctx.author.id == ctx.guild.owner_id:
            await ctx.send("❌ Only the server owner can reset fake permissions.")
            return
            
        # Confirm reset
        confirm_msg = await ctx.send(
            "⚠️ **Warning**: This will remove all fake permissions for all roles. "
            "Are you sure? Type `yes` to confirm."
        )
        
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() == "yes"
            
        try:
            await self.bot.wait_for("message", check=check, timeout=30.0)
        except:
            await confirm_msg.edit(content="Operation cancelled.")
            return
            
        # Reset permissions
        if str(ctx.guild.id) in self.perm_config:
            del self.perm_config[str(ctx.guild.id)]
            self._save_perm_config()
            
        await ctx.send("✅ All fake permissions have been reset.")

async def setup(bot):
    await bot.add_cog(FakePermissions(bot)) 