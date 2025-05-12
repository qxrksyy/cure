"""
Economy Commands Documentation

This file contains documentation for economy commands to be used with the help system.
"""

ECONOMY_COMMANDS = {
    "open": {
        "description": "Create an economy account to start gambling",
        "usage": "!open",
        "examples": ["!open"],
        "category": "economy"
    },
    "daily": {
        "description": "Claim your daily rewards (200-500 bucks)",
        "usage": "!daily",
        "examples": ["!daily"],
        "category": "economy"
    },
    "balance": {
        "description": "Check your wallet and bank balance",
        "usage": "!balance [user]",
        "examples": ["!balance", "!bal", "!balance @user"],
        "aliases": ["bal", "wallet"],
        "category": "economy"
    },
    "deposit": {
        "description": "Deposit money from your wallet to your bank",
        "usage": "!deposit <amount|all>",
        "examples": ["!deposit 1000", "!dep 500", "!deposit all"],
        "aliases": ["dep"],
        "category": "economy"
    },
    "withdraw": {
        "description": "Withdraw money from your bank to your wallet",
        "usage": "!withdraw <amount|all>",
        "examples": ["!withdraw 1000", "!wd 500", "!withdraw all"],
        "aliases": ["wd"],
        "category": "economy"
    },
    "transfer": {
        "description": "Transfer money to another user",
        "usage": "!transfer <user> <amount>",
        "examples": ["!transfer @user 1000", "!pay @user 500"],
        "aliases": ["give", "pay"],
        "category": "economy"
    },
    "gamble": {
        "description": "Gamble your money with a 45% chance to win 2x",
        "usage": "!gamble <amount|half|all>",
        "examples": ["!gamble 1000", "!bet 500", "!gamble all", "!gamble half"],
        "aliases": ["bet"],
        "category": "gambling"
    },
    "dice": {
        "description": "Roll dice with a 50% chance to win 1.8x",
        "usage": "!dice <amount|half|all>",
        "examples": ["!dice 1000", "!dice all", "!dice half"],
        "category": "gambling"
    },
    "coinflip": {
        "description": "Bet on heads or tails with a 49% chance to win 1.95x",
        "usage": "!coinflip <heads|tails> <amount|half|all>",
        "examples": ["!coinflip heads 1000", "!coin tails 500", "!flip h all"],
        "aliases": ["coin", "flip"],
        "category": "gambling"
    },
    "supergamble": {
        "description": "High risk gambling with 30% chance to win 3x (minimum 500 bucks)",
        "usage": "!supergamble <amount|half|all>",
        "examples": ["!supergamble 1000", "!sg 2000", "!highroller all"],
        "aliases": ["sg", "highroller"],
        "category": "gambling"
    },
    "rob": {
        "description": "Attempt to rob another user (40% chance of success)",
        "usage": "!rob <user>",
        "examples": ["!rob @user"],
        "category": "economy"
    },
    "shop": {
        "description": "View items available in the shop",
        "usage": "!shop",
        "examples": ["!shop", "!store"],
        "aliases": ["store"],
        "category": "economy"
    },
    "buy": {
        "description": "Buy an item from the shop",
        "usage": "!buy <item_id> [quantity]",
        "examples": ["!buy lucky_charm", "!buy shield 2"],
        "category": "economy"
    },
    "use": {
        "description": "Use an item from your inventory",
        "usage": "!use <item_name>",
        "examples": ["!use lucky charm", "!use shield"],
        "category": "economy"
    },
    "inventory": {
        "description": "View your inventory",
        "usage": "!inventory [user]",
        "examples": ["!inventory", "!inv", "!bag @user"],
        "aliases": ["inv", "bag"],
        "category": "economy"
    },
    "effects": {
        "description": "View your active effects",
        "usage": "!effects",
        "examples": ["!effects"],
        "category": "economy"
    },
    "stats": {
        "description": "View detailed gambling statistics",
        "usage": "!stats [user]",
        "examples": ["!stats", "!stats @user"],
        "category": "gambling"
    },
    "leaderboard": {
        "description": "View the richest users or highest earners",
        "usage": "!leaderboard [balance|earnings]",
        "examples": ["!leaderboard", "!lb earnings"],
        "aliases": ["lb"],
        "category": "economy"
    },
    "richest": {
        "description": "Show the richest user in the server",
        "usage": "!richest",
        "examples": ["!richest"],
        "category": "economy"
    }
}

async def setup(bot):
    # This is a documentation/utility file, no cog to add
    pass 