import discord
from discord.ext import commands
from discord import app_commands
from discord import ui
import json
import os
import logging
from datetime import datetime
import uuid

logger = logging.getLogger('bot')

class RoleButton(ui.Button):
    def __init__(self, role_id, label, style, emoji=None, custom_id=None):
        super().__init__(
            style=style,
            label=label,
            emoji=emoji,
            custom_id=custom_id or f"role_button_{uuid.uuid4()}"
        )
        self.role_id = role_id
    
    async def callback(self, interaction: discord.Interaction):
        """Handle button press to assign/remove a role"""
        # Get the role
        guild = interaction.guild
        user = interaction.user
        role = guild.get_role(int(self.role_id))
        
        if not role:
            await interaction.response.send_message(
                f"Role not found! Please contact an administrator.", 
                ephemeral=True
            )
            return
        
        # Check if user already has the role
        if role in user.roles:
            # Remove the role
            try:
                await user.remove_roles(role, reason="Button role removal")
                await interaction.response.send_message(
                    f"Removed the role {role.mention}!", 
                    ephemeral=True
                )
            except discord.Forbidden:
                await interaction.response.send_message(
                    "I don't have permission to remove that role.", 
                    ephemeral=True
                )
        else:
            # Add the role
            try:
                await user.add_roles(role, reason="Button role assignment")
                await interaction.response.send_message(
                    f"Assigned you the role {role.mention}!", 
                    ephemeral=True
                )
            except discord.Forbidden:
                await interaction.response.send_message(
                    "I don't have permission to assign that role.", 
                    ephemeral=True
                )

class ButtonRoleView(ui.View):
    def __init__(self, button_role_data):
        super().__init__(timeout=None)
        
        # Add all buttons to the view
        for button_data in button_role_data:
            style = getattr(
                discord.ButtonStyle, 
                button_data.get("style", "primary").lower(),
                discord.ButtonStyle.primary
            )
            
            button = RoleButton(
                role_id=button_data["role_id"],
                label=button_data.get("label", "Get Role"),
                style=style,
                emoji=button_data.get("emoji"),
                custom_id=button_data.get("custom_id")
            )
            
            self.add_item(button)

class ButtonRoles(commands.Cog):
    """Commands for setting up button-based role assignment"""
    
    def __init__(self, bot):
        self.bot = bot
        self.config_path = "data/autorole"
        self.button_roles = {}
        
        # Create directory if it doesn't exist
        os.makedirs(self.config_path, exist_ok=True)
        
        # Load button roles
        self._load_button_roles()
        
        # Register persistent views
        bot.loop.create_task(self._register_views())
    
    async def _register_views(self):
        """Register button views when the bot starts"""
        await self.bot.wait_until_ready()
        
        # Register views for each saved button role message
        for guild_id, guild_data in self.button_roles.items():
            for channel_id, channel_data in guild_data.items():
                for message_id, message_data in channel_data.items():
                    view = ButtonRoleView(message_data["buttons"])
                    self.bot.add_view(view, message_id=int(message_id))
        
        logger.info("Registered button role views")
    
    def _load_button_roles(self):
        """Load button role settings from file"""
        try:
            filepath = f"{self.config_path}/buttonroles.json"
            if os.path.exists(filepath):
                with open(filepath, "r") as f:
                    self.button_roles = json.load(f)
        except Exception as e:
            logger.error(f"Error loading button role settings: {str(e)}")
    
    def _save_button_roles(self):
        """Save button role settings to file"""
        try:
            filepath = f"{self.config_path}/buttonroles.json"
            with open(filepath, "w") as f:
                json.dump(self.button_roles, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving button role settings: {str(e)}")
    
    @commands.group(name="buttonrole", invoke_without_command=True)
    @commands.has_permissions(manage_guild=True, manage_roles=True)
    async def buttonrole(self, ctx):
        """Set up self-assignable roles with buttons"""
        embed = discord.Embed(
            title="Button Role Configuration",
            description="Set up buttons that users can click to assign themselves roles",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(
            name="Commands",
            value=(
                "`buttonrole list` - View a list of every button role\n"
                "`buttonrole remove <message> <index>` - Remove a button role from a message\n"
                "`buttonrole reset` - Clears every button role from guild\n"
                "`buttonrole removeall <message>` - Removes all button roles from a message"
            ),
            inline=False
        )
        
        embed.add_field(
            name="Creating Button Roles",
            value=(
                "To create a button role:\n"
                "1. Send a message with `{role:ROLE_NAME}` placeholders\n"
                "2. Reply to that message with `buttonrole create`\n"
                "3. The placeholders will be replaced with buttons to assign the roles"
            ),
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @buttonrole.command(name="create")
    @commands.has_permissions(manage_guild=True, manage_roles=True)
    async def buttonrole_create(self, ctx):
        """Create button roles from a message template"""
        # Check if the message is a reply
        if not ctx.message.reference:
            await ctx.send("❌ You must reply to a message to create button roles.")
            return
        
        # Get the message being replied to
        try:
            channel = ctx.channel
            target_message = await channel.fetch_message(ctx.message.reference.message_id)
        except discord.NotFound:
            await ctx.send("❌ Could not find the message you're replying to.")
            return
        
        # Parse the message for role placeholders
        content = target_message.content
        import re
        
        # Match {role:ROLE_NAME} or {role:ROLE_NAME:LABEL:COLOR}
        # COLOR can be one of: primary (blurple), secondary (grey), success (green), danger (red)
        role_placeholders = re.findall(r'\{role:([^:}]+)(?::([^:}]+)?)?(?::([^:}]+)?)?\}', content)
        
        if not role_placeholders:
            await ctx.send("❌ No role placeholders found in the message. Use `{role:ROLE_NAME}` format.")
            return
        
        # Prepare for button creation
        buttons_data = []
        content_to_update = content
        
        # Process each placeholder
        for role_name, label, style in role_placeholders:
            # Find the role
            role = discord.utils.get(ctx.guild.roles, name=role_name.strip())
            if not role:
                await ctx.send(f"❌ Role '{role_name}' not found.")
                continue
            
            # Check bot permissions
            if role.position >= ctx.guild.me.top_role.position:
                await ctx.send(f"❌ I cannot assign the role '{role_name}' as it is higher than my highest role.")
                continue
            
            # Default values
            button_label = label.strip() if label else role.name
            button_style = style.strip().lower() if style else "primary"
            
            # Validate style
            valid_styles = ["primary", "secondary", "success", "danger"]
            if button_style not in valid_styles:
                button_style = "primary"
            
            # Generate a custom ID for this button
            custom_id = f"role_button_{role.id}_{uuid.uuid4()}"
            
            # Add to button data
            button_data = {
                "role_id": str(role.id),
                "label": button_label,
                "style": button_style,
                "custom_id": custom_id
            }
            
            buttons_data.append(button_data)
            
            # Update content (remove placeholder)
            placeholder = f"{{role:{role_name}{':' + label if label else ''}{':' + style if style else ''}}}"
            content_to_update = content_to_update.replace(placeholder, "")
        
        # If no valid roles found, stop
        if not buttons_data:
            await ctx.send("❌ No valid roles found in placeholders.")
            return
        
        # Clean up the content
        content_to_update = content_to_update.strip()
        
        # Create a new message with the buttons
        view = ButtonRoleView(buttons_data)
        
        try:
            # Send the new message with buttons
            new_message = await channel.send(content=content_to_update or "Click a button to get/remove a role:", view=view)
            
            # Save button role data
            guild_id = str(ctx.guild.id)
            channel_id = str(channel.id)
            message_id = str(new_message.id)
            
            if guild_id not in self.button_roles:
                self.button_roles[guild_id] = {}
            
            if channel_id not in self.button_roles[guild_id]:
                self.button_roles[guild_id][channel_id] = {}
            
            self.button_roles[guild_id][channel_id][message_id] = {
                "buttons": buttons_data,
                "created_at": datetime.utcnow().isoformat(),
                "created_by": str(ctx.author.id)
            }
            
            self._save_button_roles()
            
            # Delete the original message if the bot has permissions
            try:
                await target_message.delete()
            except:
                pass
            
            # Delete the command message
            try:
                await ctx.message.delete()
            except:
                pass
            
        except Exception as e:
            logger.error(f"Error creating button roles: {str(e)}")
            await ctx.send(f"❌ Error creating button roles: {str(e)}")
    
    @buttonrole.command(name="list")
    @commands.has_permissions(manage_guild=True, manage_roles=True)
    async def buttonrole_list(self, ctx):
        """View a list of every button role"""
        guild_id = str(ctx.guild.id)
        
        # Check if guild has any button roles
        if guild_id not in self.button_roles or not self.button_roles[guild_id]:
            await ctx.send("❌ This server has no button roles set up.")
            return
        
        embed = discord.Embed(
            title="Button Roles",
            description="All button role messages in this server",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        # List all button role messages
        for channel_id, channel_data in self.button_roles[guild_id].items():
            channel = ctx.guild.get_channel(int(channel_id))
            channel_name = f"#{channel.name}" if channel else f"Unknown Channel ({channel_id})"
            
            message_list = ""
            for message_id, message_data in channel_data.items():
                # List roles in this message
                roles_text = ""
                for i, button in enumerate(message_data["buttons"]):
                    role = ctx.guild.get_role(int(button["role_id"]))
                    role_name = role.name if role else f"Unknown Role ({button['role_id']})"
                    roles_text += f"{i+1}. {role_name} ({button['label']})\n"
                
                message_list += f"**Message ID: {message_id}**\n{roles_text}\n"
            
            if message_list:
                embed.add_field(
                    name=channel_name,
                    value=message_list,
                    inline=False
                )
        
        await ctx.send(embed=embed)
    
    @buttonrole.command(name="remove")
    @commands.has_permissions(manage_guild=True, manage_roles=True)
    async def buttonrole_remove(self, ctx, message_id: str, index: int):
        """Remove a button role from a message"""
        guild_id = str(ctx.guild.id)
        
        # Find the message
        message_found = False
        target_channel_id = None
        
        if guild_id in self.button_roles:
            for channel_id, channel_data in self.button_roles[guild_id].items():
                if message_id in channel_data:
                    message_found = True
                    target_channel_id = channel_id
                    break
        
        if not message_found:
            await ctx.send("❌ Message not found in button roles database.")
            return
        
        # Check if index is valid
        message_data = self.button_roles[guild_id][target_channel_id][message_id]
        if index < 1 or index > len(message_data["buttons"]):
            await ctx.send(f"❌ Invalid index. Please choose a number between 1 and {len(message_data['buttons'])}.")
            return
        
        # Get role info for confirmation
        button_data = message_data["buttons"][index-1]
        role_id = button_data["role_id"]
        role = ctx.guild.get_role(int(role_id))
        role_name = role.name if role else f"Unknown Role ({role_id})"
        
        # Confirm removal
        embed = discord.Embed(
            title="⚠️ Confirm Removal",
            description=f"Are you sure you want to remove the button for role '{role_name}'?",
            color=discord.Color.orange(),
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
                # Remove the button
                removed_button = message_data["buttons"].pop(index-1)
                
                # If no buttons left, remove the whole message entry
                if not message_data["buttons"]:
                    del self.button_roles[guild_id][target_channel_id][message_id]
                    
                    # If no messages left in channel, remove channel entry
                    if not self.button_roles[guild_id][target_channel_id]:
                        del self.button_roles[guild_id][target_channel_id]
                        
                        # If no channels left in guild, remove guild entry
                        if not self.button_roles[guild_id]:
                            del self.button_roles[guild_id]
                
                self._save_button_roles()
                
                # Try to update the message
                try:
                    channel = ctx.guild.get_channel(int(target_channel_id))
                    if channel:
                        msg = await channel.fetch_message(int(message_id))
                        
                        if message_data["buttons"]:
                            # Create a new view with the remaining buttons
                            view = ButtonRoleView(message_data["buttons"])
                            await msg.edit(view=view)
                        else:
                            # No buttons left, delete the message or remove components
                            try:
                                await msg.delete()
                            except:
                                await msg.edit(view=None)
                except Exception as e:
                    logger.error(f"Error updating button role message: {str(e)}")
                
                await message.delete()
                
                embed = discord.Embed(
                    title="Button Role Removed",
                    description=f"Removed button for role '{role_name}' from message.",
                    color=discord.Color.green(),
                    timestamp=datetime.utcnow()
                )
                
                await ctx.send(embed=embed)
            else:
                await message.delete()
                await ctx.send("❌ Button role removal cancelled.")
                
        except TimeoutError:
            await message.delete()
            await ctx.send("❌ Button role removal timed out.")
    
    @buttonrole.command(name="removeall")
    @commands.has_permissions(manage_guild=True, manage_roles=True)
    async def buttonrole_removeall(self, ctx, message_id: str):
        """Removes all button roles from a message"""
        guild_id = str(ctx.guild.id)
        
        # Find the message
        message_found = False
        target_channel_id = None
        
        if guild_id in self.button_roles:
            for channel_id, channel_data in self.button_roles[guild_id].items():
                if message_id in channel_data:
                    message_found = True
                    target_channel_id = channel_id
                    break
        
        if not message_found:
            await ctx.send("❌ Message not found in button roles database.")
            return
        
        # Confirm removal
        embed = discord.Embed(
            title="⚠️ Confirm Removal",
            description=f"Are you sure you want to remove all button roles from this message?",
            color=discord.Color.orange(),
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
                # Try to delete the message first
                try:
                    channel = ctx.guild.get_channel(int(target_channel_id))
                    if channel:
                        msg = await channel.fetch_message(int(message_id))
                        await msg.delete()
                except Exception as e:
                    logger.error(f"Error deleting button role message: {str(e)}")
                
                # Remove from database
                del self.button_roles[guild_id][target_channel_id][message_id]
                
                # If no messages left in channel, remove channel entry
                if not self.button_roles[guild_id][target_channel_id]:
                    del self.button_roles[guild_id][target_channel_id]
                    
                    # If no channels left in guild, remove guild entry
                    if not self.button_roles[guild_id]:
                        del self.button_roles[guild_id]
                
                self._save_button_roles()
                
                await message.delete()
                
                embed = discord.Embed(
                    title="Button Roles Removed",
                    description=f"Removed all button roles from message.",
                    color=discord.Color.green(),
                    timestamp=datetime.utcnow()
                )
                
                await ctx.send(embed=embed)
            else:
                await message.delete()
                await ctx.send("❌ Button role removal cancelled.")
                
        except TimeoutError:
            await message.delete()
            await ctx.send("❌ Button role removal timed out.")
    
    @buttonrole.command(name="reset")
    @commands.has_permissions(manage_guild=True, manage_roles=True)
    async def buttonrole_reset(self, ctx):
        """Clears every button role from guild"""
        guild_id = str(ctx.guild.id)
        
        # Check if guild has any button roles
        if guild_id not in self.button_roles or not self.button_roles[guild_id]:
            await ctx.send("❌ This server has no button roles set up.")
            return
        
        # Confirm reset
        embed = discord.Embed(
            title="⚠️ Confirm Reset",
            description="Are you sure you want to clear ALL button roles from this server? This action cannot be undone.",
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
                # Try to delete all button role messages
                for channel_id, channel_data in self.button_roles[guild_id].items():
                    channel = ctx.guild.get_channel(int(channel_id))
                    if channel:
                        for message_id in channel_data.keys():
                            try:
                                msg = await channel.fetch_message(int(message_id))
                                await msg.delete()
                            except Exception as e:
                                logger.error(f"Error deleting button role message: {str(e)}")
                
                # Remove from database
                del self.button_roles[guild_id]
                self._save_button_roles()
                
                await message.delete()
                
                embed = discord.Embed(
                    title="Button Roles Reset",
                    description="All button roles have been cleared from this server.",
                    color=discord.Color.green(),
                    timestamp=datetime.utcnow()
                )
                
                await ctx.send(embed=embed)
            else:
                await message.delete()
                await ctx.send("❌ Button role reset cancelled.")
                
        except TimeoutError:
            await message.delete()
            await ctx.send("❌ Button role reset timed out.")

async def setup(bot):
    await bot.add_cog(ButtonRoles(bot)) 