import discord
from discord.ext import commands
import asyncio
import datetime
import logging
from collections import defaultdict, deque

logger = logging.getLogger('bot')

# Maximum number of messages to store per channel
MAX_SNIPE_HISTORY = 10
# Maximum number of edits to store per channel
MAX_EDIT_HISTORY = 10
# Maximum number of reactions to store per channel
MAX_REACTION_HISTORY = 10

class Snipe(commands.Cog):
    """Commands for retrieving deleted and edited messages"""
    
    def __init__(self, bot):
        self.bot = bot
        # Structure: {guild_id -> {channel_id -> deque([messages])}}
        self.deleted_messages = defaultdict(lambda: defaultdict(lambda: deque(maxlen=MAX_SNIPE_HISTORY)))
        # Structure: {guild_id -> {channel_id -> deque([{before, after}])}}
        self.edited_messages = defaultdict(lambda: defaultdict(lambda: deque(maxlen=MAX_EDIT_HISTORY)))
        # Structure: {guild_id -> {channel_id -> deque([{message_id, emoji, user}])}}
        self.deleted_reactions = defaultdict(lambda: defaultdict(lambda: deque(maxlen=MAX_REACTION_HISTORY)))
        # Structure: {message_id -> {emoji -> [users]}}
        self.reaction_history = {}
        # Structure: {guild_id -> {channel_id -> [purged_messages]}}
        self.purged_messages = defaultdict(lambda: defaultdict(list))
    
    @commands.Cog.listener()
    async def on_message_delete(self, message):
        """Store deleted messages for sniping"""
        # Ignore bots and empty messages
        if message.author.bot or not message.content:
            return
            
        # Store the message
        self.deleted_messages[message.guild.id][message.channel.id].append({
            'content': message.content,
            'author': message.author,
            'created_at': message.created_at,
            'deleted_at': datetime.datetime.utcnow(),
            'attachments': [attachment.url for attachment in message.attachments],
            'embeds': message.embeds
        })
        
        logger.debug(f"Stored deleted message in {message.guild.id}/{message.channel.id} by {message.author.id}")
    
    @commands.Cog.listener()
    async def on_bulk_message_delete(self, messages):
        """Store messages deleted through purge"""
        if not messages:
            return
            
        # Get first message's guild and channel for reference
        first_message = messages[0]
        guild_id = first_message.guild.id
        channel_id = first_message.channel.id
        
        # Clear existing purged messages for this channel
        self.purged_messages[guild_id][channel_id] = []
        
        # Store the purged messages
        for message in messages:
            if not message.author.bot and message.content:
                self.purged_messages[guild_id][channel_id].append({
                    'content': message.content,
                    'author': message.author,
                    'created_at': message.created_at,
                    'deleted_at': datetime.datetime.utcnow(),
                    'attachments': [attachment.url for attachment in message.attachments],
                    'embeds': message.embeds
                })
                
        logger.debug(f"Stored {len(self.purged_messages[guild_id][channel_id])} purged messages in {guild_id}/{channel_id}")
    
    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        """Store edited messages for editsnipe"""
        # Ignore bots and empty messages
        if before.author.bot or not before.content:
            return
            
        # Skip if content didn't change (embed loading, etc.)
        if before.content == after.content:
            return
            
        # Store the edit
        self.edited_messages[before.guild.id][before.channel.id].append({
            'before': {
                'content': before.content,
                'author': before.author,
                'created_at': before.created_at,
                'attachments': [attachment.url for attachment in before.attachments],
                'embeds': before.embeds
            },
            'after': {
                'content': after.content,
                'edited_at': datetime.datetime.utcnow()
            }
        })
        
        logger.debug(f"Stored edited message in {before.guild.id}/{before.channel.id} by {before.author.id}")
    
    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        """Store reaction for history"""
        message = reaction.message
        
        # Initialize if this is a new message
        if message.id not in self.reaction_history:
            self.reaction_history[message.id] = {}
            
        emoji_str = str(reaction.emoji)
        
        # Initialize if this is a new emoji for this message
        if emoji_str not in self.reaction_history[message.id]:
            self.reaction_history[message.id][emoji_str] = []
            
        # Add user to the list of reactors
        if user.id not in self.reaction_history[message.id][emoji_str]:
            self.reaction_history[message.id][emoji_str].append(user.id)
            
        logger.debug(f"Stored reaction {emoji_str} by {user.id} on message {message.id}")
    
    @commands.Cog.listener()
    async def on_reaction_remove(self, reaction, user):
        """Store removed reaction for sniping"""
        message = reaction.message
        
        # Ignore bot reactions
        if user.bot:
            return
            
        # Store the removed reaction
        self.deleted_reactions[message.guild.id][message.channel.id].append({
            'message_id': message.id,
            'emoji': str(reaction.emoji),
            'user': user,
            'removed_at': datetime.datetime.utcnow()
        })
        
        # Also update reaction history if we're tracking this message
        if message.id in self.reaction_history:
            emoji_str = str(reaction.emoji)
            if emoji_str in self.reaction_history[message.id]:
                if user.id in self.reaction_history[message.id][emoji_str]:
                    self.reaction_history[message.id][emoji_str].remove(user.id)
                    
        logger.debug(f"Stored removed reaction {str(reaction.emoji)} by {user.id} on message {message.id}")
    
    @commands.command(name="snipe")
    async def snipe(self, ctx, index: int = 1):
        """Retrieve a recently deleted message"""
        # Validate index
        if index < 1:
            return await ctx.send("Index must be at least 1.")
            
        # Get the deleted messages for this channel
        deleted = self.deleted_messages.get(ctx.guild.id, {}).get(ctx.channel.id, deque())
        
        # Check if there are deleted messages
        if not deleted:
            return await ctx.send("There are no deleted messages to snipe in this channel.")
            
        # Check if index is valid
        if index > len(deleted):
            return await ctx.send(f"There are only {len(deleted)} deleted messages in this channel.")
            
        # Get the requested message (convert from 1-indexed to 0-indexed)
        message = list(deleted)[-index]
        
        # Create embed
        embed = discord.Embed(
            description=message['content'],
            color=discord.Color.red(),
            timestamp=message['deleted_at']
        )
        
        embed.set_author(
            name=f"{message['author'].display_name}",
            icon_url=message['author'].display_avatar.url
        )
        
        embed.set_footer(text=f"Deleted at • Message {index}/{len(deleted)}")
        
        # Add attachment info if any
        if message['attachments']:
            attachment_links = "\n".join([f"[Attachment {i+1}]({url})" for i, url in enumerate(message['attachments'])])
            embed.add_field(name="Attachments", value=attachment_links, inline=False)
            
        await ctx.send(embed=embed)
    
    @commands.command(name="editsnipe")
    async def editsnipe(self, ctx, index: int = 1):
        """Retrieve a message's original text before edited"""
        # Validate index
        if index < 1:
            return await ctx.send("Index must be at least 1.")
            
        # Get the edited messages for this channel
        edited = self.edited_messages.get(ctx.guild.id, {}).get(ctx.channel.id, deque())
        
        # Check if there are edited messages
        if not edited:
            return await ctx.send("There are no edited messages to snipe in this channel.")
            
        # Check if index is valid
        if index > len(edited):
            return await ctx.send(f"There are only {len(edited)} edited messages in this channel.")
            
        # Get the requested edit (convert from 1-indexed to 0-indexed)
        edit = list(edited)[-index]
        
        # Create embed
        embed = discord.Embed(
            color=discord.Color.orange(),
            timestamp=edit['after']['edited_at']
        )
        
        embed.set_author(
            name=f"{edit['before']['author'].display_name}",
            icon_url=edit['before']['author'].display_avatar.url
        )
        
        embed.add_field(name="Before", value=edit['before']['content'], inline=False)
        embed.add_field(name="After", value=edit['after']['content'], inline=False)
        
        embed.set_footer(text=f"Edited at • Edit {index}/{len(edited)}")
        
        # Add attachment info if any
        if edit['before']['attachments']:
            attachment_links = "\n".join([f"[Attachment {i+1}]({url})" for i, url in enumerate(edit['before']['attachments'])])
            embed.add_field(name="Attachments", value=attachment_links, inline=False)
            
        await ctx.send(embed=embed)
    
    @commands.command(name="reactionsnipe")
    async def reactionsnipe(self, ctx, index: int = 1):
        """Retrieve a deleted reaction from a message"""
        # Validate index
        if index < 1:
            return await ctx.send("Index must be at least 1.")
            
        # Get the deleted reactions for this channel
        deleted = self.deleted_reactions.get(ctx.guild.id, {}).get(ctx.channel.id, deque())
        
        # Check if there are deleted reactions
        if not deleted:
            return await ctx.send("There are no deleted reactions to snipe in this channel.")
            
        # Check if index is valid
        if index > len(deleted):
            return await ctx.send(f"There are only {len(deleted)} deleted reactions in this channel.")
            
        # Get the requested reaction (convert from 1-indexed to 0-indexed)
        reaction = list(deleted)[-index]
        
        # Create embed
        embed = discord.Embed(
            description=f"{reaction['user'].mention} reacted with {reaction['emoji']} to a message",
            color=discord.Color.blue(),
            timestamp=reaction['removed_at']
        )
        
        embed.set_author(
            name=f"{reaction['user'].display_name}",
            icon_url=reaction['user'].display_avatar.url
        )
        
        embed.set_footer(text=f"Removed at • Reaction {index}/{len(deleted)}")
        
        # Add message link if we can construct it
        if ctx.guild.id and ctx.channel.id and reaction['message_id']:
            message_link = f"https://discord.com/channels/{ctx.guild.id}/{ctx.channel.id}/{reaction['message_id']}"
            embed.add_field(name="Message", value=f"[Jump to Message]({message_link})", inline=False)
            
        await ctx.send(embed=embed)
    
    @commands.command(name="reactionhistory")
    async def reactionhistory(self, ctx, message_id: int):
        """See logged reactions for a message"""
        # Check if we have history for this message
        if message_id not in self.reaction_history:
            return await ctx.send("No reaction history found for this message.")
            
        reaction_data = self.reaction_history[message_id]
        
        if not reaction_data:
            return await ctx.send("No reactions found for this message.")
            
        # Create embed
        embed = discord.Embed(
            title="Reaction History",
            description=f"Reactions for message ID: {message_id}",
            color=discord.Color.blue(),
            timestamp=datetime.datetime.utcnow()
        )
        
        # Add reaction info
        for emoji, user_ids in reaction_data.items():
            if user_ids:
                user_mentions = []
                for user_id in user_ids:
                    user = ctx.guild.get_member(user_id)
                    if user:
                        user_mentions.append(user.mention)
                if user_mentions:
                    embed.add_field(name=f"{emoji} ({len(user_mentions)})", value=", ".join(user_mentions[:10]) + ("..." if len(user_mentions) > 10 else ""), inline=False)
        
        # Add message link if possible
        message_link = f"https://discord.com/channels/{ctx.guild.id}/{ctx.channel.id}/{message_id}"
        embed.add_field(name="Message", value=f"[Jump to Message]({message_link})", inline=False)
        
        await ctx.send(embed=embed)
    
    @commands.command(name="clearsnipe")
    @commands.has_permissions(manage_messages=True)
    async def clearsnipe(self, ctx):
        """Clear all deleted messages from snipe history"""
        # Clear deleted messages for this channel
        if ctx.guild.id in self.deleted_messages and ctx.channel.id in self.deleted_messages[ctx.guild.id]:
            self.deleted_messages[ctx.guild.id][ctx.channel.id].clear()
            
        # Clear edited messages for this channel
        if ctx.guild.id in self.edited_messages and ctx.channel.id in self.edited_messages[ctx.guild.id]:
            self.edited_messages[ctx.guild.id][ctx.channel.id].clear()
            
        # Clear deleted reactions for this channel
        if ctx.guild.id in self.deleted_reactions and ctx.channel.id in self.deleted_reactions[ctx.guild.id]:
            self.deleted_reactions[ctx.guild.id][ctx.channel.id].clear()
            
        # Clear purged messages for this channel
        if ctx.guild.id in self.purged_messages and ctx.channel.id in self.purged_messages[ctx.guild.id]:
            self.purged_messages[ctx.guild.id][ctx.channel.id].clear()
            
        await ctx.send("Snipe history for this channel has been cleared.")
    
    @commands.command(name="removesnipe")
    @commands.has_permissions(manage_messages=True)
    async def removesnipe(self, ctx, index: int):
        """Remove a specific snipe from the snipe index"""
        # Validate index
        if index < 1:
            return await ctx.send("Index must be at least 1.")
            
        # Check if there are deleted messages
        deleted = self.deleted_messages.get(ctx.guild.id, {}).get(ctx.channel.id, deque())
        
        if not deleted:
            return await ctx.send("There are no deleted messages to remove.")
            
        # Check if index is valid
        if index > len(deleted):
            return await ctx.send(f"There are only {len(deleted)} deleted messages in this channel.")
            
        # Convert the deque to a list, remove the item, then convert back to a deque
        deleted_list = list(deleted)
        removed = deleted_list.pop(-index)  # Remove from the end (most recent first)
        self.deleted_messages[ctx.guild.id][ctx.channel.id] = deque(deleted_list, maxlen=MAX_SNIPE_HISTORY)
        
        await ctx.send(f"Removed snipe at index {index} from user {removed['author'].display_name}.")
    
    @commands.command(name="purgesnipe")
    @commands.has_permissions(manage_messages=True)
    async def purgesnipe(self, ctx):
        """View messages deleted through a purge"""
        # Check if there are purged messages
        purged = self.purged_messages.get(ctx.guild.id, {}).get(ctx.channel.id, [])
        
        if not purged:
            return await ctx.send("There are no purged messages to snipe in this channel.")
            
        # Create paginated embeds
        pages = []
        messages_per_page = 5
        
        for i in range(0, len(purged), messages_per_page):
            chunk = purged[i:i+messages_per_page]
            
            embed = discord.Embed(
                title=f"Purged Messages ({i+1}-{min(i+messages_per_page, len(purged))}/{len(purged)})",
                color=discord.Color.red(),
                timestamp=datetime.datetime.utcnow()
            )
            
            for j, message in enumerate(chunk):
                embed.add_field(
                    name=f"{i+j+1}. {message['author'].display_name} at {message['created_at'].strftime('%H:%M:%S')}",
                    value=message['content'][:1024] + ("..." if len(message['content']) > 1024 else ""),
                    inline=False
                )
                
            pages.append(embed)
            
        if not pages:
            return await ctx.send("No purged messages to display.")
            
        # Send the first page
        current_page = 0
        message = await ctx.send(embed=pages[current_page])
        
        # Add reactions for pagination
        if len(pages) > 1:
            await message.add_reaction("⬅️")
            await message.add_reaction("➡️")
            
            def check(reaction, user):
                return user == ctx.author and str(reaction.emoji) in ["⬅️", "➡️"] and reaction.message.id == message.id
                
            while True:
                try:
                    reaction, user = await self.bot.wait_for("reaction_add", timeout=60.0, check=check)
                    
                    if str(reaction.emoji) == "➡️" and current_page < len(pages) - 1:
                        current_page += 1
                        await message.edit(embed=pages[current_page])
                        await message.remove_reaction(reaction, user)
                        
                    elif str(reaction.emoji) == "⬅️" and current_page > 0:
                        current_page -= 1
                        await message.edit(embed=pages[current_page])
                        await message.remove_reaction(reaction, user)
                        
                    else:
                        await message.remove_reaction(reaction, user)
                        
                except asyncio.TimeoutError:
                    await message.clear_reactions()
                    break

async def setup(bot):
    await bot.add_cog(Snipe(bot)) 