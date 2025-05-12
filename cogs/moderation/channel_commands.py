import discord
from discord.ext import commands
import logging
import asyncio
import os

logger = logging.getLogger('bot')

class ChannelCommands(commands.Cog):
    """Commands for managing channel settings"""
    
    def __init__(self, bot):
        self.bot = bot
        self.data_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'data', 'channels')
        # Create data directory if it doesn't exist
        os.makedirs(self.data_folder, exist_ok=True)
    
    @commands.group(name="slowmode", invoke_without_command=True)
    @commands.has_permissions(manage_channels=True)
    async def slowmode(self, ctx, seconds: int = None, channel: discord.TextChannel = None):
        """Set slowmode delay for a channel"""
        if channel is None:
            channel = ctx.channel
            
        if seconds is None:
            # If no seconds provided, just show the current slowmode
            current_slowmode = channel.slowmode_delay
            if current_slowmode == 0:
                await ctx.send(f"🕒 {channel.mention} has no slowmode enabled.")
            else:
                await ctx.send(f"🕒 {channel.mention} has a slowmode delay of {current_slowmode} seconds.")
            return
            
        # Validate the input
        if seconds < 0:
            await ctx.send("❌ Slowmode delay cannot be negative.")
            return
            
        if seconds > 21600:  # Discord's max is 6 hours (21600 seconds)
            await ctx.send("❌ Slowmode delay cannot be more than 6 hours (21600 seconds).")
            return
            
        try:
            # Set the slowmode delay
            await channel.edit(slowmode_delay=seconds, reason=f"Slowmode set by {ctx.author}")
            
            if seconds == 0:
                await ctx.send(f"✅ Slowmode has been disabled in {channel.mention}.")
            else:
                # Format time for better readability
                if seconds < 60:
                    time_str = f"{seconds} second{'s' if seconds != 1 else ''}"
                elif seconds < 3600:
                    minutes = seconds // 60
                    time_str = f"{minutes} minute{'s' if minutes != 1 else ''}"
                else:
                    hours = seconds // 3600
                    minutes = (seconds % 3600) // 60
                    time_str = f"{hours} hour{'s' if hours != 1 else ''}"
                    if minutes > 0:
                        time_str += f" and {minutes} minute{'s' if minutes != 1 else ''}"
                        
                await ctx.send(f"✅ Slowmode has been set to {time_str} in {channel.mention}.")
                
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to modify this channel.")
        except discord.HTTPException as e:
            await ctx.send(f"❌ An error occurred: {str(e)}")
            
    @slowmode.command(name="disable")
    @commands.has_permissions(manage_channels=True)
    async def slowmode_disable(self, ctx, channel: discord.TextChannel = None):
        """Disable slowmode for a channel"""
        if channel is None:
            channel = ctx.channel
            
        try:
            await channel.edit(slowmode_delay=0, reason=f"Slowmode disabled by {ctx.author}")
            await ctx.send(f"✅ Slowmode has been disabled in {channel.mention}.")
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to modify this channel.")
        except discord.HTTPException as e:
            await ctx.send(f"❌ An error occurred: {str(e)}")
            
    @slowmode.command(name="all")
    @commands.has_permissions(manage_channels=True, manage_guild=True)
    async def slowmode_all(self, ctx, seconds: int):
        """Set slowmode for all text channels"""
        if seconds < 0:
            await ctx.send("❌ Slowmode delay cannot be negative.")
            return
            
        if seconds > 21600:  # Discord's max is 6 hours (21600 seconds)
            await ctx.send("❌ Slowmode delay cannot be more than 6 hours (21600 seconds).")
            return
            
        # Format time for better readability
        if seconds == 0:
            time_str = "disabled"
        elif seconds < 60:
            time_str = f"{seconds} second{'s' if seconds != 1 else ''}"
        elif seconds < 3600:
            minutes = seconds // 60
            time_str = f"{minutes} minute{'s' if minutes != 1 else ''}"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            time_str = f"{hours} hour{'s' if hours != 1 else ''}"
            if minutes > 0:
                time_str += f" and {minutes} minute{'s' if minutes != 1 else ''}"
                
        # Confirmation message
        confirm_msg = await ctx.send(f"⚠️ Are you sure you want to set slowmode to {time_str} for all text channels? React with ✅ to confirm.")
        await confirm_msg.add_reaction("✅")
        
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) == "✅" and reaction.message.id == confirm_msg.id
            
        try:
            # Wait for confirmation
            await self.bot.wait_for('reaction_add', timeout=30.0, check=check)
            
            # Get a list of all text channels
            text_channels = [channel for channel in ctx.guild.text_channels]
            
            # Send a status message
            status_msg = await ctx.send(f"Setting slowmode for {len(text_channels)} channels...")
            
            # Count successes and failures
            success_count = 0
            failed_channels = []
            
            # Set slowmode for each channel
            for channel in text_channels:
                try:
                    await channel.edit(slowmode_delay=seconds, reason=f"Bulk slowmode set by {ctx.author}")
                    success_count += 1
                except discord.Forbidden:
                    failed_channels.append(channel.mention)
                    logger.warning(f"No permission to edit slowmode for {channel.name}")
                except discord.HTTPException as e:
                    failed_channels.append(channel.mention)
                    logger.warning(f"Error setting slowmode for {channel.name}: {str(e)}")
                except Exception as e:
                    failed_channels.append(channel.mention)
                    logger.error(f"Unexpected error setting slowmode for {channel.name}: {str(e)}")
                    
            # Send completion message
            if not failed_channels:
                await status_msg.edit(content=f"✅ Slowmode has been set to {time_str} for all {success_count} text channels.")
            else:
                failed_str = ", ".join(failed_channels[:5])
                if len(failed_channels) > 5:
                    failed_str += f" and {len(failed_channels) - 5} more"
                await status_msg.edit(content=f"✅ Slowmode set to {time_str} for {success_count} channels.\n❌ Failed for: {failed_str}")
                
        except asyncio.TimeoutError:
            await confirm_msg.edit(content="⚠️ Command timed out. No changes were made.")
            try:
                await confirm_msg.clear_reactions()
            except:
                pass

async def setup(bot):
    """Set up the channel commands cog"""
    await bot.add_cog(ChannelCommands(bot)) 