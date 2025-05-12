import discord
from discord.ext import commands
import json
import os
import logging
from datetime import datetime

logger = logging.getLogger('bot')

class AutoRole(commands.Cog):
    """Commands for automatic role assignment and management"""
    
    def __init__(self, bot):
        self.bot = bot
        self.config_path = "data/autorole"
        self.auto_roles = {}
        
        # Create directory if it doesn't exist
        os.makedirs(self.config_path, exist_ok=True)
        
        # Load auto roles
        self._load_auto_roles()
        
    def _load_auto_roles(self):
        """Load autorole settings from file"""
        try:
            filepath = f"{self.config_path}/autoroles.json"
            if os.path.exists(filepath):
                with open(filepath, "r") as f:
                    self.auto_roles = json.load(f)
        except Exception as e:
            logger.error(f"Error loading autorole settings: {str(e)}")
    
    def _save_auto_roles(self):
        """Save autorole settings to file"""
        try:
            filepath = f"{self.config_path}/autoroles.json"
            with open(filepath, "w") as f:
                json.dump(self.auto_roles, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving autorole settings: {str(e)}")
    
    def _get_guild_auto_roles(self, guild_id):
        """Get auto roles for a guild"""
        guild_id = str(guild_id)
        if guild_id not in self.auto_roles:
            self.auto_roles[guild_id] = []
            self._save_auto_roles()
        return self.auto_roles[guild_id]
    
    @commands.group(name="autorole", invoke_without_command=True)
    @commands.has_permissions(manage_guild=True, manage_roles=True)
    async def autorole(self, ctx):
        """Set up automatic role assign on member join"""
        auto_roles = self._get_guild_auto_roles(ctx.guild.id)
        
        embed = discord.Embed(
            title="Auto Role Configuration",
            description="Assign roles automatically when members join",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        if not auto_roles:
            embed.add_field(
                name="No Auto Roles Configured",
                value="Use `autorole add <role>` to add a role that will be assigned when a user joins",
                inline=False
            )
        else:
            roles_text = ""
            for role_id in auto_roles:
                role = ctx.guild.get_role(int(role_id))
                if role:
                    roles_text += f"• {role.mention}\n"
                else:
                    roles_text += f"• Role ID: {role_id} (Not Found)\n"
            
            embed.add_field(
                name="Auto Roles",
                value=roles_text or "No valid auto roles found",
                inline=False
            )
        
        embed.add_field(
            name="Commands",
            value=(
                "`autorole add <role>` - Add a role to assign on join\n"
                "`autorole remove <role>` - Remove a role from auto assignment\n"
                "`autorole list` - View all auto roles\n"
                "`autorole reset` - Clear all auto roles"
            ),
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @autorole.command(name="add")
    @commands.has_permissions(manage_guild=True, manage_roles=True)
    async def autorole_add(self, ctx, role: discord.Role):
        """Adds a autorole and assigns on join to member"""
        auto_roles = self._get_guild_auto_roles(ctx.guild.id)
        
        # Check if role is already an auto role
        if str(role.id) in auto_roles:
            await ctx.send(f"❌ {role.mention} is already configured as an auto role.")
            return
        
        # Check if bot can assign the role
        if not ctx.guild.me.top_role > role:
            await ctx.send(f"❌ I cannot assign {role.mention} as it is higher than my highest role.")
            return
        
        # Add to auto roles
        auto_roles.append(str(role.id))
        self._save_auto_roles()
        
        embed = discord.Embed(
            title="Auto Role Added",
            description=f"{role.mention} will now be automatically assigned to new members.",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )
        
        await ctx.send(embed=embed)
    
    @autorole.command(name="remove")
    @commands.has_permissions(manage_guild=True, manage_roles=True)
    async def autorole_remove(self, ctx, role: discord.Role):
        """Removes a autorole and stops assigning on join"""
        auto_roles = self._get_guild_auto_roles(ctx.guild.id)
        
        # Check if role is an auto role
        if str(role.id) not in auto_roles:
            await ctx.send(f"❌ {role.mention} is not configured as an auto role.")
            return
        
        # Remove from auto roles
        auto_roles.remove(str(role.id))
        self._save_auto_roles()
        
        embed = discord.Embed(
            title="Auto Role Removed",
            description=f"{role.mention} will no longer be automatically assigned to new members.",
            color=discord.Color.orange(),
            timestamp=datetime.utcnow()
        )
        
        await ctx.send(embed=embed)
    
    @autorole.command(name="list")
    @commands.has_permissions(manage_guild=True, manage_roles=True)
    async def autorole_list(self, ctx):
        """View a list of every auto role"""
        auto_roles = self._get_guild_auto_roles(ctx.guild.id)
        
        embed = discord.Embed(
            title="Auto Roles",
            description="Roles that are automatically assigned when a user joins",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        if not auto_roles:
            embed.add_field(
                name="No Auto Roles",
                value="No roles will be automatically assigned when users join.",
                inline=False
            )
        else:
            roles_text = ""
            for role_id in auto_roles:
                role = ctx.guild.get_role(int(role_id))
                if role:
                    roles_text += f"• {role.mention} (ID: {role.id})\n"
                else:
                    roles_text += f"• Role ID: {role_id} (Not Found)\n"
            
            embed.add_field(
                name="Auto Roles",
                value=roles_text or "No valid auto roles found",
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    @autorole.command(name="reset")
    @commands.has_permissions(manage_guild=True, manage_roles=True)
    async def autorole_reset(self, ctx):
        """Clears every autorole for guild"""
        # Ask for confirmation
        embed = discord.Embed(
            title="⚠️ Confirm Reset",
            description="Are you sure you want to clear all auto roles? This action cannot be undone.",
            color=discord.Color.red(),
            timestamp=datetime.utcnow()
        )
        
        message = await ctx.send(embed=embed)
        
        # Add confirmation reactions
        await message.add_reaction("✅")
        await message.add_reaction("❌")
        
        # Wait for confirmation
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == message.id
        
        try:
            reaction, user = await self.bot.wait_for("reaction_add", timeout=60.0, check=check)
            
            if str(reaction.emoji) == "✅":
                self.auto_roles[str(ctx.guild.id)] = []
                self._save_auto_roles()
                
                await message.delete()
                
                embed = discord.Embed(
                    title="Auto Roles Reset",
                    description="All auto roles have been cleared.",
                    color=discord.Color.green(),
                    timestamp=datetime.utcnow()
                )
                
                await ctx.send(embed=embed)
            else:
                await message.delete()
                await ctx.send("❌ Auto role reset cancelled.")
                
        except TimeoutError:
            await message.delete()
            await ctx.send("❌ Auto role reset timed out.")
    
    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Assign auto roles to new members"""
        # Skip bots if desired (can be made configurable)
        # if member.bot:
        #     return
        
        auto_roles = self._get_guild_auto_roles(member.guild.id)
        
        # If no auto roles, skip
        if not auto_roles:
            return
        
        # Try to assign each auto role
        for role_id in auto_roles:
            role = member.guild.get_role(int(role_id))
            if role and role < member.guild.me.top_role:
                try:
                    await member.add_roles(role, reason="Auto role assignment")
                    logger.info(f"Assigned auto role {role.name} to {member.name} in {member.guild.name}")
                except Exception as e:
                    logger.error(f"Failed to assign auto role {role.name} to {member.name}: {str(e)}")

async def setup(bot):
    await bot.add_cog(AutoRole(bot)) 