import discord
from discord.ext import commands
import json
import os
import logging
from datetime import datetime
import asyncio

logger = logging.getLogger('bot')

class Counters(commands.Cog):
    """Commands to set up channel counters for member count and booster count"""
    
    def __init__(self, bot):
        self.bot = bot
        self.config_path = "data/counters"
        self.counters = {}
        self.update_task = None
        
        # Create directory if it doesn't exist
        os.makedirs(self.config_path, exist_ok=True)
        
        # Load settings
        self._load_counters()
        
    def cog_unload(self):
        """Called when the cog is unloaded"""
        if self.update_task:
            self.update_task.cancel()
    
    async def cog_load(self):
        """Called when the cog is loaded"""
        self.update_task = self.bot.loop.create_task(self._update_counters_loop())
    
    def _load_counters(self):
        """Load counters from file"""
        try:
            filepath = f"{self.config_path}/counters.json"
            if os.path.exists(filepath):
                with open(filepath, "r") as f:
                    self.counters = json.load(f)
        except Exception as e:
            logger.error(f"Error loading counters: {str(e)}")
            self.counters = {}
    
    def _save_counters(self):
        """Save counters to file"""
        try:
            filepath = f"{self.config_path}/counters.json"
            with open(filepath, "w") as f:
                json.dump(self.counters, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving counters: {str(e)}")
    
    def _get_guild_counters(self, guild_id):
        """Get counters for a guild"""
        guild_id = str(guild_id)
        if guild_id not in self.counters:
            self.counters[guild_id] = []
            self._save_counters()
        return self.counters[guild_id]
    
    async def _update_counters_loop(self):
        """Loop to periodically update all counters"""
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            try:
                await self._update_all_counters()
                await asyncio.sleep(300)  # Update every 5 minutes
            except Exception as e:
                logger.error(f"Error in counter update loop: {str(e)}")
                await asyncio.sleep(60)  # Shorter wait if there was an error
    
    async def _update_all_counters(self):
        """Update all counters for all guilds"""
        for guild_id, guild_counters in self.counters.items():
            try:
                guild = self.bot.get_guild(int(guild_id))
                if not guild:
                    continue
                
                for counter in guild_counters:
                    try:
                        await self._update_counter(guild, counter)
                    except Exception as e:
                        logger.error(f"Error updating counter in guild {guild_id}: {str(e)}")
            except Exception as e:
                logger.error(f"Error processing guild {guild_id}: {str(e)}")
    
    async def _update_counter(self, guild, counter):
        """Update a specific counter"""
        try:
            channel_id = counter["channel_id"]
            channel = guild.get_channel(int(channel_id))
            
            if not channel:
                return  # Channel no longer exists
            
            counter_type = counter["type"]
            
            if counter_type == "members":
                count = guild.member_count
                name = counter["format"].replace("{count}", str(count))
            elif counter_type == "boosters":
                count = len(guild.premium_subscribers)
                name = counter["format"].replace("{count}", str(count))
            else:
                return  # Unknown counter type
            
            if channel.name != name:
                await channel.edit(name=name)
                logger.info(f"Updated counter for {guild.name} ({guild.id}): {name}")
        
        except discord.Forbidden:
            logger.warning(f"Missing permissions to update counter in {guild.name} ({guild.id})")
        except Exception as e:
            logger.error(f"Error updating counter: {str(e)}")
    
    @commands.group(name="counter", invoke_without_command=True)
    @commands.has_permissions(manage_channels=True)
    async def counter(self, ctx):
        """Create a category or channel that will keep track of the member or booster count"""
        embed = discord.Embed(
            title="Server Counters",
            description="Create channels that display member or booster counts",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(
            name="Available Commands",
            value=(
                "`counter add` - Create a new counter channel\n"
                "`counter remove` - Remove an existing counter\n"
                "`counter list` - View all counters in this server\n"
            ),
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @counter.command(name="add")
    @commands.has_permissions(manage_channels=True)
    async def counter_add(self, ctx, counter_type: str = None, *, channel_name: str = None):
        """Create channel counter"""
        if not counter_type:
            await ctx.send("❌ Please specify a counter type: `members` or `boosters`")
            return
        
        if counter_type.lower() not in ["members", "boosters"]:
            await ctx.send("❌ Invalid counter type. Please use `members` or `boosters`")
            return
        
        # Default channel name formats
        if not channel_name:
            if counter_type.lower() == "members":
                channel_name = "Members: {count}"
            else:
                channel_name = "Boosters: {count}"
        
        if "{count}" not in channel_name:
            await ctx.send("❌ Channel name must include `{count}` placeholder")
            return
        
        # Create voice channel
        try:
            # Create a voice channel that will be used for display only
            overwrites = {
                ctx.guild.default_role: discord.PermissionOverwrite(connect=False)
            }
            
            counter_type_lower = counter_type.lower()
            
            if counter_type_lower == "members":
                count = ctx.guild.member_count
            else:  # boosters
                count = len(ctx.guild.premium_subscribers)
            
            # Replace the count placeholder
            initial_name = channel_name.replace("{count}", str(count))
            
            # Create the channel
            channel = await ctx.guild.create_voice_channel(
                name=initial_name,
                overwrites=overwrites,
                reason=f"Counter channel created by {ctx.author}"
            )
            
            # Save to config
            guild_counters = self._get_guild_counters(ctx.guild.id)
            
            guild_counters.append({
                "channel_id": str(channel.id),
                "type": counter_type_lower,
                "format": channel_name,
                "created_by": str(ctx.author.id),
                "created_at": datetime.utcnow().isoformat()
            })
            
            self._save_counters()
            
            await ctx.send(f"✅ Created counter channel: {channel.mention}")
            
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to create channels")
        except Exception as e:
            logger.error(f"Error creating counter: {str(e)}")
            await ctx.send(f"❌ An error occurred: {str(e)}")
    
    @counter.command(name="remove")
    @commands.has_permissions(manage_channels=True)
    async def counter_remove(self, ctx, channel: discord.TextChannel = None):
        """Remove a channel or category counter"""
        if not channel:
            await ctx.send("❌ Please mention a channel to remove")
            return
        
        guild_counters = self._get_guild_counters(ctx.guild.id)
        
        # Find the counter by channel ID
        counter_index = None
        for i, counter in enumerate(guild_counters):
            if counter["channel_id"] == str(channel.id):
                counter_index = i
                break
        
        if counter_index is None:
            await ctx.send("❌ This channel is not a counter")
            return
        
        # Remove from config
        removed_counter = guild_counters.pop(counter_index)
        self._save_counters()
        
        # Ask if the channel should also be deleted
        embed = discord.Embed(
            title="Counter Removed",
            description=f"Counter for channel {channel.mention} has been removed from the config.",
            color=discord.Color.orange(),
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(
            name="Delete Channel?",
            value="Would you also like to delete the channel itself?",
            inline=False
        )
        
        msg = await ctx.send(embed=embed)
        
        # Add reactions for yes/no
        await msg.add_reaction("✅")
        await msg.add_reaction("❌")
        
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == msg.id
        
        try:
            reaction, user = await self.bot.wait_for("reaction_add", timeout=60.0, check=check)
            
            if str(reaction.emoji) == "✅":
                try:
                    await channel.delete(reason=f"Counter removed by {ctx.author}")
                    await ctx.send("✅ Channel deleted successfully")
                except discord.Forbidden:
                    await ctx.send("❌ I don't have permission to delete that channel")
                except Exception as e:
                    await ctx.send(f"❌ An error occurred while deleting the channel: {str(e)}")
        
        except asyncio.TimeoutError:
            await ctx.send("❌ Timed out waiting for a response. The channel was not deleted.")
    
    @counter.command(name="list")
    @commands.has_permissions(manage_channels=True)
    async def counter_list(self, ctx):
        """List every category or channel keeping track of members or boosters in this server"""
        guild_counters = self._get_guild_counters(ctx.guild.id)
        
        if not guild_counters:
            await ctx.send("❌ There are no counters set up in this server")
            return
        
        embed = discord.Embed(
            title="Server Counters",
            description=f"This server has {len(guild_counters)} counter{'s' if len(guild_counters) != 1 else ''}",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        for counter in guild_counters:
            channel = ctx.guild.get_channel(int(counter["channel_id"]))
            channel_text = channel.mention if channel else f"Unknown Channel ({counter['channel_id']})"
            
            embed.add_field(
                name=f"{counter['type'].title()} Counter",
                value=(
                    f"**Channel:** {channel_text}\n"
                    f"**Format:** {counter['format']}\n"
                    f"**Created By:** <@{counter['created_by']}>\n"
                ),
                inline=False
            )
        
        await ctx.send(embed=embed)

async def setup(bot):
    counters_cog = Counters(bot)
    await bot.add_cog(counters_cog)
    
    # Import and load events with counters_cog reference
    try:
        from . import events
        await events.setup(bot, counters_cog)
        logger.info("Loaded counter events extension")
    except Exception as e:
        logger.error(f"Error loading counter events: {str(e)}") 