import discord
from discord.ext import commands
import random
import logging
from datetime import datetime
import asyncio
import os

logger = logging.getLogger('bot')

# Base URLs for different GIF APIs
TENOR_API_BASE = "https://tenor.googleapis.com/v2/search?q={}&key={}&limit=20"
GIPHY_API_BASE = "https://api.giphy.com/v1/gifs/search?api_key={}&q={}&limit=20"

class Roleplay(commands.Cog):
    """
    Commands for roleplaying emotions and actions with other users
    """
    
    def __init__(self, bot):
        self.bot = bot
        self.config_path = "data/roleplay"
        self.gif_cache = {}
        
        # Create directory if it doesn't exist
        os.makedirs(self.config_path, exist_ok=True)
        
        # Check for Tenor API key
        try:
            if not hasattr(self.bot, 'config'):
                self.bot.config = {}
                
            if 'tenor_api_key' not in self.bot.config:
                # Try to load from config file
                config_file = os.path.join('config', 'config.json')
                if os.path.exists(config_file):
                    with open(config_file, 'r') as f:
                        import json
                        config = json.load(f)
                        if 'tenor_api_key' in config:
                            self.bot.config['tenor_api_key'] = config['tenor_api_key']
                            logger.info("Loaded Tenor API key from config file")
                        else:
                            logger.warning("No Tenor API key found in config file, GIF functionality will be limited")
                else:
                    logger.warning("No config file found, GIF functionality will be limited")
        except Exception as e:
            logger.error(f"Error loading Tenor API key: {e}")
            logger.warning("GIF functionality will be limited")
        
    async def _get_gif(self, action):
        """Get a random GIF for the specified action"""
        # Check if we have cached GIFs for this action
        if action in self.gif_cache and self.gif_cache[action]:
            # Return a random GIF from the cache
            return random.choice(self.gif_cache[action])
        
        # Default GIFs for actions if API call fails
        default_gifs = {
            "surprised": ["https://media.tenor.com/images/a28c387d8dfda6af8c07c11cf6f96872/tenor.gif",
                         "https://media.tenor.com/images/26d977a9753660a0e68d15e0718a7e6a/tenor.gif"],
            "mad": ["https://media.tenor.com/images/9ea4fb41d066737c0e3f2d626c13f230/tenor.gif",
                    "https://media.tenor.com/images/a8b0a24e3a6ca0f8f8a92d388153b9d9/tenor.gif"],
            "sweat": ["https://media.tenor.com/images/5e04597f9e2857c12687614810d7230e/tenor.gif",
                      "https://media.tenor.com/images/d4c9966226c4a70a8c5933305d877906/tenor.gif"],
            "nervous": ["https://media.tenor.com/images/a3f6ffeb1aee43d21ad5c0f71258edb2/tenor.gif",
                        "https://media.tenor.com/images/bc28668e3487410d06aba9d67a6b6f8e/tenor.gif"],
            "thumbsup": ["https://media.tenor.com/images/75b49315a9c0a53836c64d5a4a0aa4c0/tenor.gif",
                         "https://media.tenor.com/images/81ef687afe58d4c84b82b0015ae445a6/tenor.gif"],
            "hug": ["https://media.tenor.com/images/c1e9bece7de32d1e5ddcd00562fe4c15/tenor.gif",
                   "https://media.tenor.com/images/1069921ddcf38ff722125c8f65401c28/tenor.gif"],
            "kiss": ["https://media.tenor.com/images/5c8972db3df932240bb191be36a77554/tenor.gif",
                    "https://media.tenor.com/images/1f9175e76488ebf226de305279151752/tenor.gif"]
        }
        
        # If we don't have default gifs for this action, use a related action or generic anime
        search_term = action
        if action not in default_gifs:
            related_terms = {
                "no": "anime no",
                "woah": "anime surprised",
                "tired": "anime tired",
                "nom": "anime eating",
                "wink": "anime wink",
                "nuzzle": "anime nuzzle",
                "nosebleed": "anime nosebleed",
                "poke": "anime poke",
                "yawn": "anime yawn",
                "nyah": "anime cat girl",
                "yay": "anime cheer",
                "pinch": "anime pinch",
                "peek": "anime peek",
                "yes": "anime yes",
                "pout": "anime pout",
                "roll": "anime roll",
                "run": "anime run",
                "sad": "anime sad",
                "scared": "anime scared",
                "shout": "anime shout",
                "shy": "anime shy",
                "sip": "anime drinking",
                "sleep": "anime sleeping",
                "sigh": "anime sigh",
                "slowclap": "anime clap",
                "pat": "anime headpat",
                "smack": "anime smack",
                "smile": "anime smile",
                "smug": "anime smug",
                "slap": "anime slap",
                "sneeze": "anime sneeze",
                "bite": "anime bite",
                "headpat": "anime headpat"
            }
            search_term = related_terms.get(action, f"anime {action}")
        
        # Try to get GIFs from Tenor API
        try:
            # Get API key from bot config
            tenor_api_key = self.bot.config.get('tenor_api_key', None)
            
            if tenor_api_key:
                import aiohttp
                
                # Format the URL
                url = TENOR_API_BASE.format(search_term, tenor_api_key)
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as response:
                        if response.status == 200:
                            data = await response.json()
                            results = data.get('results', [])
                            
                            if results:
                                # Extract GIF URLs
                                gif_urls = []
                                for result in results:
                                    # Use media_formats to get the best quality GIF
                                    media_formats = result.get('media_formats', {})
                                    if 'gif' in media_formats:
                                        gif_urls.append(media_formats['gif']['url'])
                                    elif 'mediumgif' in media_formats:
                                        gif_urls.append(media_formats['mediumgif']['url'])
                                    elif 'tinygif' in media_formats:
                                        gif_urls.append(media_formats['tinygif']['url'])
                                
                                if gif_urls:
                                    # Cache the results
                                    self.gif_cache[action] = gif_urls
                                    return random.choice(gif_urls)
        except Exception as e:
            logger.error(f"Error getting GIF from Tenor API: {str(e)}")
            
        # Fallback to default GIFs if API call fails or no results
        if action in default_gifs:
            return random.choice(default_gifs[action])
        else:
            # Default to one of these generic anime reaction GIFs if we don't have action-specific ones
            generic_gifs = [
                "https://media.tenor.com/images/01b10d6b6a525b525b213d576810ee10/tenor.gif",
                "https://media.tenor.com/images/7fd52ff62b51b15b368d65c10e67eb1c/tenor.gif",
                "https://media.tenor.com/images/13ece6247332c86f2ec5fe6fb20cc66e/tenor.gif",
                "https://media.tenor.com/images/a61b1f01d1c512dbc65b172d3c942d17/tenor.gif"
            ]
            return random.choice(generic_gifs)
    
    def _create_roleplay_embed(self, ctx, member, action, message=None, color=None):
        """Create an embed for the roleplay action"""
        # Default to blue color if none provided
        if color is None:
            color = discord.Color.blue()
            
        # Different messages based on if the action is towards self or other
        if ctx.author.id == member.id:
            title = f"{ctx.author.display_name} {action}s"
        else:
            title = f"{ctx.author.display_name} {action}s {member.display_name}"
            
        embed = discord.Embed(
            title=title,
            color=color,
            timestamp=datetime.utcnow()
        )
        
        # Add custom message if provided
        if message:
            embed.description = message
            
        # Add author info
        embed.set_author(
            name=ctx.author.display_name,
            icon_url=ctx.author.display_avatar.url
        )
        
        # Footer will be added after the GIF is set
        
        return embed
    
    @commands.command(name="rp_surprised")
    async def surprised(self, ctx, member: discord.Member = None, *, message: str = None):
        """Surprised towards a member in chat"""
        # If no member specified, default to the author
        if member is None:
            member = ctx.author
            
        async with ctx.typing():
            # Create roleplay embed
            embed = self._create_roleplay_embed(ctx, member, "surprised", message)
            
            # Get GIF
            gif_url = await self._get_gif("surprised")
            embed.set_image(url=gif_url)
            
            # Add footer
            embed.set_footer(text="Surprised Reaction")
            
            # Send the embed
            await ctx.send(embed=embed)
    
    @commands.command(name="rp_mad")
    async def mad(self, ctx, member: discord.Member = None, *, message: str = None):
        """Mad towards a member in chat"""
        if member is None:
            member = ctx.author
            
        async with ctx.typing():
            embed = self._create_roleplay_embed(ctx, member, "mad", message, discord.Color.red())
            gif_url = await self._get_gif("mad")
            embed.set_image(url=gif_url)
            embed.set_footer(text="Mad Reaction")
            await ctx.send(embed=embed)
    
    @commands.command(name="rp_sweat")
    async def sweat(self, ctx, member: discord.Member = None, *, message: str = None):
        """Sweat towards a member in chat"""
        if member is None:
            member = ctx.author
            
        async with ctx.typing():
            embed = self._create_roleplay_embed(ctx, member, "sweat", message)
            gif_url = await self._get_gif("sweat")
            embed.set_image(url=gif_url)
            embed.set_footer(text="Sweating Reaction")
            await ctx.send(embed=embed)
    
    @commands.command(name="rp_nervous")
    async def nervous(self, ctx, member: discord.Member = None, *, message: str = None):
        """Nervous towards a member in chat"""
        if member is None:
            member = ctx.author
            
        async with ctx.typing():
            embed = self._create_roleplay_embed(ctx, member, "nervous", message)
            gif_url = await self._get_gif("nervous")
            embed.set_image(url=gif_url)
            embed.set_footer(text="Nervous Reaction")
            await ctx.send(embed=embed)
    
    @commands.command(name="rp_thumbsup")
    async def thumbsup(self, ctx, member: discord.Member = None, *, message: str = None):
        """Thumbsup towards a member in chat"""
        if member is None:
            member = ctx.author
            
        async with ctx.typing():
            embed = self._create_roleplay_embed(ctx, member, "gives a thumbs up to", message, discord.Color.green())
            gif_url = await self._get_gif("thumbsup")
            embed.set_image(url=gif_url)
            embed.set_footer(text="Thumbs Up Reaction")
            await ctx.send(embed=embed)
    
    @commands.command(name="rp_no")
    async def no(self, ctx, member: discord.Member = None, *, message: str = None):
        """No towards a member in chat"""
        if member is None:
            member = ctx.author
            
        async with ctx.typing():
            embed = self._create_roleplay_embed(ctx, member, "says no to", message, discord.Color.red())
            gif_url = await self._get_gif("no")
            embed.set_image(url=gif_url)
            embed.set_footer(text="No Reaction")
            await ctx.send(embed=embed)
    
    @commands.command(name="rp_woah")
    async def woah(self, ctx, member: discord.Member = None, *, message: str = None):
        """Woah towards a member in chat"""
        if member is None:
            member = ctx.author
            
        async with ctx.typing():
            embed = self._create_roleplay_embed(ctx, member, "says woah to", message)
            gif_url = await self._get_gif("woah")
            embed.set_image(url=gif_url)
            embed.set_footer(text="Woah Reaction")
            await ctx.send(embed=embed)
    
    @commands.command(name="rp_tired")
    async def tired(self, ctx, member: discord.Member = None, *, message: str = None):
        """Tired towards a member in chat"""
        if member is None:
            member = ctx.author
            
        async with ctx.typing():
            embed = self._create_roleplay_embed(ctx, member, "is tired of", message)
            gif_url = await self._get_gif("tired")
            embed.set_image(url=gif_url)
            embed.set_footer(text="Tired Reaction")
            await ctx.send(embed=embed)
    
    @commands.command(name="rp_nom")
    async def nom(self, ctx, member: discord.Member = None, *, message: str = None):
        """Nom towards a member in chat"""
        if member is None:
            member = ctx.author
            
        async with ctx.typing():
            embed = self._create_roleplay_embed(ctx, member, "noms on", message)
            gif_url = await self._get_gif("nom")
            embed.set_image(url=gif_url)
            embed.set_footer(text="Nom Reaction")
            await ctx.send(embed=embed)
    
    @commands.command(name="rp_wink")
    async def wink(self, ctx, member: discord.Member = None, *, message: str = None):
        """Wink towards a member in chat"""
        if member is None:
            member = ctx.author
            
        async with ctx.typing():
            embed = self._create_roleplay_embed(ctx, member, "winks at", message)
            gif_url = await self._get_gif("wink")
            embed.set_image(url=gif_url)
            embed.set_footer(text="Wink Reaction")
            await ctx.send(embed=embed)
    
    @commands.command(name="rp_nuzzle")
    async def nuzzle(self, ctx, member: discord.Member = None, *, message: str = None):
        """Nuzzle towards a member in chat"""
        if member is None:
            member = ctx.author
            
        async with ctx.typing():
            embed = self._create_roleplay_embed(ctx, member, "nuzzles", message)
            gif_url = await self._get_gif("nuzzle")
            embed.set_image(url=gif_url)
            embed.set_footer(text="Nuzzle Reaction")
            await ctx.send(embed=embed)
    
    @commands.command(name="rp_nosebleed")
    async def nosebleed(self, ctx, member: discord.Member = None, *, message: str = None):
        """Nosebleed towards a member in chat"""
        if member is None:
            member = ctx.author
            
        async with ctx.typing():
            embed = self._create_roleplay_embed(ctx, member, "has a nosebleed because of", message)
            gif_url = await self._get_gif("nosebleed")
            embed.set_image(url=gif_url)
            embed.set_footer(text="Nosebleed Reaction")
            await ctx.send(embed=embed)
    
    @commands.command(name="rp_poke")
    async def poke(self, ctx, member: discord.Member = None, *, message: str = None):
        """Poke towards a member in chat"""
        if member is None:
            member = ctx.author
            
        async with ctx.typing():
            embed = self._create_roleplay_embed(ctx, member, "pokes", message)
            gif_url = await self._get_gif("poke")
            embed.set_image(url=gif_url)
            embed.set_footer(text="Poke Reaction")
            await ctx.send(embed=embed)
    
    @commands.command(name="rp_yawn")
    async def yawn(self, ctx, member: discord.Member = None, *, message: str = None):
        """Yawn towards a member in chat"""
        if member is None:
            member = ctx.author
            
        async with ctx.typing():
            embed = self._create_roleplay_embed(ctx, member, "yawns at", message)
            gif_url = await self._get_gif("yawn")
            embed.set_image(url=gif_url)
            embed.set_footer(text="Yawn Reaction")
            await ctx.send(embed=embed)
    
    @commands.command(name="rp_nyah")
    async def nyah(self, ctx, member: discord.Member = None, *, message: str = None):
        """Nyah towards a member in chat"""
        if member is None:
            member = ctx.author
            
        async with ctx.typing():
            embed = self._create_roleplay_embed(ctx, member, "nyahs at", message)
            gif_url = await self._get_gif("nyah")
            embed.set_image(url=gif_url)
            embed.set_footer(text="Nyah Reaction")
            await ctx.send(embed=embed)
    
    @commands.command(name="rp_yay")
    async def yay(self, ctx, member: discord.Member = None, *, message: str = None):
        """Yay towards a member in chat"""
        if member is None:
            member = ctx.author
            
        async with ctx.typing():
            embed = self._create_roleplay_embed(ctx, member, "says yay to", message, discord.Color.gold())
            gif_url = await self._get_gif("yay")
            embed.set_image(url=gif_url)
            embed.set_footer(text="Yay Reaction")
            await ctx.send(embed=embed)
    
    @commands.command(name="rp_pinch")
    async def pinch(self, ctx, member: discord.Member = None, *, message: str = None):
        """Pinch towards a member in chat"""
        if member is None:
            member = ctx.author
            
        async with ctx.typing():
            embed = self._create_roleplay_embed(ctx, member, "pinches", message)
            gif_url = await self._get_gif("pinch")
            embed.set_image(url=gif_url)
            embed.set_footer(text="Pinch Reaction")
            await ctx.send(embed=embed)
    
    @commands.command(name="rp_peek")
    async def peek(self, ctx, member: discord.Member = None, *, message: str = None):
        """Peek towards a member in chat"""
        if member is None:
            member = ctx.author
            
        async with ctx.typing():
            embed = self._create_roleplay_embed(ctx, member, "peeks at", message)
            gif_url = await self._get_gif("peek")
            embed.set_image(url=gif_url)
            embed.set_footer(text="Peek Reaction")
            await ctx.send(embed=embed)
    
    @commands.command(name="rp_yes")
    async def yes(self, ctx, member: discord.Member = None, *, message: str = None):
        """Yes towards a member in chat"""
        if member is None:
            member = ctx.author
            
        async with ctx.typing():
            embed = self._create_roleplay_embed(ctx, member, "says yes to", message, discord.Color.green())
            gif_url = await self._get_gif("yes")
            embed.set_image(url=gif_url)
            embed.set_footer(text="Yes Reaction")
            await ctx.send(embed=embed)
    
    @commands.command(name="rp_pout")
    async def pout(self, ctx, member: discord.Member = None, *, message: str = None):
        """Pout towards a member in chat"""
        if member is None:
            member = ctx.author
            
        async with ctx.typing():
            embed = self._create_roleplay_embed(ctx, member, "pouts at", message)
            gif_url = await self._get_gif("pout")
            embed.set_image(url=gif_url)
            embed.set_footer(text="Pout Reaction")
            await ctx.send(embed=embed)
    
    @commands.command(name="rp_roll")
    async def roll(self, ctx, member: discord.Member = None, *, message: str = None):
        """Roll towards a member in chat"""
        if member is None:
            member = ctx.author
            
        async with ctx.typing():
            embed = self._create_roleplay_embed(ctx, member, "rolls towards", message)
            gif_url = await self._get_gif("roll")
            embed.set_image(url=gif_url)
            embed.set_footer(text="Roll Reaction")
            await ctx.send(embed=embed)
    
    @commands.command(name="rp_run")
    async def run(self, ctx, member: discord.Member = None, *, message: str = None):
        """Run towards a member in chat"""
        if member is None:
            member = ctx.author
            
        async with ctx.typing():
            if ctx.author.id == member.id:
                action = "runs away"
            else:
                action = "runs towards"
                
            embed = self._create_roleplay_embed(ctx, member, action, message)
            gif_url = await self._get_gif("run")
            embed.set_image(url=gif_url)
            embed.set_footer(text="Run Reaction")
            await ctx.send(embed=embed)
    
    @commands.command(name="rp_sad")
    async def sad(self, ctx, member: discord.Member = None, *, message: str = None):
        """Sad towards a member in chat"""
        if member is None:
            member = ctx.author
            
        async with ctx.typing():
            embed = self._create_roleplay_embed(ctx, member, "is sad because of", message, discord.Color.dark_blue())
            gif_url = await self._get_gif("sad")
            embed.set_image(url=gif_url)
            embed.set_footer(text="Sad Reaction")
            await ctx.send(embed=embed)
    
    @commands.command(name="rp_scared")
    async def scared(self, ctx, member: discord.Member = None, *, message: str = None):
        """Scared towards a member in chat"""
        if member is None:
            member = ctx.author
            
        async with ctx.typing():
            embed = self._create_roleplay_embed(ctx, member, "is scared of", message)
            gif_url = await self._get_gif("scared")
            embed.set_image(url=gif_url)
            embed.set_footer(text="Scared Reaction")
            await ctx.send(embed=embed)
    
    @commands.command(name="rp_shout")
    async def shout(self, ctx, member: discord.Member = None, *, message: str = None):
        """Shout towards a member in chat"""
        if member is None:
            member = ctx.author
            
        async with ctx.typing():
            embed = self._create_roleplay_embed(ctx, member, "shouts at", message)
            gif_url = await self._get_gif("shout")
            embed.set_image(url=gif_url)
            embed.set_footer(text="Shout Reaction")
            await ctx.send(embed=embed)
    
    @commands.command()
    async def shy(self, ctx, member: discord.Member = None, *, message: str = None):
        """Shy towards a member in chat"""
        if member is None:
            member = ctx.author
            
        async with ctx.typing():
            embed = self._create_roleplay_embed(ctx, member, "is shy around", message)
            gif_url = await self._get_gif("shy")
            embed.set_image(url=gif_url)
            embed.set_footer(text="Shy Reaction")
            await ctx.send(embed=embed)
    
    @commands.command()
    async def sip(self, ctx, member: discord.Member = None, *, message: str = None):
        """Sip towards a member in chat"""
        if member is None:
            member = ctx.author
            
        async with ctx.typing():
            embed = self._create_roleplay_embed(ctx, member, "sips tea while looking at", message)
            gif_url = await self._get_gif("sip")
            embed.set_image(url=gif_url)
            embed.set_footer(text="Sip Reaction")
            await ctx.send(embed=embed)
    
    @commands.command()
    async def sleep(self, ctx, member: discord.Member = None, *, message: str = None):
        """Sleep towards a member in chat"""
        if member is None:
            member = ctx.author
            
        async with ctx.typing():
            if ctx.author.id == member.id:
                action = "falls asleep"
            else:
                action = "falls asleep on"
                
            embed = self._create_roleplay_embed(ctx, member, action, message, discord.Color.dark_purple())
            gif_url = await self._get_gif("sleep")
            embed.set_image(url=gif_url)
            embed.set_footer(text="Sleep Reaction")
            await ctx.send(embed=embed)
    
    @commands.command()
    async def sigh(self, ctx, member: discord.Member = None, *, message: str = None):
        """Sigh towards a member in chat"""
        if member is None:
            member = ctx.author
            
        async with ctx.typing():
            embed = self._create_roleplay_embed(ctx, member, "sighs at", message)
            gif_url = await self._get_gif("sigh")
            embed.set_image(url=gif_url)
            embed.set_footer(text="Sigh Reaction")
            await ctx.send(embed=embed)
    
    @commands.command()
    async def slowclap(self, ctx, member: discord.Member = None, *, message: str = None):
        """Slowclap towards a member in chat"""
        if member is None:
            member = ctx.author
            
        async with ctx.typing():
            embed = self._create_roleplay_embed(ctx, member, "slow claps at", message)
            gif_url = await self._get_gif("slowclap")
            embed.set_image(url=gif_url)
            embed.set_footer(text="Slow Clap Reaction")
            await ctx.send(embed=embed)
    
    @commands.command()
    async def pat(self, ctx, member: discord.Member = None, *, message: str = None):
        """Pat towards a member in chat"""
        if member is None:
            member = ctx.author
            
        async with ctx.typing():
            embed = self._create_roleplay_embed(ctx, member, "pats", message)
            gif_url = await self._get_gif("pat")
            embed.set_image(url=gif_url)
            embed.set_footer(text="Pat Reaction")
            await ctx.send(embed=embed)
    
    @commands.command()
    async def smack(self, ctx, member: discord.Member = None, *, message: str = None):
        """Smack towards a member in chat"""
        if member is None:
            member = ctx.author
            
        async with ctx.typing():
            embed = self._create_roleplay_embed(ctx, member, "smacks", message, discord.Color.orange())
            gif_url = await self._get_gif("smack")
            embed.set_image(url=gif_url)
            embed.set_footer(text="Smack Reaction")
            await ctx.send(embed=embed)
    
    @commands.command()
    async def smile(self, ctx, member: discord.Member = None, *, message: str = None):
        """Smile towards a member in chat"""
        if member is None:
            member = ctx.author
            
        async with ctx.typing():
            embed = self._create_roleplay_embed(ctx, member, "smiles at", message, discord.Color.gold())
            gif_url = await self._get_gif("smile")
            embed.set_image(url=gif_url)
            embed.set_footer(text="Smile Reaction")
            await ctx.send(embed=embed)
    
    @commands.command()
    async def smug(self, ctx, member: discord.Member = None, *, message: str = None):
        """Smug towards a member in chat"""
        if member is None:
            member = ctx.author
            
        async with ctx.typing():
            embed = self._create_roleplay_embed(ctx, member, "looks smugly at", message)
            gif_url = await self._get_gif("smug")
            embed.set_image(url=gif_url)
            embed.set_footer(text="Smug Reaction")
            await ctx.send(embed=embed)
    
    @commands.command()
    async def slap(self, ctx, member: discord.Member = None, *, message: str = None):
        """Slap towards a member in chat"""
        if member is None:
            member = ctx.author
            
        async with ctx.typing():
            embed = self._create_roleplay_embed(ctx, member, "slaps", message, discord.Color.red())
            gif_url = await self._get_gif("slap")
            embed.set_image(url=gif_url)
            embed.set_footer(text="Slap Reaction")
            await ctx.send(embed=embed)
    
    @commands.command()
    async def sneeze(self, ctx, member: discord.Member = None, *, message: str = None):
        """Sneeze towards a member in chat"""
        if member is None:
            member = ctx.author
            
        async with ctx.typing():
            embed = self._create_roleplay_embed(ctx, member, "sneezes at", message)
            gif_url = await self._get_gif("sneeze")
            embed.set_image(url=gif_url)
            embed.set_footer(text="Sneeze Reaction")
            await ctx.send(embed=embed)
    
    @commands.command()
    async def bite(self, ctx, member: discord.Member = None, *, message: str = None):
        """Bite towards a member in chat"""
        if member is None:
            member = ctx.author
            
        async with ctx.typing():
            embed = self._create_roleplay_embed(ctx, member, "bites", message)
            gif_url = await self._get_gif("bite")
            embed.set_image(url=gif_url)
            embed.set_footer(text="Bite Reaction")
            await ctx.send(embed=embed)
    
    @commands.command()
    async def headpat(self, ctx, member: discord.Member = None, *, message: str = None):
        """Headpat towards a member in chat"""
        if member is None:
            member = ctx.author
            
        async with ctx.typing():
            embed = self._create_roleplay_embed(ctx, member, "pats the head of", message, discord.Color.teal())
            gif_url = await self._get_gif("headpat")
            embed.set_image(url=gif_url)
            embed.set_footer(text="Headpat Reaction")
            await ctx.send(embed=embed)
    
    @commands.command()
    async def sorry(self, ctx, member: discord.Member = None, *, message: str = None):
        """Sorry towards a member in chat"""
        if member is None:
            member = ctx.author
            
        async with ctx.typing():
            embed = self._create_roleplay_embed(ctx, member, "apologizes to", message, discord.Color.dark_blue())
            gif_url = await self._get_gif("sorry")
            embed.set_image(url=gif_url)
            embed.set_footer(text="Sorry Reaction")
            await ctx.send(embed=embed)
    
    @commands.command()
    async def stare(self, ctx, member: discord.Member = None, *, message: str = None):
        """Stare towards a member in chat"""
        if member is None:
            member = ctx.author
            
        async with ctx.typing():
            embed = self._create_roleplay_embed(ctx, member, "stares at", message)
            gif_url = await self._get_gif("stare")
            embed.set_image(url=gif_url)
            embed.set_footer(text="Stare Reaction")
            await ctx.send(embed=embed)
    
    @commands.command()
    async def punch(self, ctx, member: discord.Member = None, *, message: str = None):
        """Punch towards a member in chat"""
        if member is None:
            member = ctx.author
            
        async with ctx.typing():
            embed = self._create_roleplay_embed(ctx, member, "punches", message, discord.Color.dark_red())
            gif_url = await self._get_gif("punch")
            embed.set_image(url=gif_url)
            embed.set_footer(text="Punch Reaction")
            await ctx.send(embed=embed)
    
    @commands.command()
    async def tickle(self, ctx, member: discord.Member = None, *, message: str = None):
        """Tickle towards a member in chat"""
        if member is None:
            member = ctx.author
            
        async with ctx.typing():
            embed = self._create_roleplay_embed(ctx, member, "tickles", message)
            gif_url = await self._get_gif("tickle")
            embed.set_image(url=gif_url)
            embed.set_footer(text="Tickle Reaction")
            await ctx.send(embed=embed)
    
    @commands.command()
    async def highfive(self, ctx, member: discord.Member = None, *, message: str = None):
        """Highfive towards a member in chat"""
        if member is None:
            member = ctx.author
            
        async with ctx.typing():
            embed = self._create_roleplay_embed(ctx, member, "high fives", message, discord.Color.green())
            gif_url = await self._get_gif("highfive")
            embed.set_image(url=gif_url)
            embed.set_footer(text="High Five Reaction")
            await ctx.send(embed=embed)
    
    @commands.command()
    async def shrug(self, ctx, member: discord.Member = None, *, message: str = None):
        """Shrug towards a member in chat"""
        if member is None:
            member = ctx.author
            
        async with ctx.typing():
            embed = self._create_roleplay_embed(ctx, member, "shrugs at", message)
            gif_url = await self._get_gif("shrug")
            embed.set_image(url=gif_url)
            embed.set_footer(text="Shrug Reaction")
            await ctx.send(embed=embed)
    
    @commands.command()
    async def wave(self, ctx, member: discord.Member = None, *, message: str = None):
        """Wave towards a member in chat"""
        if member is None:
            member = ctx.author
            
        async with ctx.typing():
            embed = self._create_roleplay_embed(ctx, member, "waves at", message)
            gif_url = await self._get_gif("wave")
            embed.set_image(url=gif_url)
            embed.set_footer(text="Wave Reaction")
            await ctx.send(embed=embed)
    
    @commands.command()
    async def blush(self, ctx, member: discord.Member = None, *, message: str = None):
        """Blush towards a member in chat"""
        if member is None:
            member = ctx.author
            
        async with ctx.typing():
            if ctx.author.id == member.id:
                action = "blushes"
            else:
                action = "blushes because of"
                
            embed = self._create_roleplay_embed(ctx, member, action, message, discord.Color.red())
            gif_url = await self._get_gif("blush")
            embed.set_image(url=gif_url)
            embed.set_footer(text="Blush Reaction")
            await ctx.send(embed=embed)
    
    @commands.command()
    async def cry(self, ctx, member: discord.Member = None, *, message: str = None):
        """Cry towards a member in chat"""
        if member is None:
            member = ctx.author
            
        async with ctx.typing():
            if ctx.author.id == member.id:
                action = "cries"
            else:
                action = "cries because of"
                
            embed = self._create_roleplay_embed(ctx, member, action, message, discord.Color.blue())
            gif_url = await self._get_gif("cry")
            embed.set_image(url=gif_url)
            embed.set_footer(text="Cry Reaction")
            await ctx.send(embed=embed)
    
    @commands.command()
    async def love(self, ctx, member: discord.Member = None, *, message: str = None):
        """Love towards a member in chat"""
        if member is None:
            member = ctx.author
            
        async with ctx.typing():
            embed = self._create_roleplay_embed(ctx, member, "loves", message, discord.Color.magenta())
            gif_url = await self._get_gif("love")
            embed.set_image(url=gif_url)
            embed.set_footer(text="Love Reaction")
            await ctx.send(embed=embed)
    
    @commands.command()
    async def laugh(self, ctx, member: discord.Member = None, *, message: str = None):
        """Laugh towards a member in chat"""
        if member is None:
            member = ctx.author
            
        async with ctx.typing():
            if ctx.author.id == member.id:
                action = "laughs"
            else:
                action = "laughs at"
                
            embed = self._create_roleplay_embed(ctx, member, action, message, discord.Color.gold())
            gif_url = await self._get_gif("laugh")
            embed.set_image(url=gif_url)
            embed.set_footer(text="Laugh Reaction")
            await ctx.send(embed=embed)
    
    @commands.command()
    async def airkiss(self, ctx, member: discord.Member = None, *, message: str = None):
        """Airkiss towards a member in chat"""
        if member is None:
            member = ctx.author
            
        async with ctx.typing():
            embed = self._create_roleplay_embed(ctx, member, "blows a kiss to", message, discord.Color.magenta())
            gif_url = await self._get_gif("airkiss")
            embed.set_image(url=gif_url)
            embed.set_footer(text="Air Kiss Reaction")
            await ctx.send(embed=embed)
    
    @commands.command()
    async def angrystare(self, ctx, member: discord.Member = None, *, message: str = None):
        """Angrystare towards a member in chat"""
        if member is None:
            member = ctx.author
            
        async with ctx.typing():
            embed = self._create_roleplay_embed(ctx, member, "glares angrily at", message, discord.Color.red())
            gif_url = await self._get_gif("angrystare")
            embed.set_image(url=gif_url)
            embed.set_footer(text="Angry Stare Reaction")
            await ctx.send(embed=embed)
    
    @commands.command()
    async def bleh(self, ctx, member: discord.Member = None, *, message: str = None):
        """Bleh towards a member in chat"""
        if member is None:
            member = ctx.author
            
        async with ctx.typing():
            embed = self._create_roleplay_embed(ctx, member, "sticks tongue out at", message)
            gif_url = await self._get_gif("bleh")
            embed.set_image(url=gif_url)
            embed.set_footer(text="Bleh Reaction")
            await ctx.send(embed=embed)
    
    @commands.command()
    async def celebrate(self, ctx, member: discord.Member = None, *, message: str = None):
        """Celebrate towards a member in chat"""
        if member is None:
            member = ctx.author
            
        async with ctx.typing():
            embed = self._create_roleplay_embed(ctx, member, "celebrates with", message, discord.Color.gold())
            gif_url = await self._get_gif("celebrate")
            embed.set_image(url=gif_url)
            embed.set_footer(text="Celebrate Reaction")
            await ctx.send(embed=embed)
    
    @commands.command()
    async def cheers(self, ctx, member: discord.Member = None, *, message: str = None):
        """Cheers towards a member in chat"""
        if member is None:
            member = ctx.author
            
        async with ctx.typing():
            embed = self._create_roleplay_embed(ctx, member, "cheers with", message, discord.Color.gold())
            gif_url = await self._get_gif("cheers")
            embed.set_image(url=gif_url)
            embed.set_footer(text="Cheers Reaction")
            await ctx.send(embed=embed)
    
    @commands.command()
    async def brofist(self, ctx, member: discord.Member = None, *, message: str = None):
        """Brofist towards a member in chat"""
        if member is None:
            member = ctx.author
            
        async with ctx.typing():
            embed = self._create_roleplay_embed(ctx, member, "gives a brofist to", message)
            gif_url = await self._get_gif("brofist")
            embed.set_image(url=gif_url)
            embed.set_footer(text="Brofist Reaction")
            await ctx.send(embed=embed)
    
    @commands.command()
    async def clap(self, ctx, member: discord.Member = None, *, message: str = None):
        """Clap towards a member in chat"""
        if member is None:
            member = ctx.author
            
        async with ctx.typing():
            embed = self._create_roleplay_embed(ctx, member, "claps for", message, discord.Color.green())
            gif_url = await self._get_gif("clap")
            embed.set_image(url=gif_url)
            embed.set_footer(text="Clap Reaction")
            await ctx.send(embed=embed)
    
    @commands.command()
    async def confused(self, ctx, member: discord.Member = None, *, message: str = None):
        """Confused towards a member in chat"""
        if member is None:
            member = ctx.author
            
        async with ctx.typing():
            embed = self._create_roleplay_embed(ctx, member, "is confused by", message)
            gif_url = await self._get_gif("confused")
            embed.set_image(url=gif_url)
            embed.set_footer(text="Confused Reaction")
            await ctx.send(embed=embed)
    
    @commands.command()
    async def cool(self, ctx, member: discord.Member = None, *, message: str = None):
        """Cool towards a member in chat"""
        if member is None:
            member = ctx.author
            
        async with ctx.typing():
            embed = self._create_roleplay_embed(ctx, member, "is too cool for", message, discord.Color.blue())
            gif_url = await self._get_gif("cool")
            embed.set_image(url=gif_url)
            embed.set_footer(text="Cool Reaction")
            await ctx.send(embed=embed)
    
    @commands.command()
    async def cuddle(self, ctx, member: discord.Member = None, *, message: str = None):
        """Cuddle towards a member in chat"""
        if member is None:
            member = ctx.author
            
        async with ctx.typing():
            embed = self._create_roleplay_embed(ctx, member, "cuddles with", message, discord.Color.purple())
            gif_url = await self._get_gif("cuddle")
            embed.set_image(url=gif_url)
            embed.set_footer(text="Cuddle Reaction")
            await ctx.send(embed=embed)
    
    @commands.command()
    async def evillaugh(self, ctx, member: discord.Member = None, *, message: str = None):
        """Evil laugh towards a member in chat"""
        if member is None:
            member = ctx.author
            
        async with ctx.typing():
            embed = self._create_roleplay_embed(ctx, member, "laughs evilly at", message, discord.Color.dark_red())
            gif_url = await self._get_gif("evillaugh")
            embed.set_image(url=gif_url)
            embed.set_footer(text="Evil Laugh Reaction")
            await ctx.send(embed=embed)
    
    @commands.command()
    async def dance(self, ctx, member: discord.Member = None, *, message: str = None):
        """Dance towards a member in chat"""
        if member is None:
            member = ctx.author
            
        async with ctx.typing():
            if ctx.author.id == member.id:
                action = "dances"
            else:
                action = "dances with"
                
            embed = self._create_roleplay_embed(ctx, member, action, message, discord.Color.purple())
            gif_url = await self._get_gif("dance")
            embed.set_image(url=gif_url)
            embed.set_footer(text="Dance Reaction")
            await ctx.send(embed=embed)
    
    @commands.command()
    async def drool(self, ctx, member: discord.Member = None, *, message: str = None):
        """Drool towards a member in chat"""
        if member is None:
            member = ctx.author
            
        async with ctx.typing():
            if ctx.author.id == member.id:
                action = "drools"
            else:
                action = "drools over"
                
            embed = self._create_roleplay_embed(ctx, member, action, message)
            gif_url = await self._get_gif("drool")
            embed.set_image(url=gif_url)
            embed.set_footer(text="Drool Reaction")
            await ctx.send(embed=embed)
    
    @commands.command()
    async def facepalm(self, ctx, member: discord.Member = None, *, message: str = None):
        """Facepalm towards a member in chat"""
        if member is None:
            member = ctx.author
            
        async with ctx.typing():
            if ctx.author.id == member.id:
                action = "facepalms"
            else:
                action = "facepalms at"
                
            embed = self._create_roleplay_embed(ctx, member, action, message)
            gif_url = await self._get_gif("facepalm")
            embed.set_image(url=gif_url)
            embed.set_footer(text="Facepalm Reaction")
            await ctx.send(embed=embed)
    
    @commands.command()
    async def handhold(self, ctx, member: discord.Member = None, *, message: str = None):
        """Handhold towards a member in chat"""
        if member is None:
            member = ctx.author
            
        async with ctx.typing():
            embed = self._create_roleplay_embed(ctx, member, "holds hands with", message, discord.Color.light_grey())
            gif_url = await self._get_gif("handhold")
            embed.set_image(url=gif_url)
            embed.set_footer(text="Handhold Reaction")
            await ctx.send(embed=embed)
    
    @commands.command()
    async def happy(self, ctx, member: discord.Member = None, *, message: str = None):
        """Happy towards a member in chat"""
        if member is None:
            member = ctx.author
            
        async with ctx.typing():
            if ctx.author.id == member.id:
                action = "is happy"
            else:
                action = "is happy because of"
                
            embed = self._create_roleplay_embed(ctx, member, action, message, discord.Color.gold())
            gif_url = await self._get_gif("happy")
            embed.set_image(url=gif_url)
            embed.set_footer(text="Happy Reaction")
            await ctx.send(embed=embed)
    
    @commands.command()
    async def headbang(self, ctx, member: discord.Member = None, *, message: str = None):
        """Headbang towards a member in chat"""
        if member is None:
            member = ctx.author
            
        async with ctx.typing():
            if ctx.author.id == member.id:
                action = "headbangs"
            else:
                action = "headbangs with"
                
            embed = self._create_roleplay_embed(ctx, member, action, message)
            gif_url = await self._get_gif("headbang")
            embed.set_image(url=gif_url)
            embed.set_footer(text="Headbang Reaction")
            await ctx.send(embed=embed)
    
    @commands.command()
    async def huh(self, ctx, member: discord.Member = None, *, message: str = None):
        """Huh towards a member in chat"""
        if member is None:
            member = ctx.author
            
        async with ctx.typing():
            embed = self._create_roleplay_embed(ctx, member, "looks confused at", message)
            gif_url = await self._get_gif("huh")
            embed.set_image(url=gif_url)
            embed.set_footer(text="Huh Reaction")
            await ctx.send(embed=embed)
    
    @commands.command()
    async def lick(self, ctx, member: discord.Member = None, *, message: str = None):
        """Lick towards a member in chat"""
        if member is None:
            member = ctx.author
            
        async with ctx.typing():
            embed = self._create_roleplay_embed(ctx, member, "licks", message)
            gif_url = await self._get_gif("lick")
            embed.set_image(url=gif_url)
            embed.set_footer(text="Lick Reaction")
            await ctx.send(embed=embed)
    
    @commands.command()
    async def hug(self, ctx, member: discord.Member = None, *, message: str = None):
        """Hug a member through the bot"""
        if member is None:
            member = ctx.author
            
        async with ctx.typing():
            embed = self._create_roleplay_embed(ctx, member, "hugs", message, discord.Color.purple())
            gif_url = await self._get_gif("hug")
            embed.set_image(url=gif_url)
            embed.set_footer(text="Hug Reaction")
            await ctx.send(embed=embed)
    
    @commands.command()
    async def kiss(self, ctx, member: discord.Member = None, *, message: str = None):
        """Kiss towards a member in chat"""
        if member is None:
            member = ctx.author
            
        async with ctx.typing():
            embed = self._create_roleplay_embed(ctx, member, "kisses", message, discord.Color.pink())
            gif_url = await self._get_gif("kiss")
            embed.set_image(url=gif_url)
            embed.set_footer(text="Kiss Reaction")
            await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Roleplay(bot)) 