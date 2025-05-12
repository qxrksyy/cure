"""
LastFM Commands Documentation

This file contains documentation for LastFM commands to be used with the help system.
"""

LASTFM_COMMANDS = {
    "nowplaying": {
        "description": "Shows your current song or another user's current song playing from Last.fm",
        "usage": "!lastfm nowplaying [member]",
        "aliases": ["np", "fm"],
        "examples": ["!lastfm nowplaying", "!fm", "!np @user"],
        "arguments": ["member"],
        "permissions": "None",
        "category": "lastfm"
    },
    "taste": {
        "description": "Compare your music taste between you and someone else",
        "usage": "!lastfm taste <member> [period]",
        "examples": ["!lastfm taste @user", "!lastfm taste @user 3month"],
        "arguments": ["member", "period"],
        "permissions": "None",
        "category": "lastfm"
    },
    "wktrack": {
        "description": "View the top listeners for a track",
        "usage": "!lastfm wktrack <track>",
        "examples": ["!lastfm wktrack Bohemian Rhapsody", "!lastfm wktrack 'Never Gonna Give You Up'"],
        "arguments": ["track"],
        "permissions": "None",
        "category": "lastfm"
    },
    "globalwhoknows": {
        "description": "View the top listeners for an artist globally",
        "usage": "!lastfm globalwhoknows <artist>",
        "aliases": ["gwk"],
        "examples": ["!lastfm globalwhoknows Queen", "!gwk 'The Beatles'"],
        "arguments": ["artist"],
        "permissions": "None",
        "category": "lastfm"
    },
    "itunes": {
        "description": "Gives iTunes link for the current song playing",
        "usage": "!lastfm itunes [member]",
        "examples": ["!lastfm itunes", "!lastfm itunes @user"],
        "arguments": ["member"],
        "permissions": "None",
        "category": "lastfm"
    },
    "color": {
        "description": "Set a custom now playing embed color",
        "usage": "!lastfm color <color>",
        "examples": ["!lastfm color #FF5733", "!lastfm color red"],
        "arguments": ["color"],
        "permissions": "None",
        "category": "lastfm"
    },
    "recent": {
        "description": "View your recent tracks",
        "usage": "!lastfm recent [member]",
        "examples": ["!lastfm recent", "!lastfm recent @user"],
        "arguments": ["member"],
        "permissions": "None",
        "category": "lastfm"
    },
    "spotify": {
        "description": "Gives Spotify link for the current song playing",
        "usage": "!lastfm spotify [member]",
        "examples": ["!lastfm spotify", "!lastfm spotify @user"],
        "arguments": ["member"],
        "permissions": "None",
        "category": "lastfm"
    },
    "customreactions": {
        "description": "Set a custom upvote and downvote reaction",
        "usage": "!lastfm customreactions <upvote> <downvote>",
        "examples": ["!lastfm customreactions 👍 👎", "!lastfm customreactions ❤️ 💔"],
        "arguments": ["upvote", "downvote"],
        "permissions": "Send Messages, Donator",
        "category": "lastfm"
    },
    "soundcloud": {
        "description": "Gives Soundcloud link for the current song playing",
        "usage": "!lastfm soundcloud [member]",
        "examples": ["!lastfm soundcloud", "!lastfm soundcloud @user"],
        "arguments": ["member"],
        "permissions": "None",
        "category": "lastfm"
    },
    "topalbums": {
        "description": "View your overall top albums",
        "usage": "!lastfm topalbums [member] [timeframe]",
        "aliases": ["tal"],
        "examples": ["!lastfm topalbums", "!tal @user 3month"],
        "arguments": ["member", "timeframe"],
        "permissions": "None",
        "category": "lastfm"
    },
    "collage": {
        "description": "Generate a collage out of your most listened artists in a timeperiod",
        "usage": "!lastfm collage [flags]",
        "examples": ["!lastfm collage 3x3", "!lastfm collage 4x4 --albums 6month"],
        "arguments": ["flags"],
        "permissions": "None",
        "category": "lastfm"
    },
    "topartists": {
        "description": "View your overall top artists",
        "usage": "!lastfm topartists [member] [timeframe]",
        "aliases": ["tar"],
        "examples": ["!lastfm topartists", "!tar @user 3month"],
        "arguments": ["member", "timeframe"],
        "permissions": "None",
        "category": "lastfm"
    },
    "toptracks": {
        "description": "View your overall top tracks",
        "usage": "!lastfm toptracks [member] [timeframe]",
        "aliases": ["tt"],
        "examples": ["!lastfm toptracks", "!tt @user 3month"],
        "arguments": ["member", "timeframe"],
        "permissions": "None",
        "category": "lastfm"
    },
    "login": {
        "description": "Login and authenticate coffin to use your account",
        "usage": "!lastfm login",
        "examples": ["!lastfm login"],
        "arguments": ["none"],
        "permissions": "None",
        "category": "lastfm"
    },
    "whoknows": {
        "description": "View the top listeners for an artist",
        "usage": "!lastfm whoknows <artist>",
        "aliases": ["wk"],
        "examples": ["!lastfm whoknows Queen", "!wk 'The Beatles'"],
        "arguments": ["artist"],
        "permissions": "None",
        "category": "lastfm"
    },
    "logout": {
        "description": "Remove your Last.fm account with coffin's internal system",
        "usage": "!lastfm logout",
        "examples": ["!lastfm logout"],
        "arguments": ["none"],
        "permissions": "None",
        "category": "lastfm"
    },
    "favorites": {
        "description": "View yours or a member's liked tracks",
        "usage": "!lastfm favorites [member]",
        "aliases": ["favs"],
        "examples": ["!lastfm favorites", "!lastfm favorites @user"],
        "arguments": ["member"],
        "permissions": "None",
        "category": "lastfm"
    },
    "crowns": {
        "description": "View your crowns",
        "usage": "!lastfm crowns [member]",
        "examples": ["!lastfm crowns", "!lastfm crowns @user"],
        "arguments": ["member"],
        "permissions": "None",
        "category": "lastfm"
    },
    "globalwkalbum": {
        "description": "View the top listeners for an album globally",
        "usage": "!lastfm globalwkalbum <album>",
        "aliases": ["gwka"],
        "examples": ["!lastfm globalwkalbum 'A Night at the Opera'", "!gwka 'Abbey Road'"],
        "arguments": ["album"],
        "permissions": "None",
        "category": "lastfm"
    },
    "customcommand": {
        "description": "Set your own custom Now Playing command",
        "usage": "!lastfm customcommand <command>",
        "examples": ["!lastfm customcommand !np"],
        "arguments": ["command"],
        "permissions": "None",
        "category": "lastfm"
    },
    "customcommand remove": {
        "description": "Remove a custom command for a member",
        "usage": "!lastfm customcommand remove <member>",
        "examples": ["!lastfm customcommand remove @user"],
        "arguments": ["member"],
        "permissions": "Manage Guild",
        "category": "lastfm"
    },
    "customcommand public": {
        "description": "Toggle public flag for a custom command",
        "usage": "!lastfm customcommand public <substring>",
        "examples": ["!lastfm customcommand public np"],
        "arguments": ["substring"],
        "permissions": "Manage Guild",
        "category": "lastfm"
    },
    "customcommand reset": {
        "description": "Resets all custom commands",
        "usage": "!lastfm customcommand reset",
        "examples": ["!lastfm customcommand reset"],
        "arguments": ["none"],
        "permissions": "Manage Guild",
        "category": "lastfm"
    },
    "customcommand list": {
        "description": "View list of custom commands for NP",
        "usage": "!lastfm customcommand list",
        "examples": ["!lastfm customcommand list"],
        "arguments": ["none"],
        "permissions": "Manage Guild",
        "category": "lastfm"
    },
    "customcommand blacklist": {
        "description": "Blacklist users their own Now Playing command",
        "usage": "!lastfm customcommand blacklist <member>",
        "examples": ["!lastfm customcommand blacklist @user"],
        "arguments": ["member"],
        "permissions": "Manage Guild",
        "category": "lastfm"
    },
    "customcommand blacklist list": {
        "description": "View list of blacklisted custom command users for NP",
        "usage": "!lastfm customcommand blacklist list",
        "examples": ["!lastfm customcommand blacklist list"],
        "arguments": ["none"],
        "permissions": "Manage Guild",
        "category": "lastfm"
    },
    "customcommand cleanup": {
        "description": "Clean up custom commands from absent members",
        "usage": "!lastfm customcommand cleanup",
        "examples": ["!lastfm customcommand cleanup"],
        "arguments": ["none"],
        "permissions": "Administrator",
        "category": "lastfm"
    },
    "mode": {
        "description": "Use a different embed for NP or create your own",
        "usage": "!lastfm mode <type|or|or|embed|code>",
        "examples": ["!lastfm mode nightly", "!lastfm mode custom"],
        "arguments": ["type or or or embed or code"],
        "permissions": "Send Messages, Donator",
        "category": "lastfm"
    },
    "update": {
        "description": "Refresh your local Last.fm library",
        "usage": "!lastfm update",
        "examples": ["!lastfm update"],
        "arguments": ["none"],
        "permissions": "None",
        "category": "lastfm"
    },
    "globalwktrack": {
        "description": "View the top listeners for a track globally",
        "usage": "!lastfm globalwktrack <track>",
        "aliases": ["gwkt"],
        "examples": ["!lastfm globalwktrack 'Bohemian Rhapsody'", "!gwkt 'Yesterday'"],
        "arguments": ["track"],
        "permissions": "None",
        "category": "lastfm"
    },
    "youtube": {
        "description": "Gives YouTube link for the current song playing",
        "usage": "!lastfm youtube [member]",
        "examples": ["!lastfm youtube", "!lastfm youtube @user"],
        "arguments": ["member"],
        "permissions": "None",
        "category": "lastfm"
    },
    "wkalbum": {
        "description": "View the top listeners for an album",
        "usage": "!lastfm wkalbum <album>",
        "examples": ["!lastfm wkalbum 'A Night at the Opera'", "!lastfm wkalbum 'Abbey Road'"],
        "arguments": ["album"],
        "permissions": "None",
        "category": "lastfm"
    }
}

# Additional music-related commands outside of the lastfm group
MUSIC_COMMANDS = {
    "spotifyalbum": {
        "description": "Finds album results from the Spotify API",
        "usage": "!spotifyalbum <query>",
        "examples": ["!spotifyalbum Dark Side of the Moon", "!spotifyalbum 'Abbey Road'"],
        "arguments": ["query"],
        "permissions": "None",
        "category": "music"
    },
    "spotifytrack": {
        "description": "Finds track results from the Spotify API",
        "usage": "!spotifytrack <query>",
        "examples": ["!spotifytrack Bohemian Rhapsody", "!spotifytrack 'Yesterday'"],
        "arguments": ["query"],
        "permissions": "None",
        "category": "music"
    },
    "itunes": {
        "description": "Finds a song from the iTunes API",
        "usage": "!itunes <query>",
        "examples": ["!itunes Bohemian Rhapsody", "!itunes 'Yesterday'"],
        "arguments": ["query"],
        "permissions": "None",
        "category": "music"
    }
}

async def setup(bot):
    # This is a documentation module, no cog to add
    pass 