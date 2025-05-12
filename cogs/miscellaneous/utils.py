import discord
from discord.ext import commands
import json
import os
import logging
import asyncio
import aiohttp
import tempfile
from datetime import datetime
import subprocess
import re
import io
import random
import time

logger = logging.getLogger('bot')

class MiscUtils(commands.Cog):
    """
    Miscellaneous utility commands that don't fit in other categories
    """
    
    def __init__(self, bot):
        self.bot = bot
        self.config_path = "data/miscellaneous"
        self.donator_role_id = None  # Replace with actual donator role ID when available
        
        # Create directory if it doesn't exist
        os.makedirs(self.config_path, exist_ok=True)
    
    async def is_donator(self, ctx):
        """Check if a user is a donator"""
        if not self.donator_role_id:
            return False
            
        if ctx.guild is None:
            return False
            
        member = ctx.guild.get_member(ctx.author.id)
        if not member:
            return False
            
        return any(role.id == self.donator_role_id for role in member.roles)

    # Use this static method for the check decorator
    @staticmethod
    async def is_donator_check(ctx):
        """Static method for @commands.check decorator"""
        cog = ctx.bot.get_cog("MiscUtils")
        if not cog:
            return False
        return await cog.is_donator(ctx)
    
    @commands.command()
    @commands.has_permissions(manage_guild=True)
    async def seticon(self, ctx, url: str = None):
        """Set a new guild icon"""
        if not url and not ctx.message.attachments:
            await ctx.send("❌ Please provide a URL or attach an image to set as the server icon.")
            return
            
        # Get image URL from either parameter or attachment
        image_url = url
        if not image_url and ctx.message.attachments:
            image_url = ctx.message.attachments[0].url
        
        async with ctx.typing():
            try:
                # Download image
                async with aiohttp.ClientSession() as session:
                    async with session.get(image_url) as response:
                        if response.status != 200:
                            await ctx.send(f"❌ Failed to download image. Status code: {response.status}")
                            return
                            
                        image_data = await response.read()
                
                # Update guild icon
                await ctx.guild.edit(icon=image_data)
                
                # Success message
                embed = discord.Embed(
                    title="Server Icon Updated",
                    description="The server icon has been updated successfully.",
                    color=discord.Color.green(),
                    timestamp=datetime.utcnow()
                )
                embed.set_thumbnail(url=ctx.guild.icon.url if ctx.guild.icon else image_url)
                await ctx.send(embed=embed)
                
            except discord.Forbidden:
                await ctx.send("❌ I don't have permission to change the server icon.")
            except discord.HTTPException as e:
                await ctx.send(f"❌ Failed to set server icon: {str(e)}")
    
    @commands.command()
    @commands.has_permissions(manage_guild=True)
    async def setbanner(self, ctx, url: str = None):
        """Set a new guild banner"""
        if not ctx.guild.premium_tier >= 2:
            await ctx.send("❌ This server needs to be at least level 2 (7 boosts) to have a banner.")
            return
            
        if not url and not ctx.message.attachments:
            await ctx.send("❌ Please provide a URL or attach an image to set as the server banner.")
            return
            
        # Get image URL from either parameter or attachment
        image_url = url
        if not image_url and ctx.message.attachments:
            image_url = ctx.message.attachments[0].url
        
        async with ctx.typing():
            try:
                # Download image
                async with aiohttp.ClientSession() as session:
                    async with session.get(image_url) as response:
                        if response.status != 200:
                            await ctx.send(f"❌ Failed to download image. Status code: {response.status}")
                            return
                            
                        image_data = await response.read()
                
                # Update guild banner
                await ctx.guild.edit(banner=image_data)
                
                # Success message
                embed = discord.Embed(
                    title="Server Banner Updated",
                    description="The server banner has been updated successfully.",
                    color=discord.Color.green(),
                    timestamp=datetime.utcnow()
                )
                if ctx.guild.banner:
                    embed.set_image(url=ctx.guild.banner.url)
                await ctx.send(embed=embed)
                
            except discord.Forbidden:
                await ctx.send("❌ I don't have permission to change the server banner.")
            except discord.HTTPException as e:
                await ctx.send(f"❌ Failed to set server banner: {str(e)}")
    
    @commands.command()
    @commands.has_permissions(manage_guild=True)
    async def setsplashbackground(self, ctx, url: str = None):
        """Set a new guild splash background"""
        if not ctx.guild.premium_tier >= 1:
            await ctx.send("❌ This server needs to be at least level 1 (2 boosts) to have an invite splash background.")
            return
            
        if not url and not ctx.message.attachments:
            await ctx.send("❌ Please provide a URL or attach an image to set as the server splash background.")
            return
            
        # Get image URL from either parameter or attachment
        image_url = url
        if not image_url and ctx.message.attachments:
            image_url = ctx.message.attachments[0].url
        
        async with ctx.typing():
            try:
                # Download image
                async with aiohttp.ClientSession() as session:
                    async with session.get(image_url) as response:
                        if response.status != 200:
                            await ctx.send(f"❌ Failed to download image. Status code: {response.status}")
                            return
                            
                        image_data = await response.read()
                
                # Update guild splash
                await ctx.guild.edit(splash=image_data)
                
                # Success message
                embed = discord.Embed(
                    title="Server Splash Background Updated",
                    description="The server invite splash background has been updated successfully.",
                    color=discord.Color.green(),
                    timestamp=datetime.utcnow()
                )
                if ctx.guild.splash:
                    embed.set_image(url=ctx.guild.splash.url)
                await ctx.send(embed=embed)
                
            except discord.Forbidden:
                await ctx.send("❌ I don't have permission to change the server splash background.")
            except discord.HTTPException as e:
                await ctx.send(f"❌ Failed to set server splash background: {str(e)}")
    
    @commands.command()
    @commands.check(is_donator_check)
    async def makemp3(self, ctx, url: str = None):
        """Convert a video to an audio file (requires Donator role)"""
        if not url and not ctx.message.attachments:
            await ctx.send("❌ Please provide a URL or attach a video file to convert to MP3.")
            return
            
        # Get video URL from either parameter or attachment
        video_url = url
        if not video_url and ctx.message.attachments:
            video_url = ctx.message.attachments[0].url
        
        await ctx.send("🔄 Starting conversion process. This may take a moment...")
        
        # This is a simplified version. In a real implementation, you'd need:
        # 1. A secure way to handle the download and conversion
        # 2. Error handling for large files or unsupported formats
        # 3. Perhaps a queue system for multiple requests
        # 4. Proper cleanup of temporary files
        
        # For demonstration purposes, just show that we'd process the URL
        await asyncio.sleep(2)  # Simulate processing time
        
        await ctx.send(f"⚠️ This command requires a donator role and server-side processing capabilities. The video at `{video_url}` would be converted to MP3 format.")
        
    @commands.command()
    async def uwu(self, ctx, *, text: str = None):
        """Uwuify text"""
        if not text:
            # If replying to a message, use that content
            if ctx.message.reference and ctx.message.reference.resolved:
                text = ctx.message.reference.resolved.content
            else:
                await ctx.send("❌ Please provide some text to uwuify.")
                return
        
        # Uwuify the text
        uwuified = self._uwuify_text(text)
        
        # Send the uwuified text
        await ctx.send(uwuified)
    
    def _uwuify_text(self, text):
        """Convert normal text to uwu speak"""
        # Replace common patterns
        uwuified = text.replace('r', 'w').replace('l', 'w')
        uwuified = uwuified.replace('R', 'W').replace('L', 'W')
        
        # Replace "n" followed by a vowel with "ny"
        uwuified = re.sub(r'n([aeiou])', r'ny\1', uwuified)
        uwuified = re.sub(r'N([aeiou])', r'Ny\1', uwuified)
        uwuified = re.sub(r'N([AEIOU])', r'NY\1', uwuified)
        
        # Replace "th" with "d"
        uwuified = uwuified.replace('th', 'd').replace('Th', 'D')
        
        # Add uwu faces randomly
        faces = [' uwu', ' owo', ' >w<', ' ^w^', ' :3', ' >_<', '']
        words = uwuified.split()
        
        # Approximately 1/4 chance to add a face after a word
        for i in range(len(words)):
            if random.random() < 0.15 and i > 0:  # Don't add a face to the first word
                words[i] += random.choice(faces)
        
        # Sometimes add stuttering
        for i in range(len(words)):
            if random.random() < 0.1 and words[i] and words[i][0].isalpha():
                words[i] = words[i][0] + '-' + words[i]
        
        return ' '.join(words)
    
    @commands.command()
    async def quickpoll(self, ctx, *, message: str = None):
        """Add up/down arrow to message initiating a poll"""
        if not message:
            if ctx.message.reference and ctx.message.reference.resolved:
                message_to_poll = ctx.message.reference.resolved
            else:
                await ctx.send("❌ Please provide poll content or reply to a message to make it a poll.")
                return
        else:
            # Create a new message with the poll content
            message_to_poll = await ctx.send(message)
        
        # Add reactions for voting
        await message_to_poll.add_reaction('👍')
        await message_to_poll.add_reaction('👎')
        
        # Confirmation
        await ctx.message.add_reaction('✅')
    
    @commands.command()
    async def poll(self, ctx, time: str = None, *, question: str = None):
        """Create a short poll with a time limit"""
        if not question:
            await ctx.send("❌ Please provide a question for the poll.")
            return
            
        # Parse time if provided (default to 5 minutes)
        duration = 300  # 5 minutes in seconds
        if time:
            try:
                # Check for formats like "5m", "1h", etc.
                unit = time[-1].lower()
                value = int(time[:-1])
                
                if unit == 's':
                    duration = min(value, 3600)  # Cap at 1 hour
                elif unit == 'm':
                    duration = min(value * 60, 3600 * 24)  # Cap at 24 hours
                elif unit == 'h':
                    duration = min(value * 3600, 3600 * 24)  # Cap at 24 hours
                else:
                    # If no valid unit, assume minutes
                    duration = min(int(time) * 60, 3600 * 24)
            except ValueError:
                await ctx.send("❌ Invalid time format. Using default time of 5 minutes.")
        
        # Create poll embed
        embed = discord.Embed(
            title="📊 Poll",
            description=question,
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(
            name="Vote",
            value="React with 👍 or 👎 to vote!",
            inline=False
        )
        
        # Add footer with time info
        minutes = duration // 60
        seconds = duration % 60
        time_str = f"{minutes}m {seconds}s" if seconds else f"{minutes}m"
        embed.set_footer(text=f"Poll ends in {time_str} | Started by {ctx.author.display_name}")
        
        # Send poll message
        poll_message = await ctx.send(embed=embed)
        
        # Add reactions
        await poll_message.add_reaction('👍')
        await poll_message.add_reaction('👎')
        
        # Wait for poll to complete
        await asyncio.sleep(duration)
        
        # Fetch the message again to get updated reactions
        try:
            poll_message = await ctx.channel.fetch_message(poll_message.id)
            
            # Count votes
            upvotes = 0
            downvotes = 0
            
            for reaction in poll_message.reactions:
                if str(reaction.emoji) == '👍':
                    upvotes = reaction.count - 1  # Subtract bot's reaction
                elif str(reaction.emoji) == '👎':
                    downvotes = reaction.count - 1  # Subtract bot's reaction
            
            # Update embed with results
            result_embed = discord.Embed(
                title="📊 Poll Results",
                description=question,
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            
            total_votes = upvotes + downvotes
            
            # Calculate percentages
            up_percent = int((upvotes / total_votes) * 100) if total_votes > 0 else 0
            down_percent = int((downvotes / total_votes) * 100) if total_votes > 0 else 0
            
            result_embed.add_field(
                name="Results",
                value=f"👍 {upvotes} votes ({up_percent}%)\n👎 {downvotes} votes ({down_percent}%)\nTotal: {total_votes} votes",
                inline=False
            )
            
            result_embed.set_footer(text=f"Poll started by {ctx.author.display_name}")
            
            await poll_message.edit(embed=result_embed)
            await ctx.send(f"📊 Poll ended! Check results above.")
            
        except discord.NotFound:
            logger.warning("Poll message was deleted before it could be updated with results.")
        except Exception as e:
            logger.error(f"Error updating poll results: {str(e)}")
            
    @commands.command()
    @commands.check(is_donator_check)
    async def chatgpt(self, ctx, *, question: str = None):
        """Ask a question using the ChatGPT API (requires Donator role)"""
        if not question:
            await ctx.send("❌ Please provide a question for ChatGPT.")
            return
            
        # Begin typing to indicate the bot is processing
        async with ctx.typing():
            # Simulate API response time
            await asyncio.sleep(2)
            
            # Since we don't have actual OpenAI API integration here, just provide a message
            await ctx.send(f"⚠️ This command requires a donator role and OpenAI API integration. Your question was: '{question}'")
            await ctx.send("In a full implementation, this would connect to the OpenAI API and return a response from ChatGPT.")

async def setup(bot):
    await bot.add_cog(MiscUtils(bot)) 