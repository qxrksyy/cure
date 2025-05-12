import discord
from discord.ext import commands
import asyncio
import logging
from datetime import datetime
import json
import os

logger = logging.getLogger('bot')

class RoleCommands(commands.Cog):
    """Commands for role management"""
    
    def __init__(self, bot):
        self.bot = bot
        self.data_folder = 'data/moderation'
        self.stickyroles_file = os.path.join(self.data_folder, 'stickyroles.json')
        # Create data directory if it doesn't exist
        os.makedirs(self.data_folder, exist_ok=True)
        # Load data
        self.stickyroles = self.load_stickyroles()
        # Active tasks
        self.role_tasks = {}
    
    def load_stickyroles(self):
        """Load the sticky roles from file"""
        try:
            if os.path.exists(self.stickyroles_file):
                with open(self.stickyroles_file, 'r') as f:
                    return json.load(f)
            else:
                return {}
        except json.JSONDecodeError:
            logger.error(f"Error decoding {self.stickyroles_file}. Using empty config.")
            return {}
    
    def save_stickyroles(self):
        """Save the sticky roles to file"""
        with open(self.stickyroles_file, 'w') as f:
            json.dump(self.stickyroles, f, indent=4)

    @commands.group(name="role", invoke_without_command=True)
    @commands.has_permissions(manage_roles=True)
    async def role(self, ctx, member: discord.Member, *, roles: commands.Greedy[discord.Role]):
        """Modify a member's roles"""
        if not roles:
            # If no roles provided, show the member's current roles
            role_list = [role.mention for role in member.roles if role != ctx.guild.default_role]
            if not role_list:
                await ctx.send(f"{member.mention} has no roles.")
                return
                
            embed = discord.Embed(
                title=f"Roles for {member.display_name}",
                description=", ".join(role_list),
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            await ctx.send(embed=embed)
            return
            
        # Add the roles
        try:
            # Filter out roles that are not assignable
            valid_roles = [role for role in roles if role.is_assignable()]
            
            if not valid_roles:
                await ctx.send("❌ None of the provided roles are assignable.")
                return
                
            await member.add_roles(*valid_roles, reason=f"Roles added by {ctx.author}")
            
            embed = discord.Embed(
                title="Roles Added",
                description=f"Added {len(valid_roles)} role(s) to {member.mention}",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(
                name="Roles", 
                value=", ".join([role.mention for role in valid_roles])
            )
            
            await ctx.send(embed=embed)
            
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to manage roles for that member.")
        except Exception as e:
            logger.error(f"Error adding roles: {str(e)}")
            await ctx.send(f"❌ An error occurred: {str(e)}")

    @role.command(name="create")
    @commands.has_permissions(manage_roles=True)
    async def role_create(self, ctx, name: str, *, color: discord.Color = discord.Color.default()):
        """Creates a role with optional color"""
        try:
            # Create the role
            role = await ctx.guild.create_role(
                name=name,
                color=color,
                reason=f"Role created by {ctx.author}"
            )
            
            embed = discord.Embed(
                title="Role Created",
                description=f"Created role {role.mention}",
                color=role.color,
                timestamp=datetime.utcnow()
            )
            
            await ctx.send(embed=embed)
            
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to create roles.")
        except Exception as e:
            logger.error(f"Error creating role: {str(e)}")
            await ctx.send(f"❌ An error occurred: {str(e)}")

    @role.command(name="delete")
    @commands.has_permissions(manage_roles=True)
    async def role_delete(self, ctx, *, role: discord.Role):
        """Deletes a role"""
        try:
            # Check if the role is manageable
            if not role.is_assignable():
                await ctx.send("❌ I cannot delete that role. It might be higher than my highest role or managed by an integration.")
                return
                
            role_name = role.name
            
            # Create a confirmation message
            confirm_msg = await ctx.send(
                f"⚠️ Are you sure you want to delete the role '{role_name}'? "
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
                    await confirm_msg.edit(content="❌ Role deletion cancelled.")
                    return
                
                # Delete the role
                await role.delete(reason=f"Role deleted by {ctx.author}")
                
                embed = discord.Embed(
                    title="Role Deleted",
                    description=f"Deleted role '{role_name}'",
                    color=discord.Color.red(),
                    timestamp=datetime.utcnow()
                )
                
                await ctx.send(embed=embed)
                
            except asyncio.TimeoutError:
                await confirm_msg.edit(content="❌ Role deletion timed out.")
                
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to delete that role.")
        except Exception as e:
            logger.error(f"Error deleting role: {str(e)}")
            await ctx.send(f"❌ An error occurred: {str(e)}")

    @role.command(name="edit")
    @commands.has_permissions(manage_roles=True)
    async def role_edit(self, ctx, role: discord.Role, *, name: str):
        """Change a role name"""
        try:
            # Check if the role is manageable
            if not role.is_assignable():
                await ctx.send("❌ I cannot edit that role. It might be higher than my highest role or managed by an integration.")
                return
                
            old_name = role.name
            
            # Edit the role
            await role.edit(name=name, reason=f"Role edited by {ctx.author}")
            
            embed = discord.Embed(
                title="Role Edited",
                description=f"Changed role name from '{old_name}' to '{name}'",
                color=role.color,
                timestamp=datetime.utcnow()
            )
            
            await ctx.send(embed=embed)
            
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to edit that role.")
        except Exception as e:
            logger.error(f"Error editing role: {str(e)}")
            await ctx.send(f"❌ An error occurred: {str(e)}")

    @role.command(name="color")
    @commands.has_permissions(manage_roles=True)
    async def role_color(self, ctx, role: discord.Role, *, color: discord.Color):
        """Changes a role's color"""
        try:
            # Check if the role is manageable
            if not role.is_assignable():
                await ctx.send("❌ I cannot edit that role. It might be higher than my highest role or managed by an integration.")
                return
                
            old_color = role.color
            
            # Edit the role
            await role.edit(color=color, reason=f"Role color changed by {ctx.author}")
            
            embed = discord.Embed(
                title="Role Color Changed",
                description=f"Changed color for role {role.mention}",
                color=color,
                timestamp=datetime.utcnow()
            )
            
            # Show color comparison
            embed.add_field(name="Old Color", value=str(old_color))
            embed.add_field(name="New Color", value=str(color))
            
            await ctx.send(embed=embed)
            
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to edit that role.")
        except Exception as e:
            logger.error(f"Error changing role color: {str(e)}")
            await ctx.send(f"❌ An error occurred: {str(e)}")

    @role.command(name="add")
    @commands.has_permissions(manage_roles=True)
    async def role_add(self, ctx, member: discord.Member, *, role: discord.Role):
        """Adds role to a member"""
        try:
            # Check if the role is assignable
            if not role.is_assignable():
                await ctx.send("❌ I cannot assign that role. It might be higher than my highest role or managed by an integration.")
                return
                
            if role in member.roles:
                await ctx.send(f"❌ {member.mention} already has the {role.mention} role.")
                return
                
            # Add the role
            await member.add_roles(role, reason=f"Role added by {ctx.author}")
            
            embed = discord.Embed(
                title="Role Added",
                description=f"Added {role.mention} to {member.mention}",
                color=role.color,
                timestamp=datetime.utcnow()
            )
            
            await ctx.send(embed=embed)
            
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to manage roles for that member.")
        except Exception as e:
            logger.error(f"Error adding role: {str(e)}")
            await ctx.send(f"❌ An error occurred: {str(e)}")

    @role.command(name="remove")
    @commands.has_permissions(manage_roles=True)
    async def role_remove(self, ctx, member: discord.Member, *, role: discord.Role):
        """Removes role from a member"""
        try:
            if role not in member.roles:
                await ctx.send(f"❌ {member.mention} doesn't have the {role.mention} role.")
                return
                
            # Remove the role
            await member.remove_roles(role, reason=f"Role removed by {ctx.author}")
            
            embed = discord.Embed(
                title="Role Removed",
                description=f"Removed {role.mention} from {member.mention}",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            
            await ctx.send(embed=embed)
            
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to manage roles for that member.")
        except Exception as e:
            logger.error(f"Error removing role: {str(e)}")
            await ctx.send(f"❌ An error occurred: {str(e)}")

    @commands.group(name="stickyrole", invoke_without_command=True)
    @commands.has_guild_permissions(administrator=True)
    async def stickyrole(self, ctx):
        """Reapplies a role on join"""
        await ctx.invoke(self.bot.get_command("stickyrole list"))

    @stickyrole.command(name="add")
    @commands.has_guild_permissions(administrator=True)
    async def stickyrole_add(self, ctx, member: discord.Member, *, role: discord.Role):
        """Reapplies a role on join"""
        guild_id = str(ctx.guild.id)
        member_id = str(member.id)
        
        # Initialize the guild in the stickyroles dict if it doesn't exist
        if guild_id not in self.stickyroles:
            self.stickyroles[guild_id] = {}
            
        # Initialize the member in the guild dict if they don't exist
        if member_id not in self.stickyroles[guild_id]:
            self.stickyroles[guild_id][member_id] = []
            
        # Check if the role is already sticky for this member
        if role.id in self.stickyroles[guild_id][member_id]:
            await ctx.send(f"❌ {role.mention} is already a sticky role for {member.mention}.")
            return
            
        # Add the role to the sticky roles list
        self.stickyroles[guild_id][member_id].append(role.id)
        self.save_stickyroles()
        
        # Make sure the member has the role
        if role not in member.roles:
            try:
                await member.add_roles(role, reason="Adding sticky role")
            except:
                # If we can't add the role, still make it sticky but inform the user
                await ctx.send(f"⚠️ Couldn't add {role.mention} to {member.mention}, but it will be re-applied if they leave and rejoin.")
                
        embed = discord.Embed(
            title="Sticky Role Added",
            description=f"{role.mention} will be reapplied to {member.mention} when they rejoin.",
            color=role.color,
            timestamp=datetime.utcnow()
        )
        
        await ctx.send(embed=embed)

    @stickyrole.command(name="remove")
    @commands.has_guild_permissions(administrator=True)
    async def stickyrole_remove(self, ctx, member: discord.Member, *, role: discord.Role):
        """Removes a setup sticky role"""
        guild_id = str(ctx.guild.id)
        member_id = str(member.id)
        
        # Check if the member has any sticky roles
        if (guild_id not in self.stickyroles or
            member_id not in self.stickyroles[guild_id] or
            role.id not in self.stickyroles[guild_id][member_id]):
            await ctx.send(f"❌ {role.mention} is not a sticky role for {member.mention}.")
            return
            
        # Remove the role from the sticky roles list
        self.stickyroles[guild_id][member_id].remove(role.id)
        
        # If the member has no more sticky roles, remove them from the dict
        if not self.stickyroles[guild_id][member_id]:
            del self.stickyroles[guild_id][member_id]
            
        # If the guild has no more members with sticky roles, remove it from the dict
        if not self.stickyroles[guild_id]:
            del self.stickyroles[guild_id]
            
        self.save_stickyroles()
        
        embed = discord.Embed(
            title="Sticky Role Removed",
            description=f"{role.mention} will no longer be reapplied to {member.mention} when they rejoin.",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        await ctx.send(embed=embed)

    @stickyrole.command(name="list")
    async def stickyrole_list(self, ctx):
        """View a list of every sticky role"""
        guild_id = str(ctx.guild.id)
        
        if guild_id not in self.stickyroles or not self.stickyroles[guild_id]:
            await ctx.send("❌ There are no sticky roles set up in this server.")
            return
            
        embed = discord.Embed(
            title="Sticky Roles",
            description="Roles that will be reapplied when members rejoin",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        for member_id, role_ids in self.stickyroles[guild_id].items():
            if not role_ids:  # Skip if no roles
                continue
                
            member = ctx.guild.get_member(int(member_id))
            if not member:
                continue
                
            roles = []
            for role_id in role_ids:
                role = ctx.guild.get_role(role_id)
                if role:
                    roles.append(role.mention)
                    
            if roles:
                embed.add_field(
                    name=f"{member.display_name} ({member.id})",
                    value=", ".join(roles),
                    inline=False
                )
                
        if not embed.fields:
            await ctx.send("❌ There are no valid sticky roles set up in this server.")
            return
            
        await ctx.send(embed=embed)

    # Event listener for sticky roles
    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Reapply sticky roles when a member joins"""
        guild_id = str(member.guild.id)
        member_id = str(member.id)
        
        # Check if the member has any sticky roles
        if (guild_id not in self.stickyroles or
            member_id not in self.stickyroles[guild_id]):
            return
            
        # Get the sticky roles
        role_ids = self.stickyroles[guild_id][member_id]
        roles_to_add = []
        
        for role_id in role_ids:
            role = member.guild.get_role(role_id)
            if role and role.is_assignable():
                roles_to_add.append(role)
                
        if roles_to_add:
            try:
                await member.add_roles(*roles_to_add, reason="Reapplying sticky roles")
                logger.info(f"Reapplied {len(roles_to_add)} sticky roles to {member.name} in {member.guild.name}")
            except Exception as e:
                logger.error(f"Error reapplying sticky roles: {str(e)}")

async def setup(bot):
    await bot.add_cog(RoleCommands(bot)) 