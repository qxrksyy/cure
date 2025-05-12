import discord
from discord.ext import commands
import asyncio
import re
import logging
from datetime import datetime, timedelta

logger = logging.getLogger('bot')

class PurgeCommands(commands.Cog):
    """Commands for purging messages in various ways"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @commands.group(name="purge", invoke_without_command=True)
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx, amount: int = 5, member: discord.Member = None):
        """Deletes the specified amount of messages from the current channel"""
        if amount <= 0:
            await ctx.send("❌ Amount must be greater than 0.")
            return
            
        if amount > 200:
            await ctx.send("⚠️ You can only purge up to 200 messages at once to avoid rate limits. Using 200.")
            amount = 200
            
        # Delete the command message
        await ctx.message.delete()
        
        # Confirmation message for large purges
        if amount > 50:
            confirm_msg = await ctx.send(
                f"⚠️ Are you sure you want to delete {amount} messages? "
                f"React with ✅ to confirm or ❌ to cancel."
            )
            
            await confirm_msg.add_reaction('✅')
            await confirm_msg.add_reaction('❌')
            
            def check(reaction, user):
                return user == ctx.author and str(reaction.emoji) in ['✅', '❌'] and reaction.message.id == confirm_msg.id
                
            try:
                reaction, user = await self.bot.wait_for('reaction_add', timeout=15.0, check=check)
                
                if str(reaction.emoji) == '❌':
                    await confirm_msg.delete()
                    return
                
                await confirm_msg.delete()
            except asyncio.TimeoutError:
                await confirm_msg.delete()
                await ctx.send("❌ Purge operation timed out.", delete_after=5)
                return
                
        try:
            # Define the check function for message filtering
            def check_message(message):
                if member is not None:
                    return message.author == member
                return True
                
            # Perform the purge
            deleted = await ctx.channel.purge(limit=amount, check=check_message)
            
            # Send feedback
            feedback_msg = await ctx.send(
                f"✅ Successfully deleted {len(deleted)} message{'s' if len(deleted) != 1 else ''}.",
                delete_after=5
            )
            
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to delete messages in this channel.")
        except discord.HTTPException as e:
            logger.error(f"Error when purging messages: {str(e)}")
            await ctx.send(f"❌ An error occurred while purging messages: {str(e)}")

    @purge.command(name="startswith")
    @commands.has_permissions(manage_messages=True)
    async def purge_startswith(self, ctx, *, substring: str):
        """Purge messages that start with a given substring"""
        # Delete the command message
        await ctx.message.delete()
        
        try:
            # Define the check function
            def check_message(message):
                return message.content.startswith(substring)
                
            # Perform the purge
            deleted = await ctx.channel.purge(limit=100, check=check_message)
            
            # Send feedback
            await ctx.send(
                f"✅ Successfully deleted {len(deleted)} message{'s' if len(deleted) != 1 else ''} "
                f"that start with '{substring}'.",
                delete_after=5
            )
            
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to delete messages in this channel.")
        except discord.HTTPException as e:
            logger.error(f"Error when purging messages: {str(e)}")
            await ctx.send(f"❌ An error occurred while purging messages: {str(e)}")
    
    @purge.command(name="stickers")
    @commands.has_permissions(manage_messages=True)
    async def purge_stickers(self, ctx, search: int = 100):
        """Purge stickers from chat"""
        # Delete the command message
        await ctx.message.delete()
        
        try:
            # Define the check function
            def check_message(message):
                return message.stickers
                
            # Perform the purge
            deleted = await ctx.channel.purge(limit=search, check=check_message)
            
            # Send feedback
            await ctx.send(
                f"✅ Successfully deleted {len(deleted)} message{'s' if len(deleted) != 1 else ''} with stickers.",
                delete_after=5
            )
            
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to delete messages in this channel.")
        except discord.HTTPException as e:
            logger.error(f"Error when purging stickers: {str(e)}")
            await ctx.send(f"❌ An error occurred while purging stickers: {str(e)}")
    
    @purge.command(name="mentions")
    @commands.has_permissions(manage_messages=True)
    async def purge_mentions(self, ctx, member: discord.Member, search: int = 100):
        """Purge mentions for a member from chat"""
        # Delete the command message
        await ctx.message.delete()
        
        try:
            # Define the check function
            def check_message(message):
                return member.mentioned_in(message)
                
            # Perform the purge
            deleted = await ctx.channel.purge(limit=search, check=check_message)
            
            # Send feedback
            await ctx.send(
                f"✅ Successfully deleted {len(deleted)} message{'s' if len(deleted) != 1 else ''} "
                f"mentioning {member.display_name}.",
                delete_after=5
            )
            
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to delete messages in this channel.")
        except discord.HTTPException as e:
            logger.error(f"Error when purging mentions: {str(e)}")
            await ctx.send(f"❌ An error occurred while purging mentions: {str(e)}")
    
    @purge.command(name="after")
    @commands.has_permissions(manage_messages=True)
    async def purge_after(self, ctx, message_id: int):
        """Purge messages after a given message ID"""
        # Delete the command message
        await ctx.message.delete()
        
        try:
            # Get the message
            try:
                message = await ctx.channel.fetch_message(message_id)
            except discord.NotFound:
                await ctx.send("❌ Message not found.")
                return
                
            # Perform the purge
            deleted = await ctx.channel.purge(limit=200, after=message)
            
            # Send feedback
            await ctx.send(
                f"✅ Successfully deleted {len(deleted)} message{'s' if len(deleted) != 1 else ''} "
                f"after message ID {message_id}.",
                delete_after=5
            )
            
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to delete messages in this channel.")
        except discord.HTTPException as e:
            logger.error(f"Error when purging messages: {str(e)}")
            await ctx.send(f"❌ An error occurred while purging messages: {str(e)}")
    
    @purge.command(name="bots")
    @commands.has_permissions(manage_messages=True)
    async def purge_bots(self, ctx, search: int = 100):
        """Purge messages from bots in chat"""
        # Delete the command message
        await ctx.message.delete()
        
        try:
            # Define the check function
            def check_message(message):
                return message.author.bot
                
            # Perform the purge
            deleted = await ctx.channel.purge(limit=search, check=check_message)
            
            # Send feedback
            await ctx.send(
                f"✅ Successfully deleted {len(deleted)} message{'s' if len(deleted) != 1 else ''} from bots.",
                delete_after=5
            )
            
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to delete messages in this channel.")
        except discord.HTTPException as e:
            logger.error(f"Error when purging bot messages: {str(e)}")
            await ctx.send(f"❌ An error occurred while purging bot messages: {str(e)}")
    
    @purge.command(name="humans")
    @commands.has_permissions(manage_messages=True)
    async def purge_humans(self, ctx, search: int = 100):
        """Purge messages from humans in chat"""
        # Delete the command message
        await ctx.message.delete()
        
        try:
            # Define the check function
            def check_message(message):
                return not message.author.bot
                
            # Perform the purge
            deleted = await ctx.channel.purge(limit=search, check=check_message)
            
            # Send feedback
            await ctx.send(
                f"✅ Successfully deleted {len(deleted)} message{'s' if len(deleted) != 1 else ''} from humans.",
                delete_after=5
            )
            
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to delete messages in this channel.")
        except discord.HTTPException as e:
            logger.error(f"Error when purging human messages: {str(e)}")
            await ctx.send(f"❌ An error occurred while purging human messages: {str(e)}")
    
    @purge.command(name="contains")
    @commands.has_permissions(manage_messages=True)
    async def purge_contains(self, ctx, *, substring: str):
        """Purges messages containing given substring"""
        # Delete the command message
        await ctx.message.delete()
        
        try:
            # Define the check function
            def check_message(message):
                return substring.lower() in message.content.lower()
                
            # Perform the purge
            deleted = await ctx.channel.purge(limit=100, check=check_message)
            
            # Send feedback
            await ctx.send(
                f"✅ Successfully deleted {len(deleted)} message{'s' if len(deleted) != 1 else ''} "
                f"containing '{substring}'.",
                delete_after=5
            )
            
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to delete messages in this channel.")
        except discord.HTTPException as e:
            logger.error(f"Error when purging messages: {str(e)}")
            await ctx.send(f"❌ An error occurred while purging messages: {str(e)}")
    
    @purge.command(name="emoji")
    @commands.has_permissions(manage_messages=True)
    async def purge_emoji(self, ctx, search: int = 100):
        """Purge emojis from chat"""
        # Delete the command message
        await ctx.message.delete()
        
        try:
            # Custom emoji pattern
            emoji_pattern = re.compile(r'<a?:[a-zA-Z0-9_]+:[0-9]+>')
            
            # Define the check function
            def check_message(message):
                return emoji_pattern.search(message.content) is not None
                
            # Perform the purge
            deleted = await ctx.channel.purge(limit=search, check=check_message)
            
            # Send feedback
            await ctx.send(
                f"✅ Successfully deleted {len(deleted)} message{'s' if len(deleted) != 1 else ''} with emojis.",
                delete_after=5
            )
            
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to delete messages in this channel.")
        except discord.HTTPException as e:
            logger.error(f"Error when purging emoji messages: {str(e)}")
            await ctx.send(f"❌ An error occurred while purging emoji messages: {str(e)}")
    
    @purge.command(name="links")
    @commands.has_permissions(manage_messages=True)
    async def purge_links(self, ctx, search: int = 100):
        """Purge messages containing links"""
        # Delete the command message
        await ctx.message.delete()
        
        try:
            # URL pattern
            url_pattern = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
            
            # Define the check function
            def check_message(message):
                return url_pattern.search(message.content) is not None
                
            # Perform the purge
            deleted = await ctx.channel.purge(limit=search, check=check_message)
            
            # Send feedback
            await ctx.send(
                f"✅ Successfully deleted {len(deleted)} message{'s' if len(deleted) != 1 else ''} with links.",
                delete_after=5
            )
            
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to delete messages in this channel.")
        except discord.HTTPException as e:
            logger.error(f"Error when purging link messages: {str(e)}")
            await ctx.send(f"❌ An error occurred while purging link messages: {str(e)}")
    
    @purge.command(name="reactions")
    @commands.has_permissions(manage_messages=True)
    async def purge_reactions(self, ctx, search: int = 100):
        """Purge reactions from messages in chat"""
        # Delete the command message
        await ctx.message.delete()
        
        try:
            # Get messages
            messages = []
            async for message in ctx.channel.history(limit=search):
                if message.reactions:
                    messages.append(message)
            
            if not messages:
                await ctx.send("❌ No messages with reactions found.", delete_after=5)
                return
            
            # Remove reactions
            for message in messages:
                await message.clear_reactions()
            
            # Send feedback
            await ctx.send(
                f"✅ Successfully removed reactions from {len(messages)} message{'s' if len(messages) != 1 else ''}.",
                delete_after=5
            )
            
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to manage reactions in this channel.")
        except discord.HTTPException as e:
            logger.error(f"Error when purging reactions: {str(e)}")
            await ctx.send(f"❌ An error occurred while purging reactions: {str(e)}")

    @purge.command(name="webhooks")
    @commands.has_permissions(manage_messages=True)
    async def purge_webhooks(self, ctx, search: int = 100):
        """Purge messages from webhooks in chat"""
        # Delete the command message
        await ctx.message.delete()
        
        try:
            # Define the check function
            def check_message(message):
                return message.webhook_id is not None
                
            # Perform the purge
            deleted = await ctx.channel.purge(limit=search, check=check_message)
            
            # Send feedback
            await ctx.send(
                f"✅ Successfully deleted {len(deleted)} message{'s' if len(deleted) != 1 else ''} from webhooks.",
                delete_after=5
            )
            
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to delete messages in this channel.")
        except discord.HTTPException as e:
            logger.error(f"Error when purging webhook messages: {str(e)}")
            await ctx.send(f"❌ An error occurred while purging webhook messages: {str(e)}")

async def setup(bot):
    await bot.add_cog(PurgeCommands(bot)) 