"""
Music module for QxrK Bot
"""
import discord
from discord.ext import commands
import wavelink
from wavelink.tracks import Playable
from wavelink import TrackEndEventPayload, NodeReadyEventPayload
import asyncio
import logging
import re
import datetime
import random
import typing
from typing import Dict, List, Optional, Union, Any
import urllib.parse
import traceback

# Set up logging
logger = logging.getLogger(__name__)

def format_time(milliseconds: int) -> str:
    """Format milliseconds into MM:SS format"""
    seconds = milliseconds / 1000
    minutes, seconds = divmod(seconds, 60)
    return f"{int(minutes):02d}:{int(seconds):02d}"

def parse_time(time_str: str) -> int:
    """Parse a time string (MM:SS or seconds) into milliseconds"""
    if ':' in time_str:
        minutes, seconds = time_str.split(':')
        return (int(minutes) * 60 + int(seconds)) * 1000
    return int(time_str) * 1000

class MusicView(discord.ui.View):
    """Custom view for music platform selection"""
    def __init__(self, query="", timeout=30):
        super().__init__(timeout=timeout)
        self.query = query
        
    @discord.ui.button(emoji="🔊", style=discord.ButtonStyle.secondary, custom_id="music:sc")
    async def soundcloud_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Handle SoundCloud search
        await interaction.response.defer()
        
        # Get the query from the view
        query = self.query
        if not query:
            # Try to get it from the original message context if stored
            ctx = getattr(interaction, '_original_ctx', None)
            if ctx and hasattr(ctx, 'message') and hasattr(ctx.message, 'content'):
                # Extract query from message content
                content = ctx.message.content
                if ' ' in content:
                    query = content.split(' ', 1)[1]
            
            if not query:
                query = "music"  # Fallback if we can't get the query
            
        try:
            # Check if user is in a voice channel
            if not interaction.user.voice or not interaction.user.voice.channel:
                await interaction.followup.send("❌ You need to be in a voice channel!", ephemeral=True)
                return
                
            # Search with SoundCloud
            search_query = f"scsearch:{query}"
            
            # Get Music cog and search
            music_cog = interaction.client.get_cog("Music")
            if not music_cog:
                await interaction.followup.send("❌ Music system not available.", ephemeral=True)
                return
                
            # Connect to voice channel
            player = await music_cog.ensure_voice(await interaction.client.get_context(interaction))
            if not player:
                return
                
            # Search for tracks
            tracks = await wavelink.Playable.search(search_query)
            
            if not tracks:
                await interaction.followup.send("❌ No results found on SoundCloud either.", ephemeral=True)
                return
                
            # Play the first track
            track = tracks[0]
            if player.playing:
                await interaction.followup.send(f"Added **{track.title}** to the queue from SoundCloud.")
                player.queue.put(track)
            else:
                await player.play(track)
                embed = discord.Embed(
                    description=f"Started playing [{track.title}]({track.uri}) from SoundCloud",
                    color=discord.Color.blue()
                )
                await interaction.followup.send(embed=embed)
                
        except Exception as e:
            logger.error(f"Error processing SoundCloud search: {e}")
            await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)

    @discord.ui.button(emoji="💚", style=discord.ButtonStyle.secondary, custom_id="music:sp")
    async def spotify_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Handle Spotify search
        await interaction.response.defer()
        
        # Get the query from the view
        query = self.query
        if not query:
            # Default fallback
            query = "music"
            
        try:
            # Check if user is in a voice channel
            if not interaction.user.voice or not interaction.user.voice.channel:
                await interaction.followup.send("❌ You need to be in a voice channel!", ephemeral=True)
                return
                
            # Try to get the multi-source manager from MusicSearch cog
            music_search_cog = interaction.client.get_cog("MusicSearch")
            source_manager = getattr(music_search_cog, 'source_manager', None) if music_search_cog else None
            
            if source_manager:
                # Use multi-source manager to search Spotify
                spotify_results = await source_manager.search(query, source="spotify")
                spotify_tracks = spotify_results.get("spotify", [])
                
                if spotify_tracks and len(spotify_tracks) > 0:
                    # Get the first track
                    track_data = spotify_tracks[0]
                    
                    # Get Music cog and ensure voice
                    music_cog = interaction.client.get_cog("Music")
                    player = await music_cog.ensure_voice(await interaction.client.get_context(interaction))
                    if not player:
                        return
                    
                    # Convert to playable track
                    track = await source_manager.get_playable_track(track_data["id"], "spotify")
                    
                    if not track:
                        await interaction.followup.send("❌ Could not convert Spotify track to playable format.", ephemeral=True)
                        return
                        
                    # Add to queue or play
                    if player.playing:
                        await interaction.followup.send(f"Added **{track.title}** to the queue from Spotify.")
                        player.queue.put(track)
                    else:
                        await player.play(track)
                        embed = discord.Embed(
                            description=f"Started playing [{track.title}]({track.uri}) from Spotify",
                            color=discord.Color.blue()
                        )
                        await interaction.followup.send(embed=embed)
                        
                else:
                    await interaction.followup.send("❌ No results found on Spotify either.", ephemeral=True)
            else:
                await interaction.followup.send("❌ Spotify search not available.", ephemeral=True)
                
        except Exception as e:
            logger.error(f"Error processing Spotify search: {e}")
            await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)

    @discord.ui.button(emoji="🎥", style=discord.ButtonStyle.secondary, custom_id="music:yt")
    async def youtube_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Handle YouTube search
        await interaction.response.defer()
        
        # Get the query from the view
        query = self.query
        if not query:
            # Default fallback
            query = "music"
            
        try:
            # Check if user is in a voice channel
            if not interaction.user.voice or not interaction.user.voice.channel:
                await interaction.followup.send("❌ You need to be in a voice channel!", ephemeral=True)
                return
                
            # Search with YouTube
            search_query = f"ytsearch:{query}"
            
            # Get Music cog and search
            music_cog = interaction.client.get_cog("Music")
            if not music_cog:
                await interaction.followup.send("❌ Music system not available.", ephemeral=True)
                return
                
            # Connect to voice channel
            player = await music_cog.ensure_voice(await interaction.client.get_context(interaction))
            if not player:
                return
                
            # Search for tracks
            tracks = await wavelink.Playable.search(search_query)
            
            if not tracks:
                await interaction.followup.send("❌ No results found on YouTube either.", ephemeral=True)
                return
                
            # Play the first track
            track = tracks[0]
            if player.playing:
                await interaction.followup.send(f"Added **{track.title}** to the queue from YouTube.")
                player.queue.put(track)
            else:
                await player.play(track)
                embed = discord.Embed(
                    description=f"Started playing [{track.title}]({track.uri}) from YouTube",
                    color=discord.Color.blue()
                )
                await interaction.followup.send(embed=embed)
                
        except Exception as e:
            logger.error(f"Error processing YouTube search: {e}")
            await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)

    @discord.ui.button(emoji="💯", style=discord.ButtonStyle.secondary, custom_id="music:dz")
    async def deezer_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Handle Deezer search
        await interaction.response.defer()
        
        # Get the query from the view
        query = self.query
        if not query:
            # Default fallback
            query = "music"
            
        try:
            # Check if user is in a voice channel
            if not interaction.user.voice or not interaction.user.voice.channel:
                await interaction.followup.send("❌ You need to be in a voice channel!", ephemeral=True)
                return
                
            # Try to get the multi-source manager from MusicSearch cog
            music_search_cog = interaction.client.get_cog("MusicSearch")
            source_manager = getattr(music_search_cog, 'source_manager', None) if music_search_cog else None
            
            if source_manager:
                # Use multi-source manager to search Deezer
                deezer_results = await source_manager.search(query, source="deezer")
                deezer_tracks = deezer_results.get("deezer", [])
                
                if deezer_tracks and len(deezer_tracks) > 0:
                    # Get the first track
                    track_data = deezer_tracks[0]
                    
                    # Get Music cog and ensure voice
                    music_cog = interaction.client.get_cog("Music")
                    player = await music_cog.ensure_voice(await interaction.client.get_context(interaction))
                    if not player:
                        return
                    
                    # Convert to playable track
                    track = await source_manager.get_playable_track(track_data["id"], "deezer")
                    
                    if not track:
                        await interaction.followup.send("❌ Could not convert Deezer track to playable format.", ephemeral=True)
                        return
                        
                    # Add to queue or play
                    if player.playing:
                        await interaction.followup.send(f"Added **{track.title}** to the queue from Deezer.")
                        player.queue.put(track)
                    else:
                        await player.play(track)
                        embed = discord.Embed(
                            description=f"Started playing [{track.title}]({track.uri}) from Deezer",
                            color=discord.Color.blue()
                        )
                        await interaction.followup.send(embed=embed)
                        
                else:
                    await interaction.followup.send("❌ No results found on Deezer either.", ephemeral=True)
            else:
                await interaction.followup.send("❌ Deezer search not available.", ephemeral=True)
                
        except Exception as e:
            logger.error(f"Error processing Deezer search: {e}")
            await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)

class Music(commands.Cog):
    """Music commands for playing and controlling audio in voice channels"""
    
    def __init__(self, bot):
        self.bot = bot
        self.default_volume = 50
        self.active_filters = {}
        self.node_connected = False
        self.wavelink = None
        # Track repeat mode (0 = off, 1 = track, 2 = queue)
        self.repeat_modes = {}
        # Store the last text channel used for music commands in each guild
        self.last_channel = {}
        logger.info("Music cog initialized")
        logger.info(f"Wavelink version: {wavelink.__version__}")
        self.bot.loop.create_task(self.connect_nodes())
        
    async def connect_nodes(self):
        """Connect to Lavalink nodes"""
        await self.bot.wait_until_ready()
        
        try:
            # Set node connection to False initially
            self.node_connected = False
            logger.info("Attempting to connect to Lavalink node on Raspberry Pi...")
            
            # For wavelink 3.2.0
            self.node = wavelink.Node(
                uri='http://10.0.0.75:2333',  # Using Raspberry Pi IP
                password='Confusion10072003$'
            )
            await wavelink.Pool.connect(nodes=[self.node], client=self.bot)
            logger.info("Wavelink node connected successfully to Raspberry Pi")
            
            # Node connects but on_wavelink_node_ready may not be called immediately
            # We'll set this here too as a fallback
            self.node_connected = True
        except Exception as e:
            self.node_connected = False
            logger.error(f"Wavelink node connection failed: {e}")
            logger.error(traceback.format_exc())
            
    @commands.Cog.listener()
    async def on_wavelink_node_ready(self, payload: wavelink.NodeReadyEventPayload):
        """Event fired when a wavelink node is ready"""
        logger.info(f"Wavelink node {payload.node.identifier} is ready!")
        self.node = payload.node
        self.node_connected = True
        logger.info("Node connection status set to: Connected")
        
    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload: wavelink.TrackEndEventPayload):
        """Event fired when a track ends"""
        player = payload.player
        track = payload.track
        reason = payload.reason
        
        if reason == "FINISHED":
            # Get the guild ID from the player
            guild_id = player.guild.id if hasattr(player, 'guild') else None
            
            if not guild_id:
                return
                
            # Try to play the next track
            try:
                # Check if autoplay is enabled
                if player.queue.is_empty and getattr(player, 'autoplay', False):
                    # Try to get a recommended track
                    try:
                        recommended = await player.search(f"ytmsearch:{track.title}")
                        if recommended and recommended.tracks:
                            # Filter out the current track and get a random one
                            filtered = [t for t in recommended.tracks if t.title != track.title]
                            if filtered:
                                next_track = random.choice(filtered)
                                await player.play(next_track)
                                return
                    except Exception as e:
                        logger.error(f"Error getting recommended track: {e}")
                
                # If no autoplay or it failed, try to play from queue
                if not player.queue.is_empty:
                    next_track = player.queue.get()
                    await player.play(next_track)
                # If queue is empty, can handle cleanup here
            except Exception as e:
                logger.error(f"Error playing next track: {e}")
                logger.error(traceback.format_exc())

    @commands.Cog.listener()
    async def on_wavelink_track_exception(self, payload: wavelink.TrackExceptionEventPayload):
        """Event fired when a track raises an exception while playing."""
        player = payload.player
        track = payload.track
        error = payload.exception
        
        logger.error(f"Track error: {error} for {track.title if track else 'Unknown track'}")
        ctx = getattr(player, 'ctx', None)
        if ctx:
            await ctx.send(f"Error playing track: {error}")
    
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """Detect when the bot is kicked from a voice channel"""
        # Check if this update is for the bot
        if member.id != self.bot.user.id:
            return
            
        # Check if the bot was disconnected from a voice channel
        if before.channel is not None and after.channel is None:
            # Bot was disconnected from a voice channel
            guild = member.guild
            logger.info(f"Bot was disconnected from voice channel {before.channel.name} in {guild.name}")
            
            # Store the channel where we should send the message
            # We need to do this before trying to get the player
            # because the player might already be gone
            text_channel = None
            try:
                # Try to get the player before it's destroyed
                node = wavelink.Pool.get_node()
                if node:
                    player = node.get_player(guild.id)
                    if player and hasattr(player, 'ctx'):
                        text_channel = player.ctx.channel
                        logger.info(f"Found text channel from player context: {text_channel.name}")
            except Exception as e:
                logger.error(f"Error getting player: {e}")
            
            # If we couldn't get the text channel from the player,
            # check our stored last channel
            if not text_channel and guild.id in self.last_channel:
                text_channel = self.last_channel[guild.id]
                logger.info(f"Using stored last channel: {text_channel.name}")
            
            # If we still couldn't get the text channel,
            # try to find a suitable text channel in the guild
            if not text_channel:
                logger.info("No stored channel found, searching for suitable text channel")
                # Try to find the bot-commands channel or the first text channel
                for channel in guild.text_channels:
                    if channel.permissions_for(guild.me).send_messages:
                        if channel.name.lower() in ['bot-commands', 'bot', 'music', 'commands']:
                            text_channel = channel
                            logger.info(f"Found suitable channel by name: {channel.name}")
                            break
                
                # If we still don't have a channel, use the first one we can send to
                if not text_channel:
                    for channel in guild.text_channels:
                        if channel.permissions_for(guild.me).send_messages:
                            text_channel = channel
                            logger.info(f"Using first available channel: {channel.name}")
                            break
            
            # Send the message if we found a suitable channel
            if text_channel:
                logger.info(f"Sending kicked message to channel: {text_channel.name}")
                # Create an embed message that exactly matches the example image
                embed = discord.Embed(
                    description="I have been kicked from the voice channel 😔",
                    color=discord.Color.red()
                )
                
                # Send the embed to the channel
                try:
                    await text_channel.send(embed=embed)
                    logger.info("Successfully sent kicked message")
                except Exception as e:
                    logger.error(f"Failed to send kicked message: {e}")
            else:
                logger.error("Could not find any suitable text channel to send kicked message")
    
    async def ensure_voice(self, ctx):
        """Ensures the bot is in a voice channel and returns the player"""
        if not ctx.guild:
            await ctx.send("This command can only be used in a server.")
            return None
            
        if not ctx.author.voice:
            await ctx.send("You must be in a voice channel to use this command.")
            return None
            
        if not self.node_connected:
            await ctx.send("Cannot connect to voice - Lavalink server is not connected. Please try again later.")
            return None
        
        # Store the last channel used for music commands
        self.last_channel[ctx.guild.id] = ctx.channel
        
        try:
            player = await ctx.author.voice.channel.connect(cls=wavelink.Player, self_deaf=True)
            player.ctx = ctx
            await player.set_volume(self.default_volume)
            return player
            
        except discord.ClientException as e:
            logger.error(f"Discord client exception: {e}")
            await ctx.send(f"Failed to connect to voice channel: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to connect to voice channel: {e}")
            logger.error(traceback.format_exc())
            await ctx.send(f"Failed to connect to voice channel: {e}")
            return None
    
    @commands.command(name="connect")
    async def connect(self, ctx, *, channel: discord.VoiceChannel = None):
        """Connect the bot to a voice channel"""
        try:
            # Store the last channel used for music commands
            self.last_channel[ctx.guild.id] = ctx.channel
            
            if not self.node_connected:
                await ctx.send("Cannot connect to voice - Lavalink server is not connected. Please try again later.")
                return
            
            if not channel and ctx.author.voice:
                channel = ctx.author.voice.channel
            
            if not channel:
                await ctx.send("You must be in a voice channel or specify a channel to connect to.")
                return
                
            logger.info(f"Connect command received for channel: {channel.name}")
            
            # Check if we're already connected to this channel
            if ctx.voice_client and ctx.voice_client.channel.id == channel.id:
                await ctx.send(f"Already connected to {channel.name}!")
                return
                
            # Connect to the channel
            player = await channel.connect(cls=wavelink.Player, self_deaf=True)
            player.ctx = ctx
            await player.set_volume(self.default_volume)
            logger.info(f"Connected to voice channel: {channel.name}")
                
            await ctx.send(f"Connected to {channel.name}!")
        except Exception as e:
            logger.error(f"Error in connect command: {e}")
            logger.error(traceback.format_exc())
            await ctx.send(f"Error connecting to voice channel: {e}")
    
    @commands.command(name="play")
    async def play(self, ctx, *, query: str = None):
        """Queue a track to play"""
        if not self.node_connected:
            await ctx.send("Cannot play music - Lavalink server is not connected. Please try again later.")
            return
            
        if query is None:
            await ctx.send("Please provide a song name or URL to play.\nExample: `!play despacito` or `!play https://www.youtube.com/watch?v=dQw4w9WgXcQ`")
            return
        
        # Store the last channel used for music commands
        self.last_channel[ctx.guild.id] = ctx.channel
            
        # Connect to voice if not already connected
        if not ctx.voice_client:
            player = await self.ensure_voice(ctx)
            if not player:
                return
        else:
            player = ctx.voice_client
            
        player.ctx = ctx
        
        # Try to get the multi-source manager
        music_search_cog = self.bot.get_cog("MusicSearch")
        source_manager = getattr(music_search_cog, 'source_manager', None) if music_search_cog else None
        
        # Check for platform-specific URLs
        spotify_pattern = r'https?://(?:open\.)?spotify\.com/(?:track|album|playlist)/([a-zA-Z0-9]+)'
        deezer_pattern = r'https?://(?:www\.)?deezer\.com/(?:[a-z]{2}/)?(?:track|album|playlist)/(\d+)'
        youtube_pattern = r'https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]+)'
        
        spotify_match = re.search(spotify_pattern, query)
        deezer_match = re.search(deezer_pattern, query)
        youtube_match = re.search(youtube_pattern, query)
        
        # Process the URL based on the platform
        if spotify_match and source_manager:
            # Handle Spotify URL
            await ctx.send(f"🔍 Processing Spotify link...")
            spotify_id = spotify_match.group(1)
            
            try:
                track = await source_manager.get_playable_track(spotify_id, "spotify")
                if track:
                    if player.playing:
                        await ctx.send(f'Added **{track.title}** to the queue.')
                        player.queue.put(track)
                    else:
                        await player.play(track)
                        # Create an embed similar to the example
                        try:
                            # Try to extract artist from the title if it's in "Title - Artist" format
                            title = track.title
                            artist = track.author if hasattr(track, "author") and track.author else "Unknown Artist"
                            
                            if " - " in track.title:
                                parts = track.title.split(" - ", 1)
                                title = parts[0].strip()
                                if not (hasattr(track, "author") and track.author):
                                    artist = parts[1].strip()
                            
                            embed = discord.Embed(
                                description=f"Started playing [{title}]({track.uri}) by {artist}",
                                color=discord.Color.blue()  # Use the blue color similar to the example
                            )
                            await ctx.send(embed=embed)
                        except Exception as e:
                            logger.error(f"Error creating now playing embed: {e}")
                            # Fallback to simple message
                            await ctx.send(f'🎵 Now playing: **{track.title}**')
                else:
                    await ctx.send("❌ Could not process this Spotify link. Trying as a regular search...")
                    # Fall back to regular search
                    query = f'ytsearch:{query}'
            except Exception as e:
                logger.error(f"Error processing Spotify link: {e}")
                await ctx.send(f"❌ Error processing Spotify link: {e}")
                # Fall back to regular search
                query = f'ytsearch:{query}'
                
        elif deezer_match and source_manager:
            # Handle Deezer URL
            await ctx.send(f"🔍 Processing Deezer link...")
            deezer_id = deezer_match.group(1)
            
            try:
                track = await source_manager.get_playable_track(deezer_id, "deezer")
                if track:
                    if player.playing:
                        await ctx.send(f'Added **{track.title}** to the queue.')
                        player.queue.put(track)
                    else:
                        await player.play(track)
                        # Create an embed similar to the example
                        try:
                            # Try to extract artist from the title if it's in "Title - Artist" format
                            title = track.title
                            artist = track.author if hasattr(track, "author") and track.author else "Unknown Artist"
                            
                            if " - " in track.title:
                                parts = track.title.split(" - ", 1)
                                title = parts[0].strip()
                                if not (hasattr(track, "author") and track.author):
                                    artist = parts[1].strip()
                            
                            embed = discord.Embed(
                                description=f"Started playing [{title}]({track.uri}) by {artist}",
                                color=discord.Color.blue()  # Use the blue color similar to the example
                            )
                            await ctx.send(embed=embed)
                        except Exception as e:
                            logger.error(f"Error creating now playing embed: {e}")
                            # Fallback to simple message
                            await ctx.send(f'🎵 Now playing: **{track.title}**')
                else:
                    await ctx.send("❌ Could not process this Deezer link. Trying as a regular search...")
                    # Fall back to regular search
                    query = f'ytsearch:{query}'
            except Exception as e:
                logger.error(f"Error processing Deezer link: {e}")
                await ctx.send(f"❌ Error processing Deezer link: {e}")
                # Fall back to regular search
                query = f'ytsearch:{query}'
                
        elif youtube_match or query.startswith('http'):
            # Handle YouTube URL or other direct URLs
            # No change to the original behavior for these
            pass
            
        else:
            # It's a search term
            query = f'ytsearch:{query}'
            
        # Only continue with wavelink search if we haven't already processed a platform-specific URL
        if (not spotify_match or not source_manager) and (not deezer_match or not source_manager):
            # Remove the "Searching for" message to hide it from users
            # await ctx.send(f"🔍 Searching for: `{query}`")
            
            try:
                # Search for tracks
                tracks = await wavelink.Playable.search(query)
                
                if not tracks:
                    # No tracks found - show platform selection
                    embed = discord.Embed(
                        title="No results",
                        color=discord.Color.red()
                    )
                    view = MusicView(query)
                    await ctx.send(embed=embed, view=view)
                    return
                
                # Handle different result types
                if isinstance(tracks, wavelink.Playlist):
                    # Add all playlist tracks to the queue
                    for track in tracks.tracks:
                        player.queue.put(track)
                    
                    await ctx.send(f'Added the playlist **{tracks.name}** with {len(tracks.tracks)} songs to the queue.')
                    
                    # Start playing if not already
                    if not player.playing:
                        track = player.queue.get()
                        await player.play(track)
                        # Create an embed similar to the example
                        try:
                            # Try to extract artist from the title if it's in "Title - Artist" format
                            title = track.title
                            artist = track.author if hasattr(track, "author") and track.author else "Unknown Artist"
                            
                            if " - " in track.title:
                                parts = track.title.split(" - ", 1)
                                title = parts[0].strip()
                                if not (hasattr(track, "author") and track.author):
                                    artist = parts[1].strip()
                            
                            embed = discord.Embed(
                                description=f"Started playing [{title}]({track.uri}) by {artist}",
                                color=discord.Color.blue()  # Use the blue color similar to the example
                            )
                            await ctx.send(embed=embed)
                        except Exception as e:
                            logger.error(f"Error creating now playing embed: {e}")
                            # Fallback to simple message
                            await ctx.send(f'🎵 Now playing: **{track.title}**')
                else:
                    # It's a single track or list of tracks
                    track = tracks[0]  # Get the first track
                    
                    # Add to queue and play if needed
                    if player.playing:
                        await ctx.send(f'Added **{track.title}** to the queue.')
                        player.queue.put(track)
                    else:
                        await player.play(track)
                        # Create an embed similar to the example
                        try:
                            # Try to extract artist from the title if it's in "Title - Artist" format
                            title = track.title
                            artist = track.author if hasattr(track, "author") and track.author else "Unknown Artist"
                            
                            if " - " in track.title:
                                parts = track.title.split(" - ", 1)
                                title = parts[0].strip()
                                if not (hasattr(track, "author") and track.author):
                                    artist = parts[1].strip()
                            
                            embed = discord.Embed(
                                description=f"Started playing [{title}]({track.uri}) by {artist}",
                                color=discord.Color.blue()  # Use the blue color similar to the example
                            )
                            await ctx.send(embed=embed)
                        except Exception as e:
                            logger.error(f"Error creating now playing embed: {e}")
                            # Fallback to simple message
                            await ctx.send(f'🎵 Now playing: **{track.title}**')
                        
            except Exception as e:
                logger.error(f"Error playing track: {e}")
                logger.error(traceback.format_exc())
                
                # Check if it's a "no results" error
                if "no matches" in str(e).lower() or "not found" in str(e).lower():
                    # Show platform selection
                    embed = discord.Embed(
                        title="No results",
                        color=discord.Color.red()
                    )
                    view = MusicView(query)
                    await ctx.send(embed=embed, view=view)
                else:
                    await ctx.send(f"Error playing track: {e}")
    
    @commands.command(name="skip")
    async def skip(self, ctx):
        """Skip the current track"""
        player = ctx.voice_client
        
        if not player or not player.is_connected():
            return await ctx.send("I'm not connected to a voice channel.")
            
        if not player.playing:
            return await ctx.send("Nothing is playing right now.")
            
        await player.stop()
        await ctx.send("⏭️ Skipped the current track!")
    
    @commands.group(name="queue", invoke_without_command=True)
    async def queue(self, ctx, page: int = 1):
        """View the current queue"""
        player = ctx.voice_client
        
        if not player or not player.is_connected():
            return await ctx.send("I'm not connected to a voice channel.")
            
        if player.queue.is_empty and not player.current:
            return await ctx.send("Nothing is playing and the queue is empty.")
            
        items_per_page = 10
        queue_list = list(player.queue._queue)  # Get the underlying queue list
        pages = math.ceil(len(queue_list) / items_per_page) or 1
        
        if not 1 <= page <= pages:
            page = 1
            
        start = (page - 1) * items_per_page
        end = start + items_per_page
        
        queue_message = ""
        
        # Add currently playing track
        if player.current:
            position = format_time(player.position)
            duration = format_time(player.current.length)
            queue_message += f"**Now Playing:**\n"
            queue_message += f"**[{player.current.title}]({player.current.uri})** - `{position}/{duration}`\n\n"
        
        # Add queued tracks
        if not player.queue.is_empty:
            queue_message += "**Up Next:**\n"
            for i, track in enumerate(queue_list[start:end], start=start + 1):
                duration = format_time(track.length)
                queue_message += f"`{i}.` **[{track.title}]({track.uri})** - `{duration}`\n"
                
            queue_message += f"\n**{len(queue_list)} tracks in queue | Page {page}/{pages}**"
        
        embed = discord.Embed(title="Music Queue", description=queue_message, color=discord.Color.purple())
        embed.set_footer(text=f"Use {ctx.prefix}queue <page> to view another page")
        
        await ctx.send(embed=embed)
    
    @commands.command(name="pause")
    async def pause(self, ctx):
        """Pause the currently playing track"""
        player = ctx.voice_client
        
        if not player or not player.is_connected():
            return await ctx.send("I'm not connected to a voice channel.")
            
        if not player.playing:
            return await ctx.send("Nothing is playing right now.")
            
        if player.paused:
            return await ctx.send("The track is already paused.")
            
        await player.pause()
        await ctx.send("⏸️ Paused the current track.")
    
    @commands.command(name="resume")
    async def resume(self, ctx):
        """Resume the currently paused track"""
        player = ctx.voice_client
        
        if not player or not player.is_connected():
            return await ctx.send("I'm not connected to a voice channel.")
            
        if not player.paused:
            return await ctx.send("The track is already playing.")
            
        await player.resume()
        await ctx.send("▶️ Resumed the current track.")
    
    @commands.command(name="volume")
    async def volume(self, ctx, volume: int = None):
        """Set the player volume (0-100)"""
        player = ctx.voice_client
        
        if not player or not player.is_connected():
            return await ctx.send("I'm not connected to a voice channel.")
            
        if volume is None:
            return await ctx.send(f"🔊 Current volume: **{player.volume}%**")
            
        if not 0 <= volume <= 100:
            return await ctx.send("Volume must be between 0 and 100.")
            
        await player.set_volume(volume)
        await ctx.send(f"🔊 Volume set to **{volume}%**")
    
    @commands.command(aliases=["clear_queue"])
    async def clear(self, ctx):
        """Clear the queue"""
        player = ctx.voice_client
        
        if not player or not player.is_connected():
            return await ctx.send("I'm not connected to a voice channel.")
            
        player.queue.clear()
        await ctx.send("Queue cleared!")
    
    @commands.command(name="disconnect", aliases=["dc", "leave"])
    async def disconnect(self, ctx):
        """Disconnect the bot from the voice channel"""
        player = ctx.voice_client
        
        if not player or not player.is_connected():
            return await ctx.send("I'm not connected to a voice channel.")
            
        await player.disconnect()
        await ctx.send("👋 Disconnected from voice channel.")
    
    @commands.command(name="nowplaying", aliases=["np"])
    async def nowplaying(self, ctx):
        """Show information about the currently playing track"""
        player = ctx.voice_client
        
        if not player or not player.is_connected():
            return await ctx.send("I'm not connected to a voice channel.")
            
        if not player.current:
            return await ctx.send("Nothing is playing right now.")
            
        position = format_time(player.position)
        duration = format_time(player.current.length)
        
        # Create a progress bar
        bar_length = 20
        progress = (player.position / player.current.length) * bar_length if player.current.length > 0 else 0
        progress_bar = "▬" * int(progress) + "🔘" + "▬" * (bar_length - int(progress) - 1)
        
        embed = discord.Embed(title="Now Playing", color=discord.Color.purple())
        embed.add_field(name="Track", value=f"[{player.current.title}]({player.current.uri})", inline=False)
        embed.add_field(name="Duration", value=f"{position}/{duration}", inline=True)
        embed.add_field(name="Author", value=player.current.author, inline=True)
        embed.add_field(name="Progress", value=progress_bar, inline=False)
        
        await ctx.send(embed=embed)
    
    @commands.command(name="seek")
    async def seek(self, ctx, position: str):
        """Seek to a specific position in the track (e.g. 1:30)"""
        player = ctx.voice_client
        
        if not player or not player.is_connected():
            return await ctx.send("I'm not connected to a voice channel.")
            
        if not player.current:
            return await ctx.send("Nothing is playing right now.")
            
        # Calculate position
        position_ms = parse_time(position)
        
        # Restrict to valid positions
        position_ms = max(0, min(position_ms, player.current.length))
        
        await player.seek(position_ms)
        await ctx.send(f"⏺️ Seeked to {format_time(position_ms)}")
    
    @commands.command(name="stop")
    async def stop(self, ctx):
        """Stop the currently playing track and clear the queue"""
        player = ctx.voice_client
        
        if not player or not player.is_connected():
            return await ctx.send("I'm not connected to a voice channel.")
            
        if not player.playing:
            return await ctx.send("Nothing is playing right now.")
            
        player.queue.clear()
        await player.stop()
        await ctx.send("⏹️ Stopped the player and cleared the queue.")

    @commands.command(name="shuffle")
    async def shuffle(self, ctx):
        """Shuffle the queue"""
        player = ctx.voice_client
        
        if not player or not player.is_connected():
            return await ctx.send("I'm not connected to a voice channel.")
            
        if player.queue.is_empty:
            return await ctx.send("The queue is empty.")
            
        player.queue.shuffle()
        await ctx.send("🔀 Queue has been shuffled!")
    
    @commands.command(name="test_lavalink")
    async def test_lavalink(self, ctx):
        """Test connection to the Lavalink server"""
        try:
            await ctx.send(f"Wavelink version: {wavelink.__version__}")
            
            # Check if we're connected to Lavalink
            if not self.node_connected:
                await ctx.send("❌ Not connected to any Lavalink node.")
                return
                
            # Send info about current connection
            await ctx.send("✅ Connected to Lavalink!")
            
            # Test a search to verify functionality
            await ctx.send("Testing search functionality...")
            test_search = await wavelink.Playable.search("despacito")
            
            if test_search:
                track = test_search[0]
                await ctx.send(f"✅ Search successful! Found: {track.title}")
            else:
                await ctx.send("❌ Search returned no results.")
                
        except Exception as e:
            logger.error(f"Error testing Lavalink: {e}")
            logger.error(traceback.format_exc())
            await ctx.send(f"Error testing Lavalink connection: {e}")
            
    @commands.command(name="fastforward", aliases=["ff"])
    async def fastforward(self, ctx, position: str):
        """Fast forward to a specific position in the track (e.g. 1:30)"""
        player = ctx.voice_client
        
        if not player or not player.is_connected():
            return await ctx.send("I'm not connected to a voice channel.")
            
        if not player.current:
            return await ctx.send("Nothing is playing right now.")
        
        # Calculate new position
        current_position = player.position
        position_ms = parse_time(position)
        target_position = current_position + position_ms
        
        # Restrict to valid positions
        target_position = max(0, min(target_position, player.current.length))
        
        await player.seek(target_position)
        await ctx.send(f"⏩ Fast forwarded to {format_time(target_position)}")
    
    @commands.command(name="rewind", aliases=["rw"])
    async def rewind(self, ctx, position: str):
        """Rewind to a specific position in the track (e.g. 0:30)"""
        player = ctx.voice_client
        
        if not player or not player.is_connected():
            return await ctx.send("I'm not connected to a voice channel.")
            
        if not player.current:
            return await ctx.send("Nothing is playing right now.")
        
        # Calculate new position
        current_position = player.position
        position_ms = parse_time(position)
        target_position = current_position - position_ms
        
        # Restrict to valid positions
        target_position = max(0, min(target_position, player.current.length))
        
        await player.seek(target_position)
        await ctx.send(f"⏪ Rewound to {format_time(target_position)}")
    
    @commands.command(name="current", aliases=["playing"])
    async def current(self, ctx):
        """View the current track (alias for nowplaying)"""
        await self.nowplaying(ctx)
    
    @queue.command(name="remove")
    async def queue_remove(self, ctx, index: int):
        """Remove a track from the queue by index"""
        player = ctx.voice_client
        
        if not player or not player.is_connected():
            return await ctx.send("I'm not connected to a voice channel.")
            
        if player.queue.is_empty:
            return await ctx.send("The queue is empty.")
        
        if index < 1 or index > len(player.queue):
            return await ctx.send(f"Invalid index. Please provide a number between 1 and {len(player.queue)}.")
        
        # Convert to 0-based index
        index = index - 1
        
        # Get the queue as a list to remove by index
        queue_list = list(player.queue._queue)
        removed_track = queue_list.pop(index)
        
        # Clear and rebuild queue
        player.queue.clear()
        for track in queue_list:
            player.queue.put(track)
        
        await ctx.send(f"Removed **{removed_track.title}** from the queue.")
    
    @queue.command(name="move")
    async def queue_move(self, ctx, from_index: int, to_index: int):
        """Move a track from one position to another in the queue"""
        player = ctx.voice_client
        
        if not player or not player.is_connected():
            return await ctx.send("I'm not connected to a voice channel.")
            
        if player.queue.is_empty:
            return await ctx.send("The queue is empty.")
        
        queue_length = len(player.queue)
        if from_index < 1 or from_index > queue_length or to_index < 1 or to_index > queue_length:
            return await ctx.send(f"Invalid index. Please provide numbers between 1 and {queue_length}.")
        
        # Convert to 0-based indices
        from_index = from_index - 1
        to_index = to_index - 1
        
        # Get the queue as a list
        queue_list = list(player.queue._queue)
        
        # Move the track
        track = queue_list.pop(from_index)
        queue_list.insert(to_index, track)
        
        # Clear and rebuild queue
        player.queue.clear()
        for track in queue_list:
            player.queue.put(track)
        
        await ctx.send(f"Moved **{track.title}** from position {from_index + 1} to {to_index + 1}.")
    
    @queue.command(name="shuffle")
    async def queue_shuffle(self, ctx):
        """Shuffle the music queue (alias for shuffle command)"""
        await self.shuffle(ctx)
    
    @commands.command(name="repeat")
    async def repeat(self, ctx, option: str = None):
        """Change the current loop mode (off, track, queue)"""
        player = ctx.voice_client
        
        if not player or not player.is_connected():
            return await ctx.send("I'm not connected to a voice channel.")
        
        guild_id = ctx.guild.id
        
        if option is None:
            # Display current mode
            mode = self.repeat_modes.get(guild_id, 0)
            modes = ["off", "track", "queue"]
            return await ctx.send(f"Current repeat mode: **{modes[mode]}**")
        
        option = option.lower()
        
        if option in ["off", "disable", "none", "0"]:
            self.repeat_modes[guild_id] = 0
            await ctx.send("Repeat mode: **Off**")
        elif option in ["track", "song", "current", "1"]:
            self.repeat_modes[guild_id] = 1
            await ctx.send("Repeat mode: **Track** - Current track will repeat")
        elif option in ["queue", "all", "playlist", "2"]:
            self.repeat_modes[guild_id] = 2
            await ctx.send("Repeat mode: **Queue** - Entire queue will repeat")
        else:
            await ctx.send("Invalid option. Use off, track, or queue.")
    
    @commands.group(name="preset", invoke_without_command=True)
    async def preset(self, ctx):
        """List available presets or view active filters"""
        presets = [
            "flat", "boost", "metal", "piano", "8d", "vaporwave", 
            "nightcore", "chipmunk", "karaoke", "vibrato", "soft"
        ]
        
        preset_list = ", ".join([f"`{p}`" for p in presets])
        
        embed = discord.Embed(
            title="Available Audio Presets", 
            description=f"Use `{ctx.prefix}preset <name>` to apply a preset.\nAvailable presets: {preset_list}", 
            color=discord.Color.purple()
        )
        
        # Show active filters if any
        guild_id = ctx.guild.id
        if guild_id in self.active_filters and self.active_filters[guild_id]:
            active = ", ".join([f"`{f}`" for f in self.active_filters[guild_id].keys()])
            embed.add_field(name="Active Filters", value=active, inline=False)
        
        await ctx.send(embed=embed)
    
    @preset.command(name="active")
    async def preset_active(self, ctx):
        """List all currently applied filters"""
        guild_id = ctx.guild.id
        
        if guild_id not in self.active_filters or not self.active_filters[guild_id]:
            return await ctx.send("No audio filters are currently active.")
        
        active_filters = self.active_filters[guild_id]
        embed = discord.Embed(
            title="Active Audio Filters", 
            description="The following audio filters are currently applied:", 
            color=discord.Color.purple()
        )
        
        for filter_name, filter_value in active_filters.items():
            embed.add_field(name=filter_name, value=str(filter_value), inline=True)
        
        await ctx.send(embed=embed)
    
    async def _apply_filter(self, ctx, filter_name, filter_instance):
        """Helper method to apply a filter to the player"""
        player = ctx.voice_client
        
        if not player or not player.is_connected():
            return await ctx.send("I'm not connected to a voice channel.")
            
        if not player.current:
            return await ctx.send("Nothing is playing right now.")
        
        guild_id = ctx.guild.id
        
        # Initialize filters dict if not already
        if guild_id not in self.active_filters:
            self.active_filters[guild_id] = {}
        
        # Apply the filter
        try:
            await player.set_filter(filter_instance)
            self.active_filters[guild_id][filter_name] = filter_instance
            await ctx.send(f"✅ Applied **{filter_name}** audio preset.")
        except Exception as e:
            logger.error(f"Error applying filter {filter_name}: {e}")
            await ctx.send(f"Error applying filter: {e}")
    
    @preset.command(name="clear")
    async def preset_clear(self, ctx):
        """Clear all active audio filters"""
        player = ctx.voice_client
        
        if not player or not player.is_connected():
            return await ctx.send("I'm not connected to a voice channel.")
        
        guild_id = ctx.guild.id
        
        try:
            await player.set_filter(wavelink.Filter())
            self.active_filters[guild_id] = {}
            await ctx.send("✅ Cleared all audio filters.")
        except Exception as e:
            logger.error(f"Error clearing filters: {e}")
            await ctx.send(f"Error clearing filters: {e}")
    
    @preset.command(name="flat")
    async def preset_flat(self, ctx):
        """Apply flat EQ (no effects)"""
        filter_instance = wavelink.Filter()
        await self._apply_filter(ctx, "flat", filter_instance)
    
    @preset.command(name="boost")
    async def preset_boost(self, ctx):
        """Enhance bass and treble for more dynamic sound"""
        eq = wavelink.Equalizer(
            bands=[(0, 0.2), (1, 0.15), (2, 0.1), (3, 0.05), (4, 0), 
                  (5, 0), (6, 0.05), (7, 0.1), (8, 0.15), (9, 0.2)]
        )
        filter_instance = wavelink.Filter(equalizer=eq)
        await self._apply_filter(ctx, "boost", filter_instance)
    
    @preset.command(name="metal")
    async def preset_metal(self, ctx):
        """Enhance mids for metal music"""
        eq = wavelink.Equalizer(
            bands=[(0, 0.1), (1, 0.1), (2, 0.15), (3, 0.2), (4, 0.25),
                  (5, 0.25), (6, 0.2), (7, 0.15), (8, 0.1), (9, 0.05)]
        )
        filter_instance = wavelink.Filter(equalizer=eq)
        await self._apply_filter(ctx, "metal", filter_instance)
    
    @preset.command(name="piano")
    async def preset_piano(self, ctx):
        """Enhance piano and acoustic sounds"""
        eq = wavelink.Equalizer(
            bands=[(0, -0.1), (1, -0.1), (2, -0.05), (3, 0), (4, 0.1),
                  (5, 0.1), (6, 0.15), (7, 0.15), (8, 0.1), (9, 0.05)]
        )
        filter_instance = wavelink.Filter(equalizer=eq)
        await self._apply_filter(ctx, "piano", filter_instance)
    
    @preset.command(name="8d")
    async def preset_8d(self, ctx):
        """Apply 8D audio effect (rotating stereo)"""
        rotation = wavelink.Rotation(rotation_hz=0.2)
        filter_instance = wavelink.Filter(rotation=rotation)
        await self._apply_filter(ctx, "8d", filter_instance)
    
    @preset.command(name="vaporwave")
    async def preset_vaporwave(self, ctx):
        """Apply vaporwave effect (slow down playback)"""
        timescale = wavelink.Timescale(speed=0.8, pitch=0.8)
        filter_instance = wavelink.Filter(timescale=timescale)
        await self._apply_filter(ctx, "vaporwave", filter_instance)
    
    @preset.command(name="nightcore")
    async def preset_nightcore(self, ctx):
        """Apply nightcore effect (speed up playback)"""
        timescale = wavelink.Timescale(speed=1.25, pitch=1.2)
        filter_instance = wavelink.Filter(timescale=timescale)
        await self._apply_filter(ctx, "nightcore", filter_instance)
    
    @preset.command(name="chipmunk")
    async def preset_chipmunk(self, ctx):
        """Apply chipmunk effect (high pitch)"""
        timescale = wavelink.Timescale(speed=1.4, pitch=1.4)
        filter_instance = wavelink.Filter(timescale=timescale)
        await self._apply_filter(ctx, "chipmunk", filter_instance)
    
    @preset.command(name="karaoke")
    async def preset_karaoke(self, ctx):
        """Apply karaoke effect (remove vocals)"""
        karaoke = wavelink.Karaoke(
            level=1.0,
            mono_level=1.0,
            filter_band=220.0,
            filter_width=100.0
        )
        filter_instance = wavelink.Filter(karaoke=karaoke)
        await self._apply_filter(ctx, "karaoke", filter_instance)
    
    @preset.command(name="vibrato")
    async def preset_vibrato(self, ctx):
        """Apply vibrato effect (fluctuating pitch)"""
        vibrato = wavelink.Vibrato(
            frequency=2.0,
            depth=0.5
        )
        filter_instance = wavelink.Filter(vibrato=vibrato)
        await self._apply_filter(ctx, "vibrato", filter_instance)
    
    @preset.command(name="soft")
    async def preset_soft(self, ctx):
        """Apply soft effect (lower highs, emphasis on lows)"""
        eq = wavelink.Equalizer(
            bands=[(0, 0.1), (1, 0.1), (2, 0.05), (3, 0), (4, -0.05),
                  (5, -0.1), (6, -0.1), (7, -0.15), (8, -0.15), (9, -0.2)]
        )
        filter_instance = wavelink.Filter(equalizer=eq)
        await self._apply_filter(ctx, "soft", filter_instance)

    @commands.command(name="lavalink_status")
    async def lavalink_status(self, ctx):
        """Check detailed status of the Lavalink connection"""
        embed = discord.Embed(
            title="Lavalink Connection Status",
            color=discord.Color.blue()
        )
        
        # Check wavelink import
        embed.add_field(
            name="Wavelink Import", 
            value=f"✅ Imported (v{wavelink.__version__})", 
            inline=False
        )
        
        # Check node connection flag
        status = "✅ Connected" if self.node_connected else "❌ Disconnected"
        embed.add_field(
            name="Node Connection Flag", 
            value=status, 
            inline=False
        )
        
        # Check node object
        if self.node:
            uri = self.node.uri
            embed.add_field(
                name="Node URI", 
                value=f"`{uri}`", 
                inline=True
            )
            
            # Check if node is in the Pool
            try:
                nodes = list(wavelink.Pool._nodes.values()) if hasattr(wavelink.Pool, "_nodes") else []
                in_pool = any(n.uri == uri for n in nodes)
                pool_status = "✅ In pool" if in_pool else "❌ Not in pool"
            except Exception as e:
                pool_status = f"❌ Error checking pool: {e}"
            
            embed.add_field(
                name="Pool Status", 
                value=pool_status, 
                inline=True
            )
            
            # Try to make a test search
            try:
                embed.add_field(
                    name="Testing...", 
                    value="🔍 Attempting to search...", 
                    inline=False
                )
                await ctx.send(embed=embed)
                
                # Try a test search
                tracks = await wavelink.Playable.search("test")
                if tracks:
                    success_embed = discord.Embed(
                        title="Lavalink Connection Test",
                        description="✅ Lavalink is fully operational! Search test succeeded.",
                        color=discord.Color.green()
                    )
                    await ctx.send(embed=success_embed)
                else:
                    error_embed = discord.Embed(
                        title="Lavalink Connection Test",
                        description="⚠️ Lavalink connection issues. Search returned no results.",
                        color=discord.Color.orange()
                    )
                    await ctx.send(embed=error_embed)
                return
            except Exception as e:
                error_embed = discord.Embed(
                    title="Lavalink Connection Test",
                    description=f"❌ Lavalink search failed: {e}",
                    color=discord.Color.red()
                )
                await ctx.send(embed=error_embed)
                return
        else:
            embed.add_field(
                name="Node Object", 
                value="❌ Not initialized", 
                inline=False
            )
        
        await ctx.send(embed=embed)
        
        # If node not connected, try to reconnect
        if not self.node_connected:
            await ctx.send("🔄 Attempting to reconnect to Lavalink...")
            try:
                await self.connect_nodes()
                if self.node_connected:
                    await ctx.send("✅ Successfully reconnected to Lavalink!")
                else:
                    await ctx.send("❌ Reconnection attempt failed. Check Lavalink server status.")
            except Exception as e:
                await ctx.send(f"❌ Reconnection error: {e}")

async def setup(bot):
    """Add the Music cog to the bot"""
    await bot.add_cog(Music(bot))
