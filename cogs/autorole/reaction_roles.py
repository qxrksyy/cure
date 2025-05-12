import discord
from discord.ext import commands
import json
import os
import logging
from datetime import datetime

logger = logging.getLogger('bot')

class ReactionRoles(commands.Cog):
    """Commands for setting up reaction-based role assignment"""
    
    def __init__(self, bot):
        self.bot = bot
        self.config_path = "data/autorole"
        self.reaction_roles = {}
        
        # Create directory if it doesn't exist
        os.makedirs(self.config_path, exist_ok=True)
        
        # Load reaction roles
        self._load_reaction_roles()
    
    def _load_reaction_roles(self):
        """Load reaction role settings from file"""
        try:
            filepath = f"{self.config_path}/reactionroles.json"
            if os.path.exists(filepath):
                with open(filepath, "r") as f:
                    self.reaction_roles = json.load(f)
        except Exception as e:
            logger.error(f"Error loading reaction role settings: {str(e)}")
    
    def _save_reaction_roles(self):
        """Save reaction role settings to file"""
        try:
            filepath = f"{self.config_path}/reactionroles.json"
            with open(filepath, "w") as f:
                json.dump(self.reaction_roles, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving reaction role settings: {str(e)}")
    
    @commands.group(name="reactionrole", invoke_without_command=True)
    @commands.has_permissions(manage_guild=True, manage_roles=True)
    async def reactionrole(self, ctx):
        """Set up self-assignable roles with reactions"""
        embed = discord.Embed(
            title="Reaction Role Configuration",
            description="Set up reactions that users can click to assign themselves roles",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(
            name="Commands",
            value=(
                "`reactionrole add <message> <emoji> <role>` - Adds a reaction role to a message\n"
                "`reactionrole list` - View a list of every reaction role\n"
                "`reactionrole remove <message> <emoji>` - Removes a reaction role from a message\n"
                "`reactionrole removeall <message>` - Removes all reaction roles from a message\n"
                "`reactionrole reset` - Clears every reaction role from guild"
            ),
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @reactionrole.command(name="add")
    @commands.has_permissions(manage_guild=True, manage_roles=True)
    async def reactionrole_add(self, ctx, message: discord.Message, emoji: str, role: discord.Role):
        """Adds a reaction role to a message"""
        # Check if bot has permission to add reactions
        if not ctx.channel.permissions_for(ctx.guild.me).add_reactions:
            await ctx.send("❌ I don't have permission to add reactions in this channel.")
            return
        
        # Check if bot can assign the role
        if not ctx.guild.me.top_role > role:
            await ctx.send(f"❌ I cannot assign {role.mention} as it is higher than my highest role.")
            return
        
        # Check if emoji is valid by trying to add it
        try:
            await message.add_reaction(emoji)
        except discord.HTTPException:
            await ctx.send(f"❌ Invalid emoji: `{emoji}`")
            return
        
        # Add to reaction roles database
        guild_id = str(ctx.guild.id)
        channel_id = str(message.channel.id)
        message_id = str(message.id)
        
        if guild_id not in self.reaction_roles:
            self.reaction_roles[guild_id] = {}
        
        if channel_id not in self.reaction_roles[guild_id]:
            self.reaction_roles[guild_id][channel_id] = {}
        
        if message_id not in self.reaction_roles[guild_id][channel_id]:
            self.reaction_roles[guild_id][channel_id][message_id] = {}
        
        # Store emoji to role mapping
        self.reaction_roles[guild_id][channel_id][message_id][emoji] = {
            "role_id": str(role.id),
            "added_by": str(ctx.author.id),
            "added_at": datetime.utcnow().isoformat()
        }
        
        self._save_reaction_roles()
        
        embed = discord.Embed(
            title="Reaction Role Added",
            description=f"Added reaction role to message",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(name="Emoji", value=emoji, inline=True)
        embed.add_field(name="Role", value=role.mention, inline=True)
        embed.add_field(name="Message Link", value=f"[Jump to Message]({message.jump_url})", inline=False)
        
        await ctx.send(embed=embed)
    
    @reactionrole.command(name="list")
    @commands.has_permissions(manage_guild=True, manage_roles=True)
    async def reactionrole_list(self, ctx):
        """View a list of every reaction role"""
        guild_id = str(ctx.guild.id)
        
        # Check if guild has any reaction roles
        if guild_id not in self.reaction_roles or not self.reaction_roles[guild_id]:
            await ctx.send("❌ This server has no reaction roles set up.")
            return
        
        embed = discord.Embed(
            title="Reaction Roles",
            description="All reaction roles in this server",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        # List all reaction role messages
        for channel_id, channel_data in self.reaction_roles[guild_id].items():
            channel = ctx.guild.get_channel(int(channel_id))
            channel_name = f"#{channel.name}" if channel else f"Unknown Channel ({channel_id})"
            
            for message_id, reactions in channel_data.items():
                reactions_text = ""
                
                for emoji, reaction_data in reactions.items():
                    role = ctx.guild.get_role(int(reaction_data["role_id"]))
                    role_name = role.mention if role else f"Unknown Role ({reaction_data['role_id']})"
                    reactions_text += f"{emoji} → {role_name}\n"
                
                if reactions_text:
                    embed.add_field(
                        name=f"{channel_name} - Message ID: {message_id}",
                        value=f"{reactions_text}[Jump to Message](https://discord.com/channels/{ctx.guild.id}/{channel_id}/{message_id})",
                        inline=False
                    )
        
        await ctx.send(embed=embed)
    
    @reactionrole.command(name="remove")
    @commands.has_permissions(manage_guild=True, manage_roles=True)
    async def reactionrole_remove(self, ctx, message: discord.Message, emoji: str):
        """Removes a reaction role from a message"""
        guild_id = str(ctx.guild.id)
        channel_id = str(message.channel.id)
        message_id = str(message.id)
        
        # Check if message has any reaction roles
        if (guild_id not in self.reaction_roles or
            channel_id not in self.reaction_roles[guild_id] or
            message_id not in self.reaction_roles[guild_id][channel_id] or
            emoji not in self.reaction_roles[guild_id][channel_id][message_id]):
            await ctx.send(f"❌ No reaction role found for emoji `{emoji}` on that message.")
            return
        
        # Get role info for confirmation
        reaction_data = self.reaction_roles[guild_id][channel_id][message_id][emoji]
        role_id = reaction_data["role_id"]
        role = ctx.guild.get_role(int(role_id))
        role_name = role.name if role else f"Unknown Role ({role_id})"
        
        # Confirm removal
        embed = discord.Embed(
            title="⚠️ Confirm Removal",
            description=f"Are you sure you want to remove the reaction role for emoji {emoji} (role: {role_name})?",
            color=discord.Color.orange(),
            timestamp=datetime.utcnow()
        )
        
        message_confirm = await ctx.send(embed=embed)
        
        # Add confirmation reactions
        await message_confirm.add_reaction("✅")
        await message_confirm.add_reaction("❌")
        
        # Wait for confirmation
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == message_confirm.id
        
        try:
            reaction, user = await self.bot.wait_for("reaction_add", timeout=60.0, check=check)
            
            if str(reaction.emoji) == "✅":
                # Remove the reaction role
                del self.reaction_roles[guild_id][channel_id][message_id][emoji]
                
                # If no reaction roles left for message, remove message entry
                if not self.reaction_roles[guild_id][channel_id][message_id]:
                    del self.reaction_roles[guild_id][channel_id][message_id]
                    
                    # If no messages left in channel, remove channel entry
                    if not self.reaction_roles[guild_id][channel_id]:
                        del self.reaction_roles[guild_id][channel_id]
                        
                        # If no channels left in guild, remove guild entry
                        if not self.reaction_roles[guild_id]:
                            del self.reaction_roles[guild_id]
                
                self._save_reaction_roles()
                
                # Try to remove the reaction from the message
                try:
                    await message.clear_reaction(emoji)
                except Exception as e:
                    logger.error(f"Error removing reaction: {str(e)}")
                
                await message_confirm.delete()
                
                embed = discord.Embed(
                    title="Reaction Role Removed",
                    description=f"Removed reaction role for emoji {emoji} (role: {role_name}).",
                    color=discord.Color.green(),
                    timestamp=datetime.utcnow()
                )
                
                await ctx.send(embed=embed)
            else:
                await message_confirm.delete()
                await ctx.send("❌ Reaction role removal cancelled.")
                
        except TimeoutError:
            await message_confirm.delete()
            await ctx.send("❌ Reaction role removal timed out.")
    
    @reactionrole.command(name="removeall")
    @commands.has_permissions(manage_guild=True, manage_roles=True)
    async def reactionrole_removeall(self, ctx, message: discord.Message):
        """Removes all reaction roles from a message"""
        guild_id = str(ctx.guild.id)
        channel_id = str(message.channel.id)
        message_id = str(message.id)
        
        # Check if message has any reaction roles
        if (guild_id not in self.reaction_roles or
            channel_id not in self.reaction_roles[guild_id] or
            message_id not in self.reaction_roles[guild_id][channel_id]):
            await ctx.send("❌ No reaction roles found for that message.")
            return
        
        # Confirm removal
        embed = discord.Embed(
            title="⚠️ Confirm Removal",
            description=f"Are you sure you want to remove ALL reaction roles from this message?",
            color=discord.Color.orange(),
            timestamp=datetime.utcnow()
        )
        
        message_confirm = await ctx.send(embed=embed)
        
        # Add confirmation reactions
        await message_confirm.add_reaction("✅")
        await message_confirm.add_reaction("❌")
        
        # Wait for confirmation
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == message_confirm.id
        
        try:
            reaction, user = await self.bot.wait_for("reaction_add", timeout=60.0, check=check)
            
            if str(reaction.emoji) == "✅":
                # Store emojis to remove
                emojis = list(self.reaction_roles[guild_id][channel_id][message_id].keys())
                
                # Remove from database
                del self.reaction_roles[guild_id][channel_id][message_id]
                
                # If no messages left in channel, remove channel entry
                if not self.reaction_roles[guild_id][channel_id]:
                    del self.reaction_roles[guild_id][channel_id]
                    
                    # If no channels left in guild, remove guild entry
                    if not self.reaction_roles[guild_id]:
                        del self.reaction_roles[guild_id]
                
                self._save_reaction_roles()
                
                # Try to remove all reactions from the message
                try:
                    await message.clear_reactions()
                except Exception as e:
                    # If can't remove all reactions, try to remove each one
                    for emoji in emojis:
                        try:
                            await message.clear_reaction(emoji)
                        except Exception:
                            pass
                
                await message_confirm.delete()
                
                embed = discord.Embed(
                    title="Reaction Roles Removed",
                    description=f"Removed all reaction roles from message.",
                    color=discord.Color.green(),
                    timestamp=datetime.utcnow()
                )
                
                await ctx.send(embed=embed)
            else:
                await message_confirm.delete()
                await ctx.send("❌ Reaction role removal cancelled.")
                
        except TimeoutError:
            await message_confirm.delete()
            await ctx.send("❌ Reaction role removal timed out.")
    
    @reactionrole.command(name="reset")
    @commands.has_permissions(manage_guild=True, manage_roles=True)
    async def reactionrole_reset(self, ctx):
        """Clears every reaction role from guild"""
        guild_id = str(ctx.guild.id)
        
        # Check if guild has any reaction roles
        if guild_id not in self.reaction_roles or not self.reaction_roles[guild_id]:
            await ctx.send("❌ This server has no reaction roles set up.")
            return
        
        # Confirm reset
        embed = discord.Embed(
            title="⚠️ Confirm Reset",
            description="Are you sure you want to clear ALL reaction roles from this server? This action cannot be undone.",
            color=discord.Color.red(),
            timestamp=datetime.utcnow()
        )
        
        message = await ctx.send(embed=embed)
        
        # Add confirmation reactions
        await message.add_reaction("✅")
        await message.add_reaction("❌")
        
        # Wait for confirmation
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == message.id
        
        try:
            reaction, user = await self.bot.wait_for("reaction_add", timeout=60.0, check=check)
            
            if str(reaction.emoji) == "✅":
                # Try to clear reactions from all messages
                for channel_id, channel_data in self.reaction_roles[guild_id].items():
                    channel = ctx.guild.get_channel(int(channel_id))
                    if channel:
                        for message_id in channel_data.keys():
                            try:
                                msg = await channel.fetch_message(int(message_id))
                                await msg.clear_reactions()
                            except Exception as e:
                                logger.error(f"Error clearing reactions: {str(e)}")
                
                # Remove from database
                del self.reaction_roles[guild_id]
                self._save_reaction_roles()
                
                await message.delete()
                
                embed = discord.Embed(
                    title="Reaction Roles Reset",
                    description="All reaction roles have been cleared from this server.",
                    color=discord.Color.green(),
                    timestamp=datetime.utcnow()
                )
                
                await ctx.send(embed=embed)
            else:
                await message.delete()
                await ctx.send("❌ Reaction role reset cancelled.")
                
        except TimeoutError:
            await message.delete()
            await ctx.send("❌ Reaction role reset timed out.")
    
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        """Handle reaction role assignment"""
        # Skip bot reactions
        if payload.user_id == self.bot.user.id:
            return
        
        # Get data from payload
        guild_id = str(payload.guild_id)
        channel_id = str(payload.channel_id)
        message_id = str(payload.message_id)
        emoji = str(payload.emoji)
        
        # Check if this is a reaction role
        if (guild_id in self.reaction_roles and
            channel_id in self.reaction_roles[guild_id] and
            message_id in self.reaction_roles[guild_id][channel_id] and
            emoji in self.reaction_roles[guild_id][channel_id][message_id]):
            
            # Get the role to assign
            guild = self.bot.get_guild(int(guild_id))
            if not guild:
                return
                
            role_id = self.reaction_roles[guild_id][channel_id][message_id][emoji]["role_id"]
            role = guild.get_role(int(role_id))
            if not role:
                return
                
            # Get the member
            member = guild.get_member(payload.user_id)
            if not member:
                return
                
            # Assign the role
            try:
                await member.add_roles(role, reason=f"Reaction role - reacted with {emoji}")
                logger.info(f"Assigned role {role.name} to {member.name} in {guild.name} via reaction")
            except Exception as e:
                logger.error(f"Error assigning reaction role: {str(e)}")
    
    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        """Handle reaction role removal"""
        # Skip bot reactions
        if payload.user_id == self.bot.user.id:
            return
        
        # Get data from payload
        guild_id = str(payload.guild_id)
        channel_id = str(payload.channel_id)
        message_id = str(payload.message_id)
        emoji = str(payload.emoji)
        
        # Check if this is a reaction role
        if (guild_id in self.reaction_roles and
            channel_id in self.reaction_roles[guild_id] and
            message_id in self.reaction_roles[guild_id][channel_id] and
            emoji in self.reaction_roles[guild_id][channel_id][message_id]):
            
            # Get the role to remove
            guild = self.bot.get_guild(int(guild_id))
            if not guild:
                return
                
            role_id = self.reaction_roles[guild_id][channel_id][message_id][emoji]["role_id"]
            role = guild.get_role(int(role_id))
            if not role:
                return
                
            # Get the member
            member = guild.get_member(payload.user_id)
            if not member:
                return
                
            # Remove the role
            try:
                await member.remove_roles(role, reason=f"Reaction role - removed reaction {emoji}")
                logger.info(f"Removed role {role.name} from {member.name} in {guild.name} via reaction")
            except Exception as e:
                logger.error(f"Error removing reaction role: {str(e)}")

async def setup(bot):
    await bot.add_cog(ReactionRoles(bot)) 