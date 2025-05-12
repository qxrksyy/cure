import discord
from discord.ext import commands
import os
import logging
import asyncio
import json
from dotenv import load_dotenv

# Import custom checks
import custom_checks

# Set up logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('bot')

# Load environment variables
load_dotenv()

# Create necessary directories
os.makedirs('data', exist_ok=True)
os.makedirs('config', exist_ok=True)

# Bot configuration
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

# Load config
bot.config = {}
config_file = os.path.join('config', 'config.json')
try:
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            bot.config = json.load(f)
            logger.info("Loaded configuration from config.json")
    else:
        # Create default config
        default_config = {
            "tenor_api_key": "",
            "giphy_api_key": ""
        }
        with open(config_file, 'w') as f:
            json.dump(default_config, f, indent=4)
        logger.info("Created default config.json file")
except Exception as e:
    logger.error(f"Error loading configuration: {e}")

@bot.event
async def on_ready():
    logger.info(f'Logged in as {bot.user} (ID: {bot.user.id})')
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="!help"))
    
    # Generate invite link
    invite_link = discord.utils.oauth_url(
        bot.user.id,
        permissions=discord.Permissions(administrator=True),
        scopes=("bot", "applications.commands")
    )
    logger.info(f"Invite link: {invite_link}")

async def load_extensions():
    # Load cogs from directories
    cogs_loaded = 0
    cogs_failed = 0
    failed_extensions = []
    
    # Make sure cogs directory exists
    if not os.path.exists("cogs"):
        os.makedirs("cogs", exist_ok=True)
        logger.warning("Created missing cogs directory")
        return
        
    for folder in os.listdir("cogs"):
        folder_path = os.path.join("cogs", folder)
        if os.path.isdir(folder_path):
            for file in os.listdir(folder_path):
                if file.endswith(".py") and not file.startswith("_"):
                    extension_name = f"cogs.{folder}.{file[:-3]}"
                    try:
                        await bot.load_extension(extension_name)
                        logger.info(f"Loaded extension: {extension_name}")
                        cogs_loaded += 1
                    except Exception as e:
                        logger.error(f"Failed to load extension {extension_name}: {e}")
                        failed_extensions.append(f"{extension_name}: {str(e)}")
                        cogs_failed += 1
    
    logger.info(f"Extension loading complete. Loaded: {cogs_loaded}, Failed: {cogs_failed}")
    
    if failed_extensions:
        logger.info("Failed extensions:")
        for ext in failed_extensions:
            logger.info(f"  - {ext}")
        
        # Group by error type for better debugging
        from collections import defaultdict
        error_groups = defaultdict(list)
        for ext in failed_extensions:
            error_type = ext.split(": ")[-1]
            extension = ext.split(": ")[0]
            error_groups[error_type].append(extension)
        
        logger.info("Grouped by error type:")
        for error, exts in error_groups.items():
            logger.info(f"  - {error}: {len(exts)} extensions")

@bot.event
async def setup_hook():
    try:
        await load_extensions()
        logger.info("Setup hook completed")
    except Exception as e:
        logger.error(f"Error in setup hook: {e}")

@bot.command(name="ping")
async def ping(ctx):
    """Simple command to check if the bot is responsive."""
    latency = round(bot.latency * 1000)
    await ctx.send(f"Pong! 🏓 Bot latency: {latency}ms")

# Run the bot
if __name__ == "__main__":
    token = os.getenv("TOKEN")
    if not token:
        logger.error("No token found in .env file. Please add your bot token.")
    else:
        try:
            bot.run(token)
        except discord.errors.LoginFailure:
            logger.error("Invalid token. Please check your .env file.")
        except Exception as e:
            logger.error(f"Error starting bot: {e}") 