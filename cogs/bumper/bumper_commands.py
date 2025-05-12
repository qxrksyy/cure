"""
BumpReminder Commands Documentation

This file contains documentation for BumpReminder commands to be used with the help system.
"""

BUMPER_COMMANDS = {
    "bumpreminder": {
        "description": "Get reminders to /bump your server on Disboard!",
        "usage": "!bumpreminder",
        "examples": ["!bumpreminder"],
        "arguments": ["none"],
        "permissions": "Manage Channels",
        "category": "bumper"
    },
    "bumpreminder autoclean": {
        "description": "Automatically delete messages that aren't /bump",
        "usage": "!bumpreminder autoclean <choice>",
        "examples": ["!bumpreminder autoclean on", "!bumpreminder autoclean off"],
        "arguments": ["choice"],
        "permissions": "Manage Channels",
        "category": "bumper"
    },
    "bumpreminder config": {
        "description": "View server configuration for Bump Reminder",
        "usage": "!bumpreminder config",
        "examples": ["!bumpreminder config"],
        "arguments": ["none"],
        "permissions": "Manage Channels",
        "category": "bumper"
    },
    "bumpreminder autolock": {
        "description": "Lock channel until ready to use /bump",
        "usage": "!bumpreminder autolock <choice>",
        "examples": ["!bumpreminder autolock on", "!bumpreminder autolock off"],
        "arguments": ["choice"],
        "permissions": "Manage Channels",
        "category": "bumper"
    },
    "bumpreminder message": {
        "description": "Set the reminder message to run /bump",
        "usage": "!bumpreminder message <message>",
        "examples": ["!bumpreminder message It's time to bump the server!"],
        "arguments": ["message"],
        "permissions": "Manage Channels",
        "category": "bumper"
    },
    "bumpreminder message view": {
        "description": "View the current remind message",
        "usage": "!bumpreminder message view",
        "examples": ["!bumpreminder message view"],
        "arguments": ["none"],
        "permissions": "Manage Channels",
        "category": "bumper"
    },
    "bumpreminder thankyou": {
        "description": "Set the 'Thank You' message for successfully running /bump",
        "usage": "!bumpreminder thankyou <message>",
        "examples": ["!bumpreminder thankyou Thanks for bumping the server!"],
        "arguments": ["message"],
        "permissions": "Manage Channels",
        "category": "bumper"
    },
    "bumpreminder thankyou view": {
        "description": "View the current Thank You message",
        "usage": "!bumpreminder thankyou view",
        "examples": ["!bumpreminder thankyou view"],
        "arguments": ["none"],
        "permissions": "Manage Channels",
        "category": "bumper"
    },
    "bumpreminder channel": {
        "description": "Set Bump Reminder channel for the server",
        "usage": "!bumpreminder channel <channel>",
        "examples": ["!bumpreminder channel #bump-channel", "!bumpreminder channel #general"],
        "arguments": ["channel"],
        "permissions": "Manage Channels",
        "category": "bumper"
    }
}

async def setup(bot):
    # This is a documentation file, no cog to add
    pass 