import discord
from discord.ext import commands
import json
import os
import logging
from datetime import datetime
import re
import asyncio

logger = logging.getLogger('bot')

class AutoReactions(commands.Cog):
    """Commands for auto reactions and reaction triggers"""
    
    def __init__(self, bot):
        self.bot = bot
        self.config_path = "data/reactions"
        self.reaction_triggers = {}
        self.message_reactions = {}
        
        # Create directory if it doesn't exist
        os.makedirs(self.config_path, exist_ok=True)
        
        # Load reaction data
        self._load_reaction_triggers()
        self._load_message_reactions()
    
    def _load_reaction_triggers(self):
        """Load reaction trigger settings from file"""
        try:
            filepath = f"{self.config_path}/triggers.json"
            if os.path.exists(filepath):
                with open(filepath, "r") as f:
                    self.reaction_triggers = json.load(f)
        except Exception as e:
            logger.error(f"Error loading reaction triggers: {str(e)}")
            self.reaction_triggers = {}
    
    def _save_reaction_triggers(self):
        """Save reaction trigger settings to file"""
        try:
            filepath = f"{self.config_path}/triggers.json"
            with open(filepath, "w") as f:
                json.dump(self.reaction_triggers, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving reaction triggers: {str(e)}")
    
    def _load_message_reactions(self):
        """Load message reaction settings from file"""
        try:
            filepath = f"{self.config_path}/message_reactions.json"
            if os.path.exists(filepath):
                with open(filepath, "r") as f:
                    self.message_reactions = json.load(f)
        except Exception as e:
            logger.error(f"Error loading message reactions: {str(e)}")
            self.message_reactions = {}
    
    def _save_message_reactions(self):
        """Save message reaction settings to file"""
        try:
            filepath = f"{self.config_path}/message_reactions.json"
            with open(filepath, "w") as f:
                json.dump(self.message_reactions, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving message reactions: {str(e)}")
    
    def _get_guild_reaction_triggers(self, guild_id):
        """Get reaction triggers for a guild"""
        guild_id = str(guild_id)
        if guild_id not in self.reaction_triggers:
            self.reaction_triggers[guild_id] = {}
            self._save_reaction_triggers()
        return self.reaction_triggers[guild_id]
    
    def _get_guild_message_reactions(self, guild_id):
        """Get message reactions for a guild"""
        guild_id = str(guild_id)
        if guild_id not in self.message_reactions:
            self.message_reactions[guild_id] = {}
            self._save_message_reactions()
        return self.message_reactions[guild_id]
    
    @commands.Cog.listener()
    async def on_message(self, message):
        """Listen for messages to apply auto reactions"""
        # Ignore messages from bots
        if message.author.bot:
            return
            
        # Ignore DMs
        if not message.guild:
            return
            
        try:
            # Check for trigger words
            await self._check_reaction_triggers(message)
            
            # Check for channel auto reactions
            await self._check_channel_reactions(message)
            
        except Exception as e:
            logger.error(f"Error in reaction message handler: {str(e)}")
    
    async def _check_reaction_triggers(self, message):
        """Check message for reaction triggers and add reactions if found"""
        guild_triggers = self._get_guild_reaction_triggers(message.guild.id)
        
        # No triggers for this guild
        if not guild_triggers:
            return
            
        # Check each word in the message against all triggers
        content = message.content.lower()
        
        for trigger, reaction_data in guild_triggers.items():
            pattern = re.compile(r'\b' + re.escape(trigger.lower()) + r'\b')
            if pattern.search(content):
                try:
                    emoji = reaction_data["emoji"]
                    await message.add_reaction(emoji)
                except Exception as e:
                    logger.error(f"Failed to add reaction {emoji} to message: {str(e)}")
    
    async def _check_channel_reactions(self, message):
        """Add auto reactions to message if channel is configured"""
        guild_message_reactions = self._get_guild_message_reactions(message.guild.id)
        
        channel_id = str(message.channel.id)
        if channel_id in guild_message_reactions:
            for emoji in guild_message_reactions[channel_id]:
                try:
                    await message.add_reaction(emoji)
                except Exception as e:
                    logger.error(f"Failed to add channel reaction {emoji} to message: {str(e)}")
    
    @commands.command(name="add_reaction")
    @commands.has_permissions(manage_messages=True)
    async def add_reaction(self, ctx, message_id: int = None, *emojis):
        """Add a reaction(s) to a message"""
        if not message_id:
            await ctx.send("❌ Please provide a message ID to add reactions to.")
            return
            
        if not emojis:
            await ctx.send("❌ Please provide at least one emoji to add as a reaction.")
            return
            
        try:
            # Try to find the message in the current channel
            message = await ctx.channel.fetch_message(message_id)
            
            for emoji in emojis:
                try:
                    await message.add_reaction(emoji)
                except discord.HTTPException:
                    await ctx.send(f"❌ Failed to add reaction {emoji}. Is it a valid emoji?")
                    
            await ctx.send(f"✅ Added {len(emojis)} reaction(s) to the message.")
            
        except discord.NotFound:
            await ctx.send("❌ Message not found. Make sure the ID is correct and the message is in this channel.")
        except Exception as e:
            await ctx.send(f"❌ An error occurred: {str(e)}")
    
    @commands.group(name="reaction", invoke_without_command=True)
    @commands.has_permissions(manage_expressions=True)
    async def reaction_group(self, ctx):
        """Command group for reaction management"""
        # This will show help if no subcommand is provided
        embed = discord.Embed(
            title="Reaction Commands",
            description="Manage automatic reactions and triggers",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(
            name="Available Commands",
            value=(
                "`reaction <message_id> <emoji>` - Add reactions to a message\n"
                "`reaction add <emoji> <trigger>` - Add a reaction trigger\n"
                "`reaction delete <emoji> <trigger>` - Remove a reaction trigger\n"
                "`reaction list` - List all reaction triggers\n"
                "`reaction clear` - Remove all reaction triggers\n"
                "`reaction deleteall <trigger>` - Remove all reactions for a trigger\n"
                "`reaction owner <trigger>` - See who created a trigger\n"
                "`reaction messages <channel> <emoji1> [emoji2] [emoji3]` - Set auto reactions for a channel\n"
                "`reaction messages_list` - List all auto reactions for channels\n"
            ),
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @reaction_group.command(name="add")
    @commands.has_permissions(manage_expressions=True)
    async def reaction_add(self, ctx, emoji: str, *, trigger: str):
        """Adds a reaction trigger to guild"""
        # Validate emoji
        try:
            # Test if it's a custom emoji
            if len(emoji) > 3 and emoji.startswith('<') and emoji.endswith('>'):
                # It's a custom emoji, format is fine
                pass
            # Test if it's a standard emoji by trying to add it as a reaction to the command message
            else:
                await ctx.message.add_reaction(emoji)
                await ctx.message.remove_reaction(emoji, ctx.bot.user)
        except discord.HTTPException:
            await ctx.send("❌ Invalid emoji. Please provide a valid emoji.")
            return
            
        # Normalize trigger
        trigger = trigger.lower().strip()
        
        if not trigger:
            await ctx.send("❌ Trigger word cannot be empty.")
            return
            
        guild_triggers = self._get_guild_reaction_triggers(ctx.guild.id)
        
        # Check if trigger already exists
        if trigger in guild_triggers:
            await ctx.send(f"❌ Trigger `{trigger}` already exists with reaction {guild_triggers[trigger]['emoji']}.")
            return
            
        # Add the new trigger
        guild_triggers[trigger] = {
            "emoji": emoji,
            "created_by": str(ctx.author.id),
            "created_at": datetime.utcnow().isoformat()
        }
        
        self._save_reaction_triggers()
        
        await ctx.send(f"✅ Added reaction trigger: `{trigger}` → {emoji}")
    
    @reaction_group.command(name="delete")
    @commands.has_permissions(manage_expressions=True)
    async def reaction_delete(self, ctx, emoji: str, *, trigger: str):
        """Removes a reaction trigger in guild"""
        # Normalize trigger
        trigger = trigger.lower().strip()
        
        guild_triggers = self._get_guild_reaction_triggers(ctx.guild.id)
        
        # Check if trigger exists
        if trigger not in guild_triggers:
            await ctx.send(f"❌ Trigger `{trigger}` doesn't exist.")
            return
            
        # Check if emoji matches
        if guild_triggers[trigger]["emoji"] != emoji:
            await ctx.send(f"❌ Emoji doesn't match the one set for trigger `{trigger}`.")
            return
            
        # Remove the trigger
        del guild_triggers[trigger]
        self._save_reaction_triggers()
        
        await ctx.send(f"✅ Removed reaction trigger: `{trigger}` → {emoji}")
    
    @reaction_group.command(name="list")
    @commands.has_permissions(manage_expressions=True)
    async def reaction_list(self, ctx):
        """View a list of every reaction trigger in guild"""
        guild_triggers = self._get_guild_reaction_triggers(ctx.guild.id)
        
        if not guild_triggers:
            await ctx.send("❌ No reaction triggers set up in this server.")
            return
            
        # Create paginated embed for the list
        embed = discord.Embed(
            title="Reaction Triggers",
            description=f"This server has {len(guild_triggers)} reaction trigger(s)",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        # Group triggers by emoji for better organization
        emoji_triggers = {}
        for trigger, data in guild_triggers.items():
            emoji = data["emoji"]
            if emoji not in emoji_triggers:
                emoji_triggers[emoji] = []
            emoji_triggers[emoji].append(trigger)
        
        # Add fields for each emoji group
        for emoji, triggers in emoji_triggers.items():
            trigger_text = ", ".join([f"`{t}`" for t in triggers])
            embed.add_field(
                name=f"Reaction: {emoji}",
                value=f"Triggers: {trigger_text}",
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    @reaction_group.command(name="clear")
    @commands.has_permissions(manage_expressions=True)
    async def reaction_clear(self, ctx):
        """Removes every reaction trigger in guild"""
        guild_id = str(ctx.guild.id)
        
        if guild_id not in self.reaction_triggers or not self.reaction_triggers[guild_id]:
            await ctx.send("❌ No reaction triggers to clear.")
            return
            
        # Ask for confirmation
        count = len(self.reaction_triggers[guild_id])
        confirm_msg = await ctx.send(f"⚠️ Are you sure you want to remove all {count} reaction triggers? (yes/no)")
        
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and \
                   m.content.lower() in ['yes', 'no', 'y', 'n']
                   
        try:
            msg = await self.bot.wait_for('message', check=check, timeout=30.0)
            
            if msg.content.lower() in ['yes', 'y']:
                # Clear all triggers
                self.reaction_triggers[guild_id] = {}
                self._save_reaction_triggers()
                await ctx.send(f"✅ Removed all {count} reaction triggers from this server.")
            else:
                await ctx.send("❌ Operation cancelled.")
                
        except asyncio.TimeoutError:
            await ctx.send("❌ Timed out waiting for confirmation.")
    
    @reaction_group.command(name="deleteall")
    @commands.has_permissions(manage_expressions=True)
    async def reaction_deleteall(self, ctx, *, trigger: str):
        """Removes every reaction trigger for a specific word"""
        trigger = trigger.lower().strip()
        
        guild_triggers = self._get_guild_reaction_triggers(ctx.guild.id)
        
        if trigger not in guild_triggers:
            await ctx.send(f"❌ Trigger `{trigger}` doesn't exist.")
            return
            
        # Remove the trigger
        emoji = guild_triggers[trigger]["emoji"]
        del guild_triggers[trigger]
        self._save_reaction_triggers()
        
        await ctx.send(f"✅ Removed reaction trigger: `{trigger}` → {emoji}")
    
    @reaction_group.command(name="owner")
    @commands.has_permissions(manage_expressions=True)
    async def reaction_owner(self, ctx, *, trigger: str):
        """Gets the author of a trigger word"""
        trigger = trigger.lower().strip()
        
        guild_triggers = self._get_guild_reaction_triggers(ctx.guild.id)
        
        if trigger not in guild_triggers:
            await ctx.send(f"❌ Trigger `{trigger}` doesn't exist.")
            return
            
        # Get trigger info
        trigger_data = guild_triggers[trigger]
        
        created_by_id = int(trigger_data["created_by"])
        created_by = ctx.guild.get_member(created_by_id) or f"Unknown User ({created_by_id})"
        created_at = datetime.fromisoformat(trigger_data["created_at"])
        
        embed = discord.Embed(
            title=f"Trigger Information: `{trigger}`",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(name="Reaction", value=trigger_data["emoji"], inline=True)
        embed.add_field(name="Created By", value=str(created_by), inline=True)
        embed.add_field(name="Created At", value=created_at.strftime("%Y-%m-%d %H:%M:%S"), inline=True)
        
        await ctx.send(embed=embed)
    
    @reaction_group.command(name="messages")
    @commands.has_permissions(manage_expressions=True)
    async def reaction_messages(self, ctx, channel: discord.TextChannel = None, first: str = None, second: str = None, third: str = None):
        """Add or remove auto reaction on messages"""
        if not channel:
            await ctx.send("❌ Please specify a channel.")
            return
            
        if not first:
            # If no emojis provided, remove the channel's auto reactions
            guild_message_reactions = self._get_guild_message_reactions(ctx.guild.id)
            
            channel_id = str(channel.id)
            if channel_id in guild_message_reactions:
                del guild_message_reactions[channel_id]
                self._save_message_reactions()
                await ctx.send(f"✅ Removed all auto reactions from {channel.mention}.")
            else:
                await ctx.send(f"❌ No auto reactions set for {channel.mention}.")
                
            return
            
        # Validate emojis
        emojis = [first]
        if second:
            emojis.append(second)
        if third:
            emojis.append(third)
            
        valid_emojis = []
        for emoji in emojis:
            try:
                await ctx.message.add_reaction(emoji)
                await ctx.message.remove_reaction(emoji, ctx.bot.user)
                valid_emojis.append(emoji)
            except discord.HTTPException:
                await ctx.send(f"❌ Invalid emoji: {emoji}")
        
        if not valid_emojis:
            await ctx.send("❌ No valid emojis provided.")
            return
            
        # Save the channel's auto reactions
        guild_message_reactions = self._get_guild_message_reactions(ctx.guild.id)
        guild_message_reactions[str(channel.id)] = valid_emojis
        self._save_message_reactions()
        
        emoji_text = " ".join(valid_emojis)
        await ctx.send(f"✅ Set auto reactions for {channel.mention}: {emoji_text}")
    
    @reaction_group.command(name="messages_list")
    @commands.has_permissions(manage_expressions=True)
    async def reaction_messages_list(self, ctx):
        """List auto reactions for all channels"""
        guild_message_reactions = self._get_guild_message_reactions(ctx.guild.id)
        
        if not guild_message_reactions:
            await ctx.send("❌ No auto reactions set up in this server.")
            return
            
        embed = discord.Embed(
            title="Channel Auto Reactions",
            description=f"Auto reactions are set up for {len(guild_message_reactions)} channel(s)",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        for channel_id, emojis in guild_message_reactions.items():
            channel = ctx.guild.get_channel(int(channel_id))
            channel_text = channel.mention if channel else f"Unknown Channel ({channel_id})"
            
            emoji_text = " ".join(emojis)
            embed.add_field(
                name=f"Channel: {channel_text}",
                value=f"Reactions: {emoji_text}",
                inline=False
            )
        
        await ctx.send(embed=embed)

async def setup(bot):
    # Create data directory if it doesn't exist
    os.makedirs("data/reactions", exist_ok=True)
    await bot.add_cog(AutoReactions(bot)) 