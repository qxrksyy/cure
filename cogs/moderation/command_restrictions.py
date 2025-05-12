import discord
from discord.ext import commands
import json
import os
import logging
from datetime import datetime

logger = logging.getLogger('bot')

class CommandRestrictions(commands.Cog):
    """Commands for restricting who can use specific commands"""
    
    def __init__(self, bot):
        self.bot = bot
        self.data_folder = 'data/moderation'
        self.restrictions_file = os.path.join(self.data_folder, 'command_restrictions.json')
        # Create data directory if it doesn't exist
        os.makedirs(self.data_folder, exist_ok=True)
        # Load data
        self.restrictions = self.load_restrictions()
    
    def load_restrictions(self):
        """Load the command restrictions from file"""
        try:
            if os.path.exists(self.restrictions_file):
                with open(self.restrictions_file, 'r') as f:
                    return json.load(f)
            else:
                return {}
        except json.JSONDecodeError:
            logger.error(f"Error decoding {self.restrictions_file}. Using empty config.")
            return {}
    
    def save_restrictions(self):
        """Save the command restrictions to file"""
        with open(self.restrictions_file, 'w') as f:
            json.dump(self.restrictions, f, indent=4)

    @commands.group(name="restrictcommand", aliases=["restrictcmd"], invoke_without_command=True)
    @commands.has_permissions(manage_guild=True)
    async def restrictcommand(self, ctx):
        """Only allows people with a certain role to use command"""
        await ctx.invoke(self.bot.get_command("restrictcommand list"))

    @restrictcommand.command(name="add")
    @commands.has_permissions(manage_guild=True)
    async def restrictcommand_add(self, ctx, cmd: str, *, role: discord.Role):
        """Allows the specified role exclusive permission to use a command"""
        guild_id = str(ctx.guild.id)
        
        # Initialize the guild in restrictions dict if it doesn't exist
        if guild_id not in self.restrictions:
            self.restrictions[guild_id] = {}
            
        # Check if the command exists
        cmd = cmd.lower()
        command = self.bot.get_command(cmd)
        
        if not command:
            await ctx.send(f"❌ Command `{cmd}` not found.")
            return
            
        # Store the command name (not the aliases)
        cmd_name = command.qualified_name
        
        # Add restriction
        if cmd_name not in self.restrictions[guild_id]:
            self.restrictions[guild_id][cmd_name] = []
            
        if role.id in self.restrictions[guild_id][cmd_name]:
            await ctx.send(f"❌ {role.mention} already has exclusive permission to use `{cmd_name}`.")
            return
            
        self.restrictions[guild_id][cmd_name].append(role.id)
        self.save_restrictions()
        
        embed = discord.Embed(
            title="Command Restricted",
            description=f"Only members with {role.mention} can now use `{cmd_name}`.",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        await ctx.send(embed=embed)

    @restrictcommand.command(name="remove")
    @commands.has_permissions(manage_guild=True)
    async def restrictcommand_remove(self, ctx, cmd: str, *, role: discord.Role):
        """Removes the specified role's exclusive permission to use a command"""
        guild_id = str(ctx.guild.id)
        
        # Check if the guild has restrictions
        if guild_id not in self.restrictions:
            await ctx.send("❌ This server has no command restrictions.")
            return
            
        # Check if the command exists
        cmd = cmd.lower()
        command = self.bot.get_command(cmd)
        
        if not command:
            await ctx.send(f"❌ Command `{cmd}` not found.")
            return
            
        # Store the command name (not the aliases)
        cmd_name = command.qualified_name
        
        # Check if the command is restricted
        if cmd_name not in self.restrictions[guild_id]:
            await ctx.send(f"❌ Command `{cmd_name}` is not restricted.")
            return
            
        # Check if the role has permission
        if role.id not in self.restrictions[guild_id][cmd_name]:
            await ctx.send(f"❌ {role.mention} does not have exclusive permission to use `{cmd_name}`.")
            return
            
        # Remove restriction
        self.restrictions[guild_id][cmd_name].remove(role.id)
        
        # Clean up if no more roles have permission
        if not self.restrictions[guild_id][cmd_name]:
            del self.restrictions[guild_id][cmd_name]
            
        # Clean up if no more commands are restricted
        if not self.restrictions[guild_id]:
            del self.restrictions[guild_id]
            
        self.save_restrictions()
        
        embed = discord.Embed(
            title="Command Restriction Removed",
            description=f"{role.mention}'s exclusive permission to use `{cmd_name}` has been removed.",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )
        
        await ctx.send(embed=embed)

    @restrictcommand.command(name="list")
    @commands.has_permissions(manage_guild=True)
    async def restrictcommand_list(self, ctx):
        """View a list of every restricted command"""
        guild_id = str(ctx.guild.id)
        
        # Check if the guild has restrictions
        if guild_id not in self.restrictions or not self.restrictions[guild_id]:
            await ctx.send("❌ This server has no command restrictions.")
            return
            
        embed = discord.Embed(
            title="Command Restrictions",
            description="Commands that are restricted to specific roles",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        for cmd_name, role_ids in self.restrictions[guild_id].items():
            roles = []
            for role_id in role_ids:
                role = ctx.guild.get_role(role_id)
                if role:
                    roles.append(role.mention)
                    
            if roles:
                embed.add_field(
                    name=f"!{cmd_name}",
                    value=f"Can be used by: {', '.join(roles)}",
                    inline=False
                )
                
        if not embed.fields:
            await ctx.send("❌ This server has no valid command restrictions.")
            return
            
        await ctx.send(embed=embed)

    @restrictcommand.command(name="reset")
    @commands.has_permissions(manage_guild=True)
    async def restrictcommand_reset(self, ctx):
        """Removes every restricted command"""
        guild_id = str(ctx.guild.id)
        
        # Check if the guild has restrictions
        if guild_id not in self.restrictions or not self.restrictions[guild_id]:
            await ctx.send("❌ This server has no command restrictions.")
            return
            
        # Create a confirmation message
        confirm_msg = await ctx.send(
            f"⚠️ Are you sure you want to remove ALL command restrictions in this server? "
            f"This will affect {len(self.restrictions[guild_id])} commands. "
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
                await confirm_msg.edit(content="❌ Command restriction reset cancelled.")
                return
                
            # Reset restrictions
            del self.restrictions[guild_id]
            self.save_restrictions()
            
            embed = discord.Embed(
                title="Command Restrictions Reset",
                description="All command restrictions in this server have been removed.",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            
            await ctx.send(embed=embed)
            
        except asyncio.TimeoutError:
            await confirm_msg.edit(content="❌ Command restriction reset timed out.")

    # Command-level check to enforce restrictions
    async def bot_check(self, ctx):
        """Global check to enforce command restrictions"""
        # Skip checks for DMs
        if not ctx.guild:
            return True
            
        # Skip checks for guild owners and administrators
        if ctx.author.id == ctx.guild.owner_id or ctx.author.guild_permissions.administrator:
            return True
            
        guild_id = str(ctx.guild.id)
        cmd_name = ctx.command.qualified_name
        
        # Check if the guild has restrictions
        if guild_id not in self.restrictions:
            return True
            
        # Check if the command is restricted
        if cmd_name not in self.restrictions[guild_id]:
            return True
            
        # Check if the user has any of the required roles
        allowed_role_ids = self.restrictions[guild_id][cmd_name]
        member_role_ids = [role.id for role in ctx.author.roles]
        
        if any(role_id in member_role_ids for role_id in allowed_role_ids):
            return True
            
        # User doesn't have permission to use this command
        await ctx.send(f"❌ You don't have permission to use this command.", delete_after=5)
        return False

async def setup(bot):
    await bot.add_cog(CommandRestrictions(bot)) 