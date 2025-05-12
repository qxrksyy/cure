"""
Spotify Commands Documentation

This file contains documentation for Spotify commands to be used with the help system.
"""

SPOTIFY_COMMANDS = {
    "spotify": {
        "description": "Connect to your Spotify account",
        "usage": "!spotify",
        "examples": ["!spotify"],
        "arguments": ["none"],
        "permissions": "None",
        "category": "spotify"
    },
    "nowplaying": {
        "description": "Show what you're currently playing on Spotify",
        "usage": "!nowplaying",
        "aliases": ["np"],
        "examples": ["!nowplaying", "!np"],
        "arguments": ["none"],
        "permissions": "None",
        "category": "spotify"
    },
    "spotify_volume": {
        "description": "Adjust current player volume",
        "usage": "!spotify_volume [volume]",
        "aliases": ["svolume"],
        "examples": ["!spotify_volume 50", "!svolume 75"],
        "arguments": ["volume"],
        "permissions": "None",
        "category": "spotify"
    },
    "play": {
        "description": "Play, resume or queue a track on Spotify",
        "usage": "!play [track]",
        "examples": ["!play", "!play Never Gonna Give You Up"],
        "arguments": ["track"],
        "permissions": "None",
        "category": "spotify"
    },
    "pause": {
        "description": "Pause your Spotify playback",
        "usage": "!pause",
        "examples": ["!pause"],
        "arguments": ["none"],
        "permissions": "None",
        "category": "spotify"
    },
    "skip": {
        "description": "Skip to the next track on Spotify",
        "usage": "!skip",
        "examples": ["!skip"],
        "arguments": ["none"],
        "permissions": "None",
        "category": "spotify"
    },
    "previous": {
        "description": "Go back to the previous track on Spotify",
        "usage": "!previous",
        "aliases": ["prev"],
        "examples": ["!previous", "!prev"],
        "arguments": ["none"],
        "permissions": "None",
        "category": "spotify"
    },
    "queue": {
        "description": "Show your Spotify queue",
        "usage": "!queue",
        "aliases": ["q"],
        "examples": ["!queue", "!q"],
        "arguments": ["none"],
        "permissions": "None",
        "category": "spotify"
    },
    "devices": {
        "description": "List your available Spotify devices",
        "usage": "!devices",
        "examples": ["!devices"],
        "arguments": ["none"],
        "permissions": "None",
        "category": "spotify"
    },
    "connect": {
        "description": "Connect to a specific Spotify device",
        "usage": "!connect <device_id>",
        "examples": ["!connect 1"],
        "arguments": ["device_id"],
        "permissions": "None",
        "category": "spotify"
    },
    "repeat": {
        "description": "Set repeat mode on Spotify",
        "usage": "!repeat <mode>",
        "examples": ["!repeat track", "!repeat playlist", "!repeat off"],
        "arguments": ["mode"],
        "permissions": "None",
        "category": "spotify"
    },
    "shuffle": {
        "description": "Toggle shuffle mode on Spotify",
        "usage": "!shuffle [on|off]",
        "examples": ["!shuffle", "!shuffle on", "!shuffle off"],
        "arguments": ["setting"],
        "permissions": "None",
        "category": "spotify"
    },
    "search": {
        "description": "Search for tracks on Spotify",
        "usage": "!search <query>",
        "examples": ["!search Never Gonna Give You Up"],
        "arguments": ["query"],
        "permissions": "None",
        "category": "spotify"
    }
}

async def setup(bot):
    # This is a documentation module, no cog to add
    pass 