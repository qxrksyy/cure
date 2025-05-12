import discord
from discord.ext import commands
import asyncio
import re
import logging
from datetime import datetime, timedelta

logger = logging.getLogger('bot')

class PurgeCommands2(commands.Cog):
    """Additional commands for purging messages in various ways"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @commands.group(invoke_without_command=True)
    async def purge2(self, ctx):
        """Command group for additional purge commands"""
        # Just a placeholder that will never be called directly
        # All commands will be merged into the main purge group
        pass
    
    @purge2.command(name="upto")
    @commands.has_permissions(manage_messages=True)
    async def purge_upto(self, ctx, message_id: int):
        """Purge messages up to a message link"""
        # Delete the command message
        await ctx.message.delete()
        
        try:
            # Get the message
            try:
                message = await ctx.channel.fetch_message(message_id)
            except discord.NotFound:
                await ctx.send("❌ Message not found.")
                return
                
            # Perform the purge up to the specified message
            deleted = await ctx.channel.purge(limit=200, before=ctx.message, after=message)
            
            # Send feedback
            await ctx.send(
                f"✅ Successfully deleted {len(deleted)} message{'s' if len(deleted) != 1 else ''} "
                f"up to message ID {message_id}.",
                delete_after=5
            )
            
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to delete messages in this channel.")
        except discord.HTTPException as e:
            logger.error(f"Error when purging messages: {str(e)}")
            await ctx.send(f"❌ An error occurred while purging messages: {str(e)}")
    
    @purge2.command(name="attachments")
    @commands.has_permissions(manage_messages=True)
    async def purge_attachments(self, ctx, search: int = 100):
        """Purge files/attachments from chat"""
        # Delete the command message
        await ctx.message.delete()
        
        try:
            # Define the check function
            def check_message(message):
                return len(message.attachments) > 0
                
            # Perform the purge
            deleted = await ctx.channel.purge(limit=search, check=check_message)
            
            # Send feedback
            await ctx.send(
                f"✅ Successfully deleted {len(deleted)} message{'s' if len(deleted) != 1 else ''} with attachments.",
                delete_after=5
            )
            
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to delete messages in this channel.")
        except discord.HTTPException as e:
            logger.error(f"Error when purging attachment messages: {str(e)}")
            await ctx.send(f"❌ An error occurred while purging attachment messages: {str(e)}")
    
    @purge2.command(name="between")
    @commands.has_permissions(manage_messages=True)
    async def purge_between(self, ctx, start_id: int, finish_id: int):
        """Purge between two messages"""
        # Delete the command message
        await ctx.message.delete()
        
        try:
            # Ensure start_id is before finish_id
            if start_id > finish_id:
                start_id, finish_id = finish_id, start_id
                
            # Get the messages
            try:
                start_message = await ctx.channel.fetch_message(start_id)
                finish_message = await ctx.channel.fetch_message(finish_id)
            except discord.NotFound:
                await ctx.send("❌ One or both messages not found.")
                return
                
            # Perform the purge between the two messages
            deleted = await ctx.channel.purge(
                limit=200, 
                after=start_message,
                before=finish_message
            )
            
            # Send feedback
            await ctx.send(
                f"✅ Successfully deleted {len(deleted)} message{'s' if len(deleted) != 1 else ''} "
                f"between message IDs {start_id} and {finish_id}.",
                delete_after=5
            )
            
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to delete messages in this channel.")
        except discord.HTTPException as e:
            logger.error(f"Error when purging messages: {str(e)}")
            await ctx.send(f"❌ An error occurred while purging messages: {str(e)}")
    
    @purge2.command(name="embeds")
    @commands.has_permissions(manage_messages=True)
    async def purge_embeds(self, ctx, search: int = 100):
        """Purge embeds from chat"""
        # Delete the command message
        await ctx.message.delete()
        
        try:
            # Define the check function
            def check_message(message):
                return len(message.embeds) > 0
                
            # Perform the purge
            deleted = await ctx.channel.purge(limit=search, check=check_message)
            
            # Send feedback
            await ctx.send(
                f"✅ Successfully deleted {len(deleted)} message{'s' if len(deleted) != 1 else ''} with embeds.",
                delete_after=5
            )
            
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to delete messages in this channel.")
        except discord.HTTPException as e:
            logger.error(f"Error when purging embed messages: {str(e)}")
            await ctx.send(f"❌ An error occurred while purging embed messages: {str(e)}")
    
    @purge2.command(name="before")
    @commands.has_permissions(manage_messages=True)
    async def purge_before(self, ctx, message_id: int):
        """Purge messages before a given message ID"""
        # Delete the command message
        await ctx.message.delete()
        
        try:
            # Get the message
            try:
                message = await ctx.channel.fetch_message(message_id)
            except discord.NotFound:
                await ctx.send("❌ Message not found.")
                return
                
            # Perform the purge before the specified message
            deleted = await ctx.channel.purge(limit=200, before=message)
            
            # Send feedback
            await ctx.send(
                f"✅ Successfully deleted {len(deleted)} message{'s' if len(deleted) != 1 else ''} "
                f"before message ID {message_id}.",
                delete_after=5
            )
            
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to delete messages in this channel.")
        except discord.HTTPException as e:
            logger.error(f"Error when purging messages: {str(e)}")
            await ctx.send(f"❌ An error occurred while purging messages: {str(e)}")
    
    @purge2.command(name="endswith")
    @commands.has_permissions(manage_messages=True)
    async def purge_endswith(self, ctx, *, substring: str):
        """Purge messages that ends with a given substring"""
        # Delete the command message
        await ctx.message.delete()
        
        try:
            # Define the check function
            def check_message(message):
                return message.content.endswith(substring)
                
            # Perform the purge
            deleted = await ctx.channel.purge(limit=100, check=check_message)
            
            # Send feedback
            await ctx.send(
                f"✅ Successfully deleted {len(deleted)} message{'s' if len(deleted) != 1 else ''} "
                f"that end with '{substring}'.",
                delete_after=5
            )
            
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to delete messages in this channel.")
        except discord.HTTPException as e:
            logger.error(f"Error when purging messages: {str(e)}")
            await ctx.send(f"❌ An error occurred while purging messages: {str(e)}")
    
    @purge2.command(name="images")
    @commands.has_permissions(manage_messages=True)
    async def purge_images(self, ctx, search: int = 100):
        """Purge images (including links) from chat"""
        # Delete the command message
        await ctx.message.delete()
        
        try:
            # URL image patterns
            image_url_pattern = re.compile(r'http[s]?://.*\.(jpg|jpeg|png|gif|webp)', re.IGNORECASE)
            
            # Define the check function
            def check_message(message):
                # Check for attachments with image extensions
                for attachment in message.attachments:
                    if attachment.filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
                        return True
                
                # Check for image links
                if image_url_pattern.search(message.content):
                    return True
                    
                # Check for embeds with images
                for embed in message.embeds:
                    if embed.image or embed.thumbnail:
                        return True
                        
                return False
                
            # Perform the purge
            deleted = await ctx.channel.purge(limit=search, check=check_message)
            
            # Send feedback
            await ctx.send(
                f"✅ Successfully deleted {len(deleted)} message{'s' if len(deleted) != 1 else ''} with images.",
                delete_after=5
            )
            
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to delete messages in this channel.")
        except discord.HTTPException as e:
            logger.error(f"Error when purging image messages: {str(e)}")
            await ctx.send(f"❌ An error occurred while purging image messages: {str(e)}")

    @commands.command(name="botclear")
    @commands.has_permissions(manage_messages=True)
    async def botclear(self, ctx, search: int = 100):
        """Clear messages from bots"""
        # Use purge_bots directly instead of duplicating code
        await ctx.invoke(self.bot.get_command("purge bots"), search=search)

    @commands.command(name="softban")
    @commands.has_permissions(ban_members=True)
    async def softban(self, ctx, member: discord.Member, *, reason="No reason provided"):
        """Softbans the mentioned user and deleting 1 day of messages"""
        if member == ctx.author:
            await ctx.send("❌ You cannot softban yourself.")
            return
            
        if member.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
            await ctx.send("❌ You cannot softban members with roles higher than or equal to yours.")
            return
            
        try:
            # Create an embed for the softban
            embed = discord.Embed(
                title="Member Softbanned",
                description=f"{member.mention} has been softbanned from the server.",
                color=discord.Color.orange(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Reason", value=reason)
            embed.add_field(name="Softbanned by", value=ctx.author.mention)
            embed.add_field(name="Message History Deleted", value="1 day")
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(text=f"User ID: {member.id}")
            
            # Try to send a DM to the user being softbanned
            try:
                dm_embed = discord.Embed(
                    title="You have been softbanned",
                    description=f"You have been softbanned from {ctx.guild.name}\nYou can rejoin the server if you have an invite link.",
                    color=discord.Color.orange(),
                    timestamp=datetime.utcnow()
                )
                dm_embed.add_field(name="Reason", value=reason)
                dm_embed.add_field(name="Softbanned by", value=ctx.author.name)
                dm_embed.set_footer(text="A softban is a ban followed by an immediate unban to remove your recent messages.")
                await member.send(embed=dm_embed)
            except (discord.Forbidden, discord.HTTPException):
                # User has DMs closed or there was an error
                pass
                
            # Execute the softban (ban and then unban)
            await member.ban(delete_message_days=1, reason=f"{reason} | Softbanned by {ctx.author}")
            await ctx.guild.unban(member, reason=f"Softban by {ctx.author} completed")
            await ctx.send(embed=embed)
            
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to ban that member.")
        except Exception as e:
            logger.error(f"Error when softbanning user: {str(e)}")
            await ctx.send(f"❌ An error occurred: {str(e)}")

async def setup(bot):
    await bot.add_cog(PurgeCommands2(bot)) 