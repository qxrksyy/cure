import discord
from discord.ext import commands
import json
import os
import logging
from datetime import datetime
import aiohttp
import re
import tempfile
import io
import time
import asyncio

logger = logging.getLogger('bot')

class Information(commands.Cog):
    """
    Information and utility commands for looking up various data
    """
    
    def __init__(self, bot):
        self.bot = bot
        self.config_path = "data/miscellaneous/information"
        
        # Create directory if it doesn't exist
        os.makedirs(self.config_path, exist_ok=True)
    
    @commands.group(invoke_without_command=True)
    async def emoji(self, ctx):
        """Manage server custom emojis"""
        embed = discord.Embed(
            title="Emoji Management",
            description="Manage the custom emojis in your server",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(
            name="Available Commands",
            value=(
                "`emoji add <emoji> <name>` - Create emoji(s)\n"
                "`emoji edit <emoji> <name>` - Rename an emoji\n"
                "`emoji delete <emojis>` - Delete emoji(s)\n"
                "`emoji enlarge <emoji>` - Enlarge an emoji and return an image\n"
                "`emoji list` - View the emojis in the server"
            ),
            inline=False
        )
        
        embed.set_footer(text="Use these commands to manage server emojis")
        
        await ctx.send(embed=embed)
    
    @emoji.command(name="edit")
    @commands.has_permissions(manage_emojis=True)
    async def editemoji(self, ctx, emoji: discord.Emoji, *, name: str):
        """Rename an emoji"""
        # Check if emoji is from this server
        if emoji.guild.id != ctx.guild.id:
            await ctx.send("❌ That emoji is not from this server.")
            return
        
        # Validate emoji name (alphanumeric and underscores only)
        if not re.match(r'^[a-zA-Z0-9_]+$', name):
            await ctx.send("❌ Emoji names can only contain letters, numbers, and underscores.")
            return
        
        old_name = emoji.name
        
        try:
            # Edit the emoji name
            await emoji.edit(name=name)
            
            # Success message
            embed = discord.Embed(
                title="Emoji Renamed",
                description=f"Successfully renamed emoji from `{old_name}` to `{name}`",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            embed.set_thumbnail(url=emoji.url)
            
            await ctx.send(embed=embed)
            
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to edit emojis.")
        except discord.HTTPException as e:
            await ctx.send(f"❌ Failed to rename emoji: {str(e)}")
    
    @emoji.command(name="add")
    @commands.has_permissions(manage_emojis=True)
    async def addemoji(self, ctx, emoji_or_url, *, name: str = None):
        """Create emoji(s)"""
        # Determine if input is a custom emoji or URL
        if ctx.message.attachments:
            # Use attachment as emoji image
            attachment = ctx.message.attachments[0]
            emoji_url = attachment.url
            # If name wasn't provided, use attachment filename without extension
            if not name:
                name = os.path.splitext(attachment.filename)[0]
        elif re.match(r'<a?:[a-zA-Z0-9_]+:[0-9]+>', emoji_or_url):
            # Input is a custom emoji
            emoji_id = re.findall(r'[0-9]+', emoji_or_url)[0]
            is_animated = emoji_or_url.startswith('<a:')
            extension = 'gif' if is_animated else 'png'
            emoji_url = f"https://cdn.discordapp.com/emojis/{emoji_id}.{extension}"
            
            # If name wasn't provided, extract from emoji format
            if not name:
                name = re.findall(r':[a-zA-Z0-9_]+:', emoji_or_url)[0][1:-1]
        else:
            # Assume input is a URL
            emoji_url = emoji_or_url
            if not name:
                await ctx.send("❌ Please provide a name for the emoji.")
                return
        
        # Validate emoji name
        if not re.match(r'^[a-zA-Z0-9_]+$', name):
            await ctx.send("❌ Emoji names can only contain letters, numbers, and underscores.")
            return
        
        try:
            # Download emoji image
            async with aiohttp.ClientSession() as session:
                async with session.get(emoji_url) as response:
                    if response.status != 200:
                        await ctx.send(f"❌ Failed to download emoji image. Status code: {response.status}")
                        return
                    
                    image_data = await response.read()
            
            # Create the emoji
            created_emoji = await ctx.guild.create_custom_emoji(name=name, image=image_data)
            
            # Success message
            embed = discord.Embed(
                title="Emoji Created",
                description=f"Successfully created emoji `{created_emoji.name}`",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            embed.set_thumbnail(url=created_emoji.url)
            
            await ctx.send(embed=embed)
            
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to create emojis.")
        except discord.HTTPException as e:
            await ctx.send(f"❌ Failed to create emoji: {str(e)}")
    
    @emoji.command(name="delete")
    @commands.has_permissions(manage_emojis=True)
    async def deleteemoji(self, ctx, *emojis: discord.Emoji):
        """Delete emoji(s)"""
        if not emojis:
            await ctx.send("❌ Please provide at least one emoji to delete.")
            return
        
        deleted = []
        failed = []
        
        for emoji in emojis:
            # Check if emoji is from this server
            if emoji.guild.id != ctx.guild.id:
                failed.append(f"{emoji.name} (not from this server)")
                continue
            
            try:
                # Delete the emoji
                await emoji.delete()
                deleted.append(emoji.name)
            except Exception as e:
                failed.append(f"{emoji.name} ({str(e)})")
        
        # Create response embed
        embed = discord.Embed(
            title="Emoji Deletion Results",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        if deleted:
            embed.add_field(
                name="✅ Successfully Deleted",
                value=", ".join([f"`{name}`" for name in deleted]),
                inline=False
            )
            
        if failed:
            embed.add_field(
                name="❌ Failed to Delete",
                value="\n".join([f"`{name}`" for name in failed]),
                inline=False
            )
            
        await ctx.send(embed=embed)
    
    @emoji.command(name="enlarge")
    async def enlargeemoji(self, ctx, emoji: discord.Emoji):
        """Enlarge an emoji and return an image from it"""
        # Create embed with enlarged emoji
        embed = discord.Embed(
            title=f"Enlarged Emoji: {emoji.name}",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        # Set the emoji as the image
        embed.set_image(url=emoji.url)
        
        await ctx.send(embed=embed)
    
    @emoji.command(name="list")
    async def listemojis(self, ctx):
        """View the emojis in the server"""
        guild = ctx.guild
        
        # Get all emojis in the guild
        emojis = guild.emojis
        
        if not emojis:
            await ctx.send("❌ This server has no custom emojis.")
            return
        
        # Split emojis into regular and animated
        regular_emojis = [e for e in emojis if not e.animated]
        animated_emojis = [e for e in emojis if e.animated]
        
        # Create embed
        embed = discord.Embed(
            title=f"Emojis in {guild.name}",
            description=f"Total: {len(emojis)} | Regular: {len(regular_emojis)} | Animated: {len(animated_emojis)}",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        # Format regular emojis
        if regular_emojis:
            # Group emojis into chunks to avoid field value length limits
            chunks = [regular_emojis[i:i+15] for i in range(0, len(regular_emojis), 15)]
            
            for i, chunk in enumerate(chunks):
                emoji_list = " ".join([str(emoji) for emoji in chunk])
                embed.add_field(
                    name=f"Regular Emojis {i+1}" if i > 0 else "Regular Emojis",
                    value=emoji_list or "None",
                    inline=False
                )
                
        # Format animated emojis
        if animated_emojis:
            # Group emojis into chunks to avoid field value length limits
            chunks = [animated_emojis[i:i+15] for i in range(0, len(animated_emojis), 15)]
            
            for i, chunk in enumerate(chunks):
                emoji_list = " ".join([str(emoji) for emoji in chunk])
                embed.add_field(
                    name=f"Animated Emojis {i+1}" if i > 0 else "Animated Emojis",
                    value=emoji_list or "None",
                    inline=False
                )
        
        await ctx.send(embed=embed)
            
    @commands.command()
    @commands.has_permissions(manage_emojis=True)
    async def deleteemojis(self, ctx, *emojis: discord.Emoji):
        """Delete emojis from the guild (Max of 10)"""
        if not emojis:
            await ctx.send("❌ Please provide at least one emoji to delete.")
            return
        
        # Limit to 10 emojis at a time
        if len(emojis) > 10:
            await ctx.send("❌ You can only delete up to 10 emojis at a time.")
            return
            
        # Use the existing deleteemoji command implementation
        await self.deleteemoji(ctx, *emojis)
    
    @commands.command()
    @commands.has_permissions(manage_emojis=True)
    async def addmultiple(self, ctx, *args):
        """Adds passed emojis from emotes/urls with names (max of 10)"""
        if len(args) == 0 or len(args) % 2 != 0:
            await ctx.send("❌ Please provide emoji-name pairs (emoji1 name1 emoji2 name2 ...).")
            return
        
        # Split args into emoji-name pairs
        pairs = [(args[i], args[i+1]) for i in range(0, len(args), 2)]
        
        # Limit to 10 pairs
        if len(pairs) > 10:
            await ctx.send("❌ You can only add up to 10 emojis at a time.")
            return
        
        # Process each pair
        successes = 0
        failures = 0
        
        for emoji_arg, name in pairs:
            # Create a context-like object to reuse the addemoji command
            ctx.message.content = f"!emoji add {emoji_arg} {name}"  # Mock command content
            try:
                await self.addemoji(ctx, emoji_arg, name=name)
                successes += 1
            except Exception:
                failures += 1
        
        # Send summary if multiple emojis were processed
        if len(pairs) > 1:
            await ctx.send(f"✅ Added {successes} emoji(s), failed to add {failures} emoji(s).")
    
    @commands.command()
    @commands.has_permissions(manage_emojis=True)
    async def steal(self, ctx, message_or_link=None):
        """View the most recent emote used"""
        if message_or_link is None and not ctx.message.reference:
            # Look for recent messages with emojis in the channel
            async for message in ctx.channel.history(limit=10):
                # Skip the command message itself
                if message.id == ctx.message.id:
                    continue
                    
                # Check for custom emojis in the message
                emoji_matches = re.findall(r'<a?:[a-zA-Z0-9_]+:[0-9]+>', message.content)
                if emoji_matches:
                    # Display the first emoji found for stealing
                    emoji_str = emoji_matches[0]
                    emoji_name = re.findall(r':[a-zA-Z0-9_]+:', emoji_str)[0][1:-1]
                    emoji_id = re.findall(r'[0-9]+', emoji_str)[0]
                    is_animated = emoji_str.startswith('<a:')
                    
                    embed = discord.Embed(
                        title="Emoji Found",
                        description=f"Emoji: {emoji_str}\nName: `{emoji_name}`\nID: `{emoji_id}`",
                        color=discord.Color.blue(),
                        timestamp=datetime.utcnow()
                    )
                    
                    # Add the emoji URL
                    extension = 'gif' if is_animated else 'png'
                    emoji_url = f"https://cdn.discordapp.com/emojis/{emoji_id}.{extension}"
                    embed.set_image(url=emoji_url)
                    
                    # Add instructions on how to add the emoji
                    embed.add_field(
                        name="How to Add",
                        value=f"Use the command:\n`!emoji add {emoji_str} {emoji_name}`",
                        inline=False
                    )
                    
                    await ctx.send(embed=embed)
                    return
            
            await ctx.send("❌ No recent emojis found in the channel.")
        else:
            # Handle message reference or message ID
            if ctx.message.reference:
                # Get the replied-to message
                reference_message = ctx.message.reference.resolved
                
                if not reference_message:
                    await ctx.send("❌ Could not retrieve the referenced message.")
                    return
                    
                message_to_check = reference_message
            else:
                # Try to interpret message_or_link as a message ID or link
                try:
                    # Check if it's a message ID
                    if message_or_link.isdigit():
                        message_id = int(message_or_link)
                        try:
                            message_to_check = await ctx.channel.fetch_message(message_id)
                        except discord.NotFound:
                            await ctx.send("❌ Message not found. Make sure it's in this channel.")
                            return
                    else:
                        # It might be a message link
                        matches = re.match(r'https://discord.com/channels/(\d+)/(\d+)/(\d+)', message_or_link)
                        if not matches:
                            await ctx.send("❌ Invalid message link or ID.")
                            return
                            
                        guild_id = int(matches.group(1))
                        channel_id = int(matches.group(2))
                        message_id = int(matches.group(3))
                        
                        if guild_id != ctx.guild.id:
                            await ctx.send("❌ The message is not from this server.")
                            return
                            
                        channel = ctx.guild.get_channel(channel_id)
                        if not channel:
                            await ctx.send("❌ Could not find the channel from the message link.")
                            return
                            
                        try:
                            message_to_check = await channel.fetch_message(message_id)
                        except discord.NotFound:
                            await ctx.send("❌ Message not found.")
                            return
                except Exception as e:
                    await ctx.send(f"❌ Error processing message: {str(e)}")
                    return
            
            # Check for custom emojis in the message
            emoji_matches = re.findall(r'<a?:[a-zA-Z0-9_]+:[0-9]+>', message_to_check.content)
            if emoji_matches:
                # Display all emojis found for stealing
                emoji_list = []
                
                for emoji_str in emoji_matches[:10]:  # Limit to 10 emojis
                    emoji_name = re.findall(r':[a-zA-Z0-9_]+:', emoji_str)[0][1:-1]
                    emoji_id = re.findall(r'[0-9]+', emoji_str)[0]
                    is_animated = emoji_str.startswith('<a:')
                    
                    extension = 'gif' if is_animated else 'png'
                    emoji_url = f"https://cdn.discordapp.com/emojis/{emoji_id}.{extension}"
                    
                    emoji_list.append({
                        "str": emoji_str,
                        "name": emoji_name,
                        "id": emoji_id,
                        "url": emoji_url,
                        "animated": is_animated
                    })
                
                # Create embed with all found emojis
                embed = discord.Embed(
                    title="Emojis Found",
                    description=f"Found {len(emoji_list)} emoji(s) in the message",
                    color=discord.Color.blue(),
                    timestamp=datetime.utcnow()
                )
                
                for i, emoji in enumerate(emoji_list):
                    embed.add_field(
                        name=f"Emoji {i+1}: {emoji['name']}",
                        value=(
                            f"Emoji: {emoji['str']}\n"
                            f"ID: `{emoji['id']}`\n"
                            f"Add Command: `!emoji add {emoji['str']} {emoji['name']}`"
                        ),
                        inline=True
                    )
                    
                # Set the first emoji as thumbnail
                if emoji_list:
                    embed.set_thumbnail(url=emoji_list[0]['url'])
                
                await ctx.send(embed=embed)
            else:
                await ctx.send("❌ No custom emojis found in the message.")
    
    # Basic information commands
    @commands.command()
    async def botinfo(self, ctx):
        """View information regarding the bot"""
        bot_user = self.bot.user
        
        # Calculate uptime
        current_time = datetime.utcnow()
        delta = current_time - self.bot.launch_time if hasattr(self.bot, 'launch_time') else None
        
        if delta:
            days, remainder = divmod(int(delta.total_seconds()), 86400)
            hours, remainder = divmod(remainder, 3600)
            minutes, seconds = divmod(remainder, 60)
            uptime_str = f"{days}d {hours}h {minutes}m {seconds}s"
        else:
            uptime_str = "Unknown"
        
        # Create embed with bot information
        embed = discord.Embed(
            title=f"{bot_user.name} Information",
            description="A feature-rich Discord bot with moderation, roleplay, and utility commands",
            color=bot_user.color or discord.Color.blue(),
            timestamp=current_time
        )
        
        # Set bot avatar as thumbnail
        embed.set_thumbnail(url=bot_user.display_avatar.url)
        
        # Add general info fields
        embed.add_field(name="Bot ID", value=f"`{bot_user.id}`", inline=True)
        embed.add_field(name="Created On", value=bot_user.created_at.strftime("%Y-%m-%d"), inline=True)
        embed.add_field(name="Uptime", value=uptime_str, inline=True)
        
        # Add stats fields
        guild_count = len(self.bot.guilds)
        user_count = sum(guild.member_count for guild in self.bot.guilds)
        
        embed.add_field(name="Servers", value=str(guild_count), inline=True)
        embed.add_field(name="Users", value=str(user_count), inline=True)
        embed.add_field(name="Ping", value=f"{round(self.bot.latency * 1000)}ms", inline=True)
        
        # Add technical info
        embed.add_field(
            name="Technical",
            value=(
                f"**Discord.py:** v{discord.__version__}\n"
                f"**Python:** v{'.'.join(map(str, __import__('sys').version_info[:3]))}"
            ),
            inline=False
        )
        
        # Add helpful links
        embed.add_field(
            name="Links",
            value=(
                "[Invite Bot](https://discord.com/oauth2/authorize?client_id="
                f"{bot_user.id}&scope=bot&permissions=8) | "
                "[Support Server](https://discord.gg/yourserver)"
            ),
            inline=False
        )
        
        embed.set_footer(text=f"Requested by {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
        
        await ctx.send(embed=embed)
    
    @commands.command(name="latency", aliases=["pong"])
    async def ping(self, ctx):
        """View the bot's latency"""
        # Calculate websocket latency
        ws_latency = round(self.bot.latency * 1000)
        
        # Start timing for message latency
        start_time = time.time()
        message = await ctx.send("🏓 Pinging...")
        end_time = time.time()
        
        # Calculate message latency
        message_latency = round((end_time - start_time) * 1000)
        
        # Create embed with ping information
        embed = discord.Embed(
            title="🏓 Pong!",
            color=discord.Color.green() if ws_latency < 200 else discord.Color.orange() if ws_latency < 400 else discord.Color.red(),
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(name="Websocket Latency", value=f"`{ws_latency}ms`", inline=True)
        embed.add_field(name="Message Latency", value=f"`{message_latency}ms`", inline=True)
        
        # Add rating based on latency
        if ws_latency < 100:
            rating = "Excellent"
        elif ws_latency < 200:
            rating = "Good"
        elif ws_latency < 400:
            rating = "OK"
        else:
            rating = "Poor"
            
        embed.add_field(name="Rating", value=rating, inline=True)
        
        await message.edit(content=None, embed=embed)
    
    @commands.command()
    async def membercount(self, ctx):
        """View server member count"""
        guild = ctx.guild
        
        # Get member counts by status
        total = guild.member_count
        online = len([m for m in guild.members if m.status != discord.Status.offline and not m.bot])
        bots = len([m for m in guild.members if m.bot])
        humans = total - bots
        
        # Create embed
        embed = discord.Embed(
            title=f"Member Count for {guild.name}",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        # Add guild icon as thumbnail
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        
        # Add member count fields
        embed.add_field(name="Total Members", value=str(total), inline=True)
        embed.add_field(name="Humans", value=str(humans), inline=True)
        embed.add_field(name="Bots", value=str(bots), inline=True)
        embed.add_field(name="Online Members", value=str(online), inline=True)
        
        await ctx.send(embed=embed)
    
    @commands.command()
    async def bots(self, ctx):
        """View all bots in the server"""
        guild = ctx.guild
        
        # Get all bots in the guild
        bots = [m for m in guild.members if m.bot]
        
        if not bots:
            await ctx.send("❌ There are no bots in this server.")
            return
        
        # Create embed
        embed = discord.Embed(
            title=f"Bots in {guild.name}",
            description=f"There are {len(bots)} bots in this server",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        # Add guild icon as thumbnail
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        
        # Format bot list
        bot_list = []
        for bot in bots:
            bot_list.append(f"{bot.mention} - `{bot.name}#{bot.discriminator}` (ID: {bot.id})")
        
        # Split into chunks if needed
        chunks = [bot_list[i:i+10] for i in range(0, len(bot_list), 10)]
        
        for i, chunk in enumerate(chunks):
            embed.add_field(
                name=f"Bots {i*10+1}-{i*10+len(chunk)}" if i > 0 else "Bots",
                value="\n".join(chunk),
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    @commands.command()
    async def roles(self, ctx):
        """View all roles in the server"""
        guild = ctx.guild
        
        # Get all roles in the guild (excluding @everyone)
        roles = [role for role in guild.roles if role.name != "@everyone"]
        roles.reverse()  # Show highest roles first
        
        if not roles:
            await ctx.send("❌ There are no roles in this server.")
            return
        
        # Create embed
        embed = discord.Embed(
            title=f"Roles in {guild.name}",
            description=f"There are {len(roles)} roles in this server",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        # Add guild icon as thumbnail
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        
        # Format role list
        role_chunks = []
        current_chunk = ""
        
        for role in roles:
            role_text = f"{role.mention} - {len(role.members)} members\n"
            
            # Discord has a 1024 character limit per field
            if len(current_chunk) + len(role_text) > 1000:
                role_chunks.append(current_chunk)
                current_chunk = role_text
            else:
                current_chunk += role_text
        
        if current_chunk:
            role_chunks.append(current_chunk)
        
        # Add role list fields
        for i, chunk in enumerate(role_chunks):
            embed.add_field(
                name=f"Roles {i+1}" if len(role_chunks) > 1 else "Roles",
                value=chunk,
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    @commands.command()
    async def avatar(self, ctx, *, user: discord.Member = None):
        """Get avatar of a member or yourself"""
        # Default to the command author if no user is specified
        if user is None:
            user = ctx.author
            
        # Create embed with user avatar
        embed = discord.Embed(
            title=f"Avatar for {user.display_name}",
            color=user.color,
            timestamp=datetime.utcnow()
        )
        
        # Add user info
        embed.set_footer(text=f"ID: {user.id}")
        
        # Add avatar
        embed.set_image(url=user.display_avatar.url)
        
        # Add links for different formats
        formats = []
        if user.display_avatar.url.endswith(".gif"):
            formats.append(f"[GIF]({user.display_avatar.with_format('gif').url})")
        formats.append(f"[PNG]({user.display_avatar.with_format('png').url})")
        formats.append(f"[JPG]({user.display_avatar.with_format('jpg').url})")
        formats.append(f"[WEBP]({user.display_avatar.with_format('webp').url})")
        
        embed.description = f"Download: {' | '.join(formats)}"
        
        await ctx.send(embed=embed)
    
    @commands.command()
    async def serveravatar(self, ctx, *, member: discord.Member = None):
        """Get the server avatar of a member or yourself"""
        # Default to the command author if no user is specified
        if member is None:
            member = ctx.author
            
        # Check if the user has a guild-specific avatar
        if not member.guild_avatar:
            await ctx.send(f"❌ {member.display_name} doesn't have a server-specific avatar.")
            return
            
        # Create embed with server avatar
        embed = discord.Embed(
            title=f"Server Avatar for {member.display_name}",
            color=member.color,
            timestamp=datetime.utcnow()
        )
        
        # Add user info
        embed.set_footer(text=f"ID: {member.id}")
        
        # Add avatar
        embed.set_image(url=member.guild_avatar.url)
        
        # Add links for different formats
        formats = []
        if member.guild_avatar.url.endswith(".gif"):
            formats.append(f"[GIF]({member.guild_avatar.with_format('gif').url})")
        formats.append(f"[PNG]({member.guild_avatar.with_format('png').url})")
        formats.append(f"[JPG]({member.guild_avatar.with_format('jpg').url})")
        formats.append(f"[WEBP]({member.guild_avatar.with_format('webp').url})")
        
        embed.description = f"Download: {' | '.join(formats)}"
        
        await ctx.send(embed=embed)
    
    @commands.command()
    async def banner(self, ctx, *, user: discord.User = None):
        """Get the banner of a member or yourself"""
        # Default to the command author if no user is specified
        if user is None:
            user = ctx.author
            
        # Fetch user to ensure we have banner data (needed for newer fields like banner)
        user = await self.bot.fetch_user(user.id)
        
        # Check if the user has a banner
        if not user.banner:
            await ctx.send(f"❌ {user.name} doesn't have a banner.")
            return
            
        # Create embed with user banner
        embed = discord.Embed(
            title=f"Banner for {user.name}",
            color=discord.Color.from_str(str(user.accent_color)) if user.accent_color else discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        # Add user info
        embed.set_footer(text=f"ID: {user.id}")
        
        # Add banner
        embed.set_image(url=user.banner.url)
        
        # Add links for different formats
        formats = []
        if user.banner.url.endswith(".gif"):
            formats.append(f"[GIF]({user.banner.with_format('gif').url})")
        formats.append(f"[PNG]({user.banner.with_format('png').url})")
        formats.append(f"[JPG]({user.banner.with_format('jpg').url})")
        formats.append(f"[WEBP]({user.banner.with_format('webp').url})")
        
        embed.description = f"Download: {' | '.join(formats)}"
        
        await ctx.send(embed=embed)
    
    @commands.command()
    async def userinfo(self, ctx, *, member: discord.Member = None):
        """View information about a member or yourself"""
        # Default to the command author if no member is specified
        if member is None:
            member = ctx.author
            
        # Fetch user to ensure we have all data (needed for newer fields like banner)
        user = await self.bot.fetch_user(member.id)
        
        # Create the embed
        embed = discord.Embed(
            title=f"User Information: {member.display_name}",
            color=member.color,
            timestamp=datetime.utcnow()
        )
        
        # Add member's avatar as the thumbnail
        embed.set_thumbnail(url=member.display_avatar.url)
        
        # Add banner if available
        if user.banner:
            embed.set_image(url=user.banner.url)
        
        # General user information
        created_time = int(member.created_at.timestamp())
        joined_time = int(member.joined_at.timestamp()) if member.joined_at else 0
        
        embed.add_field(
            name="User Information",
            value=(
                f"**Name:** {member.name}\n"
                f"**ID:** {member.id}\n"
                f"**Nickname:** {member.nick or 'None'}\n"
                f"**Bot Account:** {'Yes' if member.bot else 'No'}\n"
                f"**Created:** <t:{created_time}:R>\n"
                f"**Joined Server:** <t:{joined_time}:R>"
            ),
            inline=False
        )
        
        # Member status and activity information
        status_emojis = {
            "online": "🟢",
            "idle": "🟡",
            "dnd": "🔴",
            "offline": "⚫"
        }
        status_emoji = status_emojis.get(str(member.status), "⚫")
        
        activities = []
        for activity in member.activities:
            if isinstance(activity, discord.CustomActivity) and activity.name:
                activities.append(f"**Custom Status:** {activity.name}")
            elif isinstance(activity, discord.Game):
                activities.append(f"**Playing:** {activity.name}")
            elif isinstance(activity, discord.Streaming):
                activities.append(f"**Streaming:** [{activity.name}]({activity.url})")
            elif isinstance(activity, discord.Spotify):
                activities.append(f"**Spotify:** {activity.title} by {activity.artist}")
            elif isinstance(activity, discord.Activity):
                if activity.type == discord.ActivityType.listening:
                    activities.append(f"**Listening to:** {activity.name}")
                elif activity.type == discord.ActivityType.watching:
                    activities.append(f"**Watching:** {activity.name}")
                elif activity.type == discord.ActivityType.competing:
                    activities.append(f"**Competing in:** {activity.name}")
                else:
                    activities.append(f"**Activity:** {activity.name}")
        
        # Add status and activities field if there is information to display
        if str(member.status) != "offline" or activities:
            embed.add_field(
                name="Presence",
                value=(
                    f"**Status:** {status_emoji} {str(member.status).capitalize()}\n"
                    f"{chr(10).join(activities) if activities else ''}"
                ),
                inline=False
            )
        
        # Role information
        roles = [role.mention for role in reversed(member.roles) if role.name != "@everyone"]
        
        if roles:
            # Discord has a character limit for field values, so we need to truncate if needed
            roles_text = " ".join(roles)
            if len(roles_text) > 1024:
                roles_text = roles_text[:1021] + "..."
                
            embed.add_field(
                name=f"Roles [{len(roles)}]",
                value=roles_text,
                inline=False
            )
        
        # Add permissions information
        key_permissions = []
        permissions = member.guild_permissions
        
        if permissions.administrator:
            key_permissions.append("Administrator")
        else:
            if permissions.manage_guild:
                key_permissions.append("Manage Server")
            if permissions.manage_roles:
                key_permissions.append("Manage Roles")
            if permissions.manage_channels:
                key_permissions.append("Manage Channels")
            if permissions.manage_messages:
                key_permissions.append("Manage Messages")
            if permissions.manage_webhooks:
                key_permissions.append("Manage Webhooks")
            if permissions.manage_nicknames:
                key_permissions.append("Manage Nicknames")
            if permissions.kick_members:
                key_permissions.append("Kick Members")
            if permissions.ban_members:
                key_permissions.append("Ban Members")
            if permissions.mention_everyone:
                key_permissions.append("Mention Everyone")
        
        if key_permissions:
            embed.add_field(
                name="Key Permissions",
                value=", ".join(key_permissions),
                inline=False
            )
        
        # Add acknowledgements if any
        acknowledgements = []
        
        if member.id == ctx.guild.owner_id:
            acknowledgements.append("Server Owner")
        if permissions.administrator:
            acknowledgements.append("Server Administrator")
        if permissions.manage_guild and not permissions.administrator:
            acknowledgements.append("Server Manager")
        if permissions.manage_roles and not permissions.administrator:
            acknowledgements.append("Role Manager")
        
        if acknowledgements:
            embed.add_field(
                name="Acknowledgements",
                value=", ".join(acknowledgements),
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    @commands.command()
    async def serverinfo(self, ctx, *, guild_id: int = None):
        """View information about a guild"""
        # Use the specified guild ID if provided and the bot is in that guild
        guild = None
        if guild_id:
            guild = self.bot.get_guild(guild_id)
            
        # Default to the current guild if no valid guild ID was provided
        if not guild:
            guild = ctx.guild
        
        # Create embed
        embed = discord.Embed(
            title=f"Server Information: {guild.name}",
            description=guild.description or "No description set",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        # Add server icon and banner
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
            
        if guild.banner:
            embed.set_image(url=guild.banner.url)
        
        # General information
        created_time = int(guild.created_at.timestamp())
        
        embed.add_field(
            name="General Information",
            value=(
                f"**ID:** {guild.id}\n"
                f"**Owner:** {guild.owner.mention if guild.owner else 'Unknown'}\n"
                f"**Created:** <t:{created_time}:R>\n"
                f"**Verification Level:** {str(guild.verification_level).capitalize()}\n"
                f"**Explicit Content Filter:** {str(guild.explicit_content_filter).replace('_', ' ').capitalize()}"
            ),
            inline=False
        )
        
        # Member information
        embed.add_field(
            name="Member Information",
            value=(
                f"**Total Members:** {guild.member_count}\n"
                f"**Humans:** {len([m for m in guild.members if not m.bot])}\n"
                f"**Bots:** {len([m for m in guild.members if m.bot])}\n"
                f"**Boost Tier:** {guild.premium_tier}\n"
                f"**Boosts:** {guild.premium_subscription_count or 0}"
            ),
            inline=True
        )
        
        # Channel information
        text_channels = len(guild.text_channels)
        voice_channels = len(guild.voice_channels)
        categories = len(guild.categories)
        total_channels = text_channels + voice_channels
        
        embed.add_field(
            name="Channel Information",
            value=(
                f"**Total Channels:** {total_channels}\n"
                f"**Text Channels:** {text_channels}\n"
                f"**Voice Channels:** {voice_channels}\n"
                f"**Categories:** {categories}\n"
                f"**AFK Channel:** {guild.afk_channel.mention if guild.afk_channel else 'None'}"
            ),
            inline=True
        )
        
        # Other information
        emoji_count = len(guild.emojis)
        emoji_limit = guild.emoji_limit
        role_count = len(guild.roles) - 1  # Exclude @everyone
        
        embed.add_field(
            name="Other Information",
            value=(
                f"**Roles:** {role_count}\n"
                f"**Emojis:** {emoji_count}/{emoji_limit}\n"
                f"**Features:** {', '.join(guild.features) or 'None'}"
            ),
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @commands.command()
    async def channelinfo(self, ctx, *, channel: discord.TextChannel = None):
        """View information about a channel"""
        # Default to the current channel if none is specified
        if not channel:
            channel = ctx.channel
            
        # Create embed
        embed = discord.Embed(
            title=f"Channel Information: {channel.name}",
            description=channel.topic or "No topic set",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        # General information
        created_time = int(channel.created_at.timestamp())
        
        embed.add_field(
            name="General Information",
            value=(
                f"**ID:** {channel.id}\n"
                f"**Category:** {channel.category.name if channel.category else 'None'}\n"
                f"**Position:** {channel.position}\n"
                f"**Created:** <t:{created_time}:R>"
            ),
            inline=False
        )
        
        # Channel settings
        embed.add_field(
            name="Channel Settings",
            value=(
                f"**NSFW:** {'Yes' if channel.is_nsfw() else 'No'}\n"
                f"**News Channel:** {'Yes' if channel.is_news() else 'No'}\n"
                f"**Slowmode:** {channel.slowmode_delay}s\n"
                f"**Default Auto Archive:** {channel.default_auto_archive_duration} minutes"
            ),
            inline=True
        )
        
        # Channel permissions
        # We'll show the @everyone role permissions as a baseline
        everyone_permissions = channel.overwrites_for(ctx.guild.default_role)
        
        allowed = []
        denied = []
        
        # Convert permission overrides to readable strings
        for perm, value in everyone_permissions:
            if value is True:
                allowed.append(perm.replace('_', ' ').title())
            elif value is False:
                denied.append(perm.replace('_', ' ').title())
        
        if allowed or denied:
            permissions_text = ""
            
            if allowed:
                permissions_text += f"**Allowed for @everyone:**\n{', '.join(allowed)}\n\n"
                
            if denied:
                permissions_text += f"**Denied for @everyone:**\n{', '.join(denied)}"
                
            embed.add_field(
                name="Permissions (@everyone)",
                value=permissions_text or "Default permissions",
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    @commands.command()
    async def snapchat(self, ctx, username: str):
        """Get bitmoji and QR scan code for user"""
        if not username:
            await ctx.send("❌ Please provide a Snapchat username.")
            return
        
        # Create embed with Snapchat user information
        embed = discord.Embed(
            title=f"Snapchat: {username}",
            description="Scan this QR code with Snapchat to add this user.",
            color=0xFFFC00,  # Snapchat yellow
            timestamp=datetime.utcnow()
        )
        
        # Add Snapchat QR code - this is an estimation as there's no official API
        qr_url = f"https://app.snapchat.com/web/deeplink/snapcode?username={username}&type=SVG&bitmoji=1"
        embed.set_image(url=qr_url)
        
        # Add profile link
        embed.add_field(
            name="Open Profile",
            value=f"[Open in Snapchat](https://www.snapchat.com/add/{username})",
            inline=False
        )
        
        embed.set_footer(text="Note: Bot cannot verify if this username exists")
        
        await ctx.send(embed=embed)
    
    @commands.command()
    async def snapchatstory(self, ctx, username: str):
        """Gets all current stories for the given Snapchat user"""
        if not username:
            await ctx.send("❌ Please provide a Snapchat username.")
            return
        
        # Create embed for Snapchat story information
        embed = discord.Embed(
            title=f"Snapchat Stories: {username}",
            description=(
                "Snapchat doesn't provide an official API to view stories of other users.\n\n"
                "To view someone's story, you need to:\n"
                "1. Add them as a friend on Snapchat\n"
                "2. Open the Snapchat app\n"
                "3. Swipe right to the Friends screen\n"
                "4. Find their name in your friends list\n"
                "5. Tap on their name to view their story (if available)"
            ),
            color=0xFFFC00,  # Snapchat yellow
            timestamp=datetime.utcnow()
        )
        
        # Add Snapchat logo
        embed.set_thumbnail(url="https://assets.stickpng.com/images/580b57fcd9996e24bc43c536.png")
        
        # Add profile link
        embed.add_field(
            name="Add User",
            value=f"[Add on Snapchat](https://www.snapchat.com/add/{username})",
            inline=False
        )
        
        embed.set_footer(text="Note: This command cannot display actual Snapchat stories due to API limitations")
        
        await ctx.send(embed=embed)
    
    @commands.command()
    async def github(self, ctx, username: str):
        """Gets profile information on the given Github user"""
        if not username:
            await ctx.send("❌ Please provide a GitHub username.")
            return
        
        async with ctx.typing():
            try:
                # GitHub's API is public for basic user information
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"https://api.github.com/users/{username}") as response:
                        if response.status != 200:
                            await ctx.send(f"❌ GitHub user `{username}` not found or API error occurred.")
                            return
                            
                        data = await response.json()
                
                # Create embed with GitHub profile information
                embed = discord.Embed(
                    title=data.get("name") or username,
                    url=data.get("html_url"),
                    description=data.get("bio") or "No bio provided",
                    color=0x333333,  # GitHub dark gray
                    timestamp=datetime.utcnow()
                )
                
                # Set GitHub avatar as thumbnail
                embed.set_thumbnail(url=data.get("avatar_url"))
                
                # Add GitHub stats
                embed.add_field(name="Username", value=data.get("login"), inline=True)
                embed.add_field(name="Type", value=data.get("type"), inline=True)
                
                if data.get("location"):
                    embed.add_field(name="Location", value=data.get("location"), inline=True)
                    
                embed.add_field(name="Public Repos", value=str(data.get("public_repos", 0)), inline=True)
                embed.add_field(name="Public Gists", value=str(data.get("public_gists", 0)), inline=True)
                embed.add_field(name="Followers", value=str(data.get("followers", 0)), inline=True)
                embed.add_field(name="Following", value=str(data.get("following", 0)), inline=True)
                
                # Add created/updated dates
                if data.get("created_at"):
                    created = datetime.fromisoformat(data.get("created_at").replace("Z", "+00:00"))
                    embed.add_field(
                        name="Created", 
                        value=f"<t:{int(created.timestamp())}:R>", 
                        inline=True
                    )
                    
                if data.get("updated_at"):
                    updated = datetime.fromisoformat(data.get("updated_at").replace("Z", "+00:00"))
                    embed.add_field(
                        name="Last Update", 
                        value=f"<t:{int(updated.timestamp())}:R>", 
                        inline=True
                    )
                
                # Add company if available
                if data.get("company"):
                    embed.add_field(name="Company", value=data.get("company"), inline=True)
                    
                # Add blog/website if available
                if data.get("blog"):
                    embed.add_field(name="Website", value=data.get("blog"), inline=True)
                    
                # Add email if public
                if data.get("email"):
                    embed.add_field(name="Email", value=data.get("email"), inline=True)
                    
                # Add footer with GitHub ID
                embed.set_footer(text=f"GitHub ID: {data.get('id')}")
                
                await ctx.send(embed=embed)
                
            except Exception as e:
                logger.error(f"Error fetching GitHub profile: {str(e)}")
                await ctx.send(f"❌ An error occurred while fetching GitHub profile for `{username}`.")
    
    @commands.command()
    async def weather(self, ctx, *, city: str):
        """Gets simple weather from OpenWeatherMap"""
        if not city:
            await ctx.send("❌ Please provide a city name.")
            return
            
        # Replace with your actual API key for a full implementation
        api_key = None
        
        # Check if API key is available
        if not api_key:
            embed = discord.Embed(
                title="Weather Information",
                description=(
                    f"🌤️ Weather lookup for **{city}**\n\n"
                    "This command requires an OpenWeatherMap API key to function.\n"
                    "In a full implementation, this would display current weather conditions including:\n"
                    "• Temperature (current, min, max)\n"
                    "• Weather conditions (sunny, cloudy, etc.)\n"
                    "• Humidity and pressure\n"
                    "• Wind speed and direction\n"
                    "• Sunrise and sunset times"
                ),
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            
            embed.set_thumbnail(url="https://openweathermap.org/themes/openweathermap/assets/img/logo_white_cropped.png")
            embed.set_footer(text="To use this command, the bot owner needs to set up an OpenWeatherMap API key")
            
            await ctx.send(embed=embed)
            return
            
        # Here would be the implementation with the actual API key
        # For now, we'll leave this as a placeholder
    
    @commands.command()
    async def cashapp(self, ctx, cashtag: str):
        """Retrieve simple CashApp profile information"""
        if not cashtag:
            await ctx.send("❌ Please provide a CashApp $cashtag.")
            return
            
        # Ensure the cashtag starts with a $ symbol
        if not cashtag.startswith('$'):
            cashtag = f"${cashtag}"
        
        # Create embed with CashApp profile info
        embed = discord.Embed(
            title=f"CashApp: {cashtag}",
            description="Cash App doesn't provide a public API for profile information.",
            color=0x00D632,  # CashApp green
            timestamp=datetime.utcnow()
        )
        
        # Add CashApp logo
        embed.set_thumbnail(url="https://cash.app/favicon.ico")
        
        # Add profile link
        embed.add_field(
            name="Pay Link",
            value=f"[Pay with Cash App](https://cash.app/{cashtag})",
            inline=False
        )
        
        embed.add_field(
            name="Profile QR Code",
            value=f"To get a QR code for this account, visit: https://cash.app/{cashtag}",
            inline=False
        )
        
        embed.set_footer(text="Note: Bot cannot verify if this cashtag exists")
        
        await ctx.send(embed=embed)
    
    @commands.command()
    async def urbandictionary(self, ctx, *, word: str):
        """Gets the definition of a word/slang from Urban Dictionary"""
        if not word:
            await ctx.send("❌ Please provide a word to look up.")
            return
            
        async with ctx.typing():
            try:
                # Urban Dictionary has a public API
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"https://api.urbandictionary.com/v0/define?term={word}") as response:
                        if response.status != 200:
                            await ctx.send(f"❌ Failed to look up definition for `{word}`.")
                            return
                            
                        data = await response.json()
                
                # Check if there are any definitions
                if not data["list"]:
                    await ctx.send(f"❌ No Urban Dictionary definition found for `{word}`.")
                    return
                    
                # Sort definitions by thumbs up
                definitions = sorted(data["list"], key=lambda d: d.get("thumbs_up", 0), reverse=True)
                top_def = definitions[0]
                
                # Trim long definitions
                definition = top_def["definition"]
                if len(definition) > 1024:
                    definition = definition[:1021] + "..."
                    
                example = top_def["example"]
                if len(example) > 1024:
                    example = example[:1021] + "..."
                    
                # Clean up the text (remove brackets and formatting)
                definition = definition.replace("[", "").replace("]", "")
                example = example.replace("[", "").replace("]", "")
                
                # Create embed with definition
                embed = discord.Embed(
                    title=f"Urban Dictionary: {word}",
                    url=top_def["permalink"],
                    color=0xCCFF00,  # Urban Dictionary green
                    timestamp=datetime.utcnow()
                )
                
                embed.add_field(name="Definition", value=definition, inline=False)
                
                if example:
                    embed.add_field(name="Example", value=example, inline=False)
                    
                # Add stats
                embed.add_field(
                    name="Stats",
                    value=f"👍 {top_def.get('thumbs_up', 0)} | 👎 {top_def.get('thumbs_down', 0)}",
                    inline=True
                )
                
                # Add author if available
                if top_def.get("author"):
                    embed.add_field(name="Author", value=top_def["author"], inline=True)
                    
                # Add written date if available
                if top_def.get("written_on"):
                    written = datetime.fromisoformat(top_def["written_on"].replace("Z", "+00:00"))
                    embed.add_field(
                        name="Written", 
                        value=f"<t:{int(written.timestamp())}:R>", 
                        inline=True
                    )
                
                # Add thumbnails and footer
                embed.set_thumbnail(url="https://i.imgur.com/VFXr0ID.jpg")
                
                # Add footer with definition count
                embed.set_footer(
                    text=f"Definition 1 of {len(definitions)} | Powered by Urban Dictionary"
                )
                
                await ctx.send(embed=embed)
                
            except Exception as e:
                logger.error(f"Error fetching Urban Dictionary definition: {str(e)}")
                await ctx.send(f"❌ An error occurred while fetching definition for `{word}`.")
    
    @commands.command()
    async def define(self, ctx, *, word: str):
        """Get definition of a word"""
        if not word:
            await ctx.send("❌ Please provide a word to define.")
            return
            
        async with ctx.typing():
            try:
                # There are several free dictionary APIs, this is just an example
                # In a full implementation, you would need to register for an API key
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}") as response:
                        if response.status != 200:
                            await ctx.send(f"❌ No definition found for `{word}`.")
                            return
                            
                        data = await response.json()
                
                if not data or not isinstance(data, list):
                    await ctx.send(f"❌ No definition found for `{word}`.")
                    return
                    
                # Get the first entry
                entry = data[0]
                
                # Create embed with definition
                embed = discord.Embed(
                    title=f"📚 Definition: {entry.get('word', word)}",
                    color=discord.Color.blue(),
                    timestamp=datetime.utcnow()
                )
                
                # Add pronunciation if available
                if "phonetics" in entry and entry["phonetics"]:
                    for phonetic in entry["phonetics"]:
                        if "text" in phonetic:
                            embed.description = f"**Pronunciation:** {phonetic['text']}"
                            break
                
                # Add definitions grouped by part of speech
                if "meanings" in entry:
                    for meaning in entry["meanings"][:3]:  # Limit to first 3 meanings
                        part_of_speech = meaning.get("partOfSpeech", "unknown")
                        definitions = meaning.get("definitions", [])
                        
                        if definitions:
                            # Get the first definition and example
                            definition = definitions[0].get("definition", "No definition available")
                            example = definitions[0].get("example", "")
                            
                            # Format field content
                            field_content = f"{definition}"
                            if example:
                                field_content += f"\n\n**Example:** {example}"
                                
                            # Add synonyms if available
                            synonyms = definitions[0].get("synonyms", [])
                            if synonyms:
                                field_content += f"\n\n**Synonyms:** {', '.join(synonyms[:5])}"
                                
                            # Add antonyms if available
                            antonyms = definitions[0].get("antonyms", [])
                            if antonyms:
                                field_content += f"\n\n**Antonyms:** {', '.join(antonyms[:5])}"
                            
                            embed.add_field(
                                name=f"{part_of_speech.capitalize()}",
                                value=field_content,
                                inline=False
                            )
                
                # Add source information
                if "sourceUrls" in entry and entry["sourceUrls"]:
                    source_url = entry["sourceUrls"][0]
                    embed.add_field(
                        name="Source",
                        value=f"[Dictionary Link]({source_url})",
                        inline=False
                    )
                
                embed.set_footer(text="Powered by Dictionary API")
                
                await ctx.send(embed=embed)
                
            except Exception as e:
                logger.error(f"Error fetching definition: {str(e)}")
                await ctx.send(f"❌ An error occurred while fetching definition for `{word}`.")
    
    @commands.command()
    async def roleinfo(self, ctx, *, role: discord.Role):
        """View information about a role"""
        if not role:
            await ctx.send("❌ Please provide a valid role.")
            return
            
        # Create embed
        embed = discord.Embed(
            title=f"Role Information: {role.name}",
            color=role.color,
            timestamp=datetime.utcnow()
        )
        
        # General information
        created_time = int(role.created_at.timestamp())
        
        embed.add_field(
            name="General Information",
            value=(
                f"**ID:** {role.id}\n"
                f"**Color:** {str(role.color)}\n"
                f"**Created:** <t:{created_time}:R>\n"
                f"**Position:** {role.position}\n"
                f"**Mentionable:** {'Yes' if role.mentionable else 'No'}\n"
                f"**Hoisted:** {'Yes' if role.hoist else 'No'}\n"
                f"**Managed by Integration:** {'Yes' if role.managed else 'No'}"
            ),
            inline=False
        )
        
        # Permissions
        permissions = []
        for perm, value in role.permissions:
            if value:
                permissions.append(perm.replace('_', ' ').title())
                
        if permissions:
            # Split into chunks if needed to avoid hitting the field value character limit
            chunks = []
            current_chunk = ""
            
            for perm in permissions:
                if len(current_chunk) + len(perm) + 2 > 1024:  # 1024 is the field value character limit
                    chunks.append(current_chunk)
                    current_chunk = perm
                else:
                    if current_chunk:
                        current_chunk += ", " + perm
                    else:
                        current_chunk = perm
                        
            if current_chunk:
                chunks.append(current_chunk)
                
            # Add each chunk as a separate field
            for i, chunk in enumerate(chunks):
                embed.add_field(
                    name=f"Permissions {i+1}" if i > 0 else "Permissions",
                    value=chunk,
                    inline=False
                )
        else:
            embed.add_field(
                name="Permissions",
                value="This role has no permissions.",
                inline=False
            )
        
        # Members with the role
        member_count = len(role.members)
        embed.add_field(
            name=f"Members [{member_count}]",
            value=f"Use `!members {role.name}` to view members with this role.",
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @commands.command()
    async def members(self, ctx, *, role: discord.Role):
        """View members in a role"""
        if not role:
            await ctx.send("❌ Please provide a valid role.")
            return
            
        # Get members with the role
        members = role.members
        
        if not members:
            await ctx.send(f"❌ No members have the {role.mention} role.")
            return
            
        # Create embed
        embed = discord.Embed(
            title=f"Members with {role.name} role",
            description=f"There are {len(members)} members with this role",
            color=role.color,
            timestamp=datetime.utcnow()
        )
        
        # Format member list
        # Since Discord has a character limit for embed fields, we'll need to split into multiple fields if needed
        member_chunks = []
        current_chunk = ""
        
        for member in sorted(members, key=lambda m: m.display_name.lower()):
            member_line = f"{member.mention} - `{member.display_name}`\n"
            
            if len(current_chunk) + len(member_line) > 1024:  # 1024 is the field value character limit
                member_chunks.append(current_chunk)
                current_chunk = member_line
            else:
                current_chunk += member_line
                
        if current_chunk:
            member_chunks.append(current_chunk)
            
        # Add each chunk as a separate field
        for i, chunk in enumerate(member_chunks):
            embed.add_field(
                name=f"Members {i*25+1}-{min(i*25+25, len(members))}" if len(member_chunks) > 1 else "Members",
                value=chunk,
                inline=False
            )
        
        # Add role information
        embed.set_footer(text=f"Role ID: {role.id}")
        
        await ctx.send(embed=embed)
    
    @commands.group(invoke_without_command=True)
    async def sticker(self, ctx):
        """Manage guild stickers"""
        embed = discord.Embed(
            title="Sticker Management",
            description="Manage the stickers in your server",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(
            name="Available Commands",
            value=(
                "`sticker add <message> <name>` - Create sticker(s)\n"
                "`sticker delete <message>` - Delete a guild sticker\n"
                "`sticker steal <message> <name>` - Steal the most recently sent stickers\n"
                "`sticker clense` - Cleans sticker names and adds vanity to them"
            ),
            inline=False
        )
        
        embed.set_footer(text="Use these commands to manage server stickers")
        
        await ctx.send(embed=embed)
    
    @sticker.command(name="steal")
    @commands.has_permissions(manage_emojis=True)
    async def stealsticker(self, ctx, message: discord.Message = None, *, name: str = None):
        """Steal the most recently sent stickers"""
        # Get the message containing stickers
        if not message and not ctx.message.reference:
            # Look for recent messages with stickers
            async for msg in ctx.channel.history(limit=10):
                # Skip the command message itself
                if msg.id == ctx.message.id:
                    continue
                    
                # Check if the message has stickers
                if msg.stickers:
                    message = msg
                    break
                    
            if not message:
                await ctx.send("❌ No recent messages with stickers found.")
                return
        elif ctx.message.reference and not message:
            # Get the replied-to message
            message = ctx.message.reference.resolved
            
        # Check if the message has stickers
        if not message.stickers:
            await ctx.send("❌ The specified message doesn't contain any stickers.")
            return
            
        # Check if a name was provided
        if not name:
            # Use the original sticker name if no name is provided
            name = message.stickers[0].name
            
        # Validate sticker name
        if not re.match(r'^[a-zA-Z0-9_]+$', name):
            await ctx.send("❌ Sticker names can only contain letters, numbers, and underscores.")
            return
            
        # Get the first sticker in the message
        sticker = message.stickers[0]
        
        try:
            # Download the sticker
            async with aiohttp.ClientSession() as session:
                async with session.get(sticker.url) as response:
                    if response.status != 200:
                        await ctx.send(f"❌ Failed to download sticker. Status code: {response.status}")
                        return
                        
                    sticker_data = await response.read()
            
            # Get file info
            if sticker.format == discord.StickerFormatType.png or sticker.format == discord.StickerFormatType.apng:
                file_format = "png"
            elif sticker.format == discord.StickerFormatType.lottie:
                file_format = "json"  # Lottie stickers are JSON files
            else:
                file_format = "gif"  # Default to GIF
                
            # Create a temporary file for the sticker
            with tempfile.NamedTemporaryFile(suffix=f".{file_format}", delete=False) as temp_file:
                temp_file.write(sticker_data)
                temp_path = temp_file.name
                
            # Create a file object to upload
            with open(temp_path, "rb") as sticker_file:
                discord_file = discord.File(sticker_file)
                
                # Add the sticker to the guild
                try:
                    new_sticker = await ctx.guild.create_sticker(
                        name=name,
                        description=sticker.description or f"Added by {ctx.author.display_name}",
                        emoji="⭐",  # Default emoji
                        file=discord_file,
                        reason=f"Sticker added by {ctx.author.display_name}"
                    )
                    
                    # Success message
                    embed = discord.Embed(
                        title="Sticker Added",
                        description=f"Successfully added sticker `{new_sticker.name}`",
                        color=discord.Color.green(),
                        timestamp=datetime.utcnow()
                    )
                    
                    # Add sticker preview if possible
                    embed.set_image(url=new_sticker.url)
                    
                    await ctx.send(embed=embed)
                    
                except discord.Forbidden:
                    await ctx.send("❌ I don't have permission to add stickers to this server.")
                except discord.HTTPException as e:
                    await ctx.send(f"❌ Failed to add sticker: {str(e)}")
                    
            # Clean up the temporary file
            os.unlink(temp_path)
                
        except Exception as e:
            logger.error(f"Error adding sticker: {str(e)}")
            await ctx.send(f"❌ An error occurred while adding the sticker: {str(e)}")
    
    @sticker.command(name="delete")
    @commands.has_permissions(manage_emojis=True)
    async def deletesticker(self, ctx, *, message_or_sticker_id = None):
        """Delete a guild sticker"""
        # Determine if the input is a sticker ID or a message reference
        sticker_to_delete = None
        
        if message_or_sticker_id and message_or_sticker_id.isdigit():
            # Try to interpret as a sticker ID
            sticker_id = int(message_or_sticker_id)
            sticker_to_delete = discord.utils.get(ctx.guild.stickers, id=sticker_id)
            
        elif ctx.message.reference:
            # Get the replied-to message
            message = ctx.message.reference.resolved
            
            # Check if the message has stickers
            if message and message.stickers:
                # Get the first sticker in the message
                sticker_id = message.stickers[0].id
                sticker_to_delete = discord.utils.get(ctx.guild.stickers, id=sticker_id)
                
        # If no sticker was found, send an error message
        if not sticker_to_delete:
            await ctx.send("❌ Please provide a valid sticker ID or reply to a message with a sticker.")
            return
            
        try:
            # Delete the sticker
            await sticker_to_delete.delete(reason=f"Sticker deleted by {ctx.author.display_name}")
            
            # Success message
            embed = discord.Embed(
                title="Sticker Deleted",
                description=f"Successfully deleted sticker `{sticker_to_delete.name}`",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            
            await ctx.send(embed=embed)
            
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to delete stickers in this server.")
        except discord.HTTPException as e:
            await ctx.send(f"❌ Failed to delete sticker: {str(e)}")
    
    @sticker.command(name="add")
    @commands.has_permissions(manage_emojis=True)
    async def addsticker(self, ctx, message: discord.Message = None, *, name: str = None):
        """Create sticker(s)"""
        # Redirect to stealsticker command as the functionality is the same
        await self.stealsticker(ctx, message, name=name)
    
    @sticker.command(name="clense")
    @commands.has_permissions(manage_emojis=True)
    async def clensestickers(self, ctx):
        """Cleans sticker names and adds vanity to them"""
        # Get all stickers in the guild
        stickers = ctx.guild.stickers
        
        if not stickers:
            await ctx.send("❌ This server has no stickers to cleanse.")
            return
            
        # Start a confirmation message
        confirm_msg = await ctx.send(
            f"⚠️ This will rename {len(stickers)} stickers to ensure they follow naming conventions.\n"
            f"React with ✅ to continue or ❌ to cancel."
        )
        
        # Add reactions for confirmation
        await confirm_msg.add_reaction('✅')
        await confirm_msg.add_reaction('❌')
        
        # Wait for the user's reaction
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ['✅', '❌'] and reaction.message.id == confirm_msg.id
            
        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=check)
            
            # If user cancels
            if str(reaction.emoji) == '❌':
                await confirm_msg.edit(content="❌ Sticker cleansing cancelled.")
                return
                
            # If user confirms, proceed with cleansing
            status_msg = await ctx.send("🔄 Cleansing stickers... This may take a moment.")
            
            renamed = 0
            failed = 0
            
            for sticker in stickers:
                # Clean the name (remove special characters, spaces, etc.)
                current_name = sticker.name
                cleaned_name = re.sub(r'[^a-zA-Z0-9_]', '', current_name)
                
                # Add server prefix if wanted (customize this as needed)
                server_prefix = ctx.guild.name.split()[0].lower()  # Use first word of server name
                server_prefix = re.sub(r'[^a-zA-Z0-9_]', '', server_prefix)
                
                if not cleaned_name.startswith(server_prefix):
                    new_name = f"{server_prefix}_{cleaned_name}"
                else:
                    new_name = cleaned_name
                    
                # Skip if name is already clean and has prefix
                if new_name == current_name:
                    continue
                    
                try:
                    # Rename the sticker
                    await sticker.edit(name=new_name)
                    renamed += 1
                    
                except Exception:
                    failed += 1
                    
            # Update status message with results
            await status_msg.edit(
                content=f"✅ Sticker cleansing complete! Renamed {renamed} stickers. Failed to rename {failed} stickers."
            )
            
        except asyncio.TimeoutError:
            await confirm_msg.edit(content="❌ Sticker cleansing timed out. No changes were made.")
    
    @commands.command()
    async def invites(self, ctx):
        """View all active invites"""
        # Check if user has manage guild permissions
        if not ctx.author.guild_permissions.manage_guild:
            await ctx.send("❌ You need the Manage Server permission to use this command.")
            return
            
        # Get all invites for the guild
        try:
            invites = await ctx.guild.invites()
            
            if not invites:
                await ctx.send("❌ This server has no active invites.")
                return
                
            # Create embed
            embed = discord.Embed(
                title=f"Active Invites for {ctx.guild.name}",
                description=f"This server has {len(invites)} active invite(s)",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            
            # Group invites by creator
            invites_by_creator = {}
            
            for invite in invites:
                creator = invite.inviter
                if creator.id not in invites_by_creator:
                    invites_by_creator[creator.id] = []
                    
                invites_by_creator[creator.id].append(invite)
                
            # Add each creator's invites as a field
            for creator_id, creator_invites in invites_by_creator.items():
                creator = ctx.guild.get_member(creator_id) or await self.bot.fetch_user(creator_id)
                
                invites_text = ""
                for invite in creator_invites:
                    # Format max age and uses
                    max_age = "∞" if invite.max_age == 0 else str(invite.max_age // 86400) + "d" if invite.max_age >= 86400 else str(invite.max_age // 3600) + "h"
                    max_uses = "∞" if invite.max_uses == 0 else str(invite.max_uses)
                    
                    # Format channel
                    channel = f"#{invite.channel.name}" if invite.channel else "Unknown"
                    
                    invites_text += (
                        f"**Code:** `{invite.code}`\n"
                        f"**Channel:** {channel}\n"
                        f"**Uses:** {invite.uses}/{max_uses}\n"
                        f"**Expires:** {max_age}\n"
                        f"**Created:** <t:{int(invite.created_at.timestamp())}:R>\n\n"
                    )
                    
                embed.add_field(
                    name=f"Invites by {creator.display_name} ({len(creator_invites)})",
                    value=invites_text,
                    inline=False
                )
                
            await ctx.send(embed=embed)
            
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to view invites for this server.")
        except Exception as e:
            logger.error(f"Error listing invites: {str(e)}")
            await ctx.send(f"❌ An error occurred while listing invites: {str(e)}")
    
    @commands.command()
    async def inviteinfo(self, ctx, invite_code: str):
        """View basic invite code information"""
        if not invite_code:
            await ctx.send("❌ Please provide an invite code.")
            return
            
        # Clean the invite code (remove discord.gg/ if present)
        if invite_code.startswith("https://discord.gg/"):
            invite_code = invite_code[19:]
        elif invite_code.startswith("discord.gg/"):
            invite_code = invite_code[11:]
            
        try:
            # Fetch the invite
            invite = await self.bot.fetch_invite(invite_code)
            
            # Create embed
            embed = discord.Embed(
                title=f"Invite Information: {invite.code}",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            
            # Add server information
            embed.add_field(
                name="Server",
                value=(
                    f"**Name:** {invite.guild.name}\n"
                    f"**ID:** {invite.guild.id}\n"
                    f"**Members:** {invite.approximate_member_count}\n"
                    f"**Online:** {invite.approximate_presence_count}"
                ),
                inline=False
            )
            
            # Add channel information
            if invite.channel:
                embed.add_field(
                    name="Channel",
                    value=(
                        f"**Name:** {invite.channel.name}\n"
                        f"**ID:** {invite.channel.id}\n"
                        f"**Type:** {str(invite.channel.type).capitalize()}"
                    ),
                    inline=False
                )
                
            # Add inviter information if available
            if invite.inviter:
                embed.add_field(
                    name="Inviter",
                    value=(
                        f"**Name:** {invite.inviter.name}\n"
                        f"**ID:** {invite.inviter.id}\n"
                        f"**Created:** <t:{int(invite.inviter.created_at.timestamp())}:R>"
                    ),
                    inline=False
                )
                
            # Add invite details
            if hasattr(invite, 'created_at'):
                embed.add_field(
                    name="Invite Details",
                    value=(
                        f"**Created:** <t:{int(invite.created_at.timestamp())}:R>\n"
                        f"**Expires:** {'Never' if invite.max_age == 0 else f'After {invite.max_age // 86400}d' if invite.max_age >= 86400 else f'After {invite.max_age // 3600}h'}\n"
                        f"**Max Uses:** {'Unlimited' if invite.max_uses == 0 else invite.max_uses}"
                    ),
                    inline=False
                )
                
            # Add server icon as thumbnail if available
            if invite.guild.icon:
                embed.set_thumbnail(url=invite.guild.icon.url)
                
            await ctx.send(embed=embed)
            
        except discord.NotFound:
            await ctx.send("❌ Invalid invite code. The invite may have expired or been revoked.")
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to fetch this invite.")
        except Exception as e:
            logger.error(f"Error fetching invite info: {str(e)}")
            await ctx.send(f"❌ An error occurred while fetching invite information: {str(e)}")
    
    @commands.command(name="help")
    async def help_command(self, ctx, *, command_or_group: str = None):
        """View help information for commands"""
        # Get the author's name
        author_name = ctx.author.display_name
        
        # Count total commands (adjust this if you want to exclude certain commands)
        command_count = len(set(cmd.name for cmd in self.bot.commands))
        
        # Create an embed for the help message
        embed = discord.Embed(
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        # Use proper Discord hyperlink format for website
        website_url = "[website](https://example.com)"  # Replace with your actual URL
        
        # Set the description with the formatted message
        embed.description = f"⚙️ @{author_name}: For help, visit our {website_url} to view {command_count} commands"
        
        # Create an embed for the help message with dark gray color (0x36393F - Discord's dark theme color)
        embed = discord.Embed(
            color=0x36393F  # Dark gray color similar to Discord's dark theme
        )
        
        # Use proper Discord hyperlink format for website and make username clickable
        website_url = "[website](https://example.com)"  # Replace with your actual URL
        user_mention = ctx.author.mention  # This creates a clickable username
        
        # Set the description with the formatted message
        embed.description = f"⚙️ {user_mention}: For help, visit our {website_url} to view {command_count} commands"
        
        await ctx.send(embed=embed)
    
    @commands.command()
    async def reverse(self, ctx, url: str = None):
        """Reverse search an image"""
        # Check if a URL was provided or an attachment is present
        if not url and not ctx.message.attachments:
            await ctx.send("❌ Please provide an image URL or attach an image to reverse search.")
            return
            
        # Get the image URL from attachment if no URL was provided
        if not url and ctx.message.attachments:
            url = ctx.message.attachments[0].url
            
        # Create an embed with reverse search links
        embed = discord.Embed(
            title="Reverse Image Search",
            description="Click the links below to search for this image:",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        # Add the image as thumbnail
        embed.set_thumbnail(url=url)
        
        # Add reverse search engine links
        encoded_url = discord.utils.escape_markdown(url)
        google_url = f"https://www.google.com/searchbyimage?image_url={encoded_url}"
        bing_url = f"https://www.bing.com/images/searchbyimage?FORM=IRSBIQ&cbir=sbi&imgurl={encoded_url}"
        yandex_url = f"https://yandex.com/images/search?url={encoded_url}&rpt=imageview"
        tineye_url = f"https://www.tineye.com/search?url={encoded_url}"
        
        embed.add_field(
            name="Search Engines",
            value=(
                f"[Google Images]({google_url})\n"
                f"[Bing Images]({bing_url})\n"
                f"[Yandex Images]({yandex_url})\n"
                f"[TinEye]({tineye_url})"
            ),
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @commands.command()
    async def ocr(self, ctx, url: str = None):
        """Detects text in an image"""
        # Check if a URL was provided or an attachment is present
        if not url and not ctx.message.attachments:
            await ctx.send("❌ Please provide an image URL or attach an image to perform OCR.")
            return
            
        # Get the image URL from attachment if no URL was provided
        if not url and ctx.message.attachments:
            url = ctx.message.attachments[0].url
            
        # Create a placeholder message since we don't have the actual OCR API integration
        embed = discord.Embed(
            title="Optical Character Recognition (OCR)",
            description=(
                "In a full implementation, this command would detect and extract text from the provided image.\n\n"
                "To implement OCR functionality, you would need to:\n"
                "1. Sign up for an OCR API service (like Tesseract, Google Cloud Vision, or OCR.space)\n"
                "2. Download the image from the provided URL\n"
                "3. Send the image to the OCR API\n"
                "4. Process and display the detected text"
            ),
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        # Add the image as thumbnail
        embed.set_thumbnail(url=url)
        
        # Add a field with a sample of what the output might look like
        embed.add_field(
            name="Example Output",
            value=(
                "```\nDetected Text Would Appear Here\n"
                "Multiple lines of text can be detected\n"
                "With varying levels of accuracy depending on the image quality\n```"
            ),
            inline=False
        )
        
        embed.set_footer(text="Note: This command requires an OCR API integration to function properly")
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Information(bot)) 