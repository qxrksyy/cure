import discord
from discord.ext import commands
import asyncio
from datetime import datetime, timedelta
import logging

logger = logging.getLogger('bot')

class Moderation(commands.Cog):
    """Basic moderation commands"""
    
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="ban")
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, delete_history: int = 1, *, reason="No reason provided"):
        """Bans the mentioned user"""
        try:
            # Create an embed for the ban confirmation
            embed = discord.Embed(
                title="Member Banned",
                description=f"{member.mention} has been banned from the server.",
                color=discord.Color.red(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Reason", value=reason)
            embed.add_field(name="Banned by", value=ctx.author.mention)
            embed.add_field(name="Message History Deleted", value=f"{delete_history} day(s)")
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(text=f"User ID: {member.id}")
            
            # Try to send a DM to the user being banned
            try:
                dm_embed = discord.Embed(
                    title="You have been banned",
                    description=f"You have been banned from {ctx.guild.name}",
                    color=discord.Color.red(),
                    timestamp=datetime.utcnow()
                )
                dm_embed.add_field(name="Reason", value=reason)
                dm_embed.add_field(name="Banned by", value=ctx.author.name)
                dm_embed.set_footer(text="If you believe this is a mistake, please contact the server administrators.")
                await member.send(embed=dm_embed)
            except (discord.Forbidden, discord.HTTPException):
                # User has DMs closed or there was an error
                pass
                
            # Execute the ban
            await member.ban(delete_message_days=delete_history, reason=f"{reason} | Banned by {ctx.author}")
            await ctx.send(embed=embed)
            
        except discord.Forbidden:
            await ctx.send("I don't have permission to ban that member.")
        except Exception as e:
            logger.error(f"Error when banning user: {str(e)}")
            await ctx.send(f"An error occurred: {str(e)}")

    @commands.command(name="kick")
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason="No reason provided"):
        """Kicks the mentioned user"""
        try:
            # Create an embed for the kick confirmation
            embed = discord.Embed(
                title="Member Kicked",
                description=f"{member.mention} has been kicked from the server.",
                color=discord.Color.orange(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Reason", value=reason)
            embed.add_field(name="Kicked by", value=ctx.author.mention)
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(text=f"User ID: {member.id}")
            
            # Try to send a DM to the user being kicked
            try:
                dm_embed = discord.Embed(
                    title="You have been kicked",
                    description=f"You have been kicked from {ctx.guild.name}",
                    color=discord.Color.orange(),
                    timestamp=datetime.utcnow()
                )
                dm_embed.add_field(name="Reason", value=reason)
                dm_embed.add_field(name="Kicked by", value=ctx.author.name)
                dm_embed.set_footer(text="You can rejoin the server if you have an invite link.")
                await member.send(embed=dm_embed)
            except (discord.Forbidden, discord.HTTPException):
                # User has DMs closed or there was an error
                pass
            
            # Execute the kick
            await member.kick(reason=f"{reason} | Kicked by {ctx.author}")
            await ctx.send(embed=embed)
            
        except discord.Forbidden:
            await ctx.send("I don't have permission to kick that member.")
        except Exception as e:
            logger.error(f"Error when kicking user: {str(e)}")
            await ctx.send(f"An error occurred: {str(e)}")

    @commands.command(name="unban")
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx, user_id: int, *, reason="No reason provided"):
        """Unbans the user with the given ID"""
        try:
            # Get the ban entry
            banned_users = [entry async for entry in ctx.guild.bans()]
            user = None
            
            for ban_entry in banned_users:
                if ban_entry.user.id == user_id:
                    user = ban_entry.user
                    break
                    
            if user is None:
                await ctx.send(f"User with ID {user_id} is not banned.")
                return
                
            # Create an embed for the unban confirmation
            embed = discord.Embed(
                title="Member Unbanned",
                description=f"{user.name}#{user.discriminator} has been unbanned from the server.",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Reason", value=reason)
            embed.add_field(name="Unbanned by", value=ctx.author.mention)
            embed.set_thumbnail(url=user.display_avatar.url)
            embed.set_footer(text=f"User ID: {user.id}")
            
            # Execute the unban
            await ctx.guild.unban(user, reason=f"{reason} | Unbanned by {ctx.author}")
            await ctx.send(embed=embed)
            
        except discord.Forbidden:
            await ctx.send("I don't have permission to unban users.")
        except Exception as e:
            logger.error(f"Error when unbanning user: {str(e)}")
            await ctx.send(f"An error occurred: {str(e)}")

    @commands.command(name="timeout", aliases=["mute"])
    @commands.has_permissions(moderate_members=True)
    async def timeout(self, ctx, member: discord.Member, duration: str, *, reason="No reason provided"):
        """Mutes the provided member using Discord's timeout feature"""
        # Parse duration string (e.g., "1d 2h 3m 4s")
        duration_seconds = 0
        time_units = {"s": 1, "m": 60, "h": 3600, "d": 86400}
        
        # Simple duration parsing
        duration_parts = duration.lower().split()
        for part in duration_parts:
            if part[-1] in time_units and part[:-1].isdigit():
                duration_seconds += int(part[:-1]) * time_units[part[-1]]
            elif part.isdigit():
                # Default to minutes if no unit specified
                duration_seconds += int(part) * 60  
        
        if duration_seconds <= 0:
            await ctx.send("Invalid duration. Please use format like '1d 2h 3m 4s'.")
            return
            
        # Discord timeout max is 28 days
        if duration_seconds > 28 * 86400:
            duration_seconds = 28 * 86400
            await ctx.send("Maximum timeout duration is 28 days. Setting timeout to 28 days.")
            
        timeout_until = datetime.utcnow() + timedelta(seconds=duration_seconds)
        
        try:
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
            
            # Create an embed for the timeout confirmation
            embed = discord.Embed(
                title="Member Timed Out",
                description=f"{member.mention} has been timed out for {duration_str}.",
                color=discord.Color.gold(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Reason", value=reason)
            embed.add_field(name="Timed out by", value=ctx.author.mention)
            embed.add_field(name="Expires", value=discord.utils.format_dt(timeout_until, style='R'))
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(text=f"User ID: {member.id}")
            
            # Try to send a DM to the user being timed out
            try:
                dm_embed = discord.Embed(
                    title="You have been timed out",
                    description=f"You have been timed out in {ctx.guild.name} for {duration_str}",
                    color=discord.Color.gold(),
                    timestamp=datetime.utcnow()
                )
                dm_embed.add_field(name="Reason", value=reason)
                dm_embed.add_field(name="Timed out by", value=ctx.author.name)
                dm_embed.add_field(name="Expires", value=discord.utils.format_dt(timeout_until, style='R'))
                await member.send(embed=dm_embed)
            except (discord.Forbidden, discord.HTTPException):
                # User has DMs closed or there was an error
                pass
            
            # Execute the timeout
            await member.timeout(timeout_until, reason=f"{reason} | Timed out by {ctx.author}")
            await ctx.send(embed=embed)
            
        except discord.Forbidden:
            await ctx.send("I don't have permission to timeout that member.")
        except Exception as e:
            logger.error(f"Error when timing out user: {str(e)}")
            await ctx.send(f"An error occurred: {str(e)}")

    @commands.command(name="untimeout", aliases=["unmute"])
    @commands.has_permissions(moderate_members=True)
    async def untimeout(self, ctx, member: discord.Member, *, reason="No reason provided"):
        """Removes a timeout from a member"""
        try:
            if member.timed_out_until is None:
                await ctx.send(f"{member.mention} is not timed out.")
                return
                
            # Create an embed for the untimeout confirmation
            embed = discord.Embed(
                title="Timeout Removed",
                description=f"Timeout has been removed from {member.mention}.",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Reason", value=reason)
            embed.add_field(name="Removed by", value=ctx.author.mention)
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(text=f"User ID: {member.id}")
            
            # Execute the untimeout
            await member.timeout(None, reason=f"{reason} | Timeout removed by {ctx.author}")
            await ctx.send(embed=embed)
            
        except discord.Forbidden:
            await ctx.send("I don't have permission to remove timeouts from that member.")
        except Exception as e:
            logger.error(f"Error when removing timeout: {str(e)}")
            await ctx.send(f"An error occurred: {str(e)}")

    @commands.command(name="purge", aliases=["clear"])
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx, amount: int = 5, member: discord.Member = None):
        """Deletes the specified amount of messages from the current channel"""
        try:
            await ctx.message.delete()  # Delete the command message
            
            if member:
                # Delete messages from a specific member
                def check(message):
                    return message.author == member
                    
                deleted = await ctx.channel.purge(limit=100, check=check, bulk=True)
                deleted_count = len(deleted)
                
                if deleted_count == 0:
                    temp_msg = await ctx.send(f"No messages from {member.mention} found in the last 100 messages.")
                else:
                    temp_msg = await ctx.send(f"Deleted {deleted_count} message{'s' if deleted_count != 1 else ''} from {member.mention}.")
            else:
                # Delete a specific number of messages
                deleted = await ctx.channel.purge(limit=amount, bulk=True)
                deleted_count = len(deleted)
                
                temp_msg = await ctx.send(f"Deleted {deleted_count} message{'s' if deleted_count != 1 else ''}.")
                
            # Delete the confirmation message after 3 seconds
            await asyncio.sleep(3)
            await temp_msg.delete()
            
        except discord.Forbidden:
            await ctx.send("I don't have permission to delete messages.")
        except discord.HTTPException as e:
            if e.code == 50034:
                await ctx.send("Cannot delete messages older than 14 days in bulk. Please use a smaller range.")
            else:
                logger.error(f"HTTP error when purging messages: {str(e)}")
                await ctx.send(f"An error occurred: {str(e)}")
        except Exception as e:
            logger.error(f"Error when purging messages: {str(e)}")
            await ctx.send(f"An error occurred: {str(e)}")

async def setup(bot):
    await bot.add_cog(Moderation(bot)) 