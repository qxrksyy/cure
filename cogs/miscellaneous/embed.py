import discord
from discord.ext import commands
import json
import os
import logging
from datetime import datetime
import re

logger = logging.getLogger('bot')

class EmbedManager(commands.Cog):
    """
    Commands for creating and managing rich embeds
    """
    
    def __init__(self, bot):
        self.bot = bot
        self.config_path = "data/miscellaneous/embeds"
        self.embeds = {}  # Guild ID -> Dict of saved embeds
        
        # Create directory if it doesn't exist
        os.makedirs(self.config_path, exist_ok=True)
        
        # Load saved embeds
        self._load_embeds()
    
    def _load_embeds(self):
        """Load saved embeds from files"""
        for filename in os.listdir(self.config_path):
            if filename.endswith('.json'):
                guild_id = filename.split('.')[0]
                try:
                    with open(os.path.join(self.config_path, filename), 'r') as f:
                        self.embeds[guild_id] = json.load(f)
                except Exception as e:
                    logger.error(f"Error loading embeds for guild {guild_id}: {str(e)}")
                    self.embeds[guild_id] = {}
    
    def _save_embeds(self, guild_id):
        """Save embeds for a guild to file"""
        guild_id_str = str(guild_id)
        if guild_id_str in self.embeds:
            try:
                with open(os.path.join(self.config_path, f"{guild_id_str}.json"), 'w') as f:
                    json.dump(self.embeds[guild_id_str], f, indent=4)
            except Exception as e:
                logger.error(f"Error saving embeds for guild {guild_id}: {str(e)}")
    
    def _get_guild_embeds(self, guild_id):
        """Get embeds for a guild, initializing if needed"""
        guild_id_str = str(guild_id)
        if guild_id_str not in self.embeds:
            self.embeds[guild_id_str] = {}
        return self.embeds[guild_id_str]
    
    @commands.group(invoke_without_command=True)
    @commands.has_permissions(manage_messages=True)
    async def embed(self, ctx):
        """Manage and create new embeds easily"""
        embed = discord.Embed(
            title="Embed Manager",
            description="Create and manage custom embeds for your server",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(
            name="Available Commands",
            value=(
                "`embed create <name>` - Start customization for a new embed\n"
                "`embed copy <message>` - Copy an existing embed's code\n"
                "`embed delete <name>` - Delete a stored embed\n"
                "`embed preview <name>` - Preview a stored embed\n"
                "`embed list` - View all stored embeds"
            ),
            inline=False
        )
        
        embed.add_field(
            name="Related Commands",
            value=(
                "`createembed <code>` - Create an embed using JSON code\n"
                "`editembed <message> <embed>` - Edit an existing embed you created"
            ),
            inline=False
        )
        
        embed.set_footer(text="Use these commands to create and manage rich embeds")
        
        await ctx.send(embed=embed)
    
    @embed.command(name="create")
    @commands.has_permissions(manage_messages=True)
    async def embed_create(self, ctx, name: str = None):
        """Start customization for an embed"""
        if not name:
            await ctx.send("❌ Please provide a name for the embed.")
            return
            
        # Check if name is valid (no spaces or special characters except _ and -)
        if not re.match(r'^[a-zA-Z0-9_-]+$', name):
            await ctx.send("❌ Embed name must only contain letters, numbers, underscores, and hyphens.")
            return
            
        # Check if name is already in use
        guild_embeds = self._get_guild_embeds(ctx.guild.id)
        if name in guild_embeds:
            await ctx.send(f"❌ An embed with the name '{name}' already exists. Use a different name or delete the existing one first.")
            return
            
        # Start the embed creation process
        await ctx.send(
            f"🛠️ Let's create a new embed named '{name}'.\n\n"
            f"**Reply with the following information:**\n"
            f"```\n"
            f"Title: Your Title Here\n"
            f"Description: Your Description Here\n"
            f"Color: #HEX or a color name (blue, red, green, etc.)\n"
            f"Footer: Optional footer text\n"
            f"Image: Optional image URL\n"
            f"Thumbnail: Optional thumbnail URL\n"
            f"```\n"
            f"You can type 'cancel' to cancel the creation process."
        )
        
        # Wait for user response
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel
            
        try:
            response = await self.bot.wait_for('message', timeout=300.0, check=check)
            
            # Check if user wants to cancel
            if response.content.lower() == 'cancel':
                await ctx.send("❌ Embed creation cancelled.")
                return
                
            # Parse the response
            lines = response.content.split('\n')
            embed_data = {}
            current_field = None
            
            for line in lines:
                if line.startswith('Title:'):
                    embed_data['title'] = line[6:].strip()
                elif line.startswith('Description:'):
                    embed_data['description'] = line[12:].strip()
                elif line.startswith('Color:'):
                    color_str = line[6:].strip()
                    # Simple color parsing logic
                    if color_str.startswith('#'):
                        # HEX color
                        try:
                            color_int = int(color_str[1:], 16)
                            embed_data['color'] = color_int
                        except ValueError:
                            embed_data['color'] = 0x3498db  # Default blue
                    else:
                        # Named color
                        color_map = {
                            'blue': 0x3498db,
                            'red': 0xe74c3c,
                            'green': 0x2ecc71,
                            'gold': 0xf1c40f,
                            'purple': 0x9b59b6,
                            'orange': 0xe67e22,
                            'teal': 0x1abc9c
                        }
                        embed_data['color'] = color_map.get(color_str.lower(), 0x3498db)
                elif line.startswith('Footer:'):
                    embed_data['footer'] = {'text': line[7:].strip()}
                elif line.startswith('Image:'):
                    img_url = line[6:].strip()
                    if img_url:
                        embed_data['image'] = {'url': img_url}
                elif line.startswith('Thumbnail:'):
                    thumb_url = line[10:].strip()
                    if thumb_url:
                        embed_data['thumbnail'] = {'url': thumb_url}
            
            # Save the embed
            guild_embeds = self._get_guild_embeds(ctx.guild.id)
            guild_embeds[name] = embed_data
            self._save_embeds(ctx.guild.id)
            
            # Create and show preview
            embed = discord.Embed(
                title=embed_data.get('title', 'Untitled Embed'),
                description=embed_data.get('description', ''),
                color=embed_data.get('color', 0x3498db)
            )
            
            if 'footer' in embed_data:
                embed.set_footer(text=embed_data['footer']['text'])
                
            if 'image' in embed_data and embed_data['image']['url']:
                embed.set_image(url=embed_data['image']['url'])
                
            if 'thumbnail' in embed_data and embed_data['thumbnail']['url']:
                embed.set_thumbnail(url=embed_data['thumbnail']['url'])
            
            await ctx.send(f"✅ Embed '{name}' created successfully! Here's a preview:", embed=embed)
            
            # Inform about fields
            await ctx.send(
                "ℹ️ To add fields to your embed, use `createembed` with JSON code. You can use `embed copy` to get the code of this embed first."
            )
            
        except asyncio.TimeoutError:
            await ctx.send("❌ Embed creation timed out. Please try again.")
    
    @embed.command(name="list")
    @commands.has_permissions(manage_messages=True)
    async def embed_list(self, ctx):
        """View all stored embeds"""
        guild_embeds = self._get_guild_embeds(ctx.guild.id)
        
        if not guild_embeds:
            await ctx.send("ℹ️ No embeds have been saved for this server.")
            return
            
        embed = discord.Embed(
            title="Saved Embeds",
            description=f"This server has {len(guild_embeds)} saved embed(s)",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        for name, embed_data in guild_embeds.items():
            title = embed_data.get('title', 'Untitled')
            desc = embed_data.get('description', 'No description')
            # Truncate description if it's too long
            if len(desc) > 50:
                desc = desc[:50] + "..."
                
            embed.add_field(
                name=name,
                value=f"**Title:** {title}\n**Description:** {desc}",
                inline=False
            )
            
        embed.set_footer(text="Use 'embed preview <name>' to see an embed")
        
        await ctx.send(embed=embed)
    
    @embed.command(name="preview")
    @commands.has_permissions(manage_messages=True)
    async def embed_preview(self, ctx, name: str = None):
        """Send an existing embed"""
        if not name:
            await ctx.send("❌ Please specify the name of the embed to preview.")
            return
            
        guild_embeds = self._get_guild_embeds(ctx.guild.id)
        
        if name not in guild_embeds:
            await ctx.send(f"❌ No embed named '{name}' was found. Use `embed list` to see all available embeds.")
            return
            
        # Get the embed data
        embed_data = guild_embeds[name]
        
        # Create the embed
        embed = discord.Embed(
            title=embed_data.get('title', 'Untitled Embed'),
            description=embed_data.get('description', ''),
            color=embed_data.get('color', 0x3498db)
        )
        
        if 'footer' in embed_data:
            embed.set_footer(text=embed_data['footer']['text'])
            
        if 'image' in embed_data and embed_data['image']['url']:
            embed.set_image(url=embed_data['image']['url'])
            
        if 'thumbnail' in embed_data and embed_data['thumbnail']['url']:
            embed.set_thumbnail(url=embed_data['thumbnail']['url'])
            
        # Add fields if present
        if 'fields' in embed_data:
            for field in embed_data['fields']:
                embed.add_field(
                    name=field.get('name', 'Field'),
                    value=field.get('value', ''),
                    inline=field.get('inline', False)
                )
        
        await ctx.send(f"📝 Preview of embed '{name}':", embed=embed)
    
    @embed.command(name="delete")
    @commands.has_permissions(manage_messages=True)
    async def embed_delete(self, ctx, name: str = None):
        """Delete a stored embed"""
        if not name:
            await ctx.send("❌ Please specify the name of the embed to delete.")
            return
            
        guild_embeds = self._get_guild_embeds(ctx.guild.id)
        
        if name not in guild_embeds:
            await ctx.send(f"❌ No embed named '{name}' was found. Use `embed list` to see all available embeds.")
            return
            
        # Confirm deletion
        confirm_msg = await ctx.send(f"⚠️ Are you sure you want to delete the embed '{name}'? React with ✅ to confirm or ❌ to cancel.")
        
        # Add reactions
        await confirm_msg.add_reaction('✅')
        await confirm_msg.add_reaction('❌')
        
        # Wait for user's reaction
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ['✅', '❌'] and reaction.message.id == confirm_msg.id
            
        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=check)
            
            if str(reaction.emoji) == '✅':
                # Delete the embed
                del guild_embeds[name]
                self._save_embeds(ctx.guild.id)
                await ctx.send(f"✅ Embed '{name}' has been deleted.")
            else:
                await ctx.send("❌ Deletion cancelled.")
                
        except asyncio.TimeoutError:
            await ctx.send("❌ Deletion timed out. No changes were made.")
    
    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def createembed(self, ctx, *, code: str = None):
        """Create an embed using an embed code"""
        if not code:
            await ctx.send("❌ Please provide the JSON code for the embed.")
            return
            
        # Try to parse the code
        try:
            # Clean up the code in case it has code blocks
            if code.startswith('```') and code.endswith('```'):
                code = '\n'.join(code.split('\n')[1:-1])
                
            embed_data = json.loads(code)
            
            # Create the embed
            embed = discord.Embed()
            
            # Set title, description, and color if provided
            if 'title' in embed_data:
                embed.title = embed_data['title']
                
            if 'description' in embed_data:
                embed.description = embed_data['description']
                
            if 'color' in embed_data:
                embed.color = embed_data['color']
                
            # Set footer if provided
            if 'footer' in embed_data and 'text' in embed_data['footer']:
                embed.set_footer(text=embed_data['footer']['text'])
                
            # Set image if provided
            if 'image' in embed_data and 'url' in embed_data['image']:
                embed.set_image(url=embed_data['image']['url'])
                
            # Set thumbnail if provided
            if 'thumbnail' in embed_data and 'url' in embed_data['thumbnail']:
                embed.set_thumbnail(url=embed_data['thumbnail']['url'])
                
            # Add fields if provided
            if 'fields' in embed_data:
                for field in embed_data['fields']:
                    if 'name' in field and 'value' in field:
                        embed.add_field(
                            name=field['name'],
                            value=field['value'],
                            inline=field.get('inline', False)
                        )
            
            # Send the embed
            await ctx.send(embed=embed)
            
        except json.JSONDecodeError as e:
            await ctx.send(f"❌ Invalid JSON format: {str(e)}")
        except Exception as e:
            await ctx.send(f"❌ Error creating embed: {str(e)}")
            
    @embed.command(name="copy")
    @commands.has_permissions(manage_messages=True)
    async def embed_copy(self, ctx, message_id: int = None):
        """Copy an existing embed's code for creating an embed"""
        if not message_id:
            if ctx.message.reference:
                # Use replied-to message
                message = ctx.message.reference.resolved
            else:
                await ctx.send("❌ Please provide a message ID or reply to a message with an embed.")
                return
        else:
            try:
                # Try to fetch the message
                message = await ctx.channel.fetch_message(message_id)
            except discord.NotFound:
                await ctx.send("❌ Message not found. Make sure you're using the correct message ID and that it's in this channel.")
                return
                
        # Check if the message has embeds
        if not message.embeds:
            await ctx.send("❌ The specified message doesn't contain any embeds.")
            return
            
        # Get the first embed
        embed = message.embeds[0]
        
        # Convert to dict and format as JSON
        embed_dict = {
            'title': embed.title,
            'description': embed.description,
            'color': embed.color.value if embed.color else None
        }
        
        # Add footer if present
        if embed.footer and embed.footer.text:
            embed_dict['footer'] = {'text': embed.footer.text}
            
        # Add image if present
        if embed.image and embed.image.url:
            embed_dict['image'] = {'url': embed.image.url}
            
        # Add thumbnail if present
        if embed.thumbnail and embed.thumbnail.url:
            embed_dict['thumbnail'] = {'url': embed.thumbnail.url}
            
        # Add fields if present
        if embed.fields:
            embed_dict['fields'] = [
                {
                    'name': field.name,
                    'value': field.value,
                    'inline': field.inline
                }
                for field in embed.fields
            ]
            
        # Format as JSON
        formatted_json = json.dumps(embed_dict, indent=2)
        
        # Send the code
        await ctx.send(f"```json\n{formatted_json}\n```")
        await ctx.send("ℹ️ You can use this code with the `createembed` command to recreate this embed.")
        
    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def editembed(self, ctx, message_id: int = None, *, code: str = None):
        """Edit an embed you created"""
        if not message_id:
            if ctx.message.reference:
                # Use replied-to message
                message = ctx.message.reference.resolved
            else:
                await ctx.send("❌ Please provide a message ID or reply to a message with an embed.")
                return
        else:
            try:
                # Try to fetch the message
                message = await ctx.channel.fetch_message(message_id)
            except discord.NotFound:
                await ctx.send("❌ Message not found. Make sure you're using the correct message ID and that it's in this channel.")
                return
                
        # Check if the message is from the bot
        if message.author.id != self.bot.user.id:
            await ctx.send("❌ I can only edit my own messages.")
            return
            
        # Check if the message has embeds
        if not message.embeds:
            await ctx.send("❌ The specified message doesn't contain any embeds.")
            return
            
        if not code:
            await ctx.send("❌ Please provide the new JSON code for the embed.")
            return
            
        # Try to parse the code
        try:
            # Clean up the code in case it has code blocks
            if code.startswith('```') and code.endswith('```'):
                code = '\n'.join(code.split('\n')[1:-1])
                
            embed_data = json.loads(code)
            
            # Create the embed
            embed = discord.Embed()
            
            # Set title, description, and color if provided
            if 'title' in embed_data:
                embed.title = embed_data['title']
                
            if 'description' in embed_data:
                embed.description = embed_data['description']
                
            if 'color' in embed_data:
                embed.color = embed_data['color']
                
            # Set footer if provided
            if 'footer' in embed_data and 'text' in embed_data['footer']:
                embed.set_footer(text=embed_data['footer']['text'])
                
            # Set image if provided
            if 'image' in embed_data and 'url' in embed_data['image']:
                embed.set_image(url=embed_data['image']['url'])
                
            # Set thumbnail if provided
            if 'thumbnail' in embed_data and 'url' in embed_data['thumbnail']:
                embed.set_thumbnail(url=embed_data['thumbnail']['url'])
                
            # Add fields if provided
            if 'fields' in embed_data:
                for field in embed_data['fields']:
                    if 'name' in field and 'value' in field:
                        embed.add_field(
                            name=field['name'],
                            value=field['value'],
                            inline=field.get('inline', False)
                        )
            
            # Edit the message
            await message.edit(embed=embed)
            await ctx.send("✅ Embed has been edited successfully!")
            
        except json.JSONDecodeError as e:
            await ctx.send(f"❌ Invalid JSON format: {str(e)}")
        except Exception as e:
            await ctx.send(f"❌ Error editing embed: {str(e)}")

async def setup(bot):
    await bot.add_cog(EmbedManager(bot)) 