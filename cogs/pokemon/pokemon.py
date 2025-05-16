import discord
from discord.ext import commands
import random
import asyncio
from datetime import datetime
import logging
from .pokemon_db import PokemonDB
import sqlite3

logger = logging.getLogger('bot')

class PokemonCog(commands.Cog, name="Pokemon"):
    """Pokemon catching and battling commands"""
    
    def __init__(self, bot):
        self.bot = bot
        self.db = PokemonDB()
        self.shop_items = {
            'pokeballs': {
                'name': 'Pokeball',
                'emoji': '🔴',
                'price': 100,
                'description': 'Standard Pokeball with a 40% catch rate'
            },
            'greatballs': {
                'name': 'Great Ball',
                'emoji': '🔵',
                'price': 500,
                'description': 'Better Pokeball with a 60% catch rate'
            },
            'ultraballs': {
                'name': 'Ultra Ball',
                'emoji': '⚫',
                'price': 1200,
                'description': 'High-quality Pokeball with an 80% catch rate'
            },
            'masterballs': {
                'name': 'Master Ball',
                'emoji': '🟣',
                'price': 10000,
                'description': 'Special Pokeball with a 100% catch rate'
            },
            'luxuryballs': {
                'name': 'Luxury Ball',
                'emoji': '🌑',
                'price': 800,
                'description': 'Comfortable Pokeball that makes caught Pokémon friendlier'
            },
            'heavyballs': {
                'name': 'Heavy Ball',
                'emoji': '⚙️',
                'price': 600,
                'description': 'Works better on heavy Pokémon'
            },
            'netballs': {
                'name': 'Net Ball',
                'emoji': '🕸️',
                'price': 700,
                'description': 'Works better on Water and Bug type Pokémon'
            },
            'diveballs': {
                'name': 'Dive Ball',
                'emoji': '🌊',
                'price': 700,
                'description': 'Works better on Water type Pokémon'
            },
            'nestballs': {
                'name': 'Nest Ball',
                'emoji': '🌿',
                'price': 500,
                'description': 'Works better on lower level Pokémon'
            },
            'quickballs': {
                'name': 'Quick Ball',
                'emoji': '⚡',
                'price': 800,
                'description': 'Works better at the start of encounters'
            },
            'duskballs': {
                'name': 'Dusk Ball',
                'emoji': '🌙',
                'price': 800,
                'description': 'Works better during night time'
            },
            'timerballs': {
                'name': 'Timer Ball',
                'emoji': '⏱️',
                'price': 700,
                'description': 'Gets better the longer the battle lasts'
            },
            'potions': {
                'name': 'Potion',
                'emoji': '🧪',
                'price': 300,
                'description': 'Heals a Pokemon by 20 HP'
            },
            'super_potions': {
                'name': 'Super Potion',
                'emoji': '💊',
                'price': 700,
                'description': 'Heals a Pokemon by 50 HP'
            },
            'revives': {
                'name': 'Revive',
                'emoji': '💫',
                'price': 1500,
                'description': 'Revives a fainted Pokemon and restores half its HP'
            }
        }
        
    @commands.command(name="journey")
    async def journey(self, ctx):
        """Start your Pokemon journey"""
        if self.db.trainer_exists(ctx.author.id):
            embed = discord.Embed(
                title="Trainer Profile Exists",
                description="You have already started your Pokemon journey!",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        success = self.db.create_trainer(ctx.author.id, ctx.author.name)
        
        if success:
            embed = discord.Embed(
                title="Pokemon Journey Started!",
                description="Welcome to the world of Pokemon! Your journey has begun!",
                color=discord.Color.green()
            )
            embed.add_field(name="Starter Pack", value="5x Pokeballs, 3x Potions, 1x Revive")
            embed.add_field(name="Next Steps", value="Use `!catch` to find your first Pokemon!")
            embed.set_thumbnail(url="https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/items/poke-ball.png")
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="Error",
                description="There was an error creating your trainer profile. Please try again later.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
    
    @commands.command(name="catch")
    async def catch(self, ctx):
        """Try to catch a wild Pokemon"""
        if not self.db.trainer_exists(ctx.author.id):
            embed = discord.Embed(
                title="No Trainer Profile",
                description="You haven't started your Pokemon journey yet! Use `!journey` to begin.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        # Check if on cooldown
        if not self.db.can_catch_pokemon(ctx.author.id):
            cooldown = self.db.get_catch_cooldown_remaining(ctx.author.id)
            minutes = int(cooldown // 60)
            seconds = int(cooldown % 60)
            
            embed = discord.Embed(
                title="Catch Cooldown",
                description=f"You need to wait {minutes}m {seconds}s before searching for another Pokemon.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        # Check for Pokeballs
        inventory = self.db.get_inventory(ctx.author.id)
        
        # Check if the user has any Pokéballs
        has_pokeballs = False
        for ball_type in ['pokeballs', 'greatballs', 'ultraballs', 'masterballs', 
                          'luxuryballs', 'heavyballs', 'netballs', 'diveballs', 
                          'nestballs', 'quickballs', 'duskballs', 'timerballs']:
            if inventory.get(ball_type, 0) > 0:
                has_pokeballs = True
                break
                
        if not has_pokeballs:
            embed = discord.Embed(
                title="No Pokeballs",
                description="You don't have any Pokeballs! Buy some from the shop with `!pokeshop`.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        # Start the catch sequence
        loading_embed = discord.Embed(
            title="Searching for Pokemon...",
            description="Rustling in the tall grass...",
            color=discord.Color.blue()
        )
        message = await ctx.send(embed=loading_embed)
        
        # Simulate searching
        await asyncio.sleep(2)
        
        # Get a random Pokemon
        pokemon_id = self.db.get_random_wild_pokemon()
        
        # Fetch Pokemon data from API
        pokemon_data = await self.db.fetch_pokemon_data(pokemon_id)
        if not pokemon_data:
            await message.edit(embed=discord.Embed(
                title="No Pokemon Found",
                description="You couldn't find any Pokemon. Try again later.",
                color=discord.Color.red()
            ))
            return
            
        # Show the encountered Pokemon
        pokemon_name = pokemon_data['name'].capitalize()
        pokemon_sprite = pokemon_data['sprites']['front_default']
        pokemon_types = [t['type']['name'].capitalize() for t in pokemon_data['types']]
        
        # Check if this is a mythical or legendary Pokemon
        is_mythical = pokemon_data['id'] in self.db.mythical_pokemon
        is_legendary = pokemon_data['id'] in self.db.legendary_pokemon and not is_mythical
        
        # Create encounter embed with special formatting for different rarities
        if is_mythical:
            encounter_embed = discord.Embed(
                title=f"✨ A MYTHICAL {pokemon_name} appeared! ✨",
                description=f"Type: {' / '.join(pokemon_types)}\n**This is an EXTREMELY RARE mythical Pokémon!**",
                color=discord.Color.purple()  # Purple color for mythicals
            )
            # Add special message for mythicals
            encounter_embed.add_field(
                name="Extraordinary Find!", 
                value="Mythical Pokémon are almost impossible to find! This is an incredibly rare opportunity!", 
                inline=False
            )
        elif is_legendary:
            encounter_embed = discord.Embed(
                title=f"⭐ A LEGENDARY {pokemon_name} appeared! ⭐",
                description=f"Type: {' / '.join(pokemon_types)}\n**This is an extremely rare Pokémon!**",
                color=discord.Color.gold()  # Gold color for legendaries
            )
        else:
            encounter_embed = discord.Embed(
                title=f"A wild {pokemon_name} appeared!",
                description=f"Type: {' / '.join(pokemon_types)}",
                color=discord.Color.green()
            )
            
        encounter_embed.set_image(url=pokemon_sprite)
        encounter_embed.add_field(name="Options", value="Choose a Pokeball to throw:")
        
        # Add available balls
        ball_options = []
        for ball_type, ball_info in self.shop_items.items():
            if ball_type.endswith('balls') and inventory.get(ball_type, 0) > 0:
                ball_options.append(f"{ball_info['emoji']} {ball_info['name']} ({inventory[ball_type]})")
            
        encounter_embed.add_field(name="Available Balls", value="\n".join(ball_options) or "No Pokéballs available!", inline=False)
        
        await message.edit(embed=encounter_embed)
        
        # Add reaction options for Pokeballs
        ball_emojis = []
        for ball_type, ball_info in self.shop_items.items():
            if ball_type.endswith('balls') and inventory.get(ball_type, 0) > 0:
                await message.add_reaction(ball_info['emoji'])
                ball_emojis.append(ball_info['emoji'])
            
        # Wait for reaction from user
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ball_emojis and reaction.message.id == message.id
            
        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=check)
        except asyncio.TimeoutError:
            timeout_embed = discord.Embed(
                title=f"The wild {pokemon_name} fled!",
                description="You took too long to throw a Pokeball.",
                color=discord.Color.red()
            )
            await message.edit(embed=timeout_embed)
            return
            
        # Determine which ball was used
        ball_type = ""
        for ball_key, ball_info in self.shop_items.items():
            if ball_key.endswith('balls') and str(reaction.emoji) == ball_info['emoji']:
                ball_type = ball_key
                break
            
        # Remove the ball from inventory
        self.db.remove_from_inventory(ctx.author.id, ball_type, 1)
        
        # Collect encounter data for special Pokéball effects
        encounter_data = {
            'turn_count': 1,  # First turn of the encounter
            'time_of_day': 'day' if 6 <= datetime.now().hour < 18 else 'night',
            'pokemon_weight': pokemon_data.get('weight', 50),
            'pokemon_types': [t['type']['name'].lower() for t in pokemon_data['types']],
            'pokemon_level': random.randint(1, 10)  # Wild Pokémon level range
        }
        
        # Calculate catch chance
        catch_chance = self.db.calculate_catch_chance(
            ctx.author.id, 
            ball_type, 
            pokemon_data['id'], 
            encounter_data
        )
        
        # Master ball always catches
        if ball_type == "masterballs":
            catch_chance = 1.0
            
        # Animated catching sequence
        ball_name = self.shop_items[ball_type]['name']
        ball_emoji = self.shop_items[ball_type]['emoji']
        
        catch_embed = discord.Embed(
            title=f"You threw a {ball_emoji} {ball_name}!",
            description="The ball is shaking...",
            color=discord.Color.blue()
        )
        catch_embed.set_image(url=pokemon_sprite)
        await message.edit(embed=catch_embed)
        
        # Simulate ball shakes
        await asyncio.sleep(1)
        
        # Update the last catch timestamp
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE trainers SET last_catch = ? WHERE user_id = ?",
            (datetime.now().isoformat(), str(ctx.author.id))
        )
        conn.commit()
        conn.close()
        
        # Determine if caught
        caught = random.random() < catch_chance
        
        try:
            if caught:
                # Add Pokemon to collection
                caught_pokemon = await self.db.add_pokemon(ctx.author.id, pokemon_data['id'])
                
                if caught_pokemon:
                    # Check the Pokémon type
                    is_mythical = pokemon_data['id'] in self.db.mythical_pokemon
                    is_legendary = pokemon_data['id'] in self.db.legendary_pokemon and not is_mythical
                    
                    if is_mythical:
                        success_embed = discord.Embed(
                            title=f"✨ EXTRAORDINARY! You caught the MYTHICAL {pokemon_name}! ✨",
                            description=f"The MYTHICAL {pokemon_name} has been added to your collection!",
                            color=discord.Color.purple()
                        )
                        success_embed.set_image(url=pokemon_sprite)
                        success_embed.add_field(name="Level", value=caught_pokemon['level'])
                        success_embed.add_field(name="Types", value=" / ".join(caught_pokemon['types']).capitalize())
                        
                        # Display stats for mythical (with emphasis)
                        stats = caught_pokemon['stats']
                        stats_text = f"HP: **{stats['hp']}** | ATK: **{stats['attack']}** | DEF: **{stats['defense']}**\n"
                        stats_text += f"SP.ATK: **{stats['special_attack']}** | SP.DEF: **{stats['special_defense']}** | SPD: **{stats['speed']}**"
                        success_embed.add_field(name="Mythical Stats", value=stats_text, inline=False)
                        
                        # Add a special congratulatory message
                        success_embed.add_field(
                            name="PHENOMENAL ACHIEVEMENT!", 
                            value="You've caught one of the rarest Pokémon in existence! Mythical Pokémon are the stuff of legends - few trainers ever even see one, let alone catch one!",
                            inline=False
                        )
                    elif is_legendary:
                        success_embed = discord.Embed(
                            title=f"⭐ INCREDIBLE! You caught the LEGENDARY {pokemon_name}! ⭐",
                            description=f"The LEGENDARY {pokemon_name} has been added to your collection!",
                            color=discord.Color.gold()
                        )
                        success_embed.set_image(url=pokemon_sprite)
                        success_embed.add_field(name="Level", value=caught_pokemon['level'])
                        success_embed.add_field(name="Types", value=" / ".join(caught_pokemon['types']).capitalize())
                        
                        # Display stats for legendary (with emphasis)
                        stats = caught_pokemon['stats']
                        stats_text = f"HP: **{stats['hp']}** | ATK: **{stats['attack']}** | DEF: **{stats['defense']}**\n"
                        stats_text += f"SP.ATK: **{stats['special_attack']}** | SP.DEF: **{stats['special_defense']}** | SPD: **{stats['speed']}**"
                        success_embed.add_field(name="Legendary Stats", value=stats_text, inline=False)
                        
                        # Add a special congratulatory message
                        success_embed.add_field(
                            name="Congratulations!", 
                            value="You've caught an extremely rare Legendary Pokémon! This is a remarkable achievement that few trainers accomplish.",
                            inline=False
                        )
                    else:
                        success_embed = discord.Embed(
                            title=f"Gotcha! {pokemon_name} was caught!",
                            description=f"The Pokemon has been added to your collection.",
                            color=discord.Color.green()
                        )
                        success_embed.set_image(url=pokemon_sprite)
                        success_embed.add_field(name="Level", value=caught_pokemon['level'])
                        success_embed.add_field(name="Types", value=" / ".join(caught_pokemon['types']).capitalize())
                        
                        # Display some stats
                        stats = caught_pokemon['stats']
                        stats_text = f"HP: {stats['hp']} | ATK: {stats['attack']} | DEF: {stats['defense']}\n"
                        stats_text += f"SP.ATK: {stats['special_attack']} | SP.DEF: {stats['special_defense']} | SPD: {stats['speed']}"
                        success_embed.add_field(name="Stats", value=stats_text, inline=False)
                    
                    await message.edit(embed=success_embed)
                else:
                    # Something went wrong with adding the Pokemon
                    logger.error(f"Failed to add Pokemon {pokemon_data['id']} to user {ctx.author.id}'s collection")
                    error_embed = discord.Embed(
                        title="Error Catching Pokemon",
                        description="There was an error adding this Pokemon to your collection. Please try again later.",
                        color=discord.Color.red()
                    )
                    await message.edit(embed=error_embed)
            else:
                fail_embed = discord.Embed(
                    title=f"Oh no! The wild {pokemon_name} broke free!",
                    description="The Pokemon escaped and ran away.",
                    color=discord.Color.red()
                )
                fail_embed.set_image(url=pokemon_sprite)
                await message.edit(embed=fail_embed)
        except Exception as e:
            logger.error(f"Error in catch command: {e}")
            error_embed = discord.Embed(
                title="Error Processing Catch",
                description="There was an error processing your Pokemon catch. Please try again later.",
                color=discord.Color.red()
            )
            await message.edit(embed=error_embed)
    
    @commands.command(name="pokemon")
    async def pokemon(self, ctx, *, pokemon_name=None):
        """Look up a Pokemon's stats"""
        if pokemon_name is None:
            # If no Pokemon specified, show user's primary Pokemon
            if not self.db.trainer_exists(ctx.author.id):
                embed = discord.Embed(
                    title="No Trainer Profile",
                    description="You haven't started your Pokemon journey yet! Use `!journey` to begin.",
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed)
                return
                
            primary_pokemon = self.db.get_primary_pokemon(ctx.author.id)
            if not primary_pokemon:
                embed = discord.Embed(
                    title="No Primary Pokemon",
                    description="You don't have a primary Pokemon yet! Use `!catch` to find one.",
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed)
                return
                
            # Display the user's primary Pokemon
            pokemon_embed = discord.Embed(
                title=f"{primary_pokemon['display_name']} (Lvl {primary_pokemon['level']})",
                description=f"Your primary Pokemon",
                color=discord.Color.blue()
            )
            
            # Add Pokemon info
            pokemon_embed.set_thumbnail(url=primary_pokemon['sprite_url'])
            pokemon_embed.add_field(name="Types", value=" / ".join(primary_pokemon['types']).capitalize())
            pokemon_embed.add_field(name="XP", value=f"{primary_pokemon['xp']}/{primary_pokemon['xp_to_level']}")
            
            # Display stats
            stats = primary_pokemon['stats']
            stats_text = f"HP: {stats['hp']} | ATK: {stats['attack']} | DEF: {stats['defense']}\n"
            stats_text += f"SP.ATK: {stats['special_attack']} | SP.DEF: {stats['special_defense']} | SPD: {stats['speed']}"
            pokemon_embed.add_field(name="Stats", value=stats_text, inline=False)
            
            # Display moves
            moves_text = ""
            for move in primary_pokemon['moves']:
                moves_text += f"• {move['name'].replace('-', ' ').title()}\n"
            
            if moves_text:
                pokemon_embed.add_field(name="Moves", value=moves_text, inline=False)
            else:
                pokemon_embed.add_field(name="Moves", value="No moves learned", inline=False)
                
            await ctx.send(embed=pokemon_embed)
        else:
            # Look up a Pokemon by name/id
            pokemon_data = await self.db.fetch_pokemon_data(pokemon_name.lower())
            
            if not pokemon_data:
                embed = discord.Embed(
                    title="Pokemon Not Found",
                    description=f"Could not find a Pokemon named '{pokemon_name}'.",
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed)
                return
                
            # Display the Pokemon info from API
            pokemon_embed = discord.Embed(
                title=f"{pokemon_data['name'].capitalize()} #{pokemon_data['id']}",
                description=f"Pokemon information",
                color=discord.Color.blue()
            )
            
            # Add Pokemon info
            pokemon_embed.set_thumbnail(url=pokemon_data['sprites']['front_default'])
            
            # Add types
            types = [t['type']['name'].capitalize() for t in pokemon_data['types']]
            pokemon_embed.add_field(name="Types", value=" / ".join(types))
            
            # Add height and weight
            height = pokemon_data['height'] / 10  # Convert to meters
            weight = pokemon_data['weight'] / 10  # Convert to kg
            pokemon_embed.add_field(name="Height", value=f"{height} m")
            pokemon_embed.add_field(name="Weight", value=f"{weight} kg")
            
            # Display base stats
            stats_text = ""
            for stat in pokemon_data['stats']:
                stat_name = stat['stat']['name'].replace('-', ' ').title()
                stats_text += f"{stat_name}: {stat['base_stat']}\n"
            
            pokemon_embed.add_field(name="Base Stats", value=stats_text, inline=False)
            
            # Display abilities
            abilities_text = ""
            for ability in pokemon_data['abilities']:
                ability_name = ability['ability']['name'].replace('-', ' ').title()
                if ability['is_hidden']:
                    abilities_text += f"• {ability_name} (Hidden)\n"
                else:
                    abilities_text += f"• {ability_name}\n"
                    
            pokemon_embed.add_field(name="Abilities", value=abilities_text, inline=False)
            
            await ctx.send(embed=pokemon_embed)
            
    @commands.command(name="battle")
    async def battle(self, ctx):
        """Battle with your primary Pokemon to gain XP"""
        if not self.db.trainer_exists(ctx.author.id):
            embed = discord.Embed(
                title="No Trainer Profile",
                description="You haven't started your Pokemon journey yet! Use `!journey` to begin.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        primary_pokemon = self.db.get_primary_pokemon(ctx.author.id)
        if not primary_pokemon:
            embed = discord.Embed(
                title="No Primary Pokemon",
                description="You don't have a primary Pokemon yet! Use `!catch` to find one.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        # Start battle sequence
        loading_embed = discord.Embed(
            title="Looking for a battle...",
            description="Searching for a worthy opponent...",
            color=discord.Color.blue()
        )
        message = await ctx.send(embed=loading_embed)
        
        # Simulate searching
        await asyncio.sleep(2)
        
        # Get a random Pokemon as opponent
        opponent_id = self.db.get_random_wild_pokemon()
        
        # Fetch Pokemon data from API
        opponent_data = await self.db.fetch_pokemon_data(opponent_id)
        if not opponent_data:
            await message.edit(embed=discord.Embed(
                title="No Opponent Found",
                description="Couldn't find an opponent. Try again later.",
                color=discord.Color.red()
            ))
            return
            
        # Create opponent
        opponent_name = opponent_data['name'].capitalize()
        opponent_sprite = opponent_data['sprites']['front_default']
        opponent_level = random.randint(max(1, primary_pokemon['level'] - 5), primary_pokemon['level'] + 5)
        
        # Battle starts
        battle_embed = discord.Embed(
            title=f"Battle Start! {primary_pokemon['display_name']} vs {opponent_name}",
            description=f"Your Lvl {primary_pokemon['level']} {primary_pokemon['display_name']} is battling a wild Lvl {opponent_level} {opponent_name}!",
            color=discord.Color.gold()
        )
        battle_embed.set_thumbnail(url=primary_pokemon['sprite_url'])
        battle_embed.set_image(url=opponent_sprite)
        await message.edit(embed=battle_embed)
        
        # Simulate battle
        await asyncio.sleep(2)
        
        # Handle battle result
        battle_result = await self.db.handle_battle(ctx.author.id)
        
        if battle_result['winner']:
            result_embed = discord.Embed(
                title="Battle Victory!",
                description=f"Your {primary_pokemon['display_name']} defeated the wild {opponent_name}!",
                color=discord.Color.green()
            )
            
            # XP and level info
            result_embed.add_field(name="XP Gained", value=f"{battle_result['pokemon_xp']} XP")
            result_embed.add_field(name="Trainer XP", value=f"+{battle_result['trainer_xp']} XP")
            
            # Check if Pokemon leveled up
            if battle_result['pokemon_leveled']:
                result_embed.add_field(
                    name="Level Up!", 
                    value=f"Your {primary_pokemon['display_name']} is now level {battle_result['pokemon_leveled']}!",
                    inline=False
                )
            
            # Check if trainer leveled up
            if battle_result['trainer_leveled']:
                trainer_data = self.db._get_trainer_data(ctx.author.id)
                result_embed.add_field(
                    name="Trainer Level Up!", 
                    value=f"You are now level {trainer_data['level']}!",
                    inline=False
                )
            
            # Check if evolution occurred
            if battle_result.get('evolution'):
                evolved_pokemon = battle_result['evolution']
                result_embed.add_field(
                    name="Evolution!", 
                    value=f"Your {primary_pokemon['display_name']} evolved into {evolved_pokemon['display_name']}!",
                    inline=False
                )
                result_embed.set_thumbnail(url=evolved_pokemon['sprite_url'])
            else:
                result_embed.set_thumbnail(url=primary_pokemon['sprite_url'])
        else:
            result_embed = discord.Embed(
                title="Battle Defeat",
                description=f"Your {primary_pokemon['display_name']} was defeated by the wild {opponent_name}!",
                color=discord.Color.red()
            )
            result_embed.add_field(name="XP Gained", value=f"{battle_result['pokemon_xp']} XP (consolation)")
            result_embed.add_field(name="Trainer XP", value=f"+{battle_result['trainer_xp']} XP")
            result_embed.set_thumbnail(url=primary_pokemon['sprite_url'])
        
        await message.edit(embed=result_embed)
        
    @commands.command(name="evolve")
    async def evolve(self, ctx):
        """Evolve your primary Pokemon if eligible"""
        if not self.db.trainer_exists(ctx.author.id):
            embed = discord.Embed(
                title="No Trainer Profile",
                description="You haven't started your Pokemon journey yet! Use `!journey` to begin.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        primary_pokemon = self.db.get_primary_pokemon(ctx.author.id)
        if not primary_pokemon:
            embed = discord.Embed(
                title="No Primary Pokemon",
                description="You don't have a primary Pokemon yet! Use `!catch` to find one.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        # Start evolution process
        loading_embed = discord.Embed(
            title="Checking for evolution...",
            description=f"Checking if {primary_pokemon['display_name']} can evolve...",
            color=discord.Color.blue()
        )
        message = await ctx.send(embed=loading_embed)
        
        # Attempt to evolve
        evolved_pokemon = await self.db.evolve_pokemon(ctx.author.id)
        
        if evolved_pokemon:
            # Success
            evolution_embed = discord.Embed(
                title="Congratulations!",
                description=f"Your {primary_pokemon['display_name']} evolved into {evolved_pokemon['display_name']}!",
                color=discord.Color.green()
            )
            evolution_embed.set_thumbnail(url=primary_pokemon['sprite_url'])
            evolution_embed.set_image(url=evolved_pokemon['sprite_url'])
            
            # Compare stats before and after
            old_stats = primary_pokemon['stats']
            new_stats = evolved_pokemon['stats']
            
            stats_text = ""
            for stat_name in old_stats:
                old_val = old_stats[stat_name]
                new_val = new_stats[stat_name]
                change = new_val - old_val
                stats_text += f"{stat_name.upper()}: {old_val} → {new_val} ({'+' if change > 0 else ''}{change})\n"
                
            evolution_embed.add_field(name="Stats Changes", value=stats_text, inline=False)
            
            await message.edit(embed=evolution_embed)
        else:
            # Failed
            fail_embed = discord.Embed(
                title="Cannot Evolve",
                description=f"Your {primary_pokemon['display_name']} cannot evolve right now.",
                color=discord.Color.red()
            )
            fail_embed.set_thumbnail(url=primary_pokemon['sprite_url'])
            
            # Add possible reasons
            reasons = [
                "It may not have an evolution",
                "It may not be at a high enough level",
                "It may require a special item or condition"
            ]
            fail_embed.add_field(name="Possible Reasons", value="\n".join(f"• {reason}" for reason in reasons))
            
            await message.edit(embed=fail_embed)
    
    @commands.command(name="pokedex")
    async def pokedex(self, ctx, member: discord.Member = None):
        """See a member's Pokedex"""
        target = member or ctx.author
        
        if not self.db.trainer_exists(target.id):
            if target.id == ctx.author.id:
                embed = discord.Embed(
                    title="No Trainer Profile",
                    description="You haven't started your Pokemon journey yet! Use `!journey` to begin.",
                    color=discord.Color.red()
                )
            else:
                embed = discord.Embed(
                    title="No Trainer Profile",
                    description=f"{target.name} hasn't started their Pokemon journey yet!",
                    color=discord.Color.red()
                )
            await ctx.send(embed=embed)
            return
            
        pokedex = self.db.get_pokedex(target.id)
        
        if not pokedex:
            embed = discord.Embed(
                title=f"{target.name}'s Pokedex",
                description="No Pokemon caught yet!",
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)
            return
            
        # Get basic stats
        pokemon_count = len(pokedex)
        
        embed = discord.Embed(
            title=f"{target.name}'s Pokedex",
            description=f"Total Pokemon species caught: {pokemon_count}",
            color=discord.Color.blue()
        )
        
        embed.set_thumbnail(url="https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/items/pokedex.png")
        
        # Show most recent additions
        recent_pokemon = []
        for pokemon_id in pokedex[-5:]:  # Last 5 entries
            pokemon_data = await self.db.fetch_pokemon_data(pokemon_id)
            if pokemon_data:
                recent_pokemon.append(f"#{pokemon_id}: {pokemon_data['name'].capitalize()}")
        
        if recent_pokemon:
            embed.add_field(
                name="Recent Additions", 
                value="\n".join(recent_pokemon[::-1]),  # Reverse to show newest first
                inline=False
            )
        
        # Add progress info
        if pokemon_count >= 151:
            kanto_percent = 100
        else:
            kanto_percent = (len([p for p in pokedex if p <= 151]) / 151) * 100
            
        if pokemon_count >= 251:
            johto_percent = 100
        else:
            johto_pokemon = len([p for p in pokedex if 152 <= p <= 251])
            johto_percent = (johto_pokemon / 100) * 100
            
        # Add region progress
        embed.add_field(name="Kanto", value=f"{kanto_percent:.1f}% complete")
        embed.add_field(name="Johto", value=f"{johto_percent:.1f}% complete")
        
        # Add percentage of total
        total_percent = (pokemon_count / 386) * 100  # Gen 1-3
        embed.add_field(name="Total Progress", value=f"{total_percent:.1f}% complete")
        
        await ctx.send(embed=embed)

    @commands.command(name="pokeshop", aliases=["pshop"])
    async def shop(self, ctx):
        """Buy pokemon balls to higher your chances of catching a pokemon"""
        if not self.db.trainer_exists(ctx.author.id):
            embed = discord.Embed(
                title="No Trainer Profile",
                description="You haven't started your Pokemon journey yet! Use `!journey` to begin.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        # Get economy cog to check balance
        economy_cog = self.bot.get_cog('Economy')
        
        if not economy_cog:
            embed = discord.Embed(
                title="Economy Not Available",
                description="The economy system is currently unavailable. Please try again later.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        # Check if user has an economy account
        if not economy_cog.db.account_exists(ctx.author.id):
            embed = discord.Embed(
                title="No Economy Account",
                description="You don't have an economy account! Use `!open` to create one.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        balance = economy_cog.db.get_balance(ctx.author.id)
        
        embed = discord.Embed(
            title="Pokemon Shop",
            description="Buy items to help you on your Pokemon journey!",
            color=discord.Color.gold()
        )
        
        embed.set_thumbnail(url="https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/items/poke-ball.png")
        embed.add_field(name="Your Balance", value=f"{balance['wallet']} bucks in wallet", inline=False)
        
        # Add shop items
        shop_text = ""
        for item_id, item in self.shop_items.items():
            shop_text += f"{item['emoji']} **{item['name']}** - {item['price']} bucks\n"
            shop_text += f"   ↳ {item['description']}\n\n"
            
        embed.add_field(name="Available Items", value=shop_text, inline=False)
        embed.add_field(name="How to Buy", value="Use `!buy <item> <quantity>` to purchase items\nExample: `!buy pokeballs 5`", inline=False)
        
        await ctx.send(embed=embed)
        
    @commands.command(name="pokebuy")
    async def buy(self, ctx, item: str, quantity: int = 1):
        """Buy items from the Pokeshop"""
        if not self.db.trainer_exists(ctx.author.id):
            embed = discord.Embed(
                title="No Trainer Profile",
                description="You haven't started your Pokemon journey yet! Use `!journey` to begin.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        # Check for valid item and quantity
        if item.lower() not in self.shop_items:
            embed = discord.Embed(
                title="Invalid Item",
                description=f"'{item}' is not a valid shop item. Use `!shop` to see available items.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        if quantity <= 0:
            embed = discord.Embed(
                title="Invalid Quantity",
                description="You must buy at least 1 of an item.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        # Get economy DB to check balance
        economy_cog = self.bot.get_cog('Economy')
        
        if not economy_cog:
            embed = discord.Embed(
                title="Economy Not Available",
                description="The economy system is currently unavailable. Please try again later.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        # Check if user has an economy account
        if not economy_cog.db.account_exists(ctx.author.id):
            embed = discord.Embed(
                title="No Economy Account",
                description="You don't have an economy account! Use `!open` to create one.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        # Calculate total cost
        item_data = self.shop_items[item.lower()]
        total_cost = item_data['price'] * quantity
        
        # Check if user has enough money
        balance = economy_cog.db.get_balance(ctx.author.id)
        
        if balance['wallet'] < total_cost:
            embed = discord.Embed(
                title="Insufficient Funds",
                description=f"You need {total_cost} bucks to buy {quantity}x {item_data['name']}.\nYou only have {balance['wallet']} bucks in your wallet.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        # Process the purchase
        # 1. Remove the money
        success = economy_cog.db.remove_from_wallet(ctx.author.id, total_cost)
        
        if not success:
            embed = discord.Embed(
                title="Transaction Failed",
                description="There was an error processing your purchase. Please try again later.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        # 2. Add the items to inventory
        self.db.add_to_inventory(ctx.author.id, item.lower(), quantity)
        
        # 3. Send confirmation
        embed = discord.Embed(
            title="Purchase Successful",
            description=f"You bought {quantity}x {item_data['emoji']} {item_data['name']} for {total_cost} bucks.",
            color=discord.Color.green()
        )
        
        new_balance = economy_cog.db.get_balance(ctx.author.id)
        embed.add_field(name="Remaining Balance", value=f"{new_balance['wallet']} bucks in wallet", inline=False)
        
        inventory = self.db.get_inventory(ctx.author.id)
        embed.add_field(name=f"You now have", value=f"{inventory[item.lower()]}x {item_data['emoji']} {item_data['name']}", inline=False)
        
        await ctx.send(embed=embed)
        
    @commands.command(name="poke_inventory", aliases=["pinv"])
    async def inventory(self, ctx, member: discord.Member = None):
        """View your pokemon inventory"""
        target = member or ctx.author
        
        if not self.db.trainer_exists(target.id):
            if target.id == ctx.author.id:
                embed = discord.Embed(
                    title="No Trainer Profile",
                    description="You haven't started your Pokemon journey yet! Use `!journey` to begin.",
                    color=discord.Color.red()
                )
            else:
                embed = discord.Embed(
                    title="No Trainer Profile",
                    description=f"{target.name} hasn't started their Pokemon journey yet!",
                    color=discord.Color.red()
                )
            await ctx.send(embed=embed)
            return
            
        inventory = self.db.get_inventory(target.id)
        
        embed = discord.Embed(
            title=f"{target.name}'s Inventory",
            description="Items available for use",
            color=discord.Color.blue()
        )
        
        embed.set_thumbnail(url=target.display_avatar.url)
        
        # Add inventory items, grouped by category
        pokeballs_text = ""
        
        # Standard Pokéballs
        if inventory.get('pokeballs', 0) > 0:
            pokeballs_text += f"🔴 Pokeball: {inventory['pokeballs']}\n"
        if inventory.get('greatballs', 0) > 0:
            pokeballs_text += f"🔵 Great Ball: {inventory['greatballs']}\n"
        if inventory.get('ultraballs', 0) > 0:
            pokeballs_text += f"⚫ Ultra Ball: {inventory['ultraballs']}\n"
        if inventory.get('masterballs', 0) > 0:
            pokeballs_text += f"🟣 Master Ball: {inventory['masterballs']}\n"
            
        # Special Pokéballs
        if inventory.get('luxuryballs', 0) > 0:
            pokeballs_text += f"🌑 Luxury Ball: {inventory['luxuryballs']}\n"
        if inventory.get('heavyballs', 0) > 0:
            pokeballs_text += f"⚙️ Heavy Ball: {inventory['heavyballs']}\n"
        if inventory.get('netballs', 0) > 0:
            pokeballs_text += f"🕸️ Net Ball: {inventory['netballs']}\n"
        if inventory.get('diveballs', 0) > 0:
            pokeballs_text += f"🌊 Dive Ball: {inventory['diveballs']}\n"
        if inventory.get('nestballs', 0) > 0:
            pokeballs_text += f"🌿 Nest Ball: {inventory['nestballs']}\n"
        if inventory.get('quickballs', 0) > 0:
            pokeballs_text += f"⚡ Quick Ball: {inventory['quickballs']}\n"
        if inventory.get('duskballs', 0) > 0:
            pokeballs_text += f"🌙 Dusk Ball: {inventory['duskballs']}\n"
        if inventory.get('timerballs', 0) > 0:
            pokeballs_text += f"⏱️ Timer Ball: {inventory['timerballs']}\n"
            
        if pokeballs_text:
            embed.add_field(name="Pokeballs", value=pokeballs_text, inline=False)
        else:
            embed.add_field(name="Pokeballs", value="No Pokeballs", inline=False)
            
        healing_text = ""
        if inventory.get('potions', 0) > 0:
            healing_text += f"🧪 Potion: {inventory['potions']}\n"
        if inventory.get('super_potions', 0) > 0:
            healing_text += f"💊 Super Potion: {inventory['super_potions']}\n"
        if inventory.get('hyper_potions', 0) > 0:
            healing_text += f"💉 Hyper Potion: {inventory['hyper_potions']}\n"
        if inventory.get('max_potions', 0) > 0:
            healing_text += f"🔋 Max Potion: {inventory['max_potions']}\n"
        if inventory.get('revives', 0) > 0:
            healing_text += f"💫 Revive: {inventory['revives']}\n"
            
        if healing_text:
            embed.add_field(name="Healing Items", value=healing_text, inline=False)
        else:
            embed.add_field(name="Healing Items", value="No healing items", inline=False)
            
        await ctx.send(embed=embed)

    @commands.command(name="party")
    async def party(self, ctx):
        """View your primary Pokemon for battles"""
        if not self.db.trainer_exists(ctx.author.id):
            embed = discord.Embed(
                title="No Trainer Profile",
                description="You haven't started your Pokemon journey yet! Use `!journey` to begin.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        party = self.db.get_party(ctx.author.id)
        
        if not party:
            embed = discord.Embed(
                title="Empty Party",
                description="You don't have any Pokemon in your party yet! Use `!catch` to find some Pokemon.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        embed = discord.Embed(
            title=f"{ctx.author.name}'s Pokemon Party",
            description=f"Your team of {len(party)} Pokemon",
            color=discord.Color.blue()
        )
        
        primary_pokemon = self.db.get_primary_pokemon(ctx.author.id)
        
        for i, pokemon in enumerate(party):
            is_primary = primary_pokemon and pokemon['id'] == primary_pokemon['id']
            prefix = "⭐ " if is_primary else ""
            
            # Format the Pokemon info
            pokemon_info = f"**Level {pokemon['level']} {pokemon['display_name']}**"
            pokemon_info += f"\nTypes: {' / '.join(pokemon['types']).capitalize()}"
            pokemon_info += f"\nHP: {pokemon['current_hp']}/{pokemon['stats']['hp']}"
            
            # Show XP progress
            xp_percent = (pokemon['xp'] / pokemon['xp_to_level']) * 100
            pokemon_info += f"\nXP: {pokemon['xp']}/{pokemon['xp_to_level']} ({xp_percent:.1f}%)"
            
            embed.add_field(
                name=f"{prefix}Pokemon #{i+1}",
                value=pokemon_info,
                inline=(i % 2 == 0)  # Alternate inline
            )
            
        # If we have an odd number of Pokemon, add an empty field for formatting
        if len(party) % 2 == 1:
            embed.add_field(name="\u200b", value="\u200b", inline=True)
            
        # Add party management tip
        embed.add_field(
            name="Party Management", 
            value="Use `!pokemon <pokemon_id>` to see detailed stats for a specific Pokemon.",
            inline=False
        )
        
        await ctx.send(embed=embed)
        
    @commands.command(name="pc")
    async def pc(self, ctx, page: int = 1):
        """View all Pokemon in your PC storage (collection)"""
        if not self.db.trainer_exists(ctx.author.id):
            embed = discord.Embed(
                title="No Trainer Profile",
                description="You haven't started your Pokemon journey yet! Use `!journey` to begin.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        trainer = self.db._get_trainer_data(ctx.author.id)
        
        if not trainer or not trainer['pokemon']:
            embed = discord.Embed(
                title="Empty PC Storage",
                description="You don't have any Pokemon in your collection yet! Use `!catch` to find some Pokemon.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        # Calculate pagination
        pokemon_per_page = 10
        total_pokemon = len(trainer['pokemon'])
        max_pages = (total_pokemon + pokemon_per_page - 1) // pokemon_per_page  # Ceiling division
        
        # Validate page number
        if page < 1:
            page = 1
        elif page > max_pages:
            page = max_pages
            
        # Get Pokemon for current page
        start_idx = (page - 1) * pokemon_per_page
        end_idx = min(start_idx + pokemon_per_page, total_pokemon)
        current_page_pokemon = trainer['pokemon'][start_idx:end_idx]
        
        # Get party and primary Pokemon for reference
        party_ids = trainer['party']
        primary_id = trainer['primary_pokemon']
        
        embed = discord.Embed(
            title=f"{ctx.author.name}'s Pokemon PC Storage",
            description=f"Viewing {total_pokemon} Pokemon (Page {page}/{max_pages})",
            color=discord.Color.blue()
        )
        
        embed.set_thumbnail(url="https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/items/poke-ball.png")
        
        # List Pokemon with basic info
        for i, pokemon in enumerate(current_page_pokemon):
            pokemon_id = pokemon['id']
            is_primary = pokemon_id == primary_id
            in_party = pokemon_id in party_ids
            
            # Create status indicators
            status = ""
            if is_primary:
                status += "⭐ "
            if in_party:
                status += "🎯 "
                
            # Format Pokemon entry
            pokemon_info = f"**Lv.{pokemon['level']} {pokemon['display_name']}** (ID: {pokemon_id})\n"
            pokemon_info += f"Type: {' / '.join(pokemon['types']).capitalize()}\n"
            pokemon_info += f"HP: {pokemon['current_hp']}/{pokemon['stats']['hp']}"
            
            # Calculate overall index number
            idx = start_idx + i + 1
            
            embed.add_field(
                name=f"{status}#{idx}: {pokemon['display_name']}",
                value=pokemon_info,
                inline=False
            )
            
        # Add navigation instructions
        embed.add_field(
            name="Navigation", 
            value=f"Use `!pc {page-1}` or `!pc {page+1}` to navigate pages",
            inline=False
        )
        
        # Add legend for symbols
        embed.add_field(
            name="Legend", 
            value="⭐ - Primary Pokemon\n🎯 - In Party",
            inline=False
        )
        
        await ctx.send(embed=embed)
        
    @commands.command(name="pokestats")
    async def pokestats(self, ctx, amount: int = 5):
        """View the stats of Pokemon across the server"""
        if amount < 1:
            amount = 5
        elif amount > 20:
            amount = 20
            
        embed = discord.Embed(
            title="Pokemon Trainer Leaderboard",
            description=f"Top {amount} Pokemon trainers in the server",
            color=discord.Color.gold()
        )
        
        # Fetch different leaderboards
        pokedex_leaderboard = self.db.get_leaderboard('pokedex', amount)
        level_leaderboard = self.db.get_leaderboard('level', amount)
        battles_leaderboard = self.db.get_leaderboard('battles', amount)
        
        # Format the pokedex leaderboard
        if pokedex_leaderboard:
            pokedex_text = ""
            for i, entry in enumerate(pokedex_leaderboard):
                user = self.bot.get_user(int(entry['user_id']))
                username = user.name if user else entry['username']
                pokedex_text += f"{i+1}. **{username}** - {entry['value']} Pokemon\n"
                
            embed.add_field(name="Pokedex Completion", value=pokedex_text, inline=False)
        
        # Format the trainer level leaderboard
        if level_leaderboard:
            level_text = ""
            for i, entry in enumerate(level_leaderboard):
                user = self.bot.get_user(int(entry['user_id']))
                username = user.name if user else entry['username']
                level_text += f"{i+1}. **{username}** - Level {entry['value']}\n"
                
            embed.add_field(name="Trainer Level", value=level_text, inline=False)
            
        # Format the battles leaderboard
        if battles_leaderboard:
            battles_text = ""
            for i, entry in enumerate(battles_leaderboard):
                user = self.bot.get_user(int(entry['user_id']))
                username = user.name if user else entry['username']
                battles_text += f"{i+1}. **{username}** - {entry['value']} battles\n"
                
            embed.add_field(name="Most Battles", value=battles_text, inline=False)
            
        if not pokedex_leaderboard and not level_leaderboard and not battles_leaderboard:
            embed.description = "No Pokemon trainers found in the server yet!"
        
        await ctx.send(embed=embed)
        
    @commands.command(name="moves")
    async def moves(self, ctx):
        """Check new moves and reassign moves"""
        if not self.db.trainer_exists(ctx.author.id):
            embed = discord.Embed(
                title="No Trainer Profile",
                description="You haven't started your Pokemon journey yet! Use `!journey` to begin.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        primary_pokemon = self.db.get_primary_pokemon(ctx.author.id)
        if not primary_pokemon:
            embed = discord.Embed(
                title="No Primary Pokemon",
                description="You don't have a primary Pokemon yet! Use `!catch` to find one.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        # This feature would normally allow users to manage their Pokemon's moves,
        # but for simplicity, we'll just display the available moves for now
        
        embed = discord.Embed(
            title=f"{primary_pokemon['display_name']}'s Moves",
            description=f"Level {primary_pokemon['level']} {primary_pokemon['display_name']}'s current moveset",
            color=discord.Color.blue()
        )
        
        embed.set_thumbnail(url=primary_pokemon['sprite_url'])
        
        # Show current moves
        current_moves = ""
        for i, move in enumerate(primary_pokemon['moves']):
            current_moves += f"{i+1}. **{move['name'].replace('-', ' ').title()}**\n"
            
        if current_moves:
            embed.add_field(name="Current Moves", value=current_moves, inline=False)
        else:
            embed.add_field(name="Current Moves", value="No moves learned yet", inline=False)
            
        # Add a note about the full moves management feature
        embed.add_field(
            name="Note", 
            value="Full move management feature coming soon! You'll be able to replace moves and learn new ones as your Pokemon levels up.",
            inline=False
        )
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(PokemonCog(bot)) 