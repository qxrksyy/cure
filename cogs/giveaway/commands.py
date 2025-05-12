from .giveaway import Giveaway
import discord
from discord.ext import commands
import asyncio
import datetime
import re

# Constants
REACTION_EMOJI = "🎉"
DEFAULT_GIVEAWAY_COLOR = 0x1ABC9C  # Turquoise
ERROR_COLOR = 0xE74C3C  # Red
SUCCESS_COLOR = 0x2ECC71  # Green

class GiveawayCommands(Giveaway):
    """Giveaway commands implementation"""
    
    # ------------------- Main Commands ---------------------
    
    @commands.group(name="giveaway", aliases=["g"], invoke_without_command=True)
    @commands.has_permissions(manage_channels=True)
    async def giveaway(self, ctx):
        """Start a giveaway quickly and easily"""
        # Show help message with interactive setup
        embed = discord.Embed(
            title="🎉 Giveaway Setup",
            description="Let's set up a giveaway! Please answer the following questions.",
            color=discord.Color(DEFAULT_GIVEAWAY_COLOR)
        )
        
        embed.add_field(
            name="Giveaway Channel",
            value="Which channel should the giveaway be posted in? Mention the channel or type its name.",
            inline=False
        )
        
        setup_msg = await ctx.send(embed=embed)
        
        # Dictionary to store giveaway setup data
        giveaway_data = {
            "host_ids": [ctx.author.id],
            "created_at": datetime.datetime.utcnow().timestamp()
        }
        
        # Wait for channel response
        try:
            def check(m):
                return m.author == ctx.author and m.channel == ctx.channel
                
            # Get channel
            channel_msg = await self.bot.wait_for('message', check=check, timeout=60)
            channel = None
            
            # Check for channel mention
            if channel_msg.channel_mentions:
                channel = channel_msg.channel_mentions[0]
            else:
                # Try to find by name
                channel_name = channel_msg.content.strip()
                channel = discord.utils.get(ctx.guild.text_channels, name=channel_name)
                
            if not channel:
                return await ctx.send("❌ I couldn't find that channel. Please try again with a valid channel.")
            
            giveaway_data["channel_id"] = channel.id
            
            # Get duration
            embed.clear_fields()
            embed.add_field(
                name="Duration",
                value="How long should the giveaway last? (e.g. 1d, 12h, 30m)",
                inline=False
            )
            await setup_msg.edit(embed=embed)
            
            duration_msg = await self.bot.wait_for('message', check=check, timeout=60)
            duration_seconds = self.parse_duration(duration_msg.content.strip())
            
            if not duration_seconds or duration_seconds < 60:
                return await ctx.send("❌ Invalid duration. Please provide a valid duration like 1d, 12h, 30m.")
            
            giveaway_data["duration"] = duration_seconds
            giveaway_data["end_time"] = datetime.datetime.utcnow().timestamp() + duration_seconds
            
            # Get winners count
            embed.clear_fields()
            embed.add_field(
                name="Winners",
                value="How many winners should there be?",
                inline=False
            )
            await setup_msg.edit(embed=embed)
            
            winners_msg = await self.bot.wait_for('message', check=check, timeout=60)
            try:
                winners_count = int(winners_msg.content.strip())
                if winners_count < 1:
                    return await ctx.send("❌ There must be at least 1 winner.")
            except ValueError:
                return await ctx.send("❌ Please provide a valid number of winners.")
            
            giveaway_data["winners_count"] = winners_count
            
            # Get prize
            embed.clear_fields()
            embed.add_field(
                name="Prize",
                value="What is the prize for this giveaway?",
                inline=False
            )
            await setup_msg.edit(embed=embed)
            
            prize_msg = await self.bot.wait_for('message', check=check, timeout=60)
            prize = prize_msg.content.strip()
            
            if not prize:
                return await ctx.send("❌ Please provide a valid prize.")
            
            giveaway_data["prize"] = prize
            
            # Optional: Get description
            embed.clear_fields()
            embed.add_field(
                name="Description (Optional)",
                value="Add a description for this giveaway or type 'skip' to use the default.",
                inline=False
            )
            await setup_msg.edit(embed=embed)
            
            desc_msg = await self.bot.wait_for('message', check=check, timeout=60)
            if desc_msg.content.lower() != "skip":
                giveaway_data["description"] = desc_msg.content.strip()
            
            # Start the giveaway
            await ctx.invoke(self.giveaway_start, 
                            channel=channel, 
                            duration=self.format_time(duration_seconds),
                            winners=winners_count,
                            prize=prize,
                            description=giveaway_data.get("description", None))
            
        except asyncio.TimeoutError:
            await setup_msg.edit(content="❌ Giveaway setup timed out.", embed=None)
    
    @giveaway.command(name="start")
    @commands.has_permissions(manage_channels=True)
    async def giveaway_start(self, ctx, channel: discord.TextChannel, duration: str, winners: int, *, prize: str, description: str = None):
        """Start a giveaway with your provided duration, winners and prize description"""
        # Check if the guild has reached maximum active giveaways
        guild_id = ctx.guild.id
        if guild_id in self.active_giveaways and len(self.active_giveaways[guild_id]) >= MAX_ACTIVE_GIVEAWAYS:
            return await ctx.send(f"❌ This server has reached the maximum limit of {MAX_ACTIVE_GIVEAWAYS} active giveaways.")
        
        # Parse duration
        duration_seconds = self.parse_duration(duration)
        if not duration_seconds or duration_seconds < 60:
            return await ctx.send("❌ Invalid duration. Please provide a valid duration like 1d, 12h, 30m.")
        
        # Validate winners count
        if winners < 1:
            return await ctx.send("❌ There must be at least 1 winner.")
        
        # Check permissions in target channel
        bot_permissions = channel.permissions_for(ctx.guild.me)
        if not (bot_permissions.send_messages and bot_permissions.embed_links and bot_permissions.add_reactions):
            return await ctx.send(f"❌ I need permissions to send messages, embed links, and add reactions in {channel.mention}.")
        
        # Create giveaway data
        giveaway_data = {
            "prize": prize,
            "channel_id": channel.id,
            "winners_count": winners,
            "host_ids": [ctx.author.id],
            "created_at": datetime.datetime.utcnow().timestamp(),
            "end_time": datetime.datetime.utcnow().timestamp() + duration_seconds,
            "entries": []
        }
        
        # Add description if provided
        if description:
            giveaway_data["description"] = description
        
        # Create giveaway embed
        embed = self.create_giveaway_embed(giveaway_data)
        
        try:
            # Send the giveaway message
            giveaway_message = await channel.send(embed=embed)
            
            # Add reaction for entry
            await giveaway_message.add_reaction(REACTION_EMOJI)
            
            # Store the message ID in the giveaway data
            giveaway_data["message_id"] = str(giveaway_message.id)
            
            # Add to active giveaways
            if guild_id not in self.active_giveaways:
                self.active_giveaways[guild_id] = {}
            
            self.active_giveaways[guild_id][str(giveaway_message.id)] = giveaway_data
            self.save_giveaways(guild_id)
            
            # Confirmation message
            await ctx.send(f"✅ Giveaway created successfully in {channel.mention}!")
            
        except Exception as e:
            await ctx.send(f"❌ An error occurred while creating the giveaway: {str(e)}")
    
    @giveaway.command(name="end")
    @commands.has_permissions(manage_channels=True)
    async def giveaway_end(self, ctx, message_id: str):
        """End an active giveaway early"""
        guild_id = ctx.guild.id
        
        # Check if the giveaway exists
        if guild_id not in self.active_giveaways or message_id not in self.active_giveaways[guild_id]:
            return await ctx.send("❌ Giveaway not found. Please provide a valid giveaway message ID.")
        
        # Get giveaway data
        giveaway = self.active_giveaways[guild_id][message_id]
        channel_id = giveaway["channel_id"]
        channel = ctx.guild.get_channel(channel_id)
        
        if not channel:
            return await ctx.send("❌ The channel for this giveaway no longer exists.")
        
        # End the giveaway
        success = await self.end_giveaway(ctx.guild, channel, message_id, giveaway)
        
        if success:
            await ctx.send("✅ Giveaway ended successfully!")
        else:
            await ctx.send("❌ Failed to end the giveaway. Please check the logs for more information.")
    
    @giveaway.command(name="cancel")
    @commands.has_permissions(manage_channels=True)
    async def giveaway_cancel(self, ctx, message_id: str):
        """Delete a giveaway without picking any winners"""
        guild_id = ctx.guild.id
        
        # Check if the giveaway exists
        if guild_id not in self.active_giveaways or message_id not in self.active_giveaways[guild_id]:
            return await ctx.send("❌ Giveaway not found. Please provide a valid giveaway message ID.")
        
        # Get giveaway data
        giveaway = self.active_giveaways[guild_id][message_id]
        channel_id = giveaway["channel_id"]
        channel = ctx.guild.get_channel(channel_id)
        
        if channel:
            try:
                # Try to delete the message
                message = await channel.fetch_message(int(message_id))
                await message.delete()
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                pass
        
        # Remove from active giveaways
        del self.active_giveaways[guild_id][message_id]
        self.save_giveaways(guild_id)
        
        await ctx.send("✅ Giveaway cancelled successfully!")
    
    @giveaway.command(name="reroll")
    @commands.has_permissions(manage_channels=True)
    async def giveaway_reroll(self, ctx, message_id: str, winners_count: int = 1):
        """Reroll a winner for the specified giveaway"""
        guild_id = ctx.guild.id
        
        # Check if the giveaway exists in ended giveaways
        if guild_id not in self.ended_giveaways or message_id not in self.ended_giveaways[guild_id]:
            return await ctx.send("❌ Ended giveaway not found. Please provide a valid ended giveaway message ID.")
        
        # Get giveaway data
        giveaway = self.ended_giveaways[guild_id][message_id]
        channel_id = giveaway["channel_id"]
        channel = ctx.guild.get_channel(channel_id)
        
        if not channel:
            return await ctx.send("❌ The channel for this giveaway no longer exists.")
        
        # Get valid entries
        valid_entries = giveaway.get("valid_entries", [])
        
        if not valid_entries:
            return await ctx.send("❌ No valid entries found for this giveaway.")
        
        # Reroll winners
        winners_count = min(winners_count, len(valid_entries))
        new_winners = random.sample(valid_entries, winners_count)
        
        if not new_winners:
            return await ctx.send("❌ Could not select new winners.")
        
        # Find previous winners to exclude from prize roles
        previous_winners = giveaway.get("winner_ids", [])
        
        # Update giveaway data with new winners
        giveaway["winner_ids"] = new_winners
        self.save_giveaways(guild_id)
        
        # Announce new winners
        winners_mention = ", ".join([f"<@{winner_id}>" for winner_id in new_winners])
        prize = giveaway["prize"]
        
        announcement = f"🎊 Rerolled! Congratulations {winners_mention}! You won the **{prize}**!"
        
        # If there are reward roles, apply them
        reward_role_ids = giveaway.get("reward_role_ids", [])
        if reward_role_ids:
            reward_roles = [ctx.guild.get_role(role_id) for role_id in reward_role_ids if ctx.guild.get_role(role_id)]
            if reward_roles:
                # Add roles to new winners
                for winner_id in new_winners:
                    if winner_id not in previous_winners:  # Only give roles to new winners
                        member = ctx.guild.get_member(winner_id)
                        if member:
                            for role in reward_roles:
                                try:
                                    await member.add_roles(role, reason=f"Giveaway prize reroll: {prize}")
                                except discord.Forbidden:
                                    pass
                
                # Add roles info to the announcement
                role_names = ", ".join([role.mention for role in reward_roles])
                announcement += f"\n\nYou have been given the following role(s): {role_names}"
        
        # Try to update the original message if possible
        try:
            message = await channel.fetch_message(int(message_id))
            embed = self.create_giveaway_embed(giveaway, is_ended=True)
            await message.edit(embed=embed)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            pass
        
        # Send announcement
        await ctx.send(announcement)
    
    @giveaway.command(name="list")
    @commands.has_permissions(manage_channels=True)
    async def giveaway_list(self, ctx):
        """List every active giveaway in the server"""
        guild_id = ctx.guild.id
        
        if guild_id not in self.active_giveaways or not self.active_giveaways[guild_id]:
            return await ctx.send("❌ There are no active giveaways in this server.")
        
        # Create embed
        embed = discord.Embed(
            title="🎉 Active Giveaways",
            description=f"There are {len(self.active_giveaways[guild_id])} active giveaways in this server.",
            color=discord.Color(DEFAULT_GIVEAWAY_COLOR)
        )
        
        for message_id, giveaway in list(self.active_giveaways[guild_id].items()):
            channel_id = giveaway["channel_id"]
            channel = ctx.guild.get_channel(channel_id)
            channel_name = channel.name if channel else "Unknown Channel"
            
            prize = giveaway["prize"]
            winners = giveaway["winners_count"]
            time_left = self.time_remaining(giveaway["end_time"])
            entries = len(giveaway.get("entries", []))
            
            embed.add_field(
                name=f"{prize} ({winners} {'winner' if winners == 1 else 'winners'})",
                value=f"• Channel: <#{channel_id}>\n• Ends in: {time_left}\n• Entries: {entries}\n• [Jump to Giveaway](https://discord.com/channels/{guild_id}/{channel_id}/{message_id})",
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    @giveaway.group(name="edit", invoke_without_command=True)
    @commands.has_permissions(manage_channels=True)
    async def giveaway_edit(self, ctx):
        """Edit options and limits for a specific giveaway"""
        # Show help message for edit command
        embed = discord.Embed(
            title="🎉 Giveaway Edit",
            description="Edit an existing giveaway by using one of the following sub-commands:",
            color=discord.Color(DEFAULT_GIVEAWAY_COLOR)
        )
        
        commands = [
            ("requiredroles", "Set required roles for giveaway entry"),
            ("maxlevel", "Set the maximum level requirement for giveaway entry"),
            ("winners", "Change the amount of winners for a giveaway"),
            ("thumbnail", "Change thumbnail for a giveaway embed"),
            ("minlevel", "Set the minimum level requirement for giveaway entry"),
            ("prize", "Change prize for a giveaway"),
            ("roles", "Award winners specific roles for a giveaway"),
            ("age", "Set minimum account age for new entries"),
            ("stay", "Set minimum server stay for new entries"),
            ("description", "Change description for a giveaway"),
            ("duration", "Change the end date for a giveaway"),
            ("host", "Set new hosts for a giveaway"),
            ("image", "Change image for a giveaway embed")
        ]
        
        for cmd, desc in commands:
            embed.add_field(name=f"giveaway edit {cmd}", value=desc, inline=False)
            
        await ctx.send(embed=embed)
    
    async def _update_giveaway_message(self, ctx, message_id, giveaway):
        """Helper to update giveaway message after editing"""
        guild_id = ctx.guild.id
        channel_id = giveaway["channel_id"]
        channel = ctx.guild.get_channel(channel_id)
        
        if not channel:
            await ctx.send("⚠️ The giveaway channel no longer exists, but settings have been updated.")
            return False
            
        try:
            message = await channel.fetch_message(int(message_id))
            embed = self.create_giveaway_embed(giveaway)
            await message.edit(embed=embed)
            return True
        except (discord.NotFound, discord.Forbidden, discord.HTTPException) as e:
            await ctx.send(f"⚠️ Could not update the giveaway message: {str(e)}")
            return False
    
    @giveaway_edit.command(name="requiredroles")
    @commands.has_permissions(manage_channels=True)
    async def edit_required_roles(self, ctx, message_id: str, *roles: discord.Role):
        """Set required roles for giveaway entry"""
        guild_id = ctx.guild.id
        
        # Check if the giveaway exists
        if guild_id not in self.active_giveaways or message_id not in self.active_giveaways[guild_id]:
            return await ctx.send("❌ Giveaway not found. Please provide a valid giveaway message ID.")
        
        # Get and update giveaway data
        giveaway = self.active_giveaways[guild_id][message_id]
        giveaway["required_role_ids"] = [role.id for role in roles]
        
        # Update message
        if await self._update_giveaway_message(ctx, message_id, giveaway):
            self.save_giveaways(guild_id)
            
            if roles:
                role_mentions = ", ".join(role.mention for role in roles)
                await ctx.send(f"✅ Required roles updated to: {role_mentions}")
            else:
                await ctx.send("✅ Required roles requirement cleared.")
    
    @giveaway_edit.command(name="maxlevel")
    @commands.has_permissions(manage_channels=True)
    async def edit_max_level(self, ctx, message_id: str, level: int = None):
        """Set the maximum level requirement for giveaway entry"""
        guild_id = ctx.guild.id
        
        # Check if the giveaway exists
        if guild_id not in self.active_giveaways or message_id not in self.active_giveaways[guild_id]:
            return await ctx.send("❌ Giveaway not found. Please provide a valid giveaway message ID.")
        
        # Check if levels cog exists
        levels_cog = self.bot.get_cog("Levels")
        if not levels_cog:
            return await ctx.send("❌ The Levels cog is not loaded. Maximum level requirement cannot be set.")
        
        # Get and update giveaway data
        giveaway = self.active_giveaways[guild_id][message_id]
        
        if level is None:
            # Remove the requirement
            if "max_level" in giveaway:
                del giveaway["max_level"]
            await ctx.send("✅ Maximum level requirement cleared.")
        else:
            if level <= 0:
                return await ctx.send("❌ Level must be a positive number.")
            
            giveaway["max_level"] = level
            await ctx.send(f"✅ Maximum level requirement set to {level}.")
        
        # Update message
        if await self._update_giveaway_message(ctx, message_id, giveaway):
            self.save_giveaways(guild_id)
    
    @giveaway_edit.command(name="winners")
    @commands.has_permissions(manage_channels=True)
    async def edit_winners(self, ctx, message_id: str, count: int):
        """Change the amount of winners for a giveaway"""
        guild_id = ctx.guild.id
        
        # Check if the giveaway exists
        if guild_id not in self.active_giveaways or message_id not in self.active_giveaways[guild_id]:
            return await ctx.send("❌ Giveaway not found. Please provide a valid giveaway message ID.")
        
        # Validate winners count
        if count < 1:
            return await ctx.send("❌ There must be at least 1 winner.")
        
        # Get and update giveaway data
        giveaway = self.active_giveaways[guild_id][message_id]
        giveaway["winners_count"] = count
        
        # Update message
        if await self._update_giveaway_message(ctx, message_id, giveaway):
            self.save_giveaways(guild_id)
            await ctx.send(f"✅ Winner count updated to {count}.")
    
    @giveaway_edit.command(name="thumbnail")
    @commands.has_permissions(manage_channels=True)
    async def edit_thumbnail(self, ctx, message_id: str, url: str = None):
        """Change thumbnail for a giveaway embed"""
        guild_id = ctx.guild.id
        
        # Check if the giveaway exists
        if guild_id not in self.active_giveaways or message_id not in self.active_giveaways[guild_id]:
            return await ctx.send("❌ Giveaway not found. Please provide a valid giveaway message ID.")
        
        # Get url from attachment if provided
        if url is None and ctx.message.attachments:
            url = ctx.message.attachments[0].url
            
        # Get and update giveaway data
        giveaway = self.active_giveaways[guild_id][message_id]
        
        if url is None:
            # Remove the thumbnail
            if "thumbnail_url" in giveaway:
                del giveaway["thumbnail_url"]
            await ctx.send("✅ Thumbnail removed.")
        else:
            giveaway["thumbnail_url"] = url
            await ctx.send("✅ Thumbnail updated.")
        
        # Update message
        if await self._update_giveaway_message(ctx, message_id, giveaway):
            self.save_giveaways(guild_id)
    
    @giveaway_edit.command(name="minlevel")
    @commands.has_permissions(manage_channels=True)
    async def edit_min_level(self, ctx, message_id: str, level: int = None):
        """Set the minimum level requirement for giveaway entry"""
        guild_id = ctx.guild.id
        
        # Check if the giveaway exists
        if guild_id not in self.active_giveaways or message_id not in self.active_giveaways[guild_id]:
            return await ctx.send("❌ Giveaway not found. Please provide a valid giveaway message ID.")
        
        # Check if levels cog exists
        levels_cog = self.bot.get_cog("Levels")
        if not levels_cog:
            return await ctx.send("❌ The Levels cog is not loaded. Minimum level requirement cannot be set.")
        
        # Get and update giveaway data
        giveaway = self.active_giveaways[guild_id][message_id]
        
        if level is None:
            # Remove the requirement
            if "min_level" in giveaway:
                del giveaway["min_level"]
            await ctx.send("✅ Minimum level requirement cleared.")
        else:
            if level <= 0:
                return await ctx.send("❌ Level must be a positive number.")
            
            giveaway["min_level"] = level
            await ctx.send(f"✅ Minimum level requirement set to {level}.")
        
        # Update message
        if await self._update_giveaway_message(ctx, message_id, giveaway):
            self.save_giveaways(guild_id)
    
    @giveaway_edit.command(name="prize")
    @commands.has_permissions(manage_channels=True)
    async def edit_prize(self, ctx, message_id: str, *, prize: str):
        """Change prize for a giveaway"""
        guild_id = ctx.guild.id
        
        # Check if the giveaway exists
        if guild_id not in self.active_giveaways or message_id not in self.active_giveaways[guild_id]:
            return await ctx.send("❌ Giveaway not found. Please provide a valid giveaway message ID.")
        
        # Validate prize
        if not prize:
            return await ctx.send("❌ Please provide a valid prize.")
        
        # Get and update giveaway data
        giveaway = self.active_giveaways[guild_id][message_id]
        giveaway["prize"] = prize
        
        # Update message
        if await self._update_giveaway_message(ctx, message_id, giveaway):
            self.save_giveaways(guild_id)
            await ctx.send(f"✅ Prize updated to: {prize}")
    
    @giveaway_edit.command(name="roles")
    @commands.has_permissions(manage_channels=True)
    async def edit_reward_roles(self, ctx, message_id: str, *roles: discord.Role):
        """Award winners specific roles for a giveaway"""
        guild_id = ctx.guild.id
        
        # Check if the giveaway exists
        if guild_id not in self.active_giveaways or message_id not in self.active_giveaways[guild_id]:
            return await ctx.send("❌ Giveaway not found. Please provide a valid giveaway message ID.")
        
        # Get and update giveaway data
        giveaway = self.active_giveaways[guild_id][message_id]
        giveaway["reward_role_ids"] = [role.id for role in roles]
        
        # Update message
        if await self._update_giveaway_message(ctx, message_id, giveaway):
            self.save_giveaways(guild_id)
            
            if roles:
                role_mentions = ", ".join(role.mention for role in roles)
                await ctx.send(f"✅ Reward roles updated to: {role_mentions}")
            else:
                await ctx.send("✅ Reward roles cleared.")
    
    @giveaway_edit.command(name="age")
    @commands.has_permissions(manage_channels=True)
    async def edit_account_age(self, ctx, message_id: str, *, age: str = None):
        """Set minimum account age for new entries (e.g. 7d, 24h, 30m)"""
        guild_id = ctx.guild.id
        
        # Check if the giveaway exists
        if guild_id not in self.active_giveaways or message_id not in self.active_giveaways[guild_id]:
            return await ctx.send("❌ Giveaway not found. Please provide a valid giveaway message ID.")
        
        # Get and update giveaway data
        giveaway = self.active_giveaways[guild_id][message_id]
        
        if age is None:
            # Remove the requirement
            if "min_account_age" in giveaway:
                del giveaway["min_account_age"]
            await ctx.send("✅ Minimum account age requirement cleared.")
        else:
            duration_seconds = self.parse_duration(age)
            if not duration_seconds:
                return await ctx.send("❌ Invalid duration format. Use format like 7d, 24h, 30m.")
            
            giveaway["min_account_age"] = duration_seconds
            formatted_time = self.format_time(duration_seconds)
            await ctx.send(f"✅ Minimum account age set to {formatted_time}.")
        
        # Update message
        if await self._update_giveaway_message(ctx, message_id, giveaway):
            self.save_giveaways(guild_id)
    
    @giveaway_edit.command(name="stay")
    @commands.has_permissions(manage_channels=True)
    async def edit_server_stay(self, ctx, message_id: str, days: int = None):
        """Set minimum server stay for new entries (in days)"""
        guild_id = ctx.guild.id
        
        # Check if the giveaway exists
        if guild_id not in self.active_giveaways or message_id not in self.active_giveaways[guild_id]:
            return await ctx.send("❌ Giveaway not found. Please provide a valid giveaway message ID.")
        
        # Get and update giveaway data
        giveaway = self.active_giveaways[guild_id][message_id]
        
        if days is None:
            # Remove the requirement
            if "min_server_stay" in giveaway:
                del giveaway["min_server_stay"]
            await ctx.send("✅ Minimum server stay requirement cleared.")
        else:
            if days < 0:
                return await ctx.send("❌ Days must be a non-negative number.")
            
            giveaway["min_server_stay"] = days
            await ctx.send(f"✅ Minimum server stay set to {days} days.")
        
        # Update message
        if await self._update_giveaway_message(ctx, message_id, giveaway):
            self.save_giveaways(guild_id)
    
    @giveaway_edit.command(name="description")
    @commands.has_permissions(manage_channels=True)
    async def edit_description(self, ctx, message_id: str, *, description: str = None):
        """Change description for a giveaway"""
        guild_id = ctx.guild.id
        
        # Check if the giveaway exists
        if guild_id not in self.active_giveaways or message_id not in self.active_giveaways[guild_id]:
            return await ctx.send("❌ Giveaway not found. Please provide a valid giveaway message ID.")
        
        # Get and update giveaway data
        giveaway = self.active_giveaways[guild_id][message_id]
        
        if description is None or not description.strip():
            # Reset to default description
            if "description" in giveaway:
                del giveaway["description"]
            await ctx.send("✅ Description reset to default.")
        else:
            giveaway["description"] = description
            await ctx.send("✅ Description updated.")
        
        # Update message
        if await self._update_giveaway_message(ctx, message_id, giveaway):
            self.save_giveaways(guild_id)
    
    @giveaway_edit.command(name="duration")
    @commands.has_permissions(manage_channels=True)
    async def edit_duration(self, ctx, message_id: str, *, duration: str):
        """Change the end date for a giveaway (e.g. 2d, 12h, 30m)"""
        guild_id = ctx.guild.id
        
        # Check if the giveaway exists
        if guild_id not in self.active_giveaways or message_id not in self.active_giveaways[guild_id]:
            return await ctx.send("❌ Giveaway not found. Please provide a valid giveaway message ID.")
        
        # Parse duration
        duration_seconds = self.parse_duration(duration)
        if not duration_seconds or duration_seconds < 60:
            return await ctx.send("❌ Invalid duration. Please provide a valid duration like 1d, 12h, 30m (minimum 1 minute).")
        
        # Get and update giveaway data
        giveaway = self.active_giveaways[guild_id][message_id]
        giveaway["end_time"] = datetime.datetime.utcnow().timestamp() + duration_seconds
        
        # Update message
        if await self._update_giveaway_message(ctx, message_id, giveaway):
            self.save_giveaways(guild_id)
            formatted_time = self.format_time(duration_seconds)
            await ctx.send(f"✅ Giveaway duration updated. New duration: {formatted_time}")
    
    @giveaway_edit.command(name="host")
    @commands.has_permissions(manage_channels=True)
    async def edit_host(self, ctx, message_id: str, *members: discord.Member):
        """Set new hosts for a giveaway"""
        guild_id = ctx.guild.id
        
        # Check if the giveaway exists
        if guild_id not in self.active_giveaways or message_id not in self.active_giveaways[guild_id]:
            return await ctx.send("❌ Giveaway not found. Please provide a valid giveaway message ID.")
        
        # Get and update giveaway data
        giveaway = self.active_giveaways[guild_id][message_id]
        
        if not members:
            return await ctx.send("❌ Please provide at least one host.")
        
        giveaway["host_ids"] = [member.id for member in members]
        
        # Update message
        if await self._update_giveaway_message(ctx, message_id, giveaway):
            self.save_giveaways(guild_id)
            
            host_mentions = ", ".join(member.mention for member in members)
            await ctx.send(f"✅ Giveaway hosts updated to: {host_mentions}")
    
    @giveaway_edit.command(name="image")
    @commands.has_permissions(manage_channels=True)
    async def edit_image(self, ctx, message_id: str, url: str = None):
        """Change image for a giveaway embed"""
        guild_id = ctx.guild.id
        
        # Check if the giveaway exists
        if guild_id not in self.active_giveaways or message_id not in self.active_giveaways[guild_id]:
            return await ctx.send("❌ Giveaway not found. Please provide a valid giveaway message ID.")
        
        # Get url from attachment if provided
        if url is None and ctx.message.attachments:
            url = ctx.message.attachments[0].url
            
        # Get and update giveaway data
        giveaway = self.active_giveaways[guild_id][message_id]
        
        if url is None:
            # Remove the image
            if "image_url" in giveaway:
                del giveaway["image_url"]
            await ctx.send("✅ Image removed.")
        else:
            giveaway["image_url"] = url
            await ctx.send("✅ Image updated.")
        
        # Update message
        if await self._update_giveaway_message(ctx, message_id, giveaway):
            self.save_giveaways(guild_id)

async def setup(bot):
    # Don't add the cog directly, as it will be imported by the main giveaway file
    pass 