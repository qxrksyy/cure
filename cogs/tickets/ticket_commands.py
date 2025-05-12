import discord
from discord.ext import commands
import json
import os
import logging
import asyncio
from datetime import datetime
import uuid
import io
import re

logger = logging.getLogger('bot')

class TicketCommands(commands.Cog):
    """Commands for ticket system management"""
    
    def __init__(self, bot):
        self.bot = bot
        self.data_folder = 'data'
        self.config_file = os.path.join(self.data_folder, 'ticket_config.json')
        self.ticket_config = self.load_config()
        
    def load_config(self):
        """Load the ticket configuration from file"""
        if not os.path.exists(self.data_folder):
            os.makedirs(self.data_folder)
            
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            else:
                return {}
        except json.JSONDecodeError:
            logger.error(f"Error decoding {self.config_file}. Using empty config.")
            return {}
            
    def save_config(self):
        """Save the ticket configuration to file"""
        with open(self.config_file, 'w') as f:
            json.dump(self.ticket_config, f, indent=4)
    
    def get_guild_config(self, guild_id):
        """Get the ticket configuration for a specific guild"""
        guild_id = str(guild_id)
        
        if guild_id not in self.ticket_config:
            self.ticket_config[guild_id] = {
                "enabled": False,
                "support_role": None,
                "category": None,
                "log_channel": None,
                "open_emoji": "🎫",
                "close_emoji": "🔒",
                "topics": [],
                "open_message": "Thanks for creating a ticket! Support will be with you shortly.",
                "active_tickets": {},
                "panels": {}
            }
            self.save_config()
            
        return self.ticket_config[guild_id]
    
    async def create_ticket(self, guild, user, topic=None):
        """Create a new ticket channel for a user"""
        guild_id = str(guild.id)
        user_id = str(user.id)
        config = self.get_guild_config(guild_id)
        
        # Check if ticket system is enabled
        if not config["enabled"]:
            return None, "Ticket system is not enabled in this server."
            
        # Check if user already has an active ticket
        for ticket_id, ticket_data in config["active_tickets"].items():
            if ticket_data["user_id"] == user_id:
                channel = guild.get_channel(int(ticket_data["channel_id"]))
                if channel:
                    return channel, f"You already have an active ticket: {channel.mention}"
        
        # Get category
        category = None
        if config["category"]:
            category = guild.get_channel(int(config["category"]))
            if not category or not isinstance(category, discord.CategoryChannel):
                config["category"] = None
                self.save_config()
                return None, "The ticket category has been deleted. Please ask an admin to set it up again."
                
        # Create ticket channel name
        ticket_number = len(config["active_tickets"]) + 1
        channel_name = f"ticket-{ticket_number}"
        if topic:
            # Convert topic to valid channel name (alphanumeric and dashes)
            clean_topic = re.sub(r'[^a-zA-Z0-9 ]', '', topic)
            clean_topic = clean_topic.lower().replace(' ', '-')
            if clean_topic:
                channel_name = f"ticket-{clean_topic}-{ticket_number}"
                
        # Create the ticket channel
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
        }
        
        # Add support role permissions if it exists
        if config["support_role"]:
            support_role = guild.get_role(int(config["support_role"]))
            if support_role:
                overwrites[support_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
                
        try:
            ticket_channel = await guild.create_text_channel(
                name=channel_name,
                category=category,
                overwrites=overwrites,
                topic=f"Ticket for {user.display_name} | Topic: {topic or 'None'}"
            )
            
            # Generate a unique ticket ID
            ticket_id = str(uuid.uuid4())
            
            # Save ticket info
            config["active_tickets"][ticket_id] = {
                "channel_id": str(ticket_channel.id),
                "user_id": user_id,
                "created_at": datetime.now().isoformat(),
                "topic": topic,
                "number": ticket_number
            }
            self.save_config()
            
            # Send welcome message
            embed = discord.Embed(
                title="Ticket Created",
                description=config["open_message"],
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            
            embed.add_field(
                name="User",
                value=user.mention,
                inline=True
            )
            
            if topic:
                embed.add_field(
                    name="Topic",
                    value=topic,
                    inline=True
                )
                
            embed.set_footer(text=f"Ticket ID: {ticket_id}")
            
            await ticket_channel.send(content=user.mention, embed=embed)
            
            # Add close button
            close_view = discord.ui.View()
            close_button = discord.ui.Button(style=discord.ButtonStyle.danger, label="Close Ticket", emoji=config["close_emoji"])
            
            async def close_callback(interaction):
                if interaction.channel.id == ticket_channel.id:
                    await self.close_ticket(interaction, ticket_id)
                    
            close_button.callback = close_callback
            close_view.add_item(close_button)
            
            await ticket_channel.send("Click the button below to close the ticket:", view=close_view)
            
            return ticket_channel, None
            
        except Exception as e:
            logger.error(f"Failed to create ticket: {str(e)}")
            return None, f"Failed to create ticket: {str(e)}"
    
    async def close_ticket(self, interaction, ticket_id):
        """Close a ticket and archive it"""
        guild_id = str(interaction.guild.id)
        config = self.get_guild_config(guild_id)
        
        if ticket_id not in config["active_tickets"]:
            await interaction.response.send_message("This ticket no longer exists.", ephemeral=True)
            return
            
        ticket_data = config["active_tickets"][ticket_id]
        channel_id = ticket_data["channel_id"]
        
        # Check if the channel still exists
        channel = interaction.guild.get_channel(int(channel_id))
        if not channel:
            # Clean up if channel was deleted
            del config["active_tickets"][ticket_id]
            self.save_config()
            await interaction.response.send_message("The ticket channel has been deleted.", ephemeral=True)
            return
            
        # Create transcript
        messages = []
        async for message in channel.history(limit=500, oldest_first=True):
            timestamp = message.created_at.strftime("%Y-%m-%d %H:%M:%S")
            content = message.content or ""
            
            # Add embeds to content
            for embed in message.embeds:
                content += f"\n[Embed: {embed.title or 'No Title'}]"
                
            # Add attachments to content
            for attachment in message.attachments:
                content += f"\n[Attachment: {attachment.filename}]"
                
            messages.append(f"[{timestamp}] {message.author.display_name}: {content}")
            
        transcript = "\n".join(messages)
        transcript_file = discord.File(
            io.StringIO(transcript),
            filename=f"transcript-{channel.name}.txt"
        )
        
        # Send transcript to log channel if configured
        if config["log_channel"]:
            log_channel = interaction.guild.get_channel(int(config["log_channel"]))
            if log_channel:
                user = interaction.guild.get_member(int(ticket_data["user_id"]))
                user_mention = user.mention if user else f"User ID: {ticket_data['user_id']}"
                
                embed = discord.Embed(
                    title=f"Ticket Closed: {channel.name}",
                    description=f"Ticket was closed by {interaction.user.mention}",
                    color=discord.Color.red(),
                    timestamp=datetime.now()
                )
                
                embed.add_field(
                    name="Opened By",
                    value=user_mention,
                    inline=True
                )
                
                embed.add_field(
                    name="Created At",
                    value=datetime.fromisoformat(ticket_data["created_at"]).strftime("%Y-%m-%d %H:%M:%S"),
                    inline=True
                )
                
                if ticket_data["topic"]:
                    embed.add_field(
                        name="Topic",
                        value=ticket_data["topic"],
                        inline=True
                    )
                    
                embed.set_footer(text=f"Ticket ID: {ticket_id}")
                
                await log_channel.send(embed=embed, file=transcript_file)
        
        # Notify in channel that it's being closed
        await interaction.response.send_message(f"🔒 This ticket is being closed by {interaction.user.mention}...")
        
        # Remove ticket from active tickets
        del config["active_tickets"][ticket_id]
        self.save_config()
        
        # Archive ticket by changing permissions
        await channel.set_permissions(interaction.guild.default_role, read_messages=False)
        
        # Send closing message
        await channel.send(f"This ticket has been closed and archived. The channel will be deleted in 10 seconds.")
        
        # Wait and delete the channel
        await asyncio.sleep(10)
        try:
            await channel.delete(reason=f"Ticket closed by {interaction.user}")
        except Exception as e:
            logger.error(f"Failed to delete ticket channel: {str(e)}")
            
    async def create_ticket_panel(self, channel, code=None):
        """Create a ticket panel in the specified channel"""
        guild_id = str(channel.guild.id)
        config = self.get_guild_config(guild_id)
        
        # Create panel embed
        embed = discord.Embed(
            title="🎫 Support Ticket System",
            description=code or "Click the button below to create a ticket for support.",
            color=discord.Color.blurple(),
            timestamp=datetime.now()
        )
        
        if config["topics"]:
            topics_text = "\n".join([f"• {topic}" for topic in config["topics"]])
            embed.add_field(
                name="Available Topics",
                value=topics_text,
                inline=False
            )
            
        embed.set_footer(text=f"{channel.guild.name} | Ticket System")
        
        # Create ticket button
        ticket_view = discord.ui.View(timeout=None)
        ticket_button = discord.ui.Button(style=discord.ButtonStyle.primary, label="Create Ticket", emoji=config["open_emoji"], custom_id="create_ticket")
        
        # If topics exist, use select menu instead
        if config["topics"]:
            select_options = [
                discord.SelectOption(label=topic, value=topic, description=f"Create a ticket for {topic}")
                for topic in config["topics"]
            ]
            
            select_menu = discord.ui.Select(
                placeholder="Select a topic for your ticket...",
                min_values=1,
                max_values=1,
                options=select_options,
                custom_id="ticket_topic_select"
            )
            
            async def select_callback(interaction):
                selected_topic = interaction.data["values"][0]
                await interaction.response.defer(ephemeral=True)
                
                channel, error = await self.create_ticket(interaction.guild, interaction.user, selected_topic)
                if error:
                    await interaction.followup.send(error, ephemeral=True)
                else:
                    await interaction.followup.send(f"✅ Your ticket has been created: {channel.mention}", ephemeral=True)
                    
            select_menu.callback = select_callback
            ticket_view.add_item(select_menu)
            
        else:
            async def button_callback(interaction):
                await interaction.response.defer(ephemeral=True)
                
                channel, error = await self.create_ticket(interaction.guild, interaction.user)
                if error:
                    await interaction.followup.send(error, ephemeral=True)
                else:
                    await interaction.followup.send(f"✅ Your ticket has been created: {channel.mention}", ephemeral=True)
                    
            ticket_button.callback = button_callback
            ticket_view.add_item(ticket_button)
        
        # Send panel to channel
        panel_message = await channel.send(embed=embed, view=ticket_view)
        
        # Save panel info
        config["panels"][str(panel_message.id)] = {
            "channel_id": str(channel.id),
            "created_at": datetime.now().isoformat()
        }
        self.save_config()
        
        return panel_message
    
    @commands.group(name="ticket", invoke_without_command=True)
    async def ticket(self, ctx):
        """Make a ticket panel for your guild"""
        config = self.get_guild_config(ctx.guild.id)
        
        # Check if ticket system is set up
        if not config["enabled"]:
            embed = discord.Embed(
                title="🎫 Ticket System",
                description="The ticket system is not set up yet.\n\nUse the following command to set up the system:",
                color=discord.Color.orange()
            )
            
            embed.add_field(
                name="Required Setup",
                value=(
                    "`!ticket category <category>` - Set the category where tickets will be created\n"
                    "`!ticket support <role>` - Set the support role that can access tickets"
                ),
                inline=False
            )
            
            embed.add_field(
                name="Optional Setup",
                value=(
                    "`!ticket topics` - Manage ticket topics\n"
                    "`!ticket logs <channel>` - Set a channel for ticket transcripts\n"
                    "`!ticket opened <message>` - Set the message sent when a ticket is created\n"
                    "`!ticket emojis` - Customize ticket emojis"
                ),
                inline=False
            )
            
            embed.add_field(
                name="Panel Creation",
                value="`!ticket send <channel> [code]` - Send a ticket panel to a channel",
                inline=False
            )
            
            await ctx.send(embed=embed)
            return
            
        # Show ticket commands
        embed = discord.Embed(
            title="🎫 Ticket System",
            description="The ticket system is enabled.",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="Ticket Management",
            value=(
                "`!ticket add <member>` - Add a member to a ticket\n"
                "`!ticket remove <member>` - Remove a member from a ticket\n"
                "`!ticket rename <name>` - Rename a ticket channel\n"
                "`!ticket close` - Close the current ticket"
            ),
            inline=False
        )
        
        embed.add_field(
            name="Configuration",
            value=(
                "`!ticket config` - View ticket configuration\n"
                "`!ticket reset` - Disable the ticket system\n"
                "`!ticket send <channel> [code]` - Send a ticket panel"
            ),
            inline=False
        )
        
        await ctx.send(embed=embed)

    @ticket.group(name="topics", invoke_without_command=True)
    async def ticket_topics(self, ctx):
        """Manage the ticket topics"""
        config = self.get_guild_config(ctx.guild.id)
        
        if not config["topics"]:
            embed = discord.Embed(
                title="🎫 Ticket Topics",
                description="No topics have been set up yet. Add topics to categorize tickets.",
                color=discord.Color.orange()
            )
            
            embed.add_field(
                name="Add a Topic",
                value="`!ticket topics add <topic>` - Add a new ticket topic",
                inline=False
            )
            
            await ctx.send(embed=embed)
            return
            
        # Show configured topics
        topics_text = "\n".join([f"• {topic}" for topic in config["topics"]])
        
        embed = discord.Embed(
            title="🎫 Ticket Topics",
            description=f"**Configured Topics:**\n{topics_text}",
            color=discord.Color.blurple()
        )
        
        embed.add_field(
            name="Manage Topics",
            value=(
                "`!ticket topics add <topic>` - Add a new ticket topic\n"
                "`!ticket topics remove <topic>` - Remove a ticket topic\n"
                "`!ticket topics clear` - Remove all ticket topics"
            ),
            inline=False
        )
        
        await ctx.send(embed=embed)
        
    @ticket_topics.command(name="add")
    @commands.has_permissions(manage_channels=True)
    async def topics_add(self, ctx, *, topic: str):
        """Add a topic for tickets"""
        config = self.get_guild_config(ctx.guild.id)
        
        # Check if topic already exists
        if topic in config["topics"]:
            await ctx.send(f"❌ Topic `{topic}` already exists.")
            return
            
        # Add topic
        config["topics"].append(topic)
        self.save_config()
        
        await ctx.send(f"✅ Added topic `{topic}` to the ticket system.")
        
    @ticket_topics.command(name="remove")
    @commands.has_permissions(manage_channels=True)
    async def topics_remove(self, ctx, *, topic: str):
        """Remove a topic from tickets"""
        config = self.get_guild_config(ctx.guild.id)
        
        # Check if topic exists
        if topic not in config["topics"]:
            await ctx.send(f"❌ Topic `{topic}` does not exist.")
            return
            
        # Remove topic
        config["topics"].remove(topic)
        self.save_config()
        
        await ctx.send(f"✅ Removed topic `{topic}` from the ticket system.")
        
    @ticket_topics.command(name="clear")
    @commands.has_permissions(manage_channels=True)
    async def topics_clear(self, ctx):
        """Remove all ticket topics"""
        config = self.get_guild_config(ctx.guild.id)
        
        # Clear topics
        config["topics"] = []
        self.save_config()
        
        await ctx.send(f"✅ Cleared all topics from the ticket system.")

    @ticket.command(name="add")
    async def ticket_add(self, ctx, member: discord.Member):
        """Add a person to the ticket"""
        config = self.get_guild_config(ctx.guild.id)
        
        # Check if the current channel is a ticket
        is_ticket = False
        ticket_id = None
        
        for t_id, ticket_data in config["active_tickets"].items():
            if str(ctx.channel.id) == ticket_data["channel_id"]:
                is_ticket = True
                ticket_id = t_id
                break
                
        if not is_ticket:
            await ctx.send("❌ This command can only be used in an active ticket channel.")
            return
            
        # Add the member to the ticket
        try:
            await ctx.channel.set_permissions(member, read_messages=True, send_messages=True)
            await ctx.send(f"✅ {member.mention} has been added to the ticket.")
        except Exception as e:
            await ctx.send(f"❌ Failed to add {member.mention} to the ticket: {str(e)}")
            
    @ticket.command(name="remove")
    async def ticket_remove(self, ctx, member: discord.Member):
        """Remove a member from the ticket"""
        config = self.get_guild_config(ctx.guild.id)
        
        # Check if the current channel is a ticket
        is_ticket = False
        ticket_id = None
        
        for t_id, ticket_data in config["active_tickets"].items():
            if str(ctx.channel.id) == ticket_data["channel_id"]:
                is_ticket = True
                ticket_id = t_id
                break
                
        if not is_ticket:
            await ctx.send("❌ This command can only be used in an active ticket channel.")
            return
            
        # Don't remove the ticket creator
        ticket_data = config["active_tickets"][ticket_id]
        if str(member.id) == ticket_data["user_id"]:
            await ctx.send("❌ You cannot remove the ticket creator from the ticket.")
            return
            
        # Check if member is a support role member
        if config["support_role"]:
            support_role = ctx.guild.get_role(int(config["support_role"]))
            if support_role and support_role in member.roles:
                await ctx.send("❌ You cannot remove a support team member from the ticket.")
                return
                
        # Remove the member from the ticket
        try:
            await ctx.channel.set_permissions(member, overwrite=None)
            await ctx.send(f"✅ {member.mention} has been removed from the ticket.")
        except Exception as e:
            await ctx.send(f"❌ Failed to remove {member.mention} from the ticket: {str(e)}")
            
    @ticket.command(name="rename")
    async def ticket_rename(self, ctx, *, name: str):
        """Rename a ticket channel"""
        config = self.get_guild_config(ctx.guild.id)
        
        # Check if the current channel is a ticket
        is_ticket = False
        ticket_id = None
        
        for t_id, ticket_data in config["active_tickets"].items():
            if str(ctx.channel.id) == ticket_data["channel_id"]:
                is_ticket = True
                ticket_id = t_id
                break
                
        if not is_ticket:
            await ctx.send("❌ This command can only be used in an active ticket channel.")
            return
            
        # Clean the name to valid channel format
        clean_name = re.sub(r'[^a-zA-Z0-9 ]', '', name)
        clean_name = clean_name.lower().replace(' ', '-')
        
        if not clean_name:
            await ctx.send("❌ The provided name contains invalid characters. Please use alphanumeric characters.")
            return
            
        # Add ticket- prefix if not present
        if not clean_name.startswith("ticket-"):
            clean_name = f"ticket-{clean_name}"
            
        # Rename the channel
        try:
            await ctx.channel.edit(name=clean_name)
            await ctx.send(f"✅ Ticket channel has been renamed to `{clean_name}`.")
        except Exception as e:
            await ctx.send(f"❌ Failed to rename the ticket channel: {str(e)}")
            
    @ticket.command(name="close")
    async def ticket_close(self, ctx):
        """Close the ticket"""
        config = self.get_guild_config(ctx.guild.id)
        
        # Check if the current channel is a ticket
        is_ticket = False
        ticket_id = None
        
        for t_id, ticket_data in config["active_tickets"].items():
            if str(ctx.channel.id) == ticket_data["channel_id"]:
                is_ticket = True
                ticket_id = t_id
                break
                
        if not is_ticket:
            await ctx.send("❌ This command can only be used in an active ticket channel.")
            return
            
        # Send confirmation message
        embed = discord.Embed(
            title="Close Ticket",
            description="Are you sure you want to close this ticket? All messages will be archived.",
            color=discord.Color.red()
        )
        
        # Create confirm/cancel buttons
        view = discord.ui.View()
        confirm_button = discord.ui.Button(style=discord.ButtonStyle.danger, label="Close Ticket", emoji="🔒")
        cancel_button = discord.ui.Button(style=discord.ButtonStyle.secondary, label="Cancel", emoji="❌")
        
        async def confirm_callback(interaction):
            if interaction.user.id == ctx.author.id:
                await interaction.response.defer()
                await self.close_ticket(interaction, ticket_id)
                
        async def cancel_callback(interaction):
            if interaction.user.id == ctx.author.id:
                await interaction.response.edit_message(
                    content="Ticket closure cancelled.",
                    embed=None,
                    view=None
                )
                
        confirm_button.callback = confirm_callback
        cancel_button.callback = cancel_callback
        
        view.add_item(confirm_button)
        view.add_item(cancel_button)
        
        await ctx.send(embed=embed, view=view)

    @ticket.command(name="opened")
    @commands.has_permissions(manage_channels=True)
    async def ticket_opened(self, ctx, *, code: str):
        """Set a message to be sent when a member opens a ticket"""
        config = self.get_guild_config(ctx.guild.id)
        
        # Update the open message
        config["open_message"] = code
        self.save_config()
        
        await ctx.send(f"✅ The ticket opening message has been updated.")
        
    @ticket.command(name="reset")
    @commands.has_permissions(administrator=True)
    async def ticket_reset(self, ctx):
        """Disable the ticket module in the server"""
        guild_id = str(ctx.guild.id)
        
        # Confirm reset
        embed = discord.Embed(
            title="Reset Ticket System",
            description="Are you sure you want to reset the ticket system? This will disable all functionality and clear all settings.",
            color=discord.Color.red()
        )
        
        # Create confirm/cancel buttons
        view = discord.ui.View()
        confirm_button = discord.ui.Button(style=discord.ButtonStyle.danger, label="Reset System", emoji="⚠️")
        cancel_button = discord.ui.Button(style=discord.ButtonStyle.secondary, label="Cancel", emoji="❌")
        
        async def confirm_callback(interaction):
            if interaction.user.id == ctx.author.id:
                # Reset the config
                if guild_id in self.ticket_config:
                    del self.ticket_config[guild_id]
                    self.save_config()
                    
                await interaction.response.edit_message(
                    content="✅ The ticket system has been reset and disabled.",
                    embed=None,
                    view=None
                )
                
        async def cancel_callback(interaction):
            if interaction.user.id == ctx.author.id:
                await interaction.response.edit_message(
                    content="Reset cancelled.",
                    embed=None,
                    view=None
                )
                
        confirm_button.callback = confirm_callback
        cancel_button.callback = cancel_callback
        
        view.add_item(confirm_button)
        view.add_item(cancel_button)
        
        await ctx.send(embed=embed, view=view)
        
    @ticket.command(name="config")
    @commands.has_permissions(manage_channels=True)
    async def ticket_config(self, ctx):
        """Check the server's ticket settings"""
        config = self.get_guild_config(ctx.guild.id)
        
        embed = discord.Embed(
            title="🎫 Ticket System Configuration",
            color=discord.Color.blurple(),
            timestamp=datetime.now()
        )
        
        # Status
        status = "✅ Enabled" if config["enabled"] else "❌ Disabled"
        embed.add_field(name="Status", value=status, inline=True)
        
        # Support role
        if config["support_role"]:
            role = ctx.guild.get_role(int(config["support_role"]))
            role_value = role.mention if role else "Role not found"
        else:
            role_value = "Not set"
        embed.add_field(name="Support Role", value=role_value, inline=True)
        
        # Category
        if config["category"]:
            category = ctx.guild.get_channel(int(config["category"]))
            category_value = category.mention if category else "Category not found"
        else:
            category_value = "Not set"
        embed.add_field(name="Tickets Category", value=category_value, inline=True)
        
        # Log channel
        if config["log_channel"]:
            log_channel = ctx.guild.get_channel(int(config["log_channel"]))
            log_value = log_channel.mention if log_channel else "Channel not found"
        else:
            log_value = "Not set"
        embed.add_field(name="Log Channel", value=log_value, inline=True)
        
        # Emojis
        emoji_value = f"Open: {config['open_emoji']} | Close: {config['close_emoji']}"
        embed.add_field(name="Emojis", value=emoji_value, inline=True)
        
        # Topics
        topics_value = ", ".join(config["topics"]) if config["topics"] else "No topics configured"
        embed.add_field(name="Topics", value=topics_value, inline=True)
        
        # Active tickets
        active_count = len(config["active_tickets"])
        embed.add_field(name="Active Tickets", value=str(active_count), inline=True)
        
        # Open message
        if len(config["open_message"]) > 1024:
            open_message = config["open_message"][:1021] + "..."
        else:
            open_message = config["open_message"]
        embed.add_field(name="Open Message", value=open_message, inline=False)
        
        await ctx.send(embed=embed)
        
    @ticket.command(name="support")
    @commands.has_permissions(manage_channels=True)
    async def ticket_support(self, ctx, role: discord.Role):
        """Configure the ticket support role"""
        config = self.get_guild_config(ctx.guild.id)
        
        # Update support role
        config["support_role"] = str(role.id)
        
        # Enable the system if this is the first setup
        if not config["enabled"] and config["category"]:
            config["enabled"] = True
            
        self.save_config()
        
        await ctx.send(f"✅ Support role set to {role.mention} for the ticket system.")
        
        # Check if the system is fully set up
        if not config["category"]:
            await ctx.send("⚠️ You still need to set up a category for tickets using `!ticket category <category>`.")
        elif config["enabled"]:
            await ctx.send("✅ The ticket system is now fully set up and enabled!")
            
    @ticket.command(name="logs")
    @commands.has_permissions(manage_channels=True)
    async def ticket_logs(self, ctx, channel: discord.TextChannel):
        """Configure a channel for logging ticket transcripts"""
        config = self.get_guild_config(ctx.guild.id)
        
        # Update log channel
        config["log_channel"] = str(channel.id)
        self.save_config()
        
        await ctx.send(f"✅ Log channel set to {channel.mention} for ticket transcripts.")
        
    @ticket.command(name="category")
    @commands.has_permissions(manage_channels=True)
    async def ticket_category(self, ctx, *, category: discord.CategoryChannel):
        """Configure the category where the tickets should open"""
        config = self.get_guild_config(ctx.guild.id)
        
        # Update category
        config["category"] = str(category.id)
        
        # Enable the system if this is the first setup
        if not config["enabled"] and config["support_role"]:
            config["enabled"] = True
            
        self.save_config()
        
        await ctx.send(f"✅ Ticket category set to {category.mention}.")
        
        # Check if the system is fully set up
        if not config["support_role"]:
            await ctx.send("⚠️ You still need to set up a support role using `!ticket support <role>`.")
        elif config["enabled"]:
            await ctx.send("✅ The ticket system is now fully set up and enabled!")

    @ticket.group(name="emojis", invoke_without_command=True)
    @commands.has_permissions(manage_channels=True)
    async def ticket_emojis(self, ctx):
        """Edit the ticket emojis"""
        config = self.get_guild_config(ctx.guild.id)
        
        embed = discord.Embed(
            title="🎫 Ticket Emojis",
            description=f"Current emojis:\n- Open: {config['open_emoji']}\n- Close: {config['close_emoji']}",
            color=discord.Color.blurple()
        )
        
        embed.add_field(
            name="Change Emojis",
            value=(
                "`!ticket emojis open <emoji>` - Set the emoji to open a ticket\n"
                "`!ticket emojis close <emoji>` - Set the emoji to close a ticket"
            ),
            inline=False
        )
        
        await ctx.send(embed=embed)
        
    @ticket_emojis.command(name="open")
    @commands.has_permissions(manage_channels=True)
    async def emojis_open(self, ctx, emoji: str):
        """Set the emoji to open the ticket"""
        config = self.get_guild_config(ctx.guild.id)
        
        # Update open emoji
        config["open_emoji"] = emoji
        self.save_config()
        
        await ctx.send(f"✅ Open ticket emoji set to {emoji}")
        
    @ticket_emojis.command(name="close")
    @commands.has_permissions(manage_channels=True)
    async def emojis_close(self, ctx, emoji: str):
        """Set the emoji to close the ticket"""
        config = self.get_guild_config(ctx.guild.id)
        
        # Update close emoji
        config["close_emoji"] = emoji
        self.save_config()
        
        await ctx.send(f"✅ Close ticket emoji set to {emoji}")
        
    @ticket.command(name="send")
    @commands.has_permissions(manage_channels=True)
    async def ticket_send(self, ctx, channel: discord.TextChannel, *, code: str = None):
        """Send the ticket panel to a channel"""
        config = self.get_guild_config(ctx.guild.id)
        
        # Check if ticket system is enabled
        if not config["enabled"]:
            await ctx.send("❌ You need to set up the ticket system first!")
            return
            
        try:
            panel_message = await self.create_ticket_panel(channel, code)
            await ctx.send(f"✅ Ticket panel has been sent to {channel.mention}!")
        except Exception as e:
            await ctx.send(f"❌ Failed to create ticket panel: {str(e)}")

async def setup(bot):
    await bot.add_cog(TicketCommands(bot)) 