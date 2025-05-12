"""
SoundCloud Commands Documentation

This file contains documentation for SoundCloud commands to be used with the help system.
"""

SOUNDCLOUD_COMMANDS = {
    "soundcloud": {
        "description": "Search and play SoundCloud tracks directly in voice channels",
        "usage": "!soundcloud <query>",
        "aliases": ["sc"],
        "examples": ["!soundcloud lofi beats", "!sc electronic music"],
        "arguments": ["query"],
        "permissions": "None",
        "category": "soundcloud"
    },
    "scplay": {
        "description": "Play a SoundCloud track from URL or search query",
        "usage": "!scplay <url_or_query>",
        "examples": ["!scplay https://soundcloud.com/artist/track", "!scplay lofi beats"],
        "arguments": ["url_or_query"],
        "permissions": "None",
        "category": "soundcloud"
    },
    "scnext": {
        "description": "Skip to the next SoundCloud track in the queue",
        "usage": "!scnext",
        "examples": ["!scnext"],
        "arguments": ["none"],
        "permissions": "None",
        "category": "soundcloud"
    },
    "scstop": {
        "description": "Stop playing SoundCloud tracks and clear the queue",
        "usage": "!scstop",
        "examples": ["!scstop"],
        "arguments": ["none"],
        "permissions": "None",
        "category": "soundcloud"
    },
    "scpause": {
        "description": "Pause the currently playing SoundCloud track",
        "usage": "!scpause",
        "examples": ["!scpause"],
        "arguments": ["none"],
        "permissions": "None",
        "category": "soundcloud"
    },
    "scresume": {
        "description": "Resume the paused SoundCloud track",
        "usage": "!scresume",
        "examples": ["!scresume"],
        "arguments": ["none"],
        "permissions": "None",
        "category": "soundcloud"
    },
    "scqueue": {
        "description": "View the SoundCloud track queue",
        "usage": "!scqueue",
        "examples": ["!scqueue"],
        "arguments": ["none"],
        "permissions": "None",
        "category": "soundcloud"
    },
    "scvolume": {
        "description": "Set the volume for SoundCloud playback",
        "usage": "!scvolume <volume>",
        "examples": ["!scvolume 50", "!scvolume 75"],
        "arguments": ["volume"],
        "permissions": "None",
        "category": "soundcloud"
    },
    "scnotify": {
        "description": "Set up notifications for when an artist uploads new tracks",
        "usage": "!scnotify <artist_url> [channel]",
        "examples": ["!scnotify https://soundcloud.com/artist", "!scnotify https://soundcloud.com/artist #announcements"],
        "arguments": ["artist_url", "channel"],
        "permissions": "Manage Guild",
        "category": "soundcloud"
    },
    "scnotify list": {
        "description": "List all SoundCloud artist notifications for this server",
        "usage": "!scnotify list",
        "examples": ["!scnotify list"],
        "arguments": ["none"],
        "permissions": "None",
        "category": "soundcloud"
    },
    "scnotify remove": {
        "description": "Remove SoundCloud artist notifications",
        "usage": "!scnotify remove <artist_url>",
        "examples": ["!scnotify remove https://soundcloud.com/artist"],
        "arguments": ["artist_url"],
        "permissions": "Manage Guild",
        "category": "soundcloud"
    },
    "soundcloud_list": {
        "description": "View all SoundCloud stream notifications",
        "usage": "!soundcloud list",
        "examples": ["!soundcloud list"],
        "arguments": ["none"],
        "permissions": "Manage Guild",
        "category": "soundcloud"
    },
    "soundcloud_remove": {
        "description": "Remove feed for new SoundCloud posts",
        "usage": "!soundcloud remove <channel> <user>",
        "examples": ["!soundcloud remove #notifications artist123"],
        "arguments": ["channel", "user"],
        "permissions": "Manage Channels",
        "category": "soundcloud"
    },
    "soundcloud_message": {
        "description": "Set a message for SoundCloud notifications",
        "usage": "!soundcloud message <username> <message>",
        "examples": ["!soundcloud message artist123 Check out this new track!"],
        "arguments": ["username", "message"],
        "permissions": "Manage Guild",
        "category": "soundcloud"
    },
    "soundcloud_message_view": {
        "description": "View SoundCloud message for new posts",
        "usage": "!soundcloud message view <username>",
        "examples": ["!soundcloud message view artist123"],
        "arguments": ["username"],
        "permissions": "Manage Guild",
        "category": "soundcloud"
    },
    "soundcloud_add": {
        "description": "Add stream notifications to channel",
        "usage": "!soundcloud add <channel> <username>",
        "examples": ["!soundcloud add #notifications artist123"],
        "arguments": ["channel", "username"],
        "permissions": "Manage Guild",
        "category": "soundcloud"
    }
}

async def setup(bot):
    # This is a documentation module, no cog to add
    pass 