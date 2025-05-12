import discord
from discord.ext import commands
import platform
import datetime
import time
import logging

logger = logging.getLogger('bot')

class Utility(commands.Cog):
    """Utility commands for server information and user information"""
    
    def __init__(self, bot):
        self.bot = bot
        self.start_time = time.time()
        
    def get_uptime(self):
        """Get bot uptime as a formatted string"""
        uptime = int(time.time() - self.start_time)
        days, remainder = divmod(uptime, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        if seconds > 0 or not parts:
            parts.append(f"{seconds}s")
            
        return " ".join(parts)
        
    @commands.command(name="botping", aliases=["latencycheck"])
    async def ping(self, ctx):
        """Get the bot's latency"""
        start = time.perf_counter()
        message = await ctx.send("Pinging...")
        end = time.perf_counter()
        
        api_latency = round(self.bot.latency * 1000)
        message_latency = round((end - start) * 1000)
        
        embed = discord.Embed(
            title="🏓 Pong!",
            color=discord.Color.blue(),
            timestamp=datetime.datetime.utcnow()
        )
        embed.add_field(name="Bot Latency", value=f"{message_latency}ms", inline=True)
        embed.add_field(name="API Latency", value=f"{api_latency}ms", inline=True)
        embed.set_footer(text=f"Requested by {ctx.author}")
        
        await message.edit(content=None, embed=embed)
        
    @commands.command(name="serverinfo", aliases=["server", "guildinfo"])
    async def serverinfo(self, ctx):
        """Display information about the current server"""
        guild = ctx.guild
        
        # Count roles, channels, and emojis
        role_count = len(guild.roles)
        text_channels = len([c for c in guild.channels if isinstance(c, discord.TextChannel)])
        voice_channels = len([c for c in guild.channels if isinstance(c, discord.VoiceChannel)])
        emoji_count = len(guild.emojis)
        
        # Count members by status if possible
        online = 0
        idle = 0
        dnd = 0
        offline = 0
        
        for member in guild.members:
            if member.status == discord.Status.online:
                online += 1
            elif member.status == discord.Status.idle:
                idle += 1
            elif member.status == discord.Status.dnd:
                dnd += 1
            else:
                offline += 1
                
        # Create the embed
        embed = discord.Embed(
            title=f"{guild.name} Server Information",
            color=guild.me.color,
            timestamp=datetime.datetime.utcnow()
        )
        
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
            
        # General info
        embed.add_field(name="Server ID", value=guild.id, inline=True)
        embed.add_field(name="Owner", value=guild.owner.mention, inline=True)
        embed.add_field(name="Region", value=str(guild.region).title() if hasattr(guild, 'region') else "Unknown", inline=True)
        
        # Member counts
        embed.add_field(name="Total Members", value=guild.member_count, inline=True)
        embed.add_field(name="Humans", value=len([m for m in guild.members if not m.bot]), inline=True)
        embed.add_field(name="Bots", value=len([m for m in guild.members if m.bot]), inline=True)
        
        # Status counts
        embed.add_field(name="Member Status", 
            value=f"🟢 {online} 🟠 {idle} 🔴 {dnd} ⚫ {offline}", 
            inline=False)
        
        # Channel and role counts
        embed.add_field(name="Text Channels", value=text_channels, inline=True)
        embed.add_field(name="Voice Channels", value=voice_channels, inline=True)
        embed.add_field(name="Roles", value=role_count, inline=True)
        
        # Additional info
        embed.add_field(name="Emojis", value=f"{emoji_count}/{guild.emoji_limit}", inline=True)
        
        # Dates
        embed.add_field(name="Created On", 
            value=f"{discord.utils.format_dt(guild.created_at, style='F')} ({discord.utils.format_dt(guild.created_at, style='R')})", 
            inline=False)
        
        # Server features
        if guild.features:
            features_str = ", ".join(f"`{feature.replace('_', ' ').title()}`" for feature in guild.features)
            embed.add_field(name="Server Features", value=features_str, inline=False)
            
        # Server boost info
        boost_level = str(guild.premium_tier)
        boosts = guild.premium_subscription_count
        
        embed.add_field(name="Boost Level", value=f"Level {boost_level} ({boosts} boosts)", inline=True)
        
        if guild.premium_subscribers:
            boosters_count = len(guild.premium_subscribers)
            embed.add_field(name="Boosters", value=boosters_count, inline=True)
            
        # Footer
        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)
        
        await ctx.send(embed=embed)
        
    @commands.command(name="userinfo", aliases=["user", "whois", "ui"])
    async def userinfo(self, ctx, member: discord.Member = None):
        """Display information about a user"""
        member = member or ctx.author
        
        # Calculate dates
        joined_days = (datetime.datetime.utcnow() - member.joined_at).days
        created_days = (datetime.datetime.utcnow() - member.created_at).days
        
        # Get roles
        roles = [role.mention for role in reversed(member.roles) if role.name != "@everyone"]
        roles_str = " ".join(roles) if roles else "None"
        
        # Create embed
        embed = discord.Embed(
            title=f"{member.name}'s Information",
            color=member.color,
            timestamp=datetime.datetime.utcnow()
        )
        
        embed.set_thumbnail(url=member.display_avatar.url)
        
        # Basic info
        embed.add_field(name="User ID", value=member.id, inline=True)
        embed.add_field(name="Nickname", value=member.nick or "None", inline=True)
        embed.add_field(name="Bot", value="Yes" if member.bot else "No", inline=True)
        
        # Status and activity
        status_emoji = {
            discord.Status.online: "🟢 Online",
            discord.Status.idle: "🟠 Idle",
            discord.Status.dnd: "🔴 Do Not Disturb",
            discord.Status.offline: "⚫ Offline"
        }
        
        embed.add_field(name="Status", value=status_emoji.get(member.status, "Unknown"), inline=True)
        
        # Get top role
        if len(member.roles) > 1:
            embed.add_field(name="Highest Role", value=member.top_role.mention, inline=True)
            
        # Check for booster status
        is_booster = bool(member.premium_since)
        embed.add_field(name="Server Booster", value="Yes" if is_booster else "No", inline=True)
        
        # Dates
        embed.add_field(name="Joined Server", 
            value=f"{discord.utils.format_dt(member.joined_at, style='F')} ({joined_days} days ago)", 
            inline=False)
            
        embed.add_field(name="Account Created", 
            value=f"{discord.utils.format_dt(member.created_at, style='F')} ({created_days} days ago)", 
            inline=False)
            
        # Roles
        if len(roles) > 0:
            if len(roles) <= 10:
                embed.add_field(name=f"Roles [{len(roles)}]", value=roles_str, inline=False)
            else:
                embed.add_field(name=f"Roles [{len(roles)}]", value=f"{' '.join(roles[:10])}... and {len(roles) - 10} more", inline=False)
                
        # Additional info if available (permissions, etc.)
        
        # Footer
        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)
        
        await ctx.send(embed=embed)
        
    @commands.command(name="avatar", aliases=["av", "pfp"])
    async def avatar(self, ctx, member: discord.Member = None):
        """Display a user's avatar"""
        member = member or ctx.author
        
        embed = discord.Embed(
            title=f"{member.name}'s Avatar",
            color=member.color,
            timestamp=datetime.datetime.utcnow()
        )
        
        # Get both the default and server avatar if applicable
        embed.set_image(url=member.display_avatar.url)
        
        # Add links for different formats
        formats = []
        if member.display_avatar.url.endswith(".gif"):
            formats.append(f"[GIF]({member.display_avatar.url})")
        formats.append(f"[PNG]({member.display_avatar.replace(format='png', size=1024).url})")
        formats.append(f"[JPG]({member.display_avatar.replace(format='jpg', size=1024).url})")
        formats.append(f"[WEBP]({member.display_avatar.replace(format='webp', size=1024).url})")
        
        embed.add_field(name="Download", value=" | ".join(formats), inline=False)
        
        # Check if they have a different server avatar
        if member.guild_avatar and member.guild_avatar != member.avatar:
            embed.add_field(name="Server Avatar", value=f"[Link]({member.guild_avatar.url})", inline=True)
            
        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)
        
        await ctx.send(embed=embed)
        
    @commands.command(name="botinfo", aliases=["about", "info"])
    async def botinfo(self, ctx):
        """Display information about the bot"""
        # Calculate uptime
        uptime = self.get_uptime()
        
        # Get bot stats
        server_count = len(self.bot.guilds)
        member_count = sum(g.member_count for g in self.bot.guilds)
        channel_count = sum(len(g.channels) for g in self.bot.guilds)
        command_count = len(self.bot.commands)
        
        # Create embed
        embed = discord.Embed(
            title=f"{self.bot.user.name} Information",
            description="A multi-purpose Discord bot with moderation, utility, and fun commands!",
            color=discord.Color.blue(),
            timestamp=datetime.datetime.utcnow()
        )
        
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        
        # Bot stats
        embed.add_field(name="Bot ID", value=self.bot.user.id, inline=True)
        embed.add_field(name="Created", value=discord.utils.format_dt(self.bot.user.created_at, style='R'), inline=True)
        embed.add_field(name="Uptime", value=uptime, inline=True)
        
        # Usage stats
        embed.add_field(name="Servers", value=server_count, inline=True)
        embed.add_field(name="Members", value=member_count, inline=True)
        embed.add_field(name="Channels", value=channel_count, inline=True)
        
        # Technical info
        embed.add_field(name="Commands", value=command_count, inline=True)
        embed.add_field(name="Python", value=platform.python_version(), inline=True)
        embed.add_field(name="Discord.py", value=discord.__version__, inline=True)
        
        # Links
        embed.add_field(name="Links", 
            value="[Support Server](https://discord.gg/example) | [Invite Bot](https://discord.com/oauth2/authorize?client_id={self.bot.user.id}&permissions=8&scope=bot%20applications.commands) | [GitHub](https://github.com/example/bot)", 
            inline=False)
            
        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)
        
        await ctx.send(embed=embed)
        
    @commands.command(name="membercount", aliases=["members"])
    async def membercount(self, ctx):
        """Display the server's member count"""
        guild = ctx.guild
        
        total = guild.member_count
        humans = len([m for m in guild.members if not m.bot])
        bots = len([m for m in guild.members if m.bot])
        
        embed = discord.Embed(
            title=f"{guild.name} Member Count",
            color=discord.Color.green(),
            timestamp=datetime.datetime.utcnow()
        )
        
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
            
        embed.add_field(name="Total Members", value=total, inline=True)
        embed.add_field(name="Humans", value=humans, inline=True)
        embed.add_field(name="Bots", value=bots, inline=True)
        
        # Calculate online counts if available
        online = len([m for m in guild.members if m.status == discord.Status.online])
        idle = len([m for m in guild.members if m.status == discord.Status.idle])
        dnd = len([m for m in guild.members if m.status == discord.Status.dnd])
        offline = len([m for m in guild.members if m.status == discord.Status.offline])
        
        embed.add_field(name="Online", value=f"🟢 {online}", inline=True)
        embed.add_field(name="Idle", value=f"🟠 {idle}", inline=True)
        embed.add_field(name="Do Not Disturb", value=f"🔴 {dnd}", inline=True)
        embed.add_field(name="Offline", value=f"⚫ {offline}", inline=True)
        
        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Utility(bot)) 