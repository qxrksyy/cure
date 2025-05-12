import discord
from discord.ext import commands
import json
import os
import logging
import re
from datetime import datetime
import asyncio

logger = logging.getLogger('bot')

class ServerFilters(commands.Cog):
    """
    Message filtering system for Discord servers
    """
    
    def __init__(self, bot):
        self.bot = bot
        self.config_path = "data/servers"
        self.filter_config = {}
        self.spam_cooldowns = {}
        
        # Create directory if it doesn't exist
        os.makedirs(self.config_path, exist_ok=True)
        
        # Load settings
        self._load_filter_config()
        
    def _load_filter_config(self):
        """Load filter settings from file"""
        try:
            filepath = f"{self.config_path}/filters.json"
            if os.path.exists(filepath):
                with open(filepath, "r") as f:
                    self.filter_config = json.load(f)
        except Exception as e:
            logger.error(f"Error loading filter settings: {str(e)}")
            self.filter_config = {}
    
    def _save_filter_config(self):
        """Save filter settings to file"""
        try:
            filepath = f"{self.config_path}/filters.json"
            with open(filepath, "w") as f:
                json.dump(self.filter_config, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving filter settings: {str(e)}")
    
    def _get_guild_filter_config(self, guild_id):
        """Get filter config for a guild"""
        guild_id = str(guild_id)
        if guild_id not in self.filter_config:
            self.filter_config[guild_id] = {
                "words": [],
                "channels": {},  # channel_id -> filter types enabled
                "exempt_roles": {},  # filter_type -> list of role IDs
                "invites": {
                    "whitelist": []
                },
                "links": {
                    "whitelist": []
                },
                "regex": []
            }
            self._save_filter_config()
        return self.filter_config[guild_id]
    
    def _is_exempt(self, filter_type, guild_id, member):
        """Check if a member is exempt from a filter type"""
        guild_config = self._get_guild_filter_config(guild_id)
        exempt_roles = guild_config.get("exempt_roles", {}).get(filter_type, [])
        
        # Check if the member has any exempt roles
        for role in member.roles:
            if str(role.id) in exempt_roles:
                return True
                
        return False
    
    async def _delete_message_with_reason(self, message, reason):
        """Delete a message and send a temporary notice"""
        try:
            await message.delete()
            
            # Send a temporary warning message
            warning = await message.channel.send(
                f"⚠️ {message.author.mention}, your message was removed: {reason}"
            )
            
            # Delete the warning after 5 seconds
            await warning.delete(delay=5)
            
        except discord.Forbidden:
            logger.error(f"Missing permissions to delete message in channel {message.channel.id}")
        except Exception as e:
            logger.error(f"Error deleting filtered message: {str(e)}")
    
    @commands.group(name="filter", invoke_without_command=True)
    async def filter(self, ctx):
        """View a variety of options to help clean chat"""
        embed = discord.Embed(
            title="Message Filtering System",
            description="Set up automatic message filtering in your server",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        # List available filter types
        embed.add_field(
            name="Available Filters",
            value=(
                "• `invites`: Delete Discord invite links\n"
                "• `links`: Delete all links\n"
                "• `caps`: Delete messages with too many uppercase characters\n"
                "• `spam`: Delete messages from users sending too quickly\n"
                "• `massmention`: Delete messages mentioning too many users\n"
                "• `emoji`: Delete messages with too many emojis\n"
                "• `spoilers`: Delete messages with too many spoilers\n"
                "• `musicfiles`: Delete audio file attachments\n"
                "• `words`: Filter specific words or phrases\n"
                "• `regex`: Filter messages matching regex patterns"
            ),
            inline=False
        )
        
        # List filter commands
        embed.add_field(
            name="Common Commands",
            value=(
                "`filter invites #channel on/off` - Enable/disable invite filter\n"
                "`filter links #channel on/off` - Enable/disable link filter\n"
                "`filter caps #channel on/off` - Enable/disable caps filter\n"
                "`filter spam #channel on/off` - Enable/disable spam filter\n"
                "`filter add word1 [word2...]` - Add filtered words\n"
                "`filter list` - List filtered words\n"
                "`filter reset` - Reset all filter settings"
            ),
            inline=False
        )
        
        # Exemption commands
        embed.add_field(
            name="Exemption Commands",
            value=(
                "Use the following commands to exempt roles from filters:\n"
                "`filter invites exempt @role` - Exempt role from invite filter\n"
                "`filter links exempt @role` - Exempt role from link filter\n"
                "`filter caps exempt @role` - Exempt role from caps filter\n"
                "`filter spam exempt @role` - Exempt role from spam filter\n"
                "... and so on for other filter types"
            ),
            inline=False
        )
        
        await ctx.send(embed=embed)
        
    @filter.command(name="add")
    @commands.has_permissions(manage_guild=True)
    async def filter_add(self, ctx, *words):
        """Add a filtered word"""
        if not words:
            await ctx.send("❌ Please specify one or more words to filter.")
            return
            
        guild_config = self._get_guild_filter_config(ctx.guild.id)
        
        added = []
        already_filtered = []
        
        for word in words:
            word = word.lower().strip()
            if word in guild_config["words"]:
                already_filtered.append(word)
            else:
                guild_config["words"].append(word)
                added.append(word)
                
        self._save_filter_config()
        
        response = []
        if added:
            response.append(f"✅ Added {len(added)} word(s) to the filter.")
        if already_filtered:
            response.append(f"ℹ️ {len(already_filtered)} word(s) were already being filtered.")
            
        await ctx.send("\n".join(response))
        
    @filter.command(name="list")
    @commands.has_permissions(manage_guild=True)
    async def filter_list(self, ctx):
        """View a list of filtered words in guild"""
        guild_config = self._get_guild_filter_config(ctx.guild.id)
        
        embed = discord.Embed(
            title="Filtered Words",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        # Handle filtered words
        if guild_config["words"]:
            # Split into chunks to avoid hitting embed field limit
            chunks = [guild_config["words"][i:i+20] for i in range(0, len(guild_config["words"]), 20)]
            
            for i, chunk in enumerate(chunks):
                embed.add_field(
                    name=f"Words {i*20+1}-{i*20+len(chunk)}",
                    value="• " + "\n• ".join([f"`{word}`" for word in chunk]),
                    inline=False
                )
        else:
            embed.add_field(
                name="No Filtered Words",
                value="No words are currently being filtered.",
                inline=False
            )
            
        # Handle regex filters
        if guild_config.get("regex", []):
            regex_text = "• " + "\n• ".join([f"`{pattern}`" for pattern in guild_config["regex"]])
            embed.add_field(
                name="Regex Patterns",
                value=regex_text,
                inline=False
            )
            
        # Add info on enabled channels
        enabled_filters = {}
        for channel_id, filters in guild_config.get("channels", {}).items():
            channel = ctx.guild.get_channel(int(channel_id))
            if not channel:
                continue
                
            for filter_type in filters:
                if filter_type not in enabled_filters:
                    enabled_filters[filter_type] = []
                enabled_filters[filter_type].append(channel.mention)
                
        if enabled_filters:
            for filter_type, channels in enabled_filters.items():
                embed.add_field(
                    name=f"{filter_type.capitalize()} Filter",
                    value="Enabled in: " + ", ".join(channels),
                    inline=False
                )
        
        await ctx.send(embed=embed)
        
    @filter.command(name="reset")
    @commands.has_permissions(manage_guild=True)
    async def filter_reset(self, ctx):
        """Reset all filtered words"""
        # Confirm reset
        confirm_msg = await ctx.send(
            "⚠️ **Warning**: This will remove all filtered words and reset all filter settings. "
            "Are you sure? Type `yes` to confirm."
        )
        
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() == "yes"
            
        try:
            await self.bot.wait_for("message", check=check, timeout=30.0)
        except:
            await confirm_msg.edit(content="Operation cancelled.")
            return
            
        # Reset filters
        if str(ctx.guild.id) in self.filter_config:
            del self.filter_config[str(ctx.guild.id)]
            self._save_filter_config()
            
        await ctx.send("✅ All filter settings have been reset.")
        
    @filter.command(name="invites")
    @commands.has_permissions(manage_guild=True)
    async def filter_invites(self, ctx, channel: discord.TextChannel = None, setting: str = None):
        """Delete any message that contains a server invite"""
        if channel is None or setting is None:
            await ctx.send("❌ Please specify a channel and `on` or `off`.")
            return
            
        setting = setting.lower()
        if setting not in ["on", "off", "enable", "disable", "true", "false", "yes", "no"]:
            await ctx.send("❌ Invalid setting. Please use `on` or `off`.")
            return
            
        enabled = setting in ["on", "enable", "true", "yes"]
        
        guild_config = self._get_guild_filter_config(ctx.guild.id)
        
        # Initialize channel entry if it doesn't exist
        if "channels" not in guild_config:
            guild_config["channels"] = {}
            
        channel_id = str(channel.id)
        if channel_id not in guild_config["channels"]:
            guild_config["channels"][channel_id] = []
            
        # Update filter
        if enabled:
            if "invites" not in guild_config["channels"][channel_id]:
                guild_config["channels"][channel_id].append("invites")
                self._save_filter_config()
                await ctx.send(f"✅ Invite filter has been enabled in {channel.mention}.")
            else:
                await ctx.send(f"ℹ️ Invite filter is already enabled in {channel.mention}.")
        else:
            if "invites" in guild_config["channels"][channel_id]:
                guild_config["channels"][channel_id].remove("invites")
                self._save_filter_config()
                await ctx.send(f"✅ Invite filter has been disabled in {channel.mention}.")
            else:
                await ctx.send(f"ℹ️ Invite filter is already disabled in {channel.mention}.")
                
    @filter.command(name="invites_exempt")
    @commands.has_permissions(manage_guild=True)
    async def filter_invites_exempt(self, ctx, role: discord.Role = None):
        """Exempt roles from the invites filter"""
        if role is None:
            await ctx.send("❌ Please specify a role to exempt from the invite filter.")
            return
            
        guild_config = self._get_guild_filter_config(ctx.guild.id)
        
        if "exempt_roles" not in guild_config:
            guild_config["exempt_roles"] = {}
            
        if "invites" not in guild_config["exempt_roles"]:
            guild_config["exempt_roles"]["invites"] = []
            
        role_id = str(role.id)
        
        # Toggle exemption
        if role_id in guild_config["exempt_roles"]["invites"]:
            guild_config["exempt_roles"]["invites"].remove(role_id)
            self._save_filter_config()
            await ctx.send(f"✅ {role.mention} is no longer exempt from the invite filter.")
        else:
            guild_config["exempt_roles"]["invites"].append(role_id)
            self._save_filter_config()
            await ctx.send(f"✅ {role.mention} is now exempt from the invite filter.")
            
    @filter.command(name="invites_exempt_list")
    @commands.has_permissions(manage_guild=True)
    async def filter_invites_exempt_list(self, ctx):
        """View list of roles exempted from invites filter"""
        guild_config = self._get_guild_filter_config(ctx.guild.id)
        
        exempt_roles = guild_config.get("exempt_roles", {}).get("invites", [])
        
        embed = discord.Embed(
            title="Invite Filter Exemptions",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        if not exempt_roles:
            embed.description = "No roles are exempt from the invite filter."
        else:
            roles_text = []
            for role_id in exempt_roles:
                role = ctx.guild.get_role(int(role_id))
                if role:
                    roles_text.append(f"• {role.mention}")
                    
            embed.add_field(
                name="Exempt Roles",
                value="\n".join(roles_text) or "No valid exempt roles",
                inline=False
            )
            
        await ctx.send(embed=embed)
        
    @commands.Cog.listener()
    async def on_message(self, message):
        """Check messages against filters"""
        # Skip if not in a guild or if message is from a bot
        if not message.guild or message.author.bot:
            return
            
        guild_id = str(message.guild.id)
        channel_id = str(message.channel.id)
        
        # Get filter config
        if guild_id not in self.filter_config:
            return
            
        guild_config = self.filter_config[guild_id]
        
        # Check if the channel has any filters enabled
        if channel_id not in guild_config.get("channels", {}):
            return
            
        # Allow messages from users with manage messages permission
        member = message.guild.get_member(message.author.id)
        if member and member.guild_permissions.manage_messages:
            return
            
        # Get enabled filters for this channel
        enabled_filters = guild_config["channels"][channel_id]
        
        # Check invite links
        if "invites" in enabled_filters and not self._is_exempt("invites", guild_id, member):
            # Discord invite regex pattern
            invite_pattern = r"(discord\.gg|discordapp\.com\/invite|discord\.com\/invite)\/[a-zA-Z0-9]+"
            if re.search(invite_pattern, message.content, re.IGNORECASE):
                # Check whitelist
                is_whitelisted = False
                for whitelisted in guild_config.get("invites", {}).get("whitelist", []):
                    if whitelisted.lower() in message.content.lower():
                        is_whitelisted = True
                        break
                        
                if not is_whitelisted:
                    await self._delete_message_with_reason(message, "Discord invites are not allowed in this channel.")
                    return
        
        # Check word filters
        if guild_config.get("words", []):
            content_lower = message.content.lower()
            for word in guild_config["words"]:
                if word.lower() in content_lower:
                    await self._delete_message_with_reason(message, "Your message contained a filtered word.")
                    return
                    
        # Check regex filters
        if guild_config.get("regex", []):
            for pattern in guild_config["regex"]:
                try:
                    if re.search(pattern, message.content, re.IGNORECASE):
                        await self._delete_message_with_reason(message, "Your message matched a filtered pattern.")
                        return
                except:
                    # Invalid regex pattern
                    continue

async def setup(bot):
    await bot.add_cog(ServerFilters(bot)) 