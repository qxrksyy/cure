"""
Music Commands Documentation

This file contains documentation for music commands to be used with the help system.
"""

MUSIC_COMMANDS = {
    "connect": {
        "description": "Connect the bot to a voice channel",
        "usage": "!connect [channel]",
        "examples": ["!connect", "!connect General"],
        "arguments": ["channel"],
        "permissions": "None",
        "category": "music"
    },
    "play": {
        "description": "Play a song from YouTube, Spotify, or SoundCloud",
        "usage": "!play <song>",
        "examples": ["!play https://www.youtube.com/watch?v=dQw4w9WgXcQ", "!play Never Gonna Give You Up"],
        "arguments": ["song"],
        "permissions": "None",
        "category": "music"
    },
    "pause": {
        "description": "Pause the currently playing song",
        "usage": "!pause",
        "examples": ["!pause"],
        "arguments": ["none"],
        "permissions": "DJ",
        "category": "music"
    },
    "resume": {
        "description": "Resume the paused song",
        "usage": "!resume",
        "examples": ["!resume"],
        "arguments": ["none"],
        "permissions": "DJ",
        "category": "music"
    },
    "skip": {
        "description": "Skip the current song",
        "usage": "!skip",
        "examples": ["!skip"],
        "arguments": ["none"],
        "permissions": "DJ",
        "category": "music"
    },
    "stop": {
        "description": "Stop the music and clear the queue",
        "usage": "!stop",
        "examples": ["!stop"],
        "arguments": ["none"],
        "permissions": "DJ",
        "category": "music"
    },
    "nowplaying": {
        "description": "Show the currently playing song",
        "usage": "!nowplaying",
        "aliases": ["np"],
        "examples": ["!nowplaying", "!np"],
        "arguments": ["none"],
        "permissions": "None",
        "category": "music"
    },
    "queue": {
        "description": "View the current music queue",
        "usage": "!queue [page]",
        "aliases": ["q"],
        "examples": ["!queue", "!q", "!queue 2"],
        "arguments": ["page"],
        "permissions": "None",
        "category": "music"
    },
    "clear": {
        "description": "Clear the music queue",
        "usage": "!clear",
        "examples": ["!clear"],
        "arguments": ["none"],
        "permissions": "DJ",
        "category": "music"
    },
    "remove": {
        "description": "Remove a song from the queue",
        "usage": "!remove <position>",
        "examples": ["!remove 3"],
        "arguments": ["position"],
        "permissions": "DJ",
        "category": "music"
    },
    "volume": {
        "description": "Change the volume of the bot",
        "usage": "!volume <level>",
        "examples": ["!volume 50"],
        "arguments": ["level"],
        "permissions": "DJ",
        "category": "music"
    },
    "loop": {
        "description": "Loop the current song or queue",
        "usage": "!loop <mode>",
        "examples": ["!loop song", "!loop queue", "!loop off"],
        "arguments": ["mode"],
        "permissions": "DJ",
        "category": "music"
    },
    "shuffle": {
        "description": "Shuffle the music queue",
        "usage": "!shuffle",
        "examples": ["!shuffle"],
        "arguments": ["none"],
        "permissions": "DJ",
        "category": "music"
    },
    "seek": {
        "description": "Seek to a specific point in the current song",
        "usage": "!seek <time>",
        "examples": ["!seek 1:30", "!seek 90"],
        "arguments": ["time"],
        "permissions": "DJ",
        "category": "music"
    },
    "lyrics": {
        "description": "Get lyrics for the current song or a specific song",
        "usage": "!lyrics [song]",
        "examples": ["!lyrics", "!lyrics Never Gonna Give You Up"],
        "arguments": ["song"],
        "permissions": "None",
        "category": "music"
    },
    "spotify": {
        "description": "Play a Spotify track, album, or playlist",
        "usage": "!spotify <link>",
        "examples": ["!spotify https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT"],
        "arguments": ["link"],
        "permissions": "None",
        "category": "music"
    },
    "queue remove": {
        "description": "Remove a track from the queue by its index",
        "usage": "!queue remove <index>",
        "examples": ["!queue remove 3"],
        "arguments": ["index"],
        "permissions": "None",
        "category": "music"
    },
    "queue move": {
        "description": "Move a track to a new position in the queue",
        "usage": "!queue move <index> <new_index>",
        "examples": ["!queue move 3 1"],
        "arguments": ["index", "new_index"],
        "permissions": "None",
        "category": "music"
    },
    "repeat": {
        "description": "Change the current loop mode (off, track, queue)",
        "usage": "!repeat <option>",
        "aliases": ["loop"],
        "examples": ["!repeat off", "!repeat track", "!repeat queue"],
        "arguments": ["option"],
        "permissions": "None",
        "category": "music"
    },
    "fastforward": {
        "description": "Fast forward to a specific position in the track",
        "usage": "!fastforward <position>",
        "aliases": ["ff"],
        "examples": ["!fastforward 1:30", "!ff 2:45"],
        "arguments": ["position"],
        "permissions": "None",
        "category": "music"
    },
    "rewind": {
        "description": "Rewind to a specific position in the track",
        "usage": "!rewind <position>",
        "aliases": ["rw"],
        "examples": ["!rewind 1:30", "!rw 0:45"],
        "arguments": ["position"],
        "permissions": "None",
        "category": "music"
    },
    "preset": {
        "description": "Use a sound preset for music playback",
        "usage": "!preset [preset_name]",
        "examples": ["!preset", "!preset nightcore"],
        "arguments": ["preset_name"],
        "permissions": "None",
        "category": "music"
    },
    "preset chipmunk": {
        "description": "Accelerates track playback to produce a high-pitched, chipmunk-like sound",
        "usage": "!preset chipmunk [setting]",
        "examples": ["!preset chipmunk", "!preset chipmunk on"],
        "arguments": ["setting"],
        "permissions": "None",
        "category": "music"
    },
    "preset flat": {
        "description": "Represents a normal EQ setting with default levels across the board",
        "usage": "!preset flat [setting]",
        "examples": ["!preset flat", "!preset flat on"],
        "arguments": ["setting"],
        "permissions": "None",
        "category": "music"
    },
    "preset boost": {
        "description": "Enhances track with heightened bass and highs for a lively, energetic feel",
        "usage": "!preset boost [setting]",
        "examples": ["!preset boost", "!preset boost on"],
        "arguments": ["setting"],
        "permissions": "None",
        "category": "music"
    },
    "preset 8d": {
        "description": "Creates a stereo-like panning effect, rotating audio for immersive sound",
        "usage": "!preset 8d [setting]",
        "examples": ["!preset 8d", "!preset 8d on"],
        "arguments": ["setting"],
        "permissions": "None",
        "category": "music"
    },
    "preset active": {
        "description": "List all currently applied filters",
        "usage": "!preset active",
        "examples": ["!preset active"],
        "arguments": ["none"],
        "permissions": "None",
        "category": "music"
    },
    "preset vibrato": {
        "description": "Introduces a wavering pitch effect for dynamic tone",
        "usage": "!preset vibrato [setting]",
        "examples": ["!preset vibrato", "!preset vibrato on"],
        "arguments": ["setting"],
        "permissions": "None",
        "category": "music"
    },
    "preset vaporwave": {
        "description": "Slows track playback for nostalgic and vintage half-speed effect",
        "usage": "!preset vaporwave [setting]",
        "examples": ["!preset vaporwave", "!preset vaporwave on"],
        "arguments": ["setting"],
        "permissions": "None",
        "category": "music"
    },
    "preset metal": {
        "description": "Amplifies midrange for a fuller, concert-like sound, ideal for metal tracks",
        "usage": "!preset metal [setting]",
        "examples": ["!preset metal", "!preset metal on"],
        "arguments": ["setting"],
        "permissions": "None",
        "category": "music"
    },
    "preset karaoke": {
        "description": "Filters out vocals from the track, leaving only the instrumental",
        "usage": "!preset karaoke [setting]",
        "examples": ["!preset karaoke", "!preset karaoke on"],
        "arguments": ["setting"],
        "permissions": "None",
        "category": "music"
    },
    "preset nightcore": {
        "description": "Accelerates track playback for nightcore-style music",
        "usage": "!preset nightcore [setting]",
        "examples": ["!preset nightcore", "!preset nightcore on"],
        "arguments": ["setting"],
        "permissions": "None",
        "category": "music"
    },
    "preset piano": {
        "description": "Enhances mid and high tones for standout piano-based tracks",
        "usage": "!preset piano [setting]",
        "examples": ["!preset piano", "!preset piano on"],
        "arguments": ["setting"],
        "permissions": "None",
        "category": "music"
    },
    "preset soft": {
        "description": "Cuts high and mid frequencies, allowing only low frequencies",
        "usage": "!preset soft [setting]",
        "examples": ["!preset soft", "!preset soft on"],
        "arguments": ["setting"],
        "permissions": "None",
        "category": "music"
    },
    "disconnect": {
        "description": "Disconnect the bot from the voice channel",
        "usage": "!disconnect",
        "aliases": ["dc", "leave"],
        "examples": ["!disconnect", "!dc"],
        "arguments": ["none"],
        "permissions": "None",
        "category": "music"
    }
}

async def setup(bot):
    # This is a documentation module, no cog to add
    pass 