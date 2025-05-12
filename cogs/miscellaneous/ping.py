import discord
from discord.ext import commands
import asyncio
import logging
from datetime import datetime

logger = logging.getLogger('bot')

class PingTools(commands.Cog):
    """
    Tools for mass pinging and related functionality
    """
    
    def __init__(self, bot):
        self.bot = bot
        self.active_pings = {}  # Store guild ID -> task for active pingall tasks
    
    def cog_unload(self):
        """Clean up any running ping tasks when the cog is unloaded"""
        for guild_id, task in self.active_pings.items():
            if not task.done():
                task.cancel()
                
        self.active_pings.clear()
    
    @commands.command()
    @commands.has_permissions(manage_guild=True)
    async def pingall(self, ctx):
        """Mention every member with access to the current channel"""
        # Check if there's already an active ping task for this guild
        if ctx.guild.id in self.active_pings:
            await ctx.send("❌ There's already a pingall task running in this server. Use `pingall cancel` to stop it.")
            return
            
        # Get the list of members who can see this channel
        visible_members = [member for member in ctx.guild.members 
                          if ctx.channel.permissions_for(member).read_messages 
                          and not member.bot]
                          
        if not visible_members:
            await ctx.send("❌ No members with access to this channel were found.")
            return
            
        # Create a confirmation message
        confirm_message = await ctx.send(
            f"⚠️ This will ping {len(visible_members)} members in this channel. "
            f"Are you sure? React with ✅ to confirm or ❌ to cancel. "
            f"This will expire in 30 seconds."
        )
        
        # Add reactions for confirmation
        await confirm_message.add_reaction('✅')
        await confirm_message.add_reaction('❌')
        
        # Wait for the user's reaction
        def check(reaction, user):
            return (user == ctx.author and 
                   reaction.message.id == confirm_message.id and 
                   str(reaction.emoji) in ['✅', '❌'])
        
        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=check)
            
            # If user cancels
            if str(reaction.emoji) == '❌':
                await confirm_message.edit(content="❌ Pingall cancelled.")
                return
                
            # If user confirms, proceed with the pingall
            if str(reaction.emoji) == '✅':
                # Start the pingall task
                task = asyncio.create_task(self._pingall_task(ctx, visible_members, confirm_message))
                self.active_pings[ctx.guild.id] = task
                
                # Wait for the task to complete or be cancelled
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                finally:
                    # Remove the task when it's done
                    if ctx.guild.id in self.active_pings:
                        del self.active_pings[ctx.guild.id]
                
        except asyncio.TimeoutError:
            await confirm_message.edit(content="❌ Pingall timed out. No action taken.")
    
    async def _pingall_task(self, ctx, members, status_message):
        """Execute the pingall task"""
        # Update status message
        await status_message.edit(content=f"📢 Starting to ping {len(members)} members...")
        
        # Create the initial announcement message
        announce_embed = discord.Embed(
            title="📢 Mass Mention",
            description=f"Attention all members! This is a server-wide announcement.",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        announce_embed.add_field(
            name="Initiated By",
            value=ctx.author.mention,
            inline=True
        )
        
        announce_embed.add_field(
            name="Channel",
            value=ctx.channel.mention,
            inline=True
        )
        
        announce_embed.set_footer(text="Please wait while all members are mentioned.")
        
        announcement = await ctx.send(embed=announce_embed)
        
        # Ping members in chunks to avoid rate limits
        chunk_size = 5  # Number of members to ping in each message
        chunks = [members[i:i + chunk_size] for i in range(0, len(members), chunk_size)]
        
        for i, chunk in enumerate(chunks):
            # Update status occasionally
            if i % 10 == 0 and i > 0:
                progress = int((i / len(chunks)) * 100)
                await status_message.edit(content=f"📢 Pingall in progress: {progress}% complete ({i * chunk_size}/{len(members)} members)")
            
            # Create the mention string for this chunk
            mentions = " ".join(member.mention for member in chunk)
            
            try:
                # Send the mentions
                ping_message = await ctx.send(mentions)
                
                # Delete immediately to reduce spam
                await ping_message.delete()
                
                # Small delay to avoid rate limits
                await asyncio.sleep(1.5)
                
            except discord.HTTPException as e:
                logger.error(f"Error in pingall: {str(e)}")
                await status_message.edit(content=f"❌ Error occurred during pingall: {str(e)}")
                return
                
            # Check if the task should be cancelled (e.g., from pingall cancel)
            if asyncio.current_task().cancelled():
                return
        
        # Update the announcement with completion
        final_embed = announce_embed.copy()
        final_embed.description = f"Attention all members! This is a server-wide announcement.\n\n**All {len(members)} members have been notified.**"
        final_embed.set_footer(text="All members have been pinged.")
        
        await announcement.edit(embed=final_embed)
        await status_message.edit(content=f"✅ Pingall complete! {len(members)} members were notified.")
    
    @commands.command(name="pingall_cancel")
    @commands.has_permissions(manage_guild=True)
    async def pingall_cancel(self, ctx):
        """End a currently ongoing pingall task"""
        if ctx.guild.id not in self.active_pings:
            await ctx.send("❌ There's no active pingall task running in this server.")
            return
            
        # Cancel the task
        task = self.active_pings[ctx.guild.id]
        if not task.done():
            task.cancel()
            
        # Remove from active pings
        del self.active_pings[ctx.guild.id]
        
        await ctx.send("✅ Pingall task has been cancelled.")
    
    @pingall.error
    @pingall_cancel.error
    async def pingall_error(self, ctx, error):
        """Error handler for pingall commands"""
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You need the Manage Server permission to use this command.")
        else:
            logger.error(f"Error in pingall command: {str(error)}")
            await ctx.send(f"❌ An error occurred: {str(error)}")
            
    @commands.command(name="pingall_cmd", hidden=True)
    async def pingall_subcommands(self, ctx, subcommand: str = None):
        """Subcommand handler for pingall"""
        if subcommand and subcommand.lower() == "cancel":
            await self.pingall_cancel(ctx)
        else:
            await self.pingall(ctx)

async def setup(bot):
    await bot.add_cog(PingTools(bot)) 