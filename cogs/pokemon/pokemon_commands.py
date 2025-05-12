"""
Pokemon Commands Documentation

This file contains documentation for Pokemon commands to be used with the help system.
"""

POKEMON_COMMANDS = {
    "journey": {
        "description": "Start your Pokemon journey",
        "usage": "!journey",
        "examples": ["!journey"],
        "arguments": ["none"],
        "permissions": "None",
        "category": "pokemon"
    },
    "catch": {
        "description": "Try to catch a wild Pokemon",
        "usage": "!catch",
        "examples": ["!catch"],
        "arguments": ["none"],
        "permissions": "None",
        "category": "pokemon"
    },
    "pokemon": {
        "description": "Look up a Pokemon's stats",
        "usage": "!pokemon [pokemon_name]",
        "examples": ["!pokemon", "!pokemon Pikachu"],
        "arguments": ["pokemon_name"],
        "permissions": "None",
        "category": "pokemon"
    },
    "battle": {
        "description": "Battle with your primary Pokemon to gain XP",
        "usage": "!battle",
        "examples": ["!battle"],
        "arguments": ["none"],
        "permissions": "None",
        "category": "pokemon"
    },
    "evolve": {
        "description": "Evolve your primary Pokemon if eligible",
        "usage": "!evolve",
        "examples": ["!evolve"],
        "arguments": ["none"],
        "permissions": "None",
        "category": "pokemon"
    },
    "pokedex": {
        "description": "See a member's Pokedex",
        "usage": "!pokedex [member]",
        "examples": ["!pokedex", "!pokedex @user"],
        "arguments": ["member"],
        "permissions": "None",
        "category": "pokemon"
    },
    "pokeshop": {
        "description": "Buy pokemon balls to higher your chances of catching a pokemon",
        "usage": "!pokeshop",
        "aliases": ["pshop"],
        "examples": ["!pokeshop", "!pshop"],
        "arguments": ["none"],
        "permissions": "None",
        "category": "pokemon"
    },
    "buy": {
        "description": "Buy items from the Pokemon shop",
        "usage": "!buy <item> [quantity]",
        "examples": ["!buy pokeballs 5", "!buy greatballs", "!buy ultraballs 3"],
        "arguments": ["item", "quantity"],
        "permissions": "None",
        "category": "pokemon"
    },
    "inventory": {
        "description": "View your inventory",
        "usage": "!inventory [member]",
        "aliases": ["inv"],
        "examples": ["!inventory", "!inv", "!inventory @user"],
        "arguments": ["member"],
        "permissions": "None",
        "category": "pokemon"
    },
    "party": {
        "description": "View your primary Pokemon for battles",
        "usage": "!party",
        "examples": ["!party"],
        "arguments": ["none"],
        "permissions": "None",
        "category": "pokemon"
    },
    "pc": {
        "description": "View all Pokemon in your PC storage (collection)",
        "usage": "!pc [page]",
        "examples": ["!pc", "!pc 2"],
        "arguments": ["page"],
        "permissions": "None",
        "category": "pokemon"
    },
    "pokestats": {
        "description": "View the stats of Pokemon across the server",
        "usage": "!pokestats [amount]",
        "examples": ["!pokestats", "!pokestats 10"],
        "arguments": ["amount"],
        "permissions": "None",
        "category": "pokemon"
    },
    "moves": {
        "description": "Check new moves and reassign moves",
        "usage": "!moves",
        "examples": ["!moves"],
        "arguments": ["none"],
        "permissions": "None",
        "category": "pokemon"
    }
}

async def setup(bot):
    # This is a documentation module, no cog to add
    pass 