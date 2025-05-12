import json
import os
import random
import logging
from datetime import datetime, timedelta
import asyncio
import aiohttp
import sqlite3

logger = logging.getLogger('bot')

class PokemonDB:
    """Handles database operations for the Pokemon system"""
    
    def __init__(self):
        self.data_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
        self.db_path = os.path.join(self.data_folder, 'pokemon.db')
        self._initialize_db()
        self.pokemon_api_url = "https://pokeapi.co/api/v2"
        self.pokemon_types = [
            "normal", "fire", "water", "electric", "grass", "ice", "fighting", 
            "poison", "ground", "flying", "psychic", "bug", "rock", "ghost", 
            "dragon", "dark", "steel", "fairy"
        ]
        
    def _initialize_db(self):
        """Initialize the Pokemon database"""
        if not os.path.exists(self.data_folder):
            os.makedirs(self.data_folder)
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create trainer table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trainers (
                user_id TEXT PRIMARY KEY,
                username TEXT,
                level INTEGER DEFAULT 1,
                xp INTEGER DEFAULT 0,
                xp_to_level INTEGER DEFAULT 100,
                primary_pokemon TEXT,
                party TEXT, -- JSON array of Pokemon IDs
                pokedex TEXT, -- JSON array of caught Pokemon IDs
                inventory TEXT, -- JSON object with inventory items
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create Pokemon table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pokemon (
                id TEXT PRIMARY KEY,
                trainer_id TEXT,
                pokemon_id INTEGER,
                level INTEGER DEFAULT 5,
                xp INTEGER DEFAULT 0,
                xp_to_level INTEGER DEFAULT 100,
                display_name TEXT,
                nickname TEXT,
                types TEXT, -- JSON array
                stats TEXT, -- JSON object
                moves TEXT, -- JSON array
                current_hp INTEGER,
                sprite_url TEXT,
                caught_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (trainer_id) REFERENCES trainers(user_id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def trainer_exists(self, user_id):
        """Check if a trainer exists"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT 1 FROM trainers WHERE user_id = ?", (str(user_id),))
        result = cursor.fetchone()
        
        conn.close()
        return result is not None
    
    def create_trainer(self, user_id, username):
        """Create a new trainer"""
        if self.trainer_exists(user_id):
            return False
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Default inventory
        inventory = {
            'pokeballs': 5,
            'greatballs': 0,
            'ultraballs': 0,
            'masterballs': 0,
            'potions': 3,
            'super_potions': 0,
            'revives': 1
        }
        
        cursor.execute(
            "INSERT INTO trainers (user_id, username, party, pokedex, inventory) VALUES (?, ?, ?, ?, ?)",
            (str(user_id), username, '[]', '[]', json.dumps(inventory))
        )
        
        conn.commit()
        conn.close()
        return True
    
    def _get_trainer_data(self, user_id):
        """Get a trainer's data"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM trainers WHERE user_id = ?", (str(user_id),))
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            return None
            
        trainer_data = dict(result)
        
        # Parse JSON fields
        trainer_data['party'] = json.loads(trainer_data['party'])
        trainer_data['pokedex'] = json.loads(trainer_data['pokedex'])
        trainer_data['inventory'] = json.loads(trainer_data['inventory'])
        
        # Get trainer's Pokemon
        cursor.execute("SELECT id FROM pokemon WHERE trainer_id = ?", (str(user_id),))
        pokemon_ids = [row[0] for row in cursor.fetchall()]
        trainer_data['pokemon'] = []
        
        for pokemon_id in pokemon_ids:
            cursor.execute("SELECT * FROM pokemon WHERE id = ?", (pokemon_id,))
            pokemon = dict(cursor.fetchone())
            
            # Parse JSON fields
            pokemon['types'] = json.loads(pokemon['types'])
            pokemon['stats'] = json.loads(pokemon['stats'])
            pokemon['moves'] = json.loads(pokemon['moves'])
            
            trainer_data['pokemon'].append(pokemon)
        
        conn.close()
        return trainer_data
    
    def get_inventory(self, user_id):
        """Get a trainer's inventory"""
        trainer_data = self._get_trainer_data(user_id)
        if not trainer_data:
            return None
        
        return trainer_data['inventory']
    
    def add_to_inventory(self, user_id, item, quantity):
        """Add items to a trainer's inventory"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT inventory FROM trainers WHERE user_id = ?", (str(user_id),))
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            return False
            
        inventory = json.loads(result[0])
        
        if item in inventory:
            inventory[item] += quantity
        else:
            inventory[item] = quantity
            
        cursor.execute(
            "UPDATE trainers SET inventory = ? WHERE user_id = ?",
            (json.dumps(inventory), str(user_id))
        )
        
        conn.commit()
        conn.close()
        return True
    
    def remove_from_inventory(self, user_id, item, quantity):
        """Remove items from a trainer's inventory"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT inventory FROM trainers WHERE user_id = ?", (str(user_id),))
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            return False
            
        inventory = json.loads(result[0])
        
        if item in inventory and inventory[item] >= quantity:
            inventory[item] -= quantity
            
            cursor.execute(
                "UPDATE trainers SET inventory = ? WHERE user_id = ?",
                (json.dumps(inventory), str(user_id))
            )
            
            conn.commit()
            conn.close()
            return True
        
        conn.close()
        return False
    
    def get_random_wild_pokemon(self):
        """Get a random Pokemon ID for encounters"""
        # Returns a random Pokemon ID from Gen 1-3
        return random.randint(1, 386)
    
    async def fetch_pokemon_data(self, pokemon_id):
        """Fetch Pokemon data from the PokeAPI"""
        if isinstance(pokemon_id, str):
            # If it's a name, convert to lowercase
            pokemon_id = pokemon_id.lower()
            
        url = f"https://pokeapi.co/api/v2/pokemon/{pokemon_id}"
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.error(f"Error fetching Pokemon data: {response.status}")
                        return None
            except Exception as e:
                logger.error(f"Error fetching Pokemon data: {e}")
                return None
    
    async def add_pokemon(self, user_id, pokemon_id):
        """Add a caught Pokemon to a trainer's collection"""
        if not self.trainer_exists(user_id):
            return None
            
        # Fetch Pokemon data
        pokemon_data = await self.fetch_pokemon_data(pokemon_id)
        if not pokemon_data:
            return None
            
        # Generate a unique ID for this Pokemon
        pokemon_instance_id = f"{user_id}_{pokemon_id}_{random.randint(10000, 99999)}"
        
        # Generate level (1-10 for wild Pokemon)
        level = random.randint(1, 10)
        
        # Extract types
        types = [t['type']['name'] for t in pokemon_data['types']]
        
        # Extract base stats and calculate this Pokemon's stats
        stats = {}
        for stat in pokemon_data['stats']:
            stat_name = stat['stat']['name']
            base_value = stat['base_stat']
            # Simple formula for stats based on level
            stat_value = int(base_value * (1 + (level * 0.05)))
            stats[stat_name] = stat_value
            
        # Get moves
        moves = []
        available_moves = [m['move'] for m in pokemon_data['moves']]
        # Choose up to 4 random moves
        num_moves = min(4, len(available_moves))
        if num_moves > 0:
            selected_moves = random.sample(available_moves, num_moves)
            moves = [{'name': move['name'], 'url': move['url']} for move in selected_moves]
        
        # Create Pokemon entry
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            """
            INSERT INTO pokemon 
            (id, trainer_id, pokemon_id, level, xp, xp_to_level, display_name, 
            types, stats, moves, current_hp, sprite_url) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                pokemon_instance_id,
                str(user_id),
                pokemon_data['id'],
                level,
                0,
                100,  # Simple XP to level formula
                pokemon_data['name'].capitalize(),
                json.dumps(types),
                json.dumps(stats),
                json.dumps(moves),
                stats['hp'],  # Full HP when caught
                pokemon_data['sprites']['front_default']
            )
        )
        
        # Add to trainer's party if there's room (max 6)
        cursor.execute("SELECT party, pokedex FROM trainers WHERE user_id = ?", (str(user_id),))
        result = cursor.fetchone()
        
        if result:
            party = json.loads(result[0])
            pokedex = json.loads(result[1])
            
            # Add to party if there's room
            if len(party) < 6:
                party.append(pokemon_instance_id)
                
            # Add to Pokedex if this species is new
            if pokemon_data['id'] not in pokedex:
                pokedex.append(pokemon_data['id'])
                
            # If this is the trainer's first Pokemon, make it primary
            cursor.execute("SELECT primary_pokemon FROM trainers WHERE user_id = ?", (str(user_id),))
            primary_result = cursor.fetchone()
            
            if primary_result and (primary_result[0] is None or primary_result[0] == ''):
                cursor.execute(
                    "UPDATE trainers SET primary_pokemon = ? WHERE user_id = ?",
                    (pokemon_instance_id, str(user_id))
                )
            
            # Update trainer
            cursor.execute(
                "UPDATE trainers SET party = ?, pokedex = ? WHERE user_id = ?",
                (json.dumps(party), json.dumps(pokedex), str(user_id))
            )
            
        conn.commit()
        
        # Get the full Pokemon data to return
        cursor.execute("SELECT * FROM pokemon WHERE id = ?", (pokemon_instance_id,))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM pokemon WHERE id = ?", (pokemon_instance_id,))
        pokemon = dict(cursor.fetchone())
        
        # Parse JSON fields
        pokemon['types'] = json.loads(pokemon['types'])
        pokemon['stats'] = json.loads(pokemon['stats'])
        pokemon['moves'] = json.loads(pokemon['moves'])
        
        conn.close()
        return pokemon
    
    def get_primary_pokemon(self, user_id):
        """Get a trainer's primary Pokemon"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT primary_pokemon FROM trainers WHERE user_id = ?", (str(user_id),))
        result = cursor.fetchone()
        
        if not result or not result['primary_pokemon']:
            conn.close()
            return None
            
        primary_id = result['primary_pokemon']
        
        cursor.execute("SELECT * FROM pokemon WHERE id = ?", (primary_id,))
        pokemon = cursor.fetchone()
        
        if not pokemon:
            conn.close()
            return None
            
        pokemon_data = dict(pokemon)
        
        # Parse JSON fields
        pokemon_data['types'] = json.loads(pokemon_data['types'])
        pokemon_data['stats'] = json.loads(pokemon_data['stats'])
        pokemon_data['moves'] = json.loads(pokemon_data['moves'])
        
        conn.close()
        return pokemon_data
    
    def get_party(self, user_id):
        """Get a trainer's party Pokemon"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT party FROM trainers WHERE user_id = ?", (str(user_id),))
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            return []
            
        party_ids = json.loads(result['party'])
        if not party_ids:
            conn.close()
            return []
            
        party = []
        for pokemon_id in party_ids:
            cursor.execute("SELECT * FROM pokemon WHERE id = ?", (pokemon_id,))
            pokemon = cursor.fetchone()
            
            if pokemon:
                pokemon_data = dict(pokemon)
                
                # Parse JSON fields
                pokemon_data['types'] = json.loads(pokemon_data['types'])
                pokemon_data['stats'] = json.loads(pokemon_data['stats'])
                pokemon_data['moves'] = json.loads(pokemon_data['moves'])
                
                party.append(pokemon_data)
        
        conn.close()
        return party
    
    def get_pokedex(self, user_id):
        """Get a trainer's Pokedex"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT pokedex FROM trainers WHERE user_id = ?", (str(user_id),))
        result = cursor.fetchone()
        
        conn.close()
        
        if not result:
            return []
            
        return json.loads(result[0])
    
    def calculate_catch_chance(self, user_id, ball_type):
        """Calculate the catch chance based on the ball type"""
        catch_rates = {
            'pokeballs': 0.4,
            'greatballs': 0.6,
            'ultraballs': 0.8,
            'masterballs': 1.0
        }
        
        return catch_rates.get(ball_type, 0.4)
    
    async def handle_battle(self, user_id):
        """Handle a Pokemon battle"""
        trainer_data = self._get_trainer_data(user_id)
        if not trainer_data or not trainer_data['primary_pokemon']:
            return {'winner': False}
            
        # Get primary Pokemon
        primary_pokemon = self.get_primary_pokemon(user_id)
        if not primary_pokemon:
            return {'winner': False}
            
        # Random chance to win based on Pokemon level
        win_chance = 0.5 + (primary_pokemon['level'] * 0.02)  # 50% base + 2% per level
        win_chance = min(0.9, win_chance)  # Cap at 90%
        
        # Determine battle result
        winner = random.random() < win_chance
        
        # Calculate XP gain
        pokemon_xp = random.randint(10, 20) * (2 if winner else 1)
        trainer_xp = random.randint(5, 10) * (2 if winner else 1)
        
        # Update Pokemon XP
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT xp, level, xp_to_level FROM pokemon WHERE id = ?", (primary_pokemon['id'],))
        result = cursor.fetchone()
        
        if result:
            current_xp, current_level, xp_to_level = result
            new_xp = current_xp + pokemon_xp
            
            # Check if Pokemon leveled up
            pokemon_leveled = None
            if new_xp >= xp_to_level:
                new_level = current_level + 1
                new_xp_to_level = int(xp_to_level * 1.5)  # Next level requires more XP
                
                cursor.execute(
                    "UPDATE pokemon SET xp = ?, level = ?, xp_to_level = ? WHERE id = ?",
                    (new_xp - xp_to_level, new_level, new_xp_to_level, primary_pokemon['id'])
                )
                
                pokemon_leveled = new_level
                
                # Update stats based on new level
                cursor.execute("SELECT stats FROM pokemon WHERE id = ?", (primary_pokemon['id'],))
                stats_result = cursor.fetchone()
                
                if stats_result:
                    stats = json.loads(stats_result[0])
                    
                    # Increase stats with level
                    for stat_name in stats:
                        # Increase by 5-10%
                        increase = random.uniform(0.05, 0.1)
                        stats[stat_name] = int(stats[stat_name] * (1 + increase))
                    
                    cursor.execute(
                        "UPDATE pokemon SET stats = ?, current_hp = ? WHERE id = ?",
                        (json.dumps(stats), stats['hp'], primary_pokemon['id'])
                    )
            else:
                cursor.execute(
                    "UPDATE pokemon SET xp = ? WHERE id = ?",
                    (new_xp, primary_pokemon['id'])
                )
        
        # Update trainer XP
        cursor.execute("SELECT xp, level, xp_to_level FROM trainers WHERE user_id = ?", (str(user_id),))
        result = cursor.fetchone()
        
        trainer_leveled = None
        if result:
            current_xp, current_level, xp_to_level = result
            new_xp = current_xp + trainer_xp
            
            # Check if trainer leveled up
            if new_xp >= xp_to_level:
                new_level = current_level + 1
                new_xp_to_level = int(xp_to_level * 1.2)  # Next level requires more XP
                
                cursor.execute(
                    "UPDATE trainers SET xp = ?, level = ?, xp_to_level = ? WHERE user_id = ?",
                    (new_xp - xp_to_level, new_level, new_xp_to_level, str(user_id))
                )
                
                trainer_leveled = new_level
            else:
                cursor.execute(
                    "UPDATE trainers SET xp = ? WHERE user_id = ?",
                    (new_xp, str(user_id))
                )
        
        conn.commit()
        conn.close()
        
        return {
            'winner': winner,
            'pokemon_xp': pokemon_xp,
            'trainer_xp': trainer_xp,
            'pokemon_leveled': pokemon_leveled,
            'trainer_leveled': trainer_leveled
        }
    
    async def evolve_pokemon(self, user_id):
        """Evolve a Pokemon if it meets the criteria"""
        # This is a simplified implementation
        primary_pokemon = self.get_primary_pokemon(user_id)
        if not primary_pokemon:
            return None
            
        # Fetch the Pokemon species data to check for evolutions
        pokemon_data = await self.fetch_pokemon_data(primary_pokemon['pokemon_id'])
        if not pokemon_data or 'species' not in pokemon_data:
            return None
            
        # Fetch the species data which has evolution chain URL
        species_url = pokemon_data['species']['url']
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(species_url) as response:
                    if response.status != 200:
                        return None
                        
                    species_data = await response.json()
                    
                    if 'evolution_chain' not in species_data:
                        return None
                        
                    # Fetch the evolution chain
                    evolution_url = species_data['evolution_chain']['url']
                    
                    async with session.get(evolution_url) as ev_response:
                        if ev_response.status != 200:
                            return None
                            
                        evolution_data = await ev_response.json()
                        
                        # Find current Pokemon in the chain
                        chain = evolution_data['chain']
                        current_species = pokemon_data['species']['name']
                        evolution_target = None
                        
                        # Check if it's the base form
                        if chain['species']['name'] == current_species:
                            if chain['evolves_to']:
                                evolution_target = chain['evolves_to'][0]['species']
                        else:
                            # Check first evolution
                            for evolution in chain['evolves_to']:
                                if evolution['species']['name'] == current_species:
                                    if evolution['evolves_to']:
                                        evolution_target = evolution['evolves_to'][0]['species']
                                    break
                                    
                                # Check second evolution
                                for second_evolution in evolution['evolves_to']:
                                    if second_evolution['species']['name'] == current_species:
                                        # Already at final evolution
                                        return None
                        
                        if not evolution_target:
                            return None
                            
                        # Check level requirement (simplified)
                        if primary_pokemon['level'] < 20:  # Arbitrary level requirement
                            return None
                            
                        # Fetch the evolution Pokemon data
                        evolve_to_data = await self.fetch_pokemon_data(evolution_target['name'])
                        if not evolve_to_data:
                            return None
                            
                        # Update the Pokemon
                        conn = sqlite3.connect(self.db_path)
                        conn.row_factory = sqlite3.Row
                        cursor = conn.cursor()
                        
                        # Extract types
                        types = [t['type']['name'] for t in evolve_to_data['types']]
                        
                        # Extract stats and increase them for evolution
                        new_stats = {}
                        for stat in evolve_to_data['stats']:
                            stat_name = stat['stat']['name']
                            base_value = stat['base_stat']
                            # Evolution bonus
                            stat_value = int(base_value * (1 + (primary_pokemon['level'] * 0.05)))
                            new_stats[stat_name] = stat_value
                        
                        # Update the Pokemon
                        cursor.execute(
                            """
                            UPDATE pokemon 
                            SET pokemon_id = ?, display_name = ?, types = ?, 
                                stats = ?, current_hp = ?, sprite_url = ? 
                            WHERE id = ?
                            """,
                            (
                                evolve_to_data['id'],
                                evolve_to_data['name'].capitalize(),
                                json.dumps(types),
                                json.dumps(new_stats),
                                new_stats['hp'],
                                evolve_to_data['sprites']['front_default'],
                                primary_pokemon['id']
                            )
                        )
                        
                        conn.commit()
                        
                        # Get the updated Pokemon data
                        cursor.execute("SELECT * FROM pokemon WHERE id = ?", (primary_pokemon['id'],))
                        evolved_pokemon = dict(cursor.fetchone())
                        
                        # Parse JSON fields
                        evolved_pokemon['types'] = json.loads(evolved_pokemon['types'])
                        evolved_pokemon['stats'] = json.loads(evolved_pokemon['stats'])
                        evolved_pokemon['moves'] = json.loads(evolved_pokemon['moves'])
                        
                        conn.close()
                        return evolved_pokemon
                        
            except Exception as e:
                logger.error(f"Error in evolve_pokemon: {e}")
                return None
    
    def get_leaderboard(self, board_type, limit=10):
        """Get leaderboard data"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if board_type == 'pokedex':
            # Most Pokemon species caught
            cursor.execute(
                """
                SELECT user_id, username, pokedex, LENGTH(pokedex) - LENGTH(REPLACE(pokedex, ',', '')) + 1 as value
                FROM trainers
                WHERE pokedex != '[]'
                ORDER BY value DESC
                LIMIT ?
                """,
                (limit,)
            )
        elif board_type == 'level':
            # Highest trainer level
            cursor.execute(
                """
                SELECT user_id, username, level as value
                FROM trainers
                ORDER BY value DESC
                LIMIT ?
                """,
                (limit,)
            )
        elif board_type == 'battles':
            # Most battles (not tracked in this simplified version)
            return []
        else:
            conn.close()
            return []
            
        results = cursor.fetchall()
        leaderboard = []
        
        for row in results:
            leaderboard.append({
                'user_id': row['user_id'],
                'username': row['username'],
                'value': row['value']
            })
            
        conn.close()
        return leaderboard

async def setup(bot):
    # This is a database module, no cog to add
    pass 