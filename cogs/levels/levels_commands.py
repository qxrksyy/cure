"""
Levels Commands Documentation

This file contains documentation for Levels commands to be used with the help system.
"""

LEVELS_COMMANDS = {
    "levels": {
        "description": "Setup the leveling system or view a user's level",
        "usage": "!levels [member]",
        "examples": ["!levels", "!levels @user"],
        "arguments": ["member"],
        "permissions": "None",
        "category": "levels"
    },
    "levels add": {
        "description": "Create level role",
        "usage": "!levels add <role> <rank>",
        "examples": ["!levels add @Level5 5", "!levels add \"Gold Tier\" 10"],
        "arguments": ["role", "rank"],
        "permissions": "Manage Guild",
        "category": "levels"
    },
    "levels lock": {
        "description": "Disable leveling system",
        "usage": "!levels lock",
        "examples": ["!levels lock"],
        "arguments": ["none"],
        "permissions": "Manage Guild",
        "category": "levels"
    },
    "levels cleanup": {
        "description": "Reset level & XP for absent members",
        "usage": "!levels cleanup",
        "examples": ["!levels cleanup"],
        "arguments": ["none"],
        "permissions": "Manage Guild",
        "category": "levels"
    },
    "levels message": {
        "description": "Set a message for leveling up",
        "usage": "!levels message <message>",
        "examples": ["!levels message Congrats {user}, you've reached level {level}!"],
        "arguments": ["message"],
        "permissions": "Manage Guild",
        "category": "levels"
    },
    "levels message view": {
        "description": "View the level up message for the server",
        "usage": "!levels message view",
        "examples": ["!levels message view"],
        "arguments": ["none"],
        "permissions": "Manage Guild",
        "category": "levels"
    },
    "levels list": {
        "description": "View all ignored channels and roles",
        "usage": "!levels list",
        "examples": ["!levels list"],
        "arguments": ["none"],
        "permissions": "Manage Guild",
        "category": "levels"
    },
    "levels setrate": {
        "description": "Set multiplier for XP gain",
        "usage": "!levels setrate <multiplier>",
        "examples": ["!levels setrate 1.5", "!levels setrate 0.8"],
        "arguments": ["multiplier"],
        "permissions": "Manage Guild",
        "category": "levels"
    },
    "levels messages": {
        "description": "Toggle level up messages for yourself",
        "usage": "!levels messages <setting>",
        "examples": ["!levels messages on", "!levels messages off"],
        "arguments": ["setting"],
        "permissions": "None",
        "category": "levels"
    },
    "levels reset": {
        "description": "Reset all levels and configurations",
        "usage": "!levels reset",
        "examples": ["!levels reset"],
        "arguments": ["none"],
        "permissions": "Manage Guild",
        "category": "levels"
    },
    "levels remove": {
        "description": "Remove a level role",
        "usage": "!levels remove <level>",
        "examples": ["!levels remove 5"],
        "arguments": ["level"],
        "permissions": "Manage Guild",
        "category": "levels"
    },
    "levels config": {
        "description": "View server configuration for Leveling system",
        "usage": "!levels config",
        "examples": ["!levels config"],
        "arguments": ["none"],
        "permissions": "Manage Guild",
        "category": "levels"
    },
    "levels stackroles": {
        "description": "Enable or disable stacking of roles",
        "usage": "!levels stackroles <option>",
        "examples": ["!levels stackroles on", "!levels stackroles off"],
        "arguments": ["option"],
        "permissions": "Manage Guild",
        "category": "levels"
    },
    "levels ignore": {
        "description": "Ignore a channel or role for XP",
        "usage": "!levels ignore <target>",
        "examples": ["!levels ignore #no-xp", "!levels ignore @No-XP-Role"],
        "arguments": ["target"],
        "permissions": "Manage Guild",
        "category": "levels"
    },
    "levels roles": {
        "description": "Show all level rewards",
        "usage": "!levels roles",
        "examples": ["!levels roles"],
        "arguments": ["none"],
        "permissions": "None",
        "category": "levels"
    },
    "levels unlock": {
        "description": "Enable leveling system",
        "usage": "!levels unlock",
        "examples": ["!levels unlock"],
        "arguments": ["none"],
        "permissions": "Manage Guild",
        "category": "levels"
    },
    "levels sync": {
        "description": "Sync your level roles for your members",
        "usage": "!levels sync",
        "examples": ["!levels sync"],
        "arguments": ["none"],
        "permissions": "Manage Guild",
        "category": "levels"
    },
    "levels messagemode": {
        "description": "Set up where level up messages will be sent",
        "usage": "!levels messagemode <mode>",
        "examples": ["!levels messagemode dm", "!levels messagemode channel", "!levels messagemode off"],
        "arguments": ["mode"],
        "permissions": "Manage Guild",
        "category": "levels"
    },
    "levels leaderboard": {
        "description": "View the highest ranking members",
        "usage": "!levels leaderboard",
        "aliases": ["lb", "rank"],
        "examples": ["!levels leaderboard", "!lb"],
        "arguments": ["none"],
        "permissions": "None",
        "category": "levels"
    },
    "setlevel": {
        "description": "Set a user's level",
        "usage": "!setlevel <member> <level>",
        "examples": ["!setlevel @user 10"],
        "arguments": ["member", "level"],
        "permissions": "Manage Guild",
        "category": "levels"
    },
    "setxp": {
        "description": "Set a user's experience",
        "usage": "!setxp <member> <xp>",
        "examples": ["!setxp @user 1500"],
        "arguments": ["member", "xp"],
        "permissions": "Manage Guild",
        "category": "levels"
    },
    "removexp": {
        "description": "Remove experience from a user",
        "usage": "!removexp <member> <xp>",
        "examples": ["!removexp @user 500"],
        "arguments": ["member", "xp"],
        "permissions": "Manage Guild",
        "category": "levels"
    }
}

async def setup(bot):
    # This is a documentation module, no cog to add
    pass 