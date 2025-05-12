import discord
from discord.ext import commands
import aiohttp
import base64
import json
import os
import time
import logging
import asyncio
from urllib.parse import urlencode

logger = logging.getLogger('bot')

class SpotifyAPI:
    """Handles Spotify API interactions"""
    
    def __init__(self, client_id, client_secret, redirect_uri):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.base_url = "https://api.spotify.com/v1"
        self.auth_url = "https://accounts.spotify.com/authorize"
        self.token_url = "https://accounts.spotify.com/api/token"
        
    def get_auth_url(self, state):
        """Generate authorization URL for Spotify OAuth"""
        params = {
            'client_id': self.client_id,
            'response_type': 'code',
            'redirect_uri': self.redirect_uri,
            'state': state,
            'scope': 'user-read-private user-read-email user-read-playback-state user-modify-playback-state user-read-currently-playing playlist-read-private user-library-read user-library-modify user-top-read user-read-recently-played'
        }
        return f"{self.auth_url}?{urlencode(params)}"
        
    async def get_token(self, code):
        """Exchange auth code for access token"""
        auth_string = f"{self.client_id}:{self.client_secret}"
        auth_bytes = auth_string.encode('utf-8')
        auth_base64 = base64.b64encode(auth_bytes).decode('utf-8')
        
        headers = {
            'Authorization': f"Basic {auth_base64}",
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': self.redirect_uri
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(self.token_url, headers=headers, data=data) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_data = await response.text()
                    logger.error(f"Error getting token: {error_data}")
                    return None
    
    async def refresh_token(self, refresh_token):
        """Refresh an expired access token"""
        auth_string = f"{self.client_id}:{self.client_secret}"
        auth_bytes = auth_string.encode('utf-8')
        auth_base64 = base64.b64encode(auth_bytes).decode('utf-8')
        
        headers = {
            'Authorization': f"Basic {auth_base64}",
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(self.token_url, headers=headers, data=data) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_data = await response.text()
                    logger.error(f"Error refreshing token: {error_data}")
                    return None
    
    async def make_api_request(self, access_token, endpoint, method="GET", data=None, params=None):
        """Make a request to the Spotify API"""
        url = f"{self.base_url}/{endpoint}"
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        async with aiohttp.ClientSession() as session:
            if method == "GET":
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status == 200 or response.status == 201:
                        return await response.json()
                    elif response.status == 204:
                        return True
                    else:
                        error_data = await response.text()
                        logger.error(f"Error making API request: {error_data}")
                        return None
            
            elif method == "POST":
                async with session.post(url, headers=headers, json=data) as response:
                    if response.status == 200 or response.status == 201:
                        return await response.json()
                    elif response.status == 204:
                        return True
                    else:
                        error_data = await response.text()
                        logger.error(f"Error making API request: {error_data}")
                        return None
            
            elif method == "PUT":
                async with session.put(url, headers=headers, json=data) as response:
                    if response.status == 200 or response.status == 201:
                        return await response.json()
                    elif response.status == 204:
                        return True
                    else:
                        error_data = await response.text()
                        logger.error(f"Error making API request: {error_data}")
                        return None
            
            elif method == "DELETE":
                async with session.delete(url, headers=headers) as response:
                    if response.status == 200 or response.status == 201:
                        return await response.json()
                    elif response.status == 204:
                        return True
                    else:
                        error_data = await response.text()
                        logger.error(f"Error making API request: {error_data}")
                        return None

class Spotify(commands.Cog):
    """Control your music on Spotify through commands"""
    
    def __init__(self, bot):
        self.bot = bot
        # Use absolute path for data folder
        self.data_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
        self.data_file = os.path.join(self.data_folder, 'spotify.json')
        self.user_tokens = {}  # user_id -> token data
        self.auth_states = {}  # state -> user_id
        
        # Load Spotify API credentials from environment variables or config
        self.client_id = os.environ.get('SPOTIFY_CLIENT_ID', '')
        self.client_secret = os.environ.get('SPOTIFY_CLIENT_SECRET', '')
        self.redirect_uri = os.environ.get('SPOTIFY_REDIRECT_URI', 'http://localhost:8888/callback')
        
        # Initialize API
        self.spotify_api = SpotifyAPI(self.client_id, self.client_secret, self.redirect_uri)
        
        # Load existing data
        self.load_data()
    
    def load_data(self):
        """Load token data from JSON file"""
        if not os.path.exists(self.data_folder):
            os.makedirs(self.data_folder)
            
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                    self.user_tokens = data.get('user_tokens', {})
        except json.JSONDecodeError:
            logger.error(f"Error decoding {self.data_file}. Using empty data.")
            self.user_tokens = {}
    
    def save_data(self):
        """Save token data to JSON file"""
        if not os.path.exists(self.data_folder):
            os.makedirs(self.data_folder)
            
        with open(self.data_file, 'w') as f:
            data = {
                'user_tokens': self.user_tokens
            }
            json.dump(data, f, indent=4)
    
    async def cog_unload(self):
        """Save data when cog is unloaded"""
        self.save_data()
    
    async def ensure_token_valid(self, user_id):
        """Check if token is valid and refresh if needed"""
        user_id = str(user_id)
        
        if user_id not in self.user_tokens:
            return False
        
        token_data = self.user_tokens[user_id]
        
        # Check if token is expired
        current_time = time.time()
        if token_data.get('expires_at', 0) <= current_time:
            # Refresh token
            refresh_token = token_data.get('refresh_token')
            if not refresh_token:
                return False
                
            new_token_data = await self.spotify_api.refresh_token(refresh_token)
            
            if not new_token_data:
                return False
                
            # Update token data
            token_data['access_token'] = new_token_data['access_token']
            token_data['expires_at'] = current_time + new_token_data['expires_in']
            
            # Save the refresh token if provided
            if 'refresh_token' in new_token_data:
                token_data['refresh_token'] = new_token_data['refresh_token']
                
            self.user_tokens[user_id] = token_data
            self.save_data()
        
        return True
    
    async def get_current_playback(self, user_id):
        """Get user's current playback state"""
        if not await self.ensure_token_valid(user_id):
            return None
            
        user_id = str(user_id)
        access_token = self.user_tokens[user_id]['access_token']
        
        return await self.spotify_api.make_api_request(
            access_token, 
            "me/player"
        )
        
    async def search_track(self, user_id, query):
        """Search for a track on Spotify"""
        if not await self.ensure_token_valid(user_id):
            return None
            
        user_id = str(user_id)
        access_token = self.user_tokens[user_id]['access_token']
        
        params = {
            'q': query,
            'type': 'track',
            'limit': 5
        }
        
        return await self.spotify_api.make_api_request(
            access_token, 
            "search",
            params=params
        )

    @commands.command(name="spotify")
    async def spotify_cmd(self, ctx, *, track=None):
        """Control your music on Spotify through commands or search for a track"""
        if not track:
            await self.now(ctx)
            return
        
        # Search for a track if query is provided
        results = await self.search_track(ctx.author.id, track)
        if not results or 'tracks' not in results or 'items' not in results['tracks'] or not results['tracks']['items']:
            await ctx.send("❌ No tracks found matching your query.")
            return
            
        tracks = results['tracks']['items']
        
        # Create embed with results
        embed = discord.Embed(
            title=f"Spotify Search Results for '{track}'",
            color=discord.Color.green()
        )
        
        for i, track_item in enumerate(tracks[:5], 1):
            name = track_item['name']
            artists = ", ".join([artist['name'] for artist in track_item['artists']])
            album = track_item['album']['name']
            url = track_item['external_urls']['spotify']
            
            embed.add_field(
                name=f"{i}. {name}",
                value=f"**Artist:** {artists}\n**Album:** {album}\n[Open in Spotify]({url})",
                inline=False
            )
        
        # Set Spotify logo as thumbnail
        embed.set_thumbnail(url="https://upload.wikimedia.org/wikipedia/commons/thumb/1/19/Spotify_logo_without_text.svg/1024px-Spotify_logo_without_text.svg.png")
        await ctx.send(embed=embed)

    @commands.command(name="spotify_login", aliases=["login"])
    async def login(self, ctx):
        """Grant bot access to your Spotify account"""
        user_id = str(ctx.author.id)
        
        # Generate a random state for security
        state = os.urandom(16).hex()
        self.auth_states[state] = user_id
        
        # Generate auth URL
        auth_url = self.spotify_api.get_auth_url(state)
        
        # Send DM with auth URL
        try:
            embed = discord.Embed(
                title="Spotify Authorization",
                description=f"Click the link below to authorize the bot to access your Spotify account.\n\n[Authorize Spotify]({auth_url})",
                color=discord.Color.green()
            )
            embed.set_footer(text="This link will expire in 10 minutes")
            
            await ctx.author.send(embed=embed)
            await ctx.send("✅ Check your DMs for authorization instructions!")
        except discord.Forbidden:
            await ctx.send("❌ I couldn't send you a DM. Please enable DMs from server members.")

    @commands.command(name="spotify_logout", aliases=["logout"])
    async def logout(self, ctx):
        """Disconnect your Spotify from our servers"""
        user_id = str(ctx.author.id)
        
        if user_id in self.user_tokens:
            del self.user_tokens[user_id]
            self.save_data()
            await ctx.send("✅ Your Spotify account has been disconnected!")
        else:
            await ctx.send("❌ You don't have a connected Spotify account.")

    @commands.command(name="now")
    async def now(self, ctx):
        """View information regarding the currently playing track"""
        if not await self.ensure_token_valid(ctx.author.id):
            await ctx.send("❌ You need to connect your Spotify account first! Use `!spotify login`")
            return
            
        playback = await self.get_current_playback(ctx.author.id)
        
        if not playback or 'item' not in playback:
            await ctx.send("❌ No track currently playing!")
            return
            
        track = playback['item']
        is_playing = playback.get('is_playing', False)
        
        # Create embed with track info
        embed = discord.Embed(
            title="Now Playing" if is_playing else "Paused",
            description=f"**{track['name']}**",
            color=discord.Color.green() if is_playing else discord.Color.light_grey(),
            url=track.get('external_urls', {}).get('spotify', None)
        )
        
        # Add artists
        artists = ", ".join([artist['name'] for artist in track['artists']])
        embed.add_field(name="Artist", value=artists, inline=True)
        
        # Add album
        if 'album' in track and 'name' in track['album']:
            embed.add_field(name="Album", value=track['album']['name'], inline=True)
            
        # Add progress
        if 'progress_ms' in playback and 'duration_ms' in track:
            progress = self.format_ms(playback['progress_ms'])
            duration = self.format_ms(track['duration_ms'])
            embed.add_field(name="Progress", value=f"{progress} / {duration}", inline=True)
            
        # Add device info
        if 'device' in playback:
            device_name = playback['device'].get('name', 'Unknown Device')
            device_type = playback['device'].get('type', 'Unknown Type').capitalize()
            volume = playback['device'].get('volume_percent', 0)
            embed.add_field(name="Device", value=f"{device_name} ({device_type}) - Volume: {volume}%", inline=False)
            
        # Add album art
        if 'album' in track and 'images' in track['album'] and track['album']['images']:
            embed.set_thumbnail(url=track['album']['images'][0]['url'])
            
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
        embed.set_footer(text="Spotify", icon_url="https://upload.wikimedia.org/wikipedia/commons/thumb/1/19/Spotify_logo_without_text.svg/1024px-Spotify_logo_without_text.svg.png")
        
        await ctx.send(embed=embed)

    def format_ms(self, ms):
        """Format milliseconds to MM:SS"""
        seconds = ms // 1000
        minutes = seconds // 60
        seconds %= 60
        return f"{minutes}:{seconds:02d}"

    @commands.command(name="spotify_pause", aliases=["spause"])
    async def pause(self, ctx):
        """Pause the current song"""
        if not await self.ensure_token_valid(ctx.author.id):
            await ctx.send("❌ You need to connect your Spotify account first! Use `!spotify login`")
            return
            
        user_id = str(ctx.author.id)
        access_token = self.user_tokens[user_id]['access_token']
        
        result = await self.spotify_api.make_api_request(
            access_token,
            "me/player/pause",
            method="PUT"
        )
        
        if result is True:
            await ctx.send("⏸️ Spotify playback paused!")
        else:
            await ctx.send("❌ Failed to pause playback. Make sure you have an active device playing.")

    @commands.command(name="spotify_resume", aliases=["sresume"])
    async def resume(self, ctx):
        """Resume the current song"""
        if not await self.ensure_token_valid(ctx.author.id):
            await ctx.send("❌ You need to connect your Spotify account first! Use `!spotify login`")
            return
            
        user_id = str(ctx.author.id)
        access_token = self.user_tokens[user_id]['access_token']
        
        result = await self.spotify_api.make_api_request(
            access_token,
            "me/player/play",
            method="PUT"
        )
        
        if result is True:
            await ctx.send("▶️ Spotify playback resumed!")
        else:
            await ctx.send("❌ Failed to resume playback. Make sure you have an active device.")

    @commands.command(name="next")
    async def next(self, ctx):
        """Immediately skip to the next song"""
        if not await self.ensure_token_valid(ctx.author.id):
            await ctx.send("❌ You need to connect your Spotify account first! Use `!spotify login`")
            return
            
        user_id = str(ctx.author.id)
        access_token = self.user_tokens[user_id]['access_token']
        
        result = await self.spotify_api.make_api_request(
            access_token,
            "me/player/next",
            method="POST"
        )
        
        if result is True:
            await ctx.send("⏭️ Skipped to next track!")
        else:
            await ctx.send("❌ Failed to skip to next track.")

    @commands.command(name="previous")
    async def previous(self, ctx):
        """Immediately go back one song"""
        if not await self.ensure_token_valid(ctx.author.id):
            await ctx.send("❌ You need to connect your Spotify account first! Use `!spotify login`")
            return
            
        user_id = str(ctx.author.id)
        access_token = self.user_tokens[user_id]['access_token']
        
        result = await self.spotify_api.make_api_request(
            access_token,
            "me/player/previous",
            method="POST"
        )
        
        if result is True:
            await ctx.send("⏮️ Skipped to previous track!")
        else:
            await ctx.send("❌ Failed to skip to previous track.")

    @commands.command(name="spotify_volume", aliases=["svolume"])
    async def volume(self, ctx, volume: int = None):
        """Adjust current player volume"""
        if not await self.ensure_token_valid(ctx.author.id):
            await ctx.send("❌ You need to connect your Spotify account first! Use `!spotify login`")
            return
            
        if volume is None:
            # Get current playback to show volume
            playback = await self.get_current_playback(ctx.author.id)
            if not playback or 'device' not in playback:
                await ctx.send("❌ No active playback found!")
                return
                
            current_volume = playback['device'].get('volume_percent', 0)
            await ctx.send(f"🔊 Current volume: {current_volume}%")
            return
            
        # Ensure volume is within valid range
        if volume < 0 or volume > 100:
            await ctx.send("❌ Volume must be between 0 and 100!")
            return
            
        user_id = str(ctx.author.id)
        access_token = self.user_tokens[user_id]['access_token']
        
        result = await self.spotify_api.make_api_request(
            access_token,
            f"me/player/volume?volume_percent={volume}",
            method="PUT"
        )
        
        if result is True:
            await ctx.send(f"🔊 Volume set to {volume}%!")
        else:
            await ctx.send("❌ Failed to change volume. Make sure you have an active premium account.")

    @commands.command(name="device_list", aliases=["devices"])
    async def device_list(self, ctx):
        """List all current devices connected to your Spotify account"""
        if not await self.ensure_token_valid(ctx.author.id):
            await ctx.send("❌ You need to connect your Spotify account first! Use `!spotify login`")
            return
            
        user_id = str(ctx.author.id)
        access_token = self.user_tokens[user_id]['access_token']
        
        devices = await self.spotify_api.make_api_request(
            access_token,
            "me/player/devices"
        )
        
        if not devices or 'devices' not in devices or not devices['devices']:
            await ctx.send("❌ No devices found!")
            return
            
        embed = discord.Embed(
            title="Your Spotify Devices",
            color=discord.Color.green()
        )
        
        for i, device in enumerate(devices['devices'], 1):
            name = device.get('name', 'Unknown Device')
            device_type = device.get('type', 'Unknown Type').capitalize()
            volume = device.get('volume_percent', 0)
            is_active = device.get('is_active', False)
            is_restricted = device.get('is_restricted', False)
            
            status = []
            if is_active:
                status.append("🟢 Active")
            if is_restricted:
                status.append("🔒 Restricted")
                
            status_str = ", ".join(status) if status else "Inactive"
            
            embed.add_field(
                name=f"{i}. {name} ({device_type})",
                value=f"**ID:** `{device.get('id', 'Unknown')}`\n**Volume:** {volume}%\n**Status:** {status_str}",
                inline=False
            )
            
        embed.set_footer(text="Spotify", icon_url="https://upload.wikimedia.org/wikipedia/commons/thumb/1/19/Spotify_logo_without_text.svg/1024px-Spotify_logo_without_text.svg.png")
        await ctx.send(embed=embed)

    @commands.command(name="device")
    async def device(self, ctx, *, device_id=None):
        """Change the device that you're listening to Spotify with"""
        if not await self.ensure_token_valid(ctx.author.id):
            await ctx.send("❌ You need to connect your Spotify account first! Use `!spotify login`")
            return
            
        if device_id is None:
            await self.device_list(ctx)
            await ctx.send("Use `!device <device_id>` to switch to a specific device.")
            return
            
        user_id = str(ctx.author.id)
        access_token = self.user_tokens[user_id]['access_token']
        
        data = {
            "device_ids": [device_id],
            "play": True
        }
        
        result = await self.spotify_api.make_api_request(
            access_token,
            "me/player",
            method="PUT",
            data=data
        )
        
        if result is True:
            await ctx.send(f"✅ Playback transferred to the selected device!")
        else:
            await ctx.send("❌ Failed to transfer playback. Make sure the device ID is correct.")
            
    @commands.command(name="spotify_play", aliases=["splay"])
    async def play(self, ctx, *, track):
        """Play a track on Spotify"""
        if not await self.ensure_token_valid(ctx.author.id):
            await ctx.send("❌ You need to connect your Spotify account first! Use `!spotify login`")
            return
            
        user_id = str(ctx.author.id)
        access_token = self.user_tokens[user_id]['access_token']
        
        # Search for the track
        search_results = await self.search_track(ctx.author.id, track)
        
        if not search_results or 'tracks' not in search_results or not search_results['tracks']['items']:
            await ctx.send(f"❌ No tracks found for: {track}")
            return
            
        # Get the first track URI
        track_uri = search_results['tracks']['items'][0]['uri']
        
        # Play the track
        data = {
            "uris": [track_uri]
        }
        
        result = await self.spotify_api.make_api_request(
            access_token,
            "me/player/play",
            method="PUT",
            data=data
        )
        
        if result is True:
            track_name = search_results['tracks']['items'][0]['name']
            artist_name = search_results['tracks']['items'][0]['artists'][0]['name']
            await ctx.send(f"▶️ Playing Spotify track: **{track_name}** by **{artist_name}**")
        else:
            await ctx.send("❌ Failed to play track. Make sure you have an active Spotify device.")
    
    @commands.command(name="queue")
    async def queue(self, ctx, *, track):
        """Queue a song"""
        if not await self.ensure_token_valid(ctx.author.id):
            await ctx.send("❌ You need to connect your Spotify account first! Use `!spotify login`")
            return
            
        # Search for the track
        results = await self.search_track(ctx.author.id, track)
        if not results or 'tracks' not in results or 'items' not in results['tracks'] or not results['tracks']['items']:
            await ctx.send("❌ No tracks found matching your query.")
            return
            
        # Get the URI of the first result
        track_uri = results['tracks']['items'][0]['uri']
        
        user_id = str(ctx.author.id)
        access_token = self.user_tokens[user_id]['access_token']
        
        result = await self.spotify_api.make_api_request(
            access_token,
            f"me/player/queue?uri={track_uri}",
            method="POST"
        )
        
        if result is True:
            track_name = results['tracks']['items'][0]['name']
            artist_name = results['tracks']['items'][0]['artists'][0]['name']
            await ctx.send(f"➕ Added to queue: **{track_name}** by **{artist_name}**")
        else:
            await ctx.send("❌ Failed to add track to queue. Make sure you have an active device.")
    
    @commands.command(name="seek")
    async def seek(self, ctx, position):
        """Seek to position in current song (format: MM:SS or seconds)"""
        if not await self.ensure_token_valid(ctx.author.id):
            await ctx.send("❌ You need to connect your Spotify account first! Use `!spotify login`")
            return
            
        # Parse position
        ms = 0
        if ":" in position:
            try:
                minutes, seconds = position.split(":")
                ms = (int(minutes) * 60 + int(seconds)) * 1000
            except ValueError:
                await ctx.send("❌ Invalid format. Use MM:SS or seconds.")
                return
        else:
            try:
                ms = int(position) * 1000
            except ValueError:
                await ctx.send("❌ Invalid format. Use MM:SS or seconds.")
                return
                
        user_id = str(ctx.author.id)
        access_token = self.user_tokens[user_id]['access_token']
        
        result = await self.spotify_api.make_api_request(
            access_token,
            f"me/player/seek?position_ms={ms}",
            method="PUT"
        )
        
        if result is True:
            await ctx.send(f"⏩ Seeked to position {self.format_ms(ms)}!")
        else:
            await ctx.send("❌ Failed to seek. Make sure you have an active playback.")
    
    @commands.command(name="shuffle")
    async def shuffle(self, ctx, option: str = None):
        """Toggle playback shuffle"""
        if not await self.ensure_token_valid(ctx.author.id):
            await ctx.send("❌ You need to connect your Spotify account first! Use `!spotify login`")
            return
            
        # Determine shuffle state
        state = None
        if option is None:
            # Toggle current state
            playback = await self.get_current_playback(ctx.author.id)
            if not playback:
                await ctx.send("❌ No active playback found!")
                return
                
            state = not playback.get('shuffle_state', False)
        elif option.lower() in ('on', 'yes', 'true', '1'):
            state = True
        elif option.lower() in ('off', 'no', 'false', '0'):
            state = False
        else:
            await ctx.send("❌ Invalid option. Use 'on' or 'off'.")
            return
            
        user_id = str(ctx.author.id)
        access_token = self.user_tokens[user_id]['access_token']
        
        result = await self.spotify_api.make_api_request(
            access_token,
            f"me/player/shuffle?state={str(state).lower()}",
            method="PUT"
        )
        
        if result is True:
            status = "enabled" if state else "disabled"
            await ctx.send(f"🔀 Shuffle {status}!")
        else:
            await ctx.send("❌ Failed to change shuffle state. Make sure you have an active device.")
    
    @commands.command(name="spotify_repeat", aliases=["srepeat"])
    async def repeat(self, ctx, mode: str = None):
        """Change Spotify repeat mode"""
        if not await self.ensure_token_valid(ctx.author.id):
            await ctx.send("❌ You need to connect your Spotify account first! Use `!spotify login`")
            return
            
        if mode is None:
            # Get current repeat state
            playback = await self.get_current_playback(ctx.author.id)
            if not playback or 'repeat_state' not in playback:
                await ctx.send("❌ No active playback found!")
                return
                
            current_mode = playback['repeat_state']
            
            if current_mode == "off":
                emoji = "❌"
            elif current_mode == "track":
                emoji = "🔂"
            elif current_mode == "context":
                emoji = "🔁"
            else:
                emoji = "❓"
                
            await ctx.send(f"{emoji} Current Spotify repeat mode: **{current_mode}**")
            await ctx.send("Available modes: `off`, `track`, `context` (playlist/album)")
            return
            
        # Valid repeat states
        valid_modes = ["off", "track", "context"]
        
        if mode.lower() not in valid_modes:
            await ctx.send("❌ Invalid repeat mode! Valid options: `off`, `track`, `context` (playlist/album)")
            return
            
        user_id = str(ctx.author.id)
        access_token = self.user_tokens[user_id]['access_token']
        
        result = await self.spotify_api.make_api_request(
            access_token,
            f"me/player/repeat?state={mode.lower()}",
            method="PUT"
        )
        
        if result is True:
            if mode.lower() == "off":
                emoji = "❌"
            elif mode.lower() == "track":
                emoji = "🔂"
            else:  # context
                emoji = "🔁"
                
            await ctx.send(f"{emoji} Spotify repeat mode set to: **{mode.lower()}**")
        else:
            await ctx.send("❌ Failed to change repeat mode. Make sure you have an active premium account.")
    
    @commands.command(name="like")
    async def like(self, ctx):
        """Like your current playing song on Spotify"""
        if not await self.ensure_token_valid(ctx.author.id):
            await ctx.send("❌ You need to connect your Spotify account first! Use `!spotify login`")
            return
            
        # Get current playback
        playback = await self.get_current_playback(ctx.author.id)
        if not playback or 'item' not in playback:
            await ctx.send("❌ No track currently playing!")
            return
            
        track_id = playback['item']['id']
        track_name = playback['item']['name']
        artist_name = playback['item']['artists'][0]['name']
        
        user_id = str(ctx.author.id)
        access_token = self.user_tokens[user_id]['access_token']
        
        result = await self.spotify_api.make_api_request(
            access_token,
            f"me/tracks?ids={track_id}",
            method="PUT"
        )
        
        if result is True:
            await ctx.send(f"❤️ Liked: **{track_name}** by **{artist_name}**")
        else:
            await ctx.send("❌ Failed to like the track.")
    
    @commands.command(name="unlike")
    async def unlike(self, ctx):
        """Unlike your current playing song on Spotify"""
        if not await self.ensure_token_valid(ctx.author.id):
            await ctx.send("❌ You need to connect your Spotify account first! Use `!spotify login`")
            return
            
        # Get current playback
        playback = await self.get_current_playback(ctx.author.id)
        if not playback or 'item' not in playback:
            await ctx.send("❌ No track currently playing!")
            return
            
        track_id = playback['item']['id']
        track_name = playback['item']['name']
        artist_name = playback['item']['artists'][0]['name']
        
        user_id = str(ctx.author.id)
        access_token = self.user_tokens[user_id]['access_token']
        
        result = await self.spotify_api.make_api_request(
            access_token,
            f"me/tracks?ids={track_id}",
            method="DELETE"
        )
        
        if result is True:
            await ctx.send(f"💔 Removed from liked tracks: **{track_name}** by **{artist_name}**")
        else:
            await ctx.send("❌ Failed to unlike the track.")
    
    @commands.command(name="toptracks")
    async def toptracks(self, ctx, limit: int = 5):
        """View your current top tracks"""
        if not await self.ensure_token_valid(ctx.author.id):
            await ctx.send("❌ You need to connect your Spotify account first! Use `!spotify login`")
            return
            
        # Ensure limit is within valid range
        limit = min(50, max(1, limit))
        
        user_id = str(ctx.author.id)
        access_token = self.user_tokens[user_id]['access_token']
        
        params = {
            'limit': limit,
            'time_range': 'medium_term'  # Options: short_term, medium_term, long_term
        }
        
        results = await self.spotify_api.make_api_request(
            access_token,
            "me/top/tracks",
            params=params
        )
        
        if not results or 'items' not in results or not results['items']:
            await ctx.send("❌ No top tracks found!")
            return
            
        embed = discord.Embed(
            title=f"{ctx.author.display_name}'s Top Tracks",
            color=discord.Color.green()
        )
        
        for i, track in enumerate(results['items'], 1):
            name = track['name']
            artists = ", ".join([artist['name'] for artist in track['artists']])
            album = track['album']['name']
            url = track['external_urls']['spotify']
            
            embed.add_field(
                name=f"{i}. {name}",
                value=f"**Artist:** {artists}\n**Album:** {album}\n[Open in Spotify]({url})",
                inline=False
            )
            
        embed.set_thumbnail(url="https://upload.wikimedia.org/wikipedia/commons/thumb/1/19/Spotify_logo_without_text.svg/1024px-Spotify_logo_without_text.svg.png")
        embed.set_footer(text="Spotify", icon_url=ctx.author.display_avatar.url)
        
        await ctx.send(embed=embed)
    
    @commands.command(name="topartists")
    async def topartists(self, ctx, limit: int = 5):
        """View your current top artists"""
        if not await self.ensure_token_valid(ctx.author.id):
            await ctx.send("❌ You need to connect your Spotify account first! Use `!spotify login`")
            return
            
        # Ensure limit is within valid range
        limit = min(50, max(1, limit))
        
        user_id = str(ctx.author.id)
        access_token = self.user_tokens[user_id]['access_token']
        
        params = {
            'limit': limit,
            'time_range': 'medium_term'  # Options: short_term, medium_term, long_term
        }
        
        results = await self.spotify_api.make_api_request(
            access_token,
            "me/top/artists",
            params=params
        )
        
        if not results or 'items' not in results or not results['items']:
            await ctx.send("❌ No top artists found!")
            return
            
        embed = discord.Embed(
            title=f"{ctx.author.display_name}'s Top Artists",
            color=discord.Color.green()
        )
        
        for i, artist in enumerate(results['items'], 1):
            name = artist['name']
            genres = ", ".join(artist['genres'][:3]) if artist['genres'] else "No genres listed"
            popularity = artist['popularity']
            url = artist['external_urls']['spotify']
            
            embed.add_field(
                name=f"{i}. {name}",
                value=f"**Genres:** {genres}\n**Popularity:** {popularity}/100\n[Open in Spotify]({url})",
                inline=False
            )
            
            # Set the first artist's image as thumbnail
            if i == 1 and artist['images']:
                embed.set_thumbnail(url=artist['images'][0]['url'])
                
        embed.set_footer(text="Spotify", icon_url=ctx.author.display_avatar.url)
        
        await ctx.send(embed=embed)
    
    @commands.command(name="new")
    async def new(self, ctx):
        """View new releases for you"""
        if not await self.ensure_token_valid(ctx.author.id):
            await ctx.send("❌ You need to connect your Spotify account first! Use `!spotify login`")
            return
            
        user_id = str(ctx.author.id)
        access_token = self.user_tokens[user_id]['access_token']
        
        params = {
            'limit': 5,
            'country': 'US'  # This could be personalized based on user's country
        }
        
        results = await self.spotify_api.make_api_request(
            access_token,
            "browse/new-releases",
            params=params
        )
        
        if not results or 'albums' not in results or 'items' not in results['albums'] or not results['albums']['items']:
            await ctx.send("❌ No new releases found!")
            return
            
        embed = discord.Embed(
            title="New Releases on Spotify",
            color=discord.Color.green()
        )
        
        for i, album in enumerate(results['albums']['items'], 1):
            name = album['name']
            artists = ", ".join([artist['name'] for artist in album['artists']])
            release_date = album['release_date']
            url = album['external_urls']['spotify']
            
            embed.add_field(
                name=f"{i}. {name}",
                value=f"**Artist:** {artists}\n**Released:** {release_date}\n[Open in Spotify]({url})",
                inline=False
            )
            
            # Set the first album's image as thumbnail
            if i == 1 and album['images']:
                embed.set_thumbnail(url=album['images'][0]['url'])
                
        embed.set_footer(text="Spotify", icon_url=ctx.author.display_avatar.url)
        
        await ctx.send(embed=embed)
        
async def setup(bot):
    await bot.add_cog(Spotify(bot)) 