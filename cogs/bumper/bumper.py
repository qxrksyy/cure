import discord
from discord.ext import commands, tasks
import logging
import datetime
import asyncio
import re

from .bumper_db import BumperDB

logger = logging.getLogger('bot')

class BumpReminder(commands.Cog):
    """BumpReminder for Discord servers using Disboard"""
    
    def __init__(self, bot):
        self.bot = bot
        self.db = BumperDB()
        self.check_reminders.start()
        
    async def cog_load(self):
        """Initialize the cog on load"""
        await self.db.initialize()
        
    def cog_unload(self):
        """Clean up on cog unload"""
        self.check_reminders.cancel()
        
    @tasks.loop(minutes=1)
    async def check_reminders(self):
        """Check for reminders that need to be sent"""
        try:
            due_reminders = await self.db.get_due_reminders()
            
            for reminder in due_reminders:
                guild = self.bot.get_guild(int(reminder['guild_id']))
                if not guild:
                    continue
                    
                channel = guild.get_channel(int(reminder['channel_id']))
                if not channel:
                    continue
                    
                # Send reminder message
                try:
                    message = reminder['reminder_message'] or "Time to bump the server! Type /bump"
                    await channel.send(message)
                    
                    # Handle autolock if enabled
                    if reminder['autolock']:
                        # Set channel permissions to allow /bump but restrict general messages
                        try:
                            overwrites = channel.overwrites_for(guild.default_role)
                            overwrites.send_messages = False
                            await channel.set_permissions(guild.default_role, overwrite=overwrites)
                            await channel.send("Channel locked until the server is bumped. Only `/bump` command will work.")
                        except discord.Forbidden:
                            await channel.send("I don't have permission to lock the channel. Please give me 'Manage Channels' permission.")
                except Exception as e:
                    logger.error(f"Error sending reminder for guild {guild.id}: {e}")
        except Exception as e:
            logger.error(f"Error in check_reminders task: {e}")
    
    @check_reminders.before_loop
    async def before_check_reminders(self):
        """Wait for the bot to be ready before starting the loop"""
        await self.bot.wait_until_ready()
        
    @commands.group(name="bumpreminder", aliases=["bump", "br"], invoke_without_command=True)
    @commands.has_permissions(manage_channels=True)
    async def bumpreminder(self, ctx):
        """Get reminders to /bump your server on Disboard!"""
        # If no subcommand is called, show help
        settings = await self.db.get_guild_settings(ctx.guild.id)
        
        if not settings:
            embed = discord.Embed(
                title="Bump Reminder",
                description="Bump Reminder is not set up for this server yet.",
                color=discord.Color.blue()
            )
            embed.add_field(name="Setup", value="Use `!bumpreminder channel #channel` to set up bump reminders.")
            await ctx.send(embed=embed)
            return
            
        # Show current settings
        channel = ctx.guild.get_channel(int(settings['channel_id'])) if settings['channel_id'] else None
        
        embed = discord.Embed(
            title="Bump Reminder Settings",
            color=discord.Color.blue()
        )
        
        embed.add_field(name="Status", value="Enabled" if settings['enabled'] else "Disabled", inline=True)
        embed.add_field(name="Channel", value=channel.mention if channel else "Not set", inline=True)
        embed.add_field(name="Auto-clean", value="Enabled" if settings['autoclean'] else "Disabled", inline=True)
        embed.add_field(name="Auto-lock", value="Enabled" if settings['autolock'] else "Disabled", inline=True)
        
        if settings['last_bumped']:
            last_bumped = datetime.datetime.fromisoformat(settings['last_bumped'])
            embed.add_field(name="Last Bumped", value=f"<t:{int(last_bumped.timestamp())}:R>", inline=True)
            
        if settings['next_bump']:
            next_bump = datetime.datetime.fromisoformat(settings['next_bump'])
            embed.add_field(name="Next Bump", value=f"<t:{int(next_bump.timestamp())}:R>", inline=True)
            
        await ctx.send(embed=embed)
    
    @bumpreminder.command(name="channel")
    @commands.has_permissions(manage_channels=True)
    async def set_channel(self, ctx, channel: discord.TextChannel):
        """Set Bump Reminder channel for the server"""
        success = await self.db.set_channel(ctx.guild.id, str(channel.id))
        
        if success:
            embed = discord.Embed(
                title="Bump Reminder Channel Set",
                description=f"Bump reminders will now be sent to {channel.mention}.",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="Error",
                description="Failed to set bump reminder channel. Please try again.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
    
    @bumpreminder.command(name="autoclean")
    @commands.has_permissions(manage_channels=True)
    async def set_autoclean(self, ctx, choice: str):
        """Automatically delete messages that aren't /bump"""
        choice = choice.lower()
        
        if choice not in ["on", "off", "enable", "disable", "true", "false"]:
            embed = discord.Embed(
                title="Invalid Choice",
                description="Please use 'on' or 'off' to enable or disable auto-clean.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        enabled = choice in ["on", "enable", "true"]
        success = await self.db.set_autoclean(ctx.guild.id, enabled)
        
        if success:
            embed = discord.Embed(
                title="Auto-clean " + ("Enabled" if enabled else "Disabled"),
                description=f"Messages that aren't /bump will {'now' if enabled else 'no longer'} be automatically deleted.",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="Error",
                description="Failed to update auto-clean setting. Please try again.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
    
    @bumpreminder.command(name="autolock")
    @commands.has_permissions(manage_channels=True)
    async def set_autolock(self, ctx, choice: str):
        """Lock channel until ready to use /bump"""
        choice = choice.lower()
        
        if choice not in ["on", "off", "enable", "disable", "true", "false"]:
            embed = discord.Embed(
                title="Invalid Choice",
                description="Please use 'on' or 'off' to enable or disable auto-lock.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        enabled = choice in ["on", "enable", "true"]
        success = await self.db.set_autolock(ctx.guild.id, enabled)
        
        if success:
            embed = discord.Embed(
                title="Auto-lock " + ("Enabled" if enabled else "Disabled"),
                description=f"The channel will {'now' if enabled else 'no longer'} be locked until the server is bumped.",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="Error",
                description="Failed to update auto-lock setting. Please try again.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
    
    @bumpreminder.group(name="message", invoke_without_command=True)
    @commands.has_permissions(manage_channels=True)
    async def message(self, ctx, *, message: str = None):
        """Set the reminder message to run /bump"""
        if message is None:
            await ctx.invoke(self.message_view)
            return
            
        success = await self.db.set_reminder_message(ctx.guild.id, message)
        
        if success:
            embed = discord.Embed(
                title="Reminder Message Set",
                description="The reminder message has been updated.",
                color=discord.Color.green()
            )
            embed.add_field(name="New Message", value=message)
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="Error",
                description="Failed to update reminder message. Please try again.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
    
    @message.command(name="view")
    @commands.has_permissions(manage_channels=True)
    async def message_view(self, ctx):
        """View the current remind message"""
        settings = await self.db.get_guild_settings(ctx.guild.id)
        
        if not settings or not settings.get('reminder_message'):
            embed = discord.Embed(
                title="Reminder Message",
                description="No custom reminder message set. Using default message.",
                color=discord.Color.blue()
            )
            embed.add_field(name="Default Message", value="Time to bump the server! Type /bump")
        else:
            embed = discord.Embed(
                title="Reminder Message",
                description="Current reminder message:",
                color=discord.Color.blue()
            )
            embed.add_field(name="Message", value=settings['reminder_message'])
            
        await ctx.send(embed=embed)
    
    @bumpreminder.group(name="thankyou", invoke_without_command=True)
    @commands.has_permissions(manage_channels=True)
    async def thankyou(self, ctx, *, message: str = None):
        """Set the 'Thank You' message for successfully running /bump"""
        if message is None:
            await ctx.invoke(self.thankyou_view)
            return
            
        success = await self.db.set_thankyou_message(ctx.guild.id, message)
        
        if success:
            embed = discord.Embed(
                title="Thank You Message Set",
                description="The thank you message has been updated.",
                color=discord.Color.green()
            )
            embed.add_field(name="New Message", value=message)
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="Error",
                description="Failed to update thank you message. Please try again.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
    
    @thankyou.command(name="view")
    @commands.has_permissions(manage_channels=True)
    async def thankyou_view(self, ctx):
        """View the current Thank You message"""
        settings = await self.db.get_guild_settings(ctx.guild.id)
        
        if not settings or not settings.get('thankyou_message'):
            embed = discord.Embed(
                title="Thank You Message",
                description="No custom thank you message set. Using default message.",
                color=discord.Color.blue()
            )
            embed.add_field(name="Default Message", value="Thanks for bumping the server! I will remind you in 2 hours.")
        else:
            embed = discord.Embed(
                title="Thank You Message",
                description="Current thank you message:",
                color=discord.Color.blue()
            )
            embed.add_field(name="Message", value=settings['thankyou_message'])
            
        await ctx.send(embed=embed)
    
    @bumpreminder.command(name="config")
    @commands.has_permissions(manage_channels=True)
    async def config(self, ctx):
        """View server configuration for Bump Reminder"""
        settings = await self.db.get_guild_settings(ctx.guild.id)
        
        if not settings:
            embed = discord.Embed(
                title="Bump Reminder Configuration",
                description="Bump Reminder is not set up for this server yet.",
                color=discord.Color.blue()
            )
            embed.add_field(name="Setup", value="Use `!bumpreminder channel #channel` to set up bump reminders.")
            await ctx.send(embed=embed)
            return
            
        # Show detailed configuration
        channel = ctx.guild.get_channel(int(settings['channel_id'])) if settings['channel_id'] else None
        
        embed = discord.Embed(
            title="Bump Reminder Configuration",
            color=discord.Color.blue()
        )
        
        embed.add_field(name="Status", value="Enabled" if settings['enabled'] else "Disabled", inline=True)
        embed.add_field(name="Channel", value=channel.mention if channel else "Not set", inline=True)
        embed.add_field(name="Auto-clean", value="Enabled" if settings['autoclean'] else "Disabled", inline=True)
        embed.add_field(name="Auto-lock", value="Enabled" if settings['autolock'] else "Disabled", inline=True)
        
        if settings['reminder_message']:
            embed.add_field(name="Reminder Message", value=settings['reminder_message'], inline=False)
            
        if settings['thankyou_message']:
            embed.add_field(name="Thank You Message", value=settings['thankyou_message'], inline=False)
            
        if settings['last_bumped']:
            last_bumped = datetime.datetime.fromisoformat(settings['last_bumped'])
            embed.add_field(name="Last Bumped", value=f"<t:{int(last_bumped.timestamp())}:R>", inline=True)
            
        if settings['next_bump']:
            next_bump = datetime.datetime.fromisoformat(settings['next_bump'])
            embed.add_field(name="Next Bump", value=f"<t:{int(next_bump.timestamp())}:R>", inline=True)
            
        # Get bump stats
        stats = await self.db.get_bump_stats(ctx.guild.id)
        
        embed.add_field(name="Total Bumps (30 days)", value=stats['total_bumps'], inline=False)
        
        if stats['top_bumpers']:
            top_bumpers = []
            for i, bumper in enumerate(stats['top_bumpers'][:5], 1):
                user = self.bot.get_user(int(bumper['user_id']))
                user_name = user.name if user else f"User {bumper['user_id']}"
                top_bumpers.append(f"{i}. {user_name}: {bumper['count']} bumps")
                
            embed.add_field(name="Top Bumpers", value="\n".join(top_bumpers) or "No bumps recorded", inline=False)
            
        await ctx.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_message(self, message):
        """Monitor for Disboard bump messages"""
        # Ignore messages from bots other than Disboard
        if message.author.bot and message.author.id != 302050872383242240:  # Disboard bot ID
            return
            
        # Check if this is a bump command
        if message.author.id != 302050872383242240:
            # Check if autoclean is enabled for this channel
            if not message.guild:
                return
                
            settings = await self.db.get_guild_settings(message.guild.id)
            if not settings or not settings.get('channel_id') or int(settings['channel_id']) != message.channel.id:
                return
                
            if settings.get('autoclean') and message.content != "/bump":
                try:
                    await message.delete()
                except discord.Forbidden:
                    pass
                
            return
            
        # Check if this is a successful bump message from Disboard
        if "bump done" in message.content.lower():
            # Looks like a successful bump
            settings = await self.db.get_guild_settings(message.guild.id)
            if not settings:
                return
                
            # Find the user who did the bump by checking the previous message
            async for msg in message.channel.history(limit=5, before=message):
                if msg.content == "/bump" and not msg.author.bot:
                    # This user did the bump
                    await self.db.log_bump(message.guild.id, msg.author.id)
                    
                    # Send thank you message
                    thank_you = settings.get('thankyou_message') or "Thanks for bumping the server! I will remind you in 2 hours."
                    await message.channel.send(thank_you)
                    
                    # If autolock is enabled, unlock the channel
                    if settings.get('autolock'):
                        try:
                            overwrites = message.channel.overwrites_for(message.guild.default_role)
                            overwrites.send_messages = None  # Reset to server default
                            await message.channel.set_permissions(message.guild.default_role, overwrite=overwrites)
                            await message.channel.send("Channel unlocked! Thank you for bumping the server.")
                        except discord.Forbidden:
                            pass
                    
                    break

async def setup(bot):
    """Load the BumpReminder cog"""
    await bot.add_cog(BumpReminder(bot)) 