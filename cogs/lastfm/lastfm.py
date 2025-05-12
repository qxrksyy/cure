import discord
from discord.ext import commands
import logging
import datetime
import json
import re
import aiohttp
import os
import asyncio
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from urllib.parse import quote

from .lastfm_db import LastFMDB
from .lastfm_api import LastFMAPI

logger = logging.getLogger('bot')

class LastFM(commands.Cog):
    """Last.fm integration for Discord"""
    
    def __init__(self, bot):
        self.bot = bot
        self.db = LastFMDB()
        self.api = LastFMAPI()
        self.default_color = 0xb90000  # Last.fm red
        self.DEFAULT_EMOJIS = {"upvote": "👍", "downvote": "👎"}
        
    async def cog_load(self):
        """Initialize the cog on load"""
        await self.db.initialize()
        
    @commands.group(name="lastfm", aliases=["fm", "lf"], invoke_without_command=True)
    async def lastfm(self, ctx):
        """Last.fm commands"""
        # If no subcommand is called, invoke the nowplaying command
        if ctx.invoked_subcommand is None:
            await self.nowplaying(ctx)
    
    @lastfm.command(name="login", aliases=["set", "register"])
    async def login(self, ctx, lastfm_username: str = None):
        """Link your Last.fm account to your Discord account"""
        if not lastfm_username:
            embed = discord.Embed(
                title="Last.fm Login",
                description="Please provide your Last.fm username.\nUsage: `!lastfm login <username>`",
                color=self.default_color
            )
            await ctx.send(embed=embed)
            return
            
        # Check if the Last.fm username exists
        user_info = await self.api.get_user_info(lastfm_username)
        if not user_info or "user" not in user_info:
            embed = discord.Embed(
                title="Error",
                description=f"The Last.fm username `{lastfm_username}` was not found. Please check and try again.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        # Register the user
        success = await self.db.register_user(ctx.author.id, ctx.author.name, lastfm_username)
        
        if success:
            embed = discord.Embed(
                title="Last.fm Account Linked",
                description=f"Your Discord account has been linked to the Last.fm account `{lastfm_username}`.",
                color=discord.Color.green()
            )
            embed.add_field(name="Now Playing", value="Use `!fm` or `!np` to show your current song.", inline=False)
            embed.set_thumbnail(url="https://cdn2.iconfinder.com/data/icons/social-icon-3/512/social_style_3_lastfm-512.png")
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="Error",
                description="Failed to link your Last.fm account. Please try again later.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
    
    @lastfm.command(name="logout", aliases=["unregister", "unlink"])
    async def logout(self, ctx):
        """Unlink your Last.fm account from your Discord account"""
        # Check if the user is registered
        lastfm_username = await self.db.get_lastfm_username(ctx.author.id)
        if not lastfm_username:
            embed = discord.Embed(
                title="Error",
                description="You don't have a Last.fm account linked to your Discord account.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        # Ask for confirmation
        embed = discord.Embed(
            title="Confirmation",
            description=f"Are you sure you want to unlink your Last.fm account `{lastfm_username}`?",
            color=self.default_color
        )
        confirm_msg = await ctx.send(embed=embed)
        
        # Add reactions for confirmation
        await confirm_msg.add_reaction("✅")
        await confirm_msg.add_reaction("❌")
        
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == confirm_msg.id
            
        try:
            reaction, user = await self.bot.wait_for("reaction_add", timeout=30.0, check=check)
            
            if str(reaction.emoji) == "✅":
                # Remove the user
                success = await self.db.remove_user(ctx.author.id)
                
                if success:
                    embed = discord.Embed(
                        title="Last.fm Account Unlinked",
                        description=f"Your Last.fm account `{lastfm_username}` has been unlinked from your Discord account.",
                        color=discord.Color.green()
                    )
                    await confirm_msg.edit(embed=embed)
                else:
                    embed = discord.Embed(
                        title="Error",
                        description="Failed to unlink your Last.fm account. Please try again later.",
                        color=discord.Color.red()
                    )
                    await confirm_msg.edit(embed=embed)
            else:
                embed = discord.Embed(
                    title="Cancelled",
                    description="Account unlinking cancelled.",
                    color=discord.Color.blue()
                )
                await confirm_msg.edit(embed=embed)
                
            # Remove reactions
            await confirm_msg.clear_reactions()
                
        except asyncio.TimeoutError:
            embed = discord.Embed(
                title="Timeout",
                description="Account unlinking timed out.",
                color=discord.Color.blue()
            )
            await confirm_msg.edit(embed=embed)
            await confirm_msg.clear_reactions()
    
    @lastfm.command(name="nowplaying", aliases=["np", "current"])
    async def nowplaying(self, ctx, member: discord.Member = None):
        """Shows what you're currently listening to on Last.fm"""
        target = member or ctx.author
        
        # Get the user's Last.fm username
        lastfm_username = await self.db.get_lastfm_username(target.id)
        if not lastfm_username:
            if target == ctx.author:
                embed = discord.Embed(
                    title="Not Registered",
                    description="You don't have a Last.fm account linked to your Discord account.\nUse `!lastfm login <username>` to link your account.",
                    color=discord.Color.red()
                )
            else:
                embed = discord.Embed(
                    title="Not Registered",
                    description=f"{target.name} doesn't have a Last.fm account linked to their Discord account.",
                    color=discord.Color.red()
                )
            await ctx.send(embed=embed)
            return
            
        # Get the user's custom color
        custom_color = await self.db.get_embed_color(target.id)
        color = int(custom_color, 16) if custom_color else self.default_color
        
        # Get the currently playing track
        track_info = await self.api.get_now_playing(lastfm_username)
        
        if not track_info:
            embed = discord.Embed(
                title=f"{target.name}'s Last.fm",
                description=f"No recently played tracks found for `{lastfm_username}`.",
                color=color
            )
            embed.set_footer(text="Last.fm", icon_url="https://cdn2.iconfinder.com/data/icons/social-icon-3/512/social_style_3_lastfm-512.png")
            await ctx.send(embed=embed)
            return
            
        # Get the user's display mode
        mode = await self.db.get_mode(target.id)
        
        if mode == "default":
            # Default mode
            if track_info.get("now_playing", False):
                embed = discord.Embed(
                    title="Now Playing",
                    description=f"**{track_info['artist']}** - **{track_info['track']}**",
                    color=color,
                    url=track_info['url']
                )
            else:
                embed = discord.Embed(
                    title="Last Played",
                    description=f"**{track_info['artist']}** - **{track_info['track']}**",
                    color=color,
                    url=track_info['url']
                )
                if "date" in track_info:
                    embed.set_footer(text=f"Played {track_info['date']}")
                    
            # Add album if available
            if track_info.get("album"):
                embed.add_field(name="Album", value=track_info['album'], inline=True)
                
            # Set thumbnail if available
            if track_info.get("image"):
                embed.set_thumbnail(url=track_info['image'])
                
            embed.set_author(name=f"{lastfm_username}", url=f"https://www.last.fm/user/{lastfm_username}", icon_url=target.display_avatar.url)
            
        elif mode == "compact":
            # Compact mode
            status = "Now Playing" if track_info.get("now_playing", False) else "Last Played"
            album_info = f" | {track_info['album']}" if track_info.get("album") else ""
            
            embed = discord.Embed(
                description=f"**{status}**: **{track_info['artist']}** - **{track_info['track']}**{album_info}",
                color=color
            )
            embed.set_author(name=f"{lastfm_username}", url=f"https://www.last.fm/user/{lastfm_username}", icon_url=target.display_avatar.url)
            
            if not track_info.get("now_playing", False) and "date" in track_info:
                embed.set_footer(text=f"Played {track_info['date']}")
                
        elif mode == "nightly":
            # Nightly mode (dark theme with larger image)
            embed = discord.Embed(color=0x2F3136)  # Discord dark theme color
            
            status = "NOW PLAYING" if track_info.get("now_playing", False) else "LAST PLAYED"
            
            embed.set_author(name=f"{status} - {lastfm_username}", url=f"https://www.last.fm/user/{lastfm_username}", icon_url="https://cdn2.iconfinder.com/data/icons/social-icon-3/512/social_style_3_lastfm-512.png")
            
            # Track and artist in title
            embed.title = f"{track_info['track']} by {track_info['artist']}"
            embed.url = track_info['url']
            
            # Add album if available
            if track_info.get("album"):
                embed.add_field(name="Album", value=track_info['album'], inline=True)
                
            # Set image if available (using image instead of thumbnail for larger display)
            if track_info.get("image"):
                embed.set_image(url=track_info['image'])
                
            if not track_info.get("now_playing", False) and "date" in track_info:
                embed.set_footer(text=f"Played {track_info['date']}")
                
        else:
            # Fallback to default mode
            embed = discord.Embed(
                title="Now Playing" if track_info.get("now_playing", False) else "Last Played",
                description=f"**{track_info['artist']}** - **{track_info['track']}**",
                color=color,
                url=track_info['url']
            )
            
            # Add album if available
            if track_info.get("album"):
                embed.add_field(name="Album", value=track_info['album'], inline=True)
                
            # Set thumbnail if available
            if track_info.get("image"):
                embed.set_thumbnail(url=track_info['image'])
                
            embed.set_author(name=f"{lastfm_username}", url=f"https://www.last.fm/user/{lastfm_username}", icon_url=target.display_avatar.url)
            
        # Add buttons for external services
        spotify_link = await self.api.get_spotify_link(track_info['artist'], track_info['track'])
        youtube_link = await self.api.get_youtube_link(track_info['artist'], track_info['track'])
        
        embed.add_field(
            name="Links", 
            value=f"[Spotify]({spotify_link}) | [YouTube]({youtube_link}) | [Last.fm]({track_info['url']})", 
            inline=False
        )
        
        # Check if the track is in favorites
        is_favorite = await self.db.is_favorite(target.id, track_info['track'], track_info['artist'])
        
        if is_favorite:
            embed.add_field(name="❤️", value="Favorited track", inline=True)
            
        # Send the embed
        message = await ctx.send(embed=embed)
        
        # Add reactions for favoriting and links
        await message.add_reaction("❤️")  # Favorite
        
        # Get custom reactions if available
        custom_reactions = await self.db.get_custom_reactions(target.id)
        
        upvote_emoji = custom_reactions['upvote'] if custom_reactions else self.DEFAULT_EMOJIS["upvote"]
        downvote_emoji = custom_reactions['downvote'] if custom_reactions else self.DEFAULT_EMOJIS["downvote"]
        
        await message.add_reaction(upvote_emoji)
        await message.add_reaction(downvote_emoji)
    
    @lastfm.command(name="recent", aliases=["recents", "history"])
    async def recent(self, ctx, member: discord.Member = None):
        """View your recent tracks"""
        target = member or ctx.author
        
        # Get the user's Last.fm username
        lastfm_username = await self.db.get_lastfm_username(target.id)
        if not lastfm_username:
            if target == ctx.author:
                embed = discord.Embed(
                    title="Not Registered",
                    description="You don't have a Last.fm account linked to your Discord account.\nUse `!lastfm login <username>` to link your account.",
                    color=discord.Color.red()
                )
            else:
                embed = discord.Embed(
                    title="Not Registered",
                    description=f"{target.name} doesn't have a Last.fm account linked to their Discord account.",
                    color=discord.Color.red()
                )
            await ctx.send(embed=embed)
            return
            
        # Get the user's custom color
        custom_color = await self.db.get_embed_color(target.id)
        color = int(custom_color, 16) if custom_color else self.default_color
        
        # Get recent tracks
        response = await self.api.get_recent_tracks(lastfm_username, limit=10)
        
        if not response or "recenttracks" not in response or "track" not in response["recenttracks"]:
            embed = discord.Embed(
                title=f"{target.name}'s Recent Tracks",
                description=f"No recent tracks found for `{lastfm_username}`.",
                color=color
            )
            embed.set_footer(text="Last.fm", icon_url="https://cdn2.iconfinder.com/data/icons/social-icon-3/512/social_style_3_lastfm-512.png")
            await ctx.send(embed=embed)
            return
            
        tracks = response["recenttracks"]["track"]
        # Make sure tracks is a list
        if not isinstance(tracks, list):
            tracks = [tracks]
            
        embed = discord.Embed(
            title=f"{target.name}'s Recent Tracks",
            color=color
        )
        
        # Show last 10 tracks
        for i, track in enumerate(tracks[:10], 1):
            artist = track.get("artist", {}).get("#text", "Unknown Artist")
            track_name = track.get("name", "Unknown Track")
            album = track.get("album", {}).get("#text", "")
            
            # Check if the track is currently playing
            now_playing = False
            if "@attr" in track and "nowplaying" in track["@attr"]:
                now_playing = True
                
            # Format track info
            track_info = f"**{artist}** - **{track_name}**"
            if album:
                track_info += f" | *{album}*"
                
            # Add timestamp if not currently playing
            if not now_playing and "date" in track:
                date = track["date"].get("#text", "")
                track_info += f" | {date}"
                
            # Add emoji for currently playing track
            prefix = "🎵 " if now_playing else f"{i}. "
            
            embed.add_field(name=prefix, value=track_info, inline=False)
            
        # Set thumbnail to user's avatar
        embed.set_thumbnail(url=target.display_avatar.url)
        
        # Set author with Last.fm profile link
        embed.set_author(name=f"{lastfm_username}", url=f"https://www.last.fm/user/{lastfm_username}", icon_url="https://cdn2.iconfinder.com/data/icons/social-icon-3/512/social_style_3_lastfm-512.png")
        
        # Add total scrobbles if available
        if "recenttracks" in response and "@attr" in response["recenttracks"]:
            total_scrobbles = response["recenttracks"]["@attr"].get("total", "Unknown")
            embed.set_footer(text=f"Total Scrobbles: {total_scrobbles}")
            
        await ctx.send(embed=embed)
    
    @lastfm.command(name="color", aliases=["setcolor", "embedcolor"])
    async def color(self, ctx, color: str = None):
        """Set a custom color for your Now Playing embeds"""
        # Check if the user is registered
        lastfm_username = await self.db.get_lastfm_username(ctx.author.id)
        if not lastfm_username:
            embed = discord.Embed(
                title="Not Registered",
                description="You don't have a Last.fm account linked to your Discord account.\nUse `!lastfm login <username>` to link your account.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        if not color:
            # Reset to default color
            await self.db.set_embed_color(ctx.author.id, None)
            
            embed = discord.Embed(
                title="Embed Color Reset",
                description="Your Now Playing embed color has been reset to the default Last.fm red.",
                color=self.default_color
            )
            await ctx.send(embed=embed)
            return
            
        # Try to parse color
        try:
            # Remove # if present
            if color.startswith('#'):
                color = color[1:]
                
            # Check if it's a valid hex color
            if not re.match(r'^[0-9A-Fa-f]{6}$', color):
                raise ValueError("Invalid hex color format")
                
            # Convert to integer
            color_int = int(color, 16)
            
            # Check if it's a valid RGB color
            if color_int < 0 or color_int > 0xFFFFFF:
                raise ValueError("Color value out of range")
                
            # Save the color
            await self.db.set_embed_color(ctx.author.id, color)
            
            # Create sample embed with the new color
            embed = discord.Embed(
                title="Embed Color Updated",
                description=f"Your Now Playing embed color has been set to `#{color}`.",
                color=color_int
            )
            embed.set_footer(text="This is how your embeds will look with the new color.")
            
            await ctx.send(embed=embed)
            
        except ValueError as e:
            embed = discord.Embed(
                title="Invalid Color",
                description=f"Please provide a valid hex color code (e.g. `#FF0000`).\nError: {str(e)}",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            
    @lastfm.command(name="mode", aliases=["setmode", "embedmode"])
    async def mode(self, ctx, mode: str = None):
        """Set a display mode for your Now Playing embeds"""
        # Check if the user is registered
        lastfm_username = await self.db.get_lastfm_username(ctx.author.id)
        if not lastfm_username:
            embed = discord.Embed(
                title="Not Registered",
                description="You don't have a Last.fm account linked to your Discord account.\nUse `!lastfm login <username>` to link your account.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        valid_modes = ["default", "compact", "nightly"]
        
        if not mode or mode.lower() not in valid_modes:
            # Show available modes
            embed = discord.Embed(
                title="Available Display Modes",
                description="Choose from the following display modes for your Now Playing embeds:",
                color=self.default_color
            )
            
            embed.add_field(name="default", value="Standard display with artist, track, and album information", inline=False)
            embed.add_field(name="compact", value="Compact display in a single line", inline=False)
            embed.add_field(name="nightly", value="Dark theme with larger album art", inline=False)
            
            embed.set_footer(text=f"Usage: !lastfm mode <mode>")
            
            await ctx.send(embed=embed)
            return
            
        # Set the mode
        await self.db.set_mode(ctx.author.id, mode.lower())
        
        embed = discord.Embed(
            title="Display Mode Updated",
            description=f"Your Now Playing display mode has been set to `{mode.lower()}`.",
            color=self.default_color
        )
        embed.set_footer(text="This change will apply to your future Now Playing embeds.")
        
        await ctx.send(embed=embed)
    
    @lastfm.command(name="customreactions", aliases=["reactions", "emojis"])
    async def customreactions(self, ctx, upvote_emoji: str = None, downvote_emoji: str = None):
        """Set custom reaction emojis for your Now Playing embeds"""
        # Check if the user is registered
        lastfm_username = await self.db.get_lastfm_username(ctx.author.id)
        if not lastfm_username:
            embed = discord.Embed(
                title="Not Registered",
                description="You don't have a Last.fm account linked to your Discord account.\nUse `!lastfm login <username>` to link your account.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        if not upvote_emoji or not downvote_emoji:
            # Show current reactions
            current_reactions = await self.db.get_custom_reactions(ctx.author.id)
            
            if current_reactions:
                embed = discord.Embed(
                    title="Current Custom Reactions",
                    description=f"Upvote: {current_reactions['upvote']}\nDownvote: {current_reactions['downvote']}",
                    color=self.default_color
                )
            else:
                embed = discord.Embed(
                    title="Current Reactions",
                    description=f"Upvote: {self.DEFAULT_EMOJIS['upvote']}\nDownvote: {self.DEFAULT_EMOJIS['downvote']}\n\nYou don't have custom reactions set.",
                    color=self.default_color
                )
                
            embed.set_footer(text="Usage: !lastfm customreactions <upvote_emoji> <downvote_emoji>")
            
            await ctx.send(embed=embed)
            return
            
        # Validate emojis
        try:
            # Try to add the reactions to a test message
            test_message = await ctx.send("Testing reactions...")
            await test_message.add_reaction(upvote_emoji)
            await test_message.add_reaction(downvote_emoji)
            
            # Set the custom reactions
            await self.db.set_custom_reactions(ctx.author.id, upvote_emoji, downvote_emoji)
            
            embed = discord.Embed(
                title="Custom Reactions Updated",
                description=f"Your Now Playing reactions have been set to:\nUpvote: {upvote_emoji}\nDownvote: {downvote_emoji}",
                color=self.default_color
            )
            
            await test_message.edit(content=None, embed=embed)
            
        except discord.errors.HTTPException:
            embed = discord.Embed(
                title="Invalid Emoji",
                description="One or both of the emojis you provided are invalid. Please make sure you're using valid emojis that the bot can access.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)

async def setup(bot):
    """Load the LastFM cog"""
    await bot.add_cog(LastFM(bot)) 