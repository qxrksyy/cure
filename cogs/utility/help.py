import discord
from discord.ext import commands
import datetime

class CustomHelp(commands.Cog):
    """Custom help command implementation"""
    
    def __init__(self, bot):
        self.bot = bot
        self._original_help_command = bot.help_command
        bot.help_command = CustomHelpCommand()
        bot.help_command.cog = self
        bot.help_command.name = "bothelp"
        
    def cog_unload(self):
        self.bot.help_command = self._original_help_command

class CustomHelpCommand(commands.HelpCommand):
    """A custom help command that displays commands in categories with their descriptions."""
    
    async def send_bot_help(self, mapping):
        """Send the main help page with command categories."""
        embed = discord.Embed(
            title="Bot Help",
            description="Use `!help [command]` for more info on a command.\nUse `!help [category]` for more info on a category.",
            color=discord.Color.blue(),
            timestamp=datetime.datetime.utcnow()
        )
        
        # Filter to only show cogs with commands and sort them
        filtered_mapping = {cog: cmds for cog, cmds in mapping.items() if cmds and (cog is not None)}
        sorted_cogs = sorted(filtered_mapping.keys(), key=lambda x: x.qualified_name if x else "")
        
        # Add fields for each cog
        for cog in sorted_cogs:
            commands_list = await self.filter_commands(mapping[cog], sort=True)
            if not commands_list:
                continue
                
            cog_name = cog.qualified_name
            command_signatures = [f"`{cmd.name}`" for cmd in commands_list]
            
            # Only show first 10 commands per category in main help
            if len(command_signatures) > 10:
                command_signatures = command_signatures[:10]
                command_signatures.append(f"... and {len(commands_list) - 10} more")
                
            commands_text = ", ".join(command_signatures)
            
            # Check if cog_name already ends with "Commands"
            if cog_name.endswith("Commands"):
                display_name = cog_name
            else:
                display_name = f"{cog_name} Commands"
                
            embed.add_field(
                name=display_name,
                value=f"{cog.description or 'No description'}\n{commands_text}",
                inline=False
            )
            
        embed.set_footer(text=f"Requested by {self.context.author}", icon_url=self.context.author.display_avatar.url)
        
        await self.get_destination().send(embed=embed)
        
    async def send_cog_help(self, cog):
        """Send help for a specific category (cog)."""
        # Use the same naming convention as in send_bot_help
        cog_name = cog.qualified_name
        if cog_name.endswith("Commands"):
            display_name = cog_name
        else:
            display_name = f"{cog_name} Commands"
            
        embed = discord.Embed(
            title=display_name,
            description=cog.description or "No description provided.",
            color=discord.Color.green(),
            timestamp=datetime.datetime.utcnow()
        )
        
        # Add commands from this cog
        commands_list = await self.filter_commands(cog.get_commands(), sort=True)
        
        for command in commands_list:
            # Get command signature and description
            signature = self.get_command_signature(command)
            description = command.help or "No description provided."
            
            embed.add_field(
                name=signature,
                value=description,
                inline=False
            )
            
        if not commands_list:
            embed.add_field(name="No Commands", value="This category has no commands available to you.")
            
        embed.set_footer(text=f"Requested by {self.context.author}", icon_url=self.context.author.display_avatar.url)
        
        await self.get_destination().send(embed=embed)
        
    async def send_command_help(self, command):
        """Send help for a specific command."""
        embed = discord.Embed(
            title=f"Command: {command.name}",
            color=discord.Color.gold(),
            timestamp=datetime.datetime.utcnow()
        )
        
        # Add command details
        signature = self.get_command_signature(command)
        embed.add_field(name="Usage", value=f"`{signature}`", inline=False)
        
        if command.help:
            embed.add_field(name="Description", value=command.help, inline=False)
            
        if command.aliases:
            aliases = ", ".join(f"`{alias}`" for alias in command.aliases)
            embed.add_field(name="Aliases", value=aliases, inline=False)
            
        if isinstance(command, commands.Group):
            subcommands = list(command.commands)
            if subcommands:
                subcommands_text = ", ".join(f"`{cmd.name}`" for cmd in subcommands)
                embed.add_field(name="Subcommands", value=subcommands_text, inline=False)
                embed.add_field(name="Note", value="Use `!help [command] [subcommand]` for more info on a subcommand.", inline=False)
        
        # Check for required permissions
        checks = getattr(command, "checks", [])
        permissions = []
        
        for check in checks:
            # Try to extract permissions from the check
            if hasattr(check, "__qualname__"):
                name = check.__qualname__
                if "has_permissions" in name:
                    # Extract the permission
                    param_str = str(check)
                    if "has_permissions" in param_str:
                        import re
                        result = re.search(r'has_permissions\((.*?)\)', param_str)
                        if result:
                            perms = result.group(1).split(",")
                            for perm in perms:
                                if "=" in perm:
                                    perm_name = perm.split("=")[0].strip()
                                    permissions.append(perm_name.replace("_", " ").title())
                                    
        if permissions:
            embed.add_field(name="Required Permissions", value=", ".join(permissions), inline=False)
            
        embed.set_footer(text=f"Requested by {self.context.author}", icon_url=self.context.author.display_avatar.url)
        
        await self.get_destination().send(embed=embed)
        
    async def send_group_help(self, group):
        """Send help for a command group with subcommands."""
        embed = discord.Embed(
            title=f"Command Group: {group.name}",
            description=group.help or "No description provided.",
            color=discord.Color.purple(),
            timestamp=datetime.datetime.utcnow()
        )
        
        # Add command details
        signature = self.get_command_signature(group)
        embed.add_field(name="Usage", value=f"`{signature}`", inline=False)
        
        if group.aliases:
            aliases = ", ".join(f"`{alias}`" for alias in group.aliases)
            embed.add_field(name="Aliases", value=aliases, inline=False)
            
        # Add subcommands
        filtered_commands = await self.filter_commands(group.commands, sort=True)
        if filtered_commands:
            for command in filtered_commands:
                name = f"{command.name}"
                value = command.help or "No description provided."
                embed.add_field(name=name, value=value, inline=False)
                
        # If no subcommands could be displayed due to filtering
        if not filtered_commands:
            embed.add_field(
                name="No Subcommands Available",
                value="You don't have permissions to use any subcommands in this group.",
                inline=False
            )
            
        embed.set_footer(text=f"Requested by {self.context.author}", icon_url=self.context.author.display_avatar.url)
        
        await self.get_destination().send(embed=embed)
        
    async def send_error_message(self, error):
        """Send an error message when a command is not found."""
        embed = discord.Embed(
            title="Help Error",
            description=error,
            color=discord.Color.red(),
            timestamp=datetime.datetime.utcnow()
        )
        embed.set_footer(text=f"Requested by {self.context.author}", icon_url=self.context.author.display_avatar.url)
        
        await self.get_destination().send(embed=embed)

async def setup(bot):
    await bot.add_cog(CustomHelp(bot)) 