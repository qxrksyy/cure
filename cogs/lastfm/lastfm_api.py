import aiohttp
import os
import logging
import datetime
import json
from urllib.parse import quote

logger = logging.getLogger('bot')

class LastFMAPI:
    """Client for the Last.fm API"""
    
    def __init__(self):
        self.api_key = os.getenv("LASTFM_API_KEY")
        self.api_secret = os.getenv("LASTFM_API_SECRET")
        self.base_url = "http://ws.audioscrobbler.com/2.0/"
        self.user_agent = "QxrkBot/1.0"
        self.headers = {
            "User-Agent": self.user_agent
        }
    
    async def make_request(self, method, params=None):
        """Make a request to the Last.fm API"""
        if params is None:
            params = {}
            
        params.update({
            "method": method,
            "api_key": self.api_key,
            "format": "json"
        })
        
        async with aiohttp.ClientSession(headers=self.headers) as session:
            try:
                async with session.get(self.base_url, params=params) as response:
                    if response.status != 200:
                        logger.error(f"Last.fm API error: {response.status} - {await response.text()}")
                        return None
                    
                    return await response.json()
            except Exception as e:
                logger.error(f"Error making Last.fm API request: {e}")
                return None
    
    async def get_user_info(self, username):
        """Get information about a Last.fm user"""
        params = {"user": username}
        return await self.make_request("user.getInfo", params)
    
    async def get_recent_tracks(self, username, limit=10):
        """Get a user's recent tracks"""
        params = {
            "user": username,
            "limit": limit
        }
        return await self.make_request("user.getRecentTracks", params)
    
    async def get_now_playing(self, username):
        """Get a user's currently playing track"""
        params = {
            "user": username,
            "limit": 1
        }
        response = await self.make_request("user.getRecentTracks", params)
        
        if not response or "recenttracks" not in response:
            return None
        
        tracks = response["recenttracks"].get("track", [])
        if not tracks:
            return None
        
        # Last.fm returns a list or a single track if there's only one result
        track = tracks[0] if isinstance(tracks, list) else tracks
        
        # Check if the track is currently playing
        if isinstance(track, dict) and "@attr" in track and "nowplaying" in track["@attr"]:
            return {
                "artist": track.get("artist", {}).get("#text", "Unknown Artist"),
                "track": track.get("name", "Unknown Track"),
                "album": track.get("album", {}).get("#text", "Unknown Album"),
                "image": self._get_largest_image(track.get("image", [])),
                "url": track.get("url", ""),
                "now_playing": True
            }
            
        # Return the most recent track if it's not playing now
        if isinstance(track, dict):
            return {
                "artist": track.get("artist", {}).get("#text", "Unknown Artist"),
                "track": track.get("name", "Unknown Track"),
                "album": track.get("album", {}).get("#text", "Unknown Album"),
                "image": self._get_largest_image(track.get("image", [])),
                "url": track.get("url", ""),
                "now_playing": False,
                "date": track.get("date", {}).get("#text", "Unknown Date")
            }
            
        return None
    
    async def get_top_artists(self, username, period="overall", limit=10):
        """Get a user's top artists"""
        params = {
            "user": username,
            "period": period,
            "limit": limit
        }
        return await self.make_request("user.getTopArtists", params)
    
    async def get_top_albums(self, username, period="overall", limit=10):
        """Get a user's top albums"""
        params = {
            "user": username,
            "period": period,
            "limit": limit
        }
        return await self.make_request("user.getTopAlbums", params)
    
    async def get_top_tracks(self, username, period="overall", limit=10):
        """Get a user's top tracks"""
        params = {
            "user": username,
            "period": period,
            "limit": limit
        }
        return await self.make_request("user.getTopTracks", params)
    
    async def get_artist_info(self, artist, username=None):
        """Get information about an artist"""
        params = {
            "artist": artist,
        }
        
        if username:
            params["username"] = username
            
        return await self.make_request("artist.getInfo", params)
    
    async def get_track_info(self, artist, track, username=None):
        """Get information about a track"""
        params = {
            "artist": artist,
            "track": track
        }
        
        if username:
            params["username"] = username
            
        return await self.make_request("track.getInfo", params)
    
    async def get_album_info(self, artist, album, username=None):
        """Get information about an album"""
        params = {
            "artist": artist,
            "album": album
        }
        
        if username:
            params["username"] = username
            
        return await self.make_request("album.getInfo", params)
    
    async def get_artist_top_tracks(self, artist, limit=10):
        """Get an artist's top tracks"""
        params = {
            "artist": artist,
            "limit": limit
        }
        return await self.make_request("artist.getTopTracks", params)
    
    async def search_artist(self, artist, limit=10):
        """Search for an artist"""
        params = {
            "artist": artist,
            "limit": limit
        }
        return await self.make_request("artist.search", params)
    
    async def search_track(self, track, limit=10):
        """Search for a track"""
        params = {
            "track": track,
            "limit": limit
        }
        return await self.make_request("track.search", params)
    
    async def search_album(self, album, limit=10):
        """Search for an album"""
        params = {
            "album": album,
            "limit": limit
        }
        return await self.make_request("album.search", params)
    
    async def get_artist_correction(self, artist):
        """Get a corrected artist name"""
        params = {
            "artist": artist
        }
        return await self.make_request("artist.getCorrection", params)
    
    async def get_spotify_link(self, artist, track):
        """Search for a Spotify link for a track
        Note: Last.fm API doesn't directly provide Spotify links, so we need to use the Spotify API for this.
        This is just a placeholder method."""
        # Spotify API integration would go here
        return f"https://open.spotify.com/search/{quote(f'{artist} {track}')}"
    
    async def get_youtube_link(self, artist, track):
        """Search for a YouTube link for a track
        Note: Last.fm API doesn't directly provide YouTube links, so we need to make a search link.
        This is just a placeholder method."""
        return f"https://www.youtube.com/results?search_query={quote(f'{artist} {track}')}"
    
    async def get_itunes_link(self, artist, track):
        """Search for an iTunes link for a track
        Note: Last.fm API doesn't directly provide iTunes links, so we need to make a search link.
        This is just a placeholder method."""
        return f"https://music.apple.com/search?term={quote(f'{artist} {track}')}"
    
    async def get_soundcloud_link(self, artist, track):
        """Search for a SoundCloud link for a track
        Note: Last.fm API doesn't directly provide SoundCloud links, so we need to make a search link.
        This is just a placeholder method."""
        return f"https://soundcloud.com/search?q={quote(f'{artist} {track}')}"
    
    def format_period(self, period):
        """Format a time period string to a Last.fm API period string"""
        period = period.lower()
        
        if period in ["day", "1day", "24h", "24hours"]:
            return "7day"  # Last.fm's minimum period
        elif period in ["week", "7day", "7days"]:
            return "7day"
        elif period in ["month", "1month", "30days", "30day"]:
            return "1month"
        elif period in ["3month", "3months", "90days", "90day"]:
            return "3month"
        elif period in ["6month", "6months", "180days", "180day"]:
            return "6month"
        elif period in ["year", "1year", "12months", "12month", "365days", "365day"]:
            return "12month"
        else:
            return "overall"

    def _get_largest_image(self, images):
        """Get the largest image URL from a list of Last.fm images"""
        if not images or not isinstance(images, list):
            return None
            
        for size in ["extralarge", "large", "medium", "small"]:
            for image in images:
                if image.get("size") == size and image.get("#text"):
                    return image.get("#text")
                    
        # If no sizes matched, try to get any valid image
        for image in images:
            if image.get("#text"):
                return image.get("#text")
                
        return None 

async def setup(bot):
    # This is an API wrapper, no cog to add
    pass 