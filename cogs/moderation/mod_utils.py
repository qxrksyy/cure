import discord
from discord.ext import commands
import logging
import asyncio
from datetime import datetime, timedelta
import json
import os

logger = logging.getLogger('bot')

class ModUtils(commands.Cog):
    """Utility commands for server moderators"""
    
    def __init__(self, bot):
        self.bot = bot
        self.data_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'data', 'moderation')
        self.mod_history_file = os.path.join(self.data_folder, 'mod_history.json')
        # Create data directory if it doesn't exist
        os.makedirs(self.data_folder, exist_ok=True)
        # Load data
        self.mod_history = self.load_data(self.mod_history_file)
        
        # Register listeners for tracking mod actions
        self.register_listeners()
    
    def load_data(self, file_path):
        """Load data from file"""
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    return json.load(f)
            else:
                return {}
        except json.JSONDecodeError:
            logger.error(f"Error decoding {file_path}. Using empty config.")
            return {}
    
    def save_data(self, data, file_path):
        """Save data to file"""
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=4)
    
    def register_listeners(self):
        """Register listeners to track moderator actions"""
        self.bot.add_listener(self.on_member_ban, 'on_member_ban')
        self.bot.add_listener(self.on_member_unban, 'on_member_unban')
        
        # Special handling for kicks since there's no specific kick event
        self.bot.add_listener(self.on_member_remove, 'on_member_remove')
    
    def add_mod_action(self, guild_id, mod_id, action_type, target_id, reason=None):
        """Add a moderation action to the history"""
        guild_id = str(guild_id)
        mod_id = str(mod_id)
        
        if guild_id not in self.mod_history:
            self.mod_history[guild_id] = {}
            
        if mod_id not in self.mod_history[guild_id]:
            self.mod_history[guild_id][mod_id] = []
        
        # Add the action to history
        self.mod_history[guild_id][mod_id].append({
            "action": action_type,
            "target": str(target_id),
            "timestamp": datetime.utcnow().isoformat(),
            "reason": reason
        })
        
        # Keep only the last 100 actions per mod to prevent excessive storage
        if len(self.mod_history[guild_id][mod_id]) > 100:
            self.mod_history[guild_id][mod_id] = self.mod_history[guild_id][mod_id][-100:]
            
        self.save_data(self.mod_history, self.mod_history_file)
    
    async def on_member_ban(self, guild, user):
        """Track member bans"""
        try:
            # Fetch ban information to get the moderator
            await asyncio.sleep(1)  # Wait for audit log to be updated
            
            # Get recent bans within the last minute
            one_minute_ago = datetime.utcnow() - timedelta(minutes=1)
            
            async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.ban, after=one_minute_ago):
                if entry.target.id == user.id:
                    self.add_mod_action(
                        guild.id, 
                        entry.user.id, 
                        "ban", 
                        user.id, 
                        entry.reason
                    )
                    break
        except Exception as e:
            logger.error(f"Error tracking ban action: {str(e)}")
    
    async def on_member_unban(self, guild, user):
        """Track member unbans"""
        try:
            # Fetch unban information to get the moderator
            await asyncio.sleep(1)  # Wait for audit log to be updated
            
            # Get recent unbans within the last minute
            one_minute_ago = datetime.utcnow() - timedelta(minutes=1)
            
            async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.unban, after=one_minute_ago):
                if entry.target.id == user.id:
                    self.add_mod_action(
                        guild.id, 
                        entry.user.id, 
                        "unban", 
                        user.id, 
                        entry.reason
                    )
                    break
        except Exception as e:
            logger.error(f"Error tracking unban action: {str(e)}")
    
    async def on_member_remove(self, member):
        """Handle member leave/kick events"""
        try:
            # Ignore bot leaves
            if member.bot:
                return
                
            # Wait a bit for audit logs to update
            await asyncio.sleep(1)
            
            # Check if this was a kick or a ban (don't track regular leaves)
            one_minute_ago = datetime.utcnow() - timedelta(minutes=1)
            
            # First check if it was a ban
            ban_found = False
            try:
                async for entry in member.guild.audit_logs(limit=5, action=discord.AuditLogAction.ban, after=one_minute_ago):
                    if entry.target.id == member.id:
                        ban_found = True
                        # Ban event will be handled by on_member_ban, so we don't need to do anything here
                        logger.debug(f"Member {member} was banned, not kicked")
                        break
            except Exception as e:
                logger.error(f"Error checking ban logs: {str(e)}")
            
            # If it wasn't a ban, check if it was a kick
            if not ban_found:
                kick_found = False
                try:
                    async for entry in member.guild.audit_logs(limit=5, action=discord.AuditLogAction.kick, after=one_minute_ago):
                        if entry.target.id == member.id:
                            kick_found = True
                            self.add_mod_action(
                                member.guild.id, 
                                entry.user.id, 
                                "kick", 
                                member.id, 
                                entry.reason
                            )
                            logger.info(f"Tracked kick of {member} by {entry.user} in {member.guild}")
                            break
                except Exception as e:
                    logger.error(f"Error checking kick logs: {str(e)}")
                
                if not kick_found:
                    # This was likely a regular leave
                    logger.debug(f"Member {member} left {member.guild} (regular leave)")
        except Exception as e:
            logger.error(f"Error in on_member_remove: {str(e)}")
    
    @commands.command(name="moderationhistory")
    @commands.has_permissions(manage_messages=True)
    async def moderationhistory(self, ctx, member: discord.Member = None, command: str = None):
        """View moderation actions from a staff member"""
        if member is None:
            member = ctx.author
            
        guild_id = str(ctx.guild.id)
        member_id = str(member.id)
        
        if (guild_id not in self.mod_history or 
            member_id not in self.mod_history[guild_id] or
            not self.mod_history[guild_id][member_id]):
            await ctx.send(f"❌ No moderation history found for {member.mention}.")
            return
            
        # Filter by command if specified
        actions = self.mod_history[guild_id][member_id]
        if command:
            actions = [action for action in actions if action["action"].lower() == command.lower()]
            
            if not actions:
                await ctx.send(f"❌ No '{command}' actions found for {member.mention}.")
                return
        
        # Sort actions by timestamp (newest first)
        try:
            actions = sorted(actions, key=lambda x: datetime.fromisoformat(x["timestamp"]), reverse=True)
        except Exception as e:
            logger.error(f"Error sorting mod actions: {str(e)}")
                
        # Create paginated embeds for the actions
        actions_per_page = 5
        pages = []
        
        for i in range(0, len(actions), actions_per_page):
            page_actions = actions[i:i+actions_per_page]
            
            embed = discord.Embed(
                title=f"Moderation History for {member.display_name}",
                description=f"Showing moderation actions by {member.mention}",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            
            for action in page_actions:
                # Try to get the target user
                try:
                    target_id = int(action["target"])
                    target = ctx.guild.get_member(target_id)
                    if not target:
                        try:
                            target = await self.bot.fetch_user(target_id)
                        except:
                            target = f"Unknown User ({target_id})"
                            
                    target_display = target.mention if isinstance(target, (discord.Member, discord.User)) else target
                    action_type = action["action"].capitalize()
                    timestamp = datetime.fromisoformat(action["timestamp"])
                    reason = action["reason"] or "No reason provided"
                    
                    embed.add_field(
                        name=f"{action_type} - <t:{int(timestamp.timestamp())}:R>",
                        value=f"**Target:** {target_display}\n**Reason:** {reason}",
                        inline=False
                    )
                except Exception as e:
                    # If there's an error processing one action, add an error field but continue
                    logger.error(f"Error processing action in moderationhistory: {str(e)}")
                    embed.add_field(
                        name=f"Error Processing Action",
                        value=f"There was an error processing an action in the moderation history.",
                        inline=False
                    )
                
            embed.set_thumbnail(url=member.display_avatar.url)
            # Calculate total pages and current page safely
            total_pages = max(1, (len(actions) - 1) // actions_per_page + 1)
            current_page = i // actions_per_page + 1
            embed.set_footer(text=f"Page {current_page}/{total_pages}")
            
            pages.append(embed)
            
        if not pages:
            await ctx.send(f"❌ No moderation history found for {member.mention}.")
            return
            
        # Send the first page
        current_page = 0
        message = await ctx.send(embed=pages[current_page])
        
        # Add reactions for pagination if there are multiple pages
        if len(pages) > 1:
            reactions = ['⬅️', '➡️']
            for reaction in reactions:
                try:
                    await message.add_reaction(reaction)
                except Exception as e:
                    logger.error(f"Error adding reaction: {str(e)}")
                
            def check(reaction, user):
                return user == ctx.author and str(reaction.emoji) in reactions and reaction.message.id == message.id
                
            while True:
                try:
                    reaction, user = await self.bot.wait_for('reaction_add', timeout=60.0, check=check)
                    
                    if str(reaction.emoji) == '⬅️':
                        current_page = (current_page - 1) % len(pages)
                    elif str(reaction.emoji) == '➡️':
                        current_page = (current_page + 1) % len(pages)
                        
                    await message.edit(embed=pages[current_page])
                    await message.remove_reaction(reaction.emoji, user)
                    
                except asyncio.TimeoutError:
                    # Remove our reactions when the pagination times out
                    try:
                        await message.clear_reactions()
                    except Exception as e:
                        logger.debug(f"Could not clear reactions: {str(e)}")
                    break
                    
                except Exception as e:
                    logger.error(f"Error in pagination: {str(e)}")
                    break

async def setup(bot):
    """Set up the moderator utilities cog"""
    await bot.add_cog(ModUtils(bot)) 