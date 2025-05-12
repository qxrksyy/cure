import discord
from discord.ext import commands
import asyncio
import logging
from datetime import datetime, timedelta
import json
import os

logger = logging.getLogger('bot')

class ReminderCommands(commands.Cog):
    """Commands for setting reminders"""
    
    def __init__(self, bot):
        self.bot = bot
        self.data_folder = 'data/moderation'
        self.reminders_file = os.path.join(self.data_folder, 'reminders.json')
        # Create data directory if it doesn't exist
        os.makedirs(self.data_folder, exist_ok=True)
        # Load data
        self.reminders = self.load_reminders()
        # Start background task
        self.check_reminders_task = self.bot.loop.create_task(self.check_reminders())
    
    def load_reminders(self):
        """Load reminders from file"""
        try:
            if os.path.exists(self.reminders_file):
                with open(self.reminders_file, 'r') as f:
                    return json.load(f)
            else:
                return {}
        except json.JSONDecodeError:
            logger.error(f"Error decoding {self.reminders_file}. Using empty config.")
            return {}
    
    def save_reminders(self):
        """Save reminders to file"""
        with open(self.reminders_file, 'w') as f:
            json.dump(self.reminders, f, indent=4)

    @commands.command(name="remind")
    async def remind(self, ctx, timeframe: str, *, reason: str = "No reason provided"):
        """Get reminders for a duration set about whatever you choose"""
        # Parse the timeframe
        duration_seconds = 0
        time_units = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}
        
        # Simple timeframe parsing
        timeframe_parts = timeframe.lower().split()
        for part in timeframe_parts:
            if part[-1] in time_units and part[:-1].isdigit():
                duration_seconds += int(part[:-1]) * time_units[part[-1]]
            elif part.isdigit():
                # Default to minutes if no unit specified
                duration_seconds += int(part) * 60
                
        if duration_seconds <= 0:
            await ctx.send("❌ Invalid timeframe. Please use format like '1d 2h 3m 4s'.")
            return
            
        # Format readable duration
        days, remainder = divmod(duration_seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        duration_str = ""
        if days > 0:
            duration_str += f"{days} day{'s' if days != 1 else ''} "
        if hours > 0:
            duration_str += f"{hours} hour{'s' if hours != 1 else ''} "
        if minutes > 0:
            duration_str += f"{minutes} minute{'s' if minutes != 1 else ''} "
        if seconds > 0:
            duration_str += f"{seconds} second{'s' if seconds != 1 else ''}"
            
        duration_str = duration_str.strip()
        
        # Calculate the expiry time
        expiry_time = datetime.utcnow() + timedelta(seconds=duration_seconds)
        
        # Initialize the user in reminders dict if they don't exist
        user_id = str(ctx.author.id)
        if user_id not in self.reminders:
            self.reminders[user_id] = []
            
        # Generate a unique ID for the reminder
        if self.reminders[user_id]:
            reminder_id = max(int(r["id"]) for r in self.reminders[user_id]) + 1
        else:
            reminder_id = 1
            
        # Add the reminder
        self.reminders[user_id].append({
            "id": str(reminder_id),
            "reason": reason,
            "channel_id": str(ctx.channel.id),
            "guild_id": str(ctx.guild.id) if ctx.guild else None,
            "created_at": datetime.utcnow().isoformat(),
            "expires": expiry_time.isoformat()
        })
        
        self.save_reminders()
        
        # Create an embed for the reminder confirmation
        embed = discord.Embed(
            title="Reminder Set",
            description=f"I'll remind you in {duration_str}.",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        embed.add_field(name="Reason", value=reason)
        embed.add_field(name="Reminder ID", value=reminder_id)
        embed.add_field(name="Expires", value=f"<t:{int(expiry_time.timestamp())}:R>")
        
        await ctx.send(embed=embed)

    @commands.command(name="remind_remove", aliases=["remindremove"])
    async def remind_remove(self, ctx, reminder_id: int):
        """Remove a reminder"""
        user_id = str(ctx.author.id)
        
        # Check if the user has reminders
        if user_id not in self.reminders or not self.reminders[user_id]:
            await ctx.send("❌ You don't have any active reminders.")
            return
            
        # Find the reminder
        reminder_str_id = str(reminder_id)
        reminder = None
        
        for r in self.reminders[user_id]:
            if r["id"] == reminder_str_id:
                reminder = r
                break
                
        if not reminder:
            await ctx.send(f"❌ Reminder with ID {reminder_id} not found.")
            return
            
        # Remove the reminder
        self.reminders[user_id].remove(reminder)
        
        # Clean up empty entries
        if not self.reminders[user_id]:
            del self.reminders[user_id]
            
        self.save_reminders()
        
        # Create an embed for the removal confirmation
        embed = discord.Embed(
            title="Reminder Removed",
            description=f"Reminder with ID {reminder_id} has been removed.",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )
        embed.add_field(name="Reason", value=reminder["reason"])
        embed.add_field(name="Was Due", value=f"<t:{int(datetime.fromisoformat(reminder['expires']).timestamp())}:R>")
        
        await ctx.send(embed=embed)

    @commands.command(name="remind_list", aliases=["remindlist", "reminders"])
    async def remind_list(self, ctx):
        """View a list of your reminders"""
        user_id = str(ctx.author.id)
        
        # Check if the user has reminders
        if user_id not in self.reminders or not self.reminders[user_id]:
            await ctx.send("❌ You don't have any active reminders.")
            return
            
        # Create an embed with the reminder list
        embed = discord.Embed(
            title="Your Reminders",
            description=f"You have {len(self.reminders[user_id])} active reminders.",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        # Add each reminder to the embed
        for reminder in sorted(self.reminders[user_id], key=lambda r: datetime.fromisoformat(r["expires"])):
            reminder_id = reminder["id"]
            reason = reminder["reason"]
            expires = datetime.fromisoformat(reminder["expires"])
            
            embed.add_field(
                name=f"ID: {reminder_id}",
                value=(
                    f"**Reason:** {reason}\n"
                    f"**Expires:** <t:{int(expires.timestamp())}:R>"
                ),
                inline=False
            )
            
        await ctx.send(embed=embed)

    async def check_reminders(self):
        """Background task to check and send reminders"""
        await self.bot.wait_until_ready()
        
        while not self.bot.is_closed():
            try:
                current_time = datetime.utcnow()
                users_to_update = []
                
                for user_id, reminders in self.reminders.items():
                    reminders_to_remove = []
                    
                    for reminder in reminders:
                        expires = datetime.fromisoformat(reminder["expires"])
                        
                        if current_time >= expires:
                            # Time to send the reminder
                            try:
                                channel_id = int(reminder["channel_id"])
                                channel = self.bot.get_channel(channel_id)
                                
                                if not channel:
                                    # Try to fetch the channel if it's not in cache
                                    try:
                                        channel = await self.bot.fetch_channel(channel_id)
                                    except:
                                        channel = None
                                        
                                if channel:
                                    user = await self.bot.fetch_user(int(user_id))
                                    
                                    # Create an embed for the reminder
                                    embed = discord.Embed(
                                        title="Reminder",
                                        description=f"{user.mention}, you asked me to remind you:",
                                        color=discord.Color.blue(),
                                        timestamp=datetime.utcnow()
                                    )
                                    embed.add_field(name="Reason", value=reminder["reason"])
                                    embed.add_field(
                                        name="Originally Set", 
                                        value=f"<t:{int(datetime.fromisoformat(reminder['created_at']).timestamp())}:R>"
                                    )
                                    
                                    await channel.send(user.mention, embed=embed)
                                    logger.info(f"Sent reminder to {user.name}: {reminder['reason']}")
                                    
                            except Exception as e:
                                logger.error(f"Error sending reminder: {str(e)}")
                                
                            # Mark the reminder for removal
                            reminders_to_remove.append(reminder)
                    
                    # Remove completed reminders
                    for reminder in reminders_to_remove:
                        self.reminders[user_id].remove(reminder)
                        
                    # If the user has no more reminders, mark them for removal
                    if not self.reminders[user_id]:
                        users_to_update.append(user_id)
                
                # Remove users with no reminders
                for user_id in users_to_update:
                    del self.reminders[user_id]
                    
                # Save if changes were made
                if users_to_update or any(reminders_to_remove):
                    self.save_reminders()
                    
            except Exception as e:
                logger.error(f"Error in check_reminders task: {str(e)}")
                
            # Check every minute
            await asyncio.sleep(60)
    
    def cog_unload(self):
        """Clean up when the cog is unloaded"""
        self.check_reminders_task.cancel()

async def setup(bot):
    await bot.add_cog(ReminderCommands(bot)) 