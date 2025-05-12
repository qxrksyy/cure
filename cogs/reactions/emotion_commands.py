import discord
from discord.ext import commands
import random
import aiohttp
import logging

logger = logging.getLogger('bot')

class EmotionCommands(commands.Cog):
    """Commands for expressing emotions toward other members"""
    
    def __init__(self, bot):
        self.bot = bot
        # Dictionary of emotion types with sample GIF URLs
        self.emotion_gifs = {
            # Basic emotions
            "surprised": [
                "https://media.giphy.com/media/3o7TKqnN349PBUtGFO/giphy.gif",
                "https://media.giphy.com/media/5p2wQFyu8GsFO/giphy.gif"
            ],
            "mad": [
                "https://media.giphy.com/media/l1J9u3TZfpmeDLkD6/giphy.gif",
                "https://media.giphy.com/media/11tTNkNy1SdXGg/giphy.gif"
            ],
            "sweat": [
                "https://media.giphy.com/media/32mC2kXYWCsg0/giphy.gif",
                "https://media.giphy.com/media/3oKHWzOXDG0tqOdhe0/giphy.gif"
            ],
            "nervous": [
                "https://media.giphy.com/media/xT5LMB2WiOdjpB7K4o/giphy.gif",
                "https://media.giphy.com/media/bGCwmLDnwL25kCg3FV/giphy.gif"
            ],
            "thumbsup": [
                "https://media.giphy.com/media/3o7TKF5DnsSLv4zVBu/giphy.gif",
                "https://media.giphy.com/media/l4q8cJzGdR9J8w3hS/giphy.gif"
            ],
            # Physical interactions
            "hug": [
                "https://media.giphy.com/media/l2QDM9Jnim1YVILXa/giphy.gif",
                "https://media.giphy.com/media/3oEhmDMA4r9GxhM6oU/giphy.gif"
            ],
            "kiss": [
                "https://media.giphy.com/media/l2Je2M4Nfrit0L7sQ/giphy.gif",
                "https://media.giphy.com/media/3og0IvIXD1UrcEvNmw/giphy.gif"
            ],
            "pat": [
                "https://media.giphy.com/media/L2z7dnOduqEow/giphy.gif",
                "https://media.giphy.com/media/5tmRHwTlHAA9WkVxTU/giphy.gif"
            ],
            "slap": [
                "https://media.giphy.com/media/xUO4t2gkWBxDi/giphy.gif",
                "https://media.giphy.com/media/uqSU9IEYEKAbS/giphy.gif"
            ],
            "highfive": [
                "https://media.giphy.com/media/3oEjHV0z8S7WM4MwnK/giphy.gif",
                "https://media.giphy.com/media/qHY2zxSp7Tbj2/giphy.gif"
            ]
        }

    async def get_gif(self, emotion):
        """Get a random GIF for the given emotion"""
        if emotion in self.emotion_gifs and self.emotion_gifs[emotion]:
            return random.choice(self.emotion_gifs[emotion])
        
        # Fallback to Tenor API search if no pre-defined GIFs
        try:
            async with aiohttp.ClientSession() as session:
                params = {
                    'q': f"{emotion} anime",
                    'key': 'LIVDSRZULELA',  # Public Tenor API key for testing
                    'limit': 10
                }
                async with session.get("https://g.tenor.com/v1/search", params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        results = data.get("results", [])
                        if results:
                            return random.choice(results)["media"][0]["gif"]["url"]
        except Exception as e:
            logger.error(f"Error fetching GIF from Tenor: {str(e)}")
            
        # Default GIF if all else fails
        return "https://media.giphy.com/media/9Y5BbDSkSTiY8/giphy.gif"

    @commands.command(name="surprised")
    async def surprised(self, ctx, member: discord.Member = None):
        """Surprised towards a member in chat"""
        member = member or ctx.author
        gif_url = await self.get_gif("surprised")
        
        embed = discord.Embed(
            description=f"{ctx.author.mention} is surprised at {member.mention}!",
            color=discord.Color.blue()
        )
        embed.set_image(url=gif_url)
        await ctx.send(embed=embed)

    @commands.command(name="mad")
    async def mad(self, ctx, member: discord.Member = None):
        """Mad towards a member in chat"""
        member = member or ctx.author
        gif_url = await self.get_gif("mad")
        
        embed = discord.Embed(
            description=f"{ctx.author.mention} is mad at {member.mention}!",
            color=discord.Color.red()
        )
        embed.set_image(url=gif_url)
        await ctx.send(embed=embed)

    @commands.command(name="sweat")
    async def sweat(self, ctx, member: discord.Member = None):
        """Sweat towards a member in chat"""
        member = member or ctx.author
        gif_url = await self.get_gif("sweat")
        
        embed = discord.Embed(
            description=f"{ctx.author.mention} is sweating because of {member.mention}!",
            color=discord.Color.blue()
        )
        embed.set_image(url=gif_url)
        await ctx.send(embed=embed)

    @commands.command(name="nervous")
    async def nervous(self, ctx, member: discord.Member = None):
        """Nervous towards a member in chat"""
        member = member or ctx.author
        gif_url = await self.get_gif("nervous")
        
        embed = discord.Embed(
            description=f"{ctx.author.mention} is nervous around {member.mention}!",
            color=discord.Color.blue()
        )
        embed.set_image(url=gif_url)
        await ctx.send(embed=embed)

    @commands.command(name="thumbsup")
    async def thumbsup(self, ctx, member: discord.Member = None):
        """Thumbsup towards a member in chat"""
        member = member or ctx.author
        gif_url = await self.get_gif("thumbsup")
        
        embed = discord.Embed(
            description=f"{ctx.author.mention} gives {member.mention} a thumbs up!",
            color=discord.Color.green()
        )
        embed.set_image(url=gif_url)
        await ctx.send(embed=embed)

    @commands.command(name="hug")
    async def hug(self, ctx, member: discord.Member = None):
        """Hug a member through the bot"""
        if not member:
            await ctx.send("Please specify a member to hug!")
            return
            
        gif_url = await self.get_gif("hug")
        
        embed = discord.Embed(
            description=f"{ctx.author.mention} hugs {member.mention}! 🤗",
            color=discord.Color.purple()
        )
        embed.set_image(url=gif_url)
        await ctx.send(embed=embed)

    @commands.command(name="kiss")
    async def kiss(self, ctx, member: discord.Member = None):
        """Kiss towards a member in chat"""
        if not member:
            await ctx.send("Please specify a member to kiss!")
            return
            
        gif_url = await self.get_gif("kiss")
        
        embed = discord.Embed(
            description=f"{ctx.author.mention} kisses {member.mention}! 💋",
            color=discord.Color.red()
        )
        embed.set_image(url=gif_url)
        await ctx.send(embed=embed)

    @commands.command(name="pat")
    async def pat(self, ctx, member: discord.Member = None):
        """Pat towards a member in chat"""
        if not member:
            await ctx.send("Please specify a member to pat!")
            return
            
        gif_url = await self.get_gif("pat")
        
        embed = discord.Embed(
            description=f"{ctx.author.mention} pats {member.mention} on the head! ✋",
            color=discord.Color.gold()
        )
        embed.set_image(url=gif_url)
        await ctx.send(embed=embed)

    @commands.command(name="slap")
    async def slap(self, ctx, member: discord.Member = None):
        """Slap towards a member in chat"""
        if not member:
            await ctx.send("Please specify a member to slap!")
            return
            
        gif_url = await self.get_gif("slap")
        
        embed = discord.Embed(
            description=f"{ctx.author.mention} slaps {member.mention}! 👋",
            color=discord.Color.orange()
        )
        embed.set_image(url=gif_url)
        await ctx.send(embed=embed)

    @commands.command(name="highfive")
    async def highfive(self, ctx, member: discord.Member = None):
        """Highfive towards a member in chat"""
        if not member:
            await ctx.send("Please specify a member to high five!")
            return
            
        gif_url = await self.get_gif("highfive")
        
        embed = discord.Embed(
            description=f"{ctx.author.mention} high fives {member.mention}! ✋",
            color=discord.Color.green()
        )
        embed.set_image(url=gif_url)
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(EmotionCommands(bot)) 