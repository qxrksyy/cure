import json
import os
import random
import logging
from datetime import datetime, timedelta

logger = logging.getLogger('bot')

class EconomyDB:
    """Handles database operations for the economy system"""
    
    def __init__(self):
        self.data_folder = 'data'
        self.economy_file = os.path.join(self.data_folder, 'economy.json')
        self.economy_data = self._load_data()
        self.shop_items = {
            'lucky_charm': {
                'name': 'Lucky Charm 🍀',
                'price': 1000,
                'description': 'Increases your chance of winning gambles by 5% for the next 5 gambles.',
                'effect': {'type': 'win_chance', 'value': 5, 'duration': 5}
            },
            'shield': {
                'name': 'Shield 🛡️',
                'price': 2000,
                'description': 'Protects your wallet from being robbed for 24 hours.',
                'effect': {'type': 'rob_protection', 'value': 100, 'duration': 86400}
            },
            'multiplier': {
                'name': 'Multiplier 💰',
                'price': 5000,
                'description': 'Multiplies your winnings by 1.5x for the next 3 gambles.',
                'effect': {'type': 'win_multiplier', 'value': 1.5, 'duration': 3}
            },
            'golden_dice': {
                'name': 'Golden Dice 🎲',
                'price': 7500,
                'description': 'Increases your chance of winning dice games by 10% for the next 10 dice rolls.',
                'effect': {'type': 'dice_boost', 'value': 10, 'duration': 10}
            },
            'bank_upgrade': {
                'name': 'Bank Upgrade 🏦',
                'price': 10000,
                'description': 'Increases your bank capacity by 20000.',
                'effect': {'type': 'bank_capacity', 'value': 20000, 'duration': -1}
            }
        }
        
    def _load_data(self):
        """Load economy data from JSON file"""
        if not os.path.exists(self.data_folder):
            os.makedirs(self.data_folder)
            
        try:
            if os.path.exists(self.economy_file):
                with open(self.economy_file, 'r') as f:
                    return json.load(f)
            else:
                return {'users': {}, 'leaderboard': {'balance': [], 'earnings': []}}
        except json.JSONDecodeError:
            logger.error(f"Error decoding {self.economy_file}. Using empty data.")
            return {'users': {}, 'leaderboard': {'balance': [], 'earnings': []}}
    
    def _save_data(self):
        """Save economy data to JSON file"""
        with open(self.economy_file, 'w') as f:
            json.dump(self.economy_data, f, indent=4)
    
    def _get_user_data(self, user_id):
        """Get a user's economy data, creating it if it doesn't exist"""
        user_id = str(user_id)
        
        if user_id not in self.economy_data['users']:
            return None
        
        return self.economy_data['users'][user_id]
    
    def create_account(self, user_id, username):
        """Create a new economy account for a user"""
        user_id = str(user_id)
        
        if user_id in self.economy_data['users']:
            return False
        
        # Create new user data
        self.economy_data['users'][user_id] = {
            'username': username,
            'wallet': 100,
            'bank': 0,
            'bank_capacity': 10000,
            'items': [],
            'active_effects': [],
            'daily_last_claimed': None,
            'total_earnings': 100, # Starting amount counts as earnings
            'total_losses': 0,
            'total_gambles': 0,
            'wins': 0,
            'losses': 0,
            'stats': {
                'dice_plays': 0,
                'dice_wins': 0,
                'coinflip_plays': 0,
                'coinflip_wins': 0,
                'blackjack_plays': 0,
                'blackjack_wins': 0,
                'gamble_plays': 0,
                'gamble_wins': 0,
                'supergamble_plays': 0,
                'supergamble_wins': 0,
                'rob_attempts': 0,
                'successful_robs': 0,
                'times_robbed': 0
            },
            'created_at': datetime.utcnow().isoformat()
        }
        
        self._save_data()
        return True
    
    def account_exists(self, user_id):
        """Check if a user has an economy account"""
        return str(user_id) in self.economy_data['users']
    
    def get_balance(self, user_id):
        """Get a user's wallet and bank balance"""
        user_data = self._get_user_data(user_id)
        
        if user_data is None:
            return None
        
        return {
            'wallet': user_data['wallet'],
            'bank': user_data['bank'],
            'bank_capacity': user_data['bank_capacity'],
            'total': user_data['wallet'] + user_data['bank']
        }
    
    def add_to_wallet(self, user_id, amount):
        """Add funds to a user's wallet"""
        user_id = str(user_id)
        
        if user_id not in self.economy_data['users']:
            return False
        
        self.economy_data['users'][user_id]['wallet'] += amount
        self.economy_data['users'][user_id]['total_earnings'] += amount
        
        self._save_data()
        self._update_leaderboard()
        return True
    
    def remove_from_wallet(self, user_id, amount):
        """Remove funds from a user's wallet"""
        user_id = str(user_id)
        
        if user_id not in self.economy_data['users']:
            return False
        
        if self.economy_data['users'][user_id]['wallet'] < amount:
            return False
        
        self.economy_data['users'][user_id]['wallet'] -= amount
        self.economy_data['users'][user_id]['total_losses'] += amount
        
        self._save_data()
        self._update_leaderboard()
        return True
    
    def deposit(self, user_id, amount):
        """Deposit funds from wallet to bank"""
        user_id = str(user_id)
        
        if user_id not in self.economy_data['users']:
            return False
        
        user_data = self.economy_data['users'][user_id]
        
        if user_data['wallet'] < amount:
            return False
        
        # Check if this would exceed bank capacity
        available_space = user_data['bank_capacity'] - user_data['bank']
        if amount > available_space:
            depositable_amount = available_space
        else:
            depositable_amount = amount
            
        if depositable_amount <= 0:
            return False
        
        user_data['wallet'] -= depositable_amount
        user_data['bank'] += depositable_amount
        
        self._save_data()
        self._update_leaderboard()
        return depositable_amount
    
    def withdraw(self, user_id, amount):
        """Withdraw funds from bank to wallet"""
        user_id = str(user_id)
        
        if user_id not in self.economy_data['users']:
            return False
        
        if self.economy_data['users'][user_id]['bank'] < amount:
            return False
        
        self.economy_data['users'][user_id]['bank'] -= amount
        self.economy_data['users'][user_id]['wallet'] += amount
        
        self._save_data()
        return True
    
    def transfer(self, sender_id, receiver_id, amount):
        """Transfer funds from one user to another"""
        sender_id = str(sender_id)
        receiver_id = str(receiver_id)
        
        if sender_id not in self.economy_data['users'] or receiver_id not in self.economy_data['users']:
            return False
        
        if self.economy_data['users'][sender_id]['wallet'] < amount:
            return False
        
        self.economy_data['users'][sender_id]['wallet'] -= amount
        self.economy_data['users'][receiver_id]['wallet'] += amount
        
        self._save_data()
        self._update_leaderboard()
        return True
    
    def claim_daily(self, user_id):
        """Claim daily rewards"""
        user_id = str(user_id)
        
        if user_id not in self.economy_data['users']:
            return None
        
        user_data = self.economy_data['users'][user_id]
        
        # Check if daily was already claimed
        if user_data['daily_last_claimed'] is not None:
            last_claimed = datetime.fromisoformat(user_data['daily_last_claimed'])
            now = datetime.utcnow()
            
            # Check if 24 hours have passed
            if now - last_claimed < timedelta(days=1):
                time_remaining = timedelta(days=1) - (now - last_claimed)
                hours, remainder = divmod(time_remaining.seconds, 3600)
                minutes, _ = divmod(remainder, 60)
                
                return {
                    'success': False,
                    'time_remaining': {'hours': hours, 'minutes': minutes}
                }
        
        # Calculate daily amount (random between 200-500)
        amount = random.randint(200, 500)
        
        # Update user data
        user_data['wallet'] += amount
        user_data['total_earnings'] += amount
        user_data['daily_last_claimed'] = datetime.utcnow().isoformat()
        
        self._save_data()
        self._update_leaderboard()
        
        return {
            'success': True,
            'amount': amount
        }
    
    def rob_user(self, robber_id, victim_id):
        """Attempt to rob another user"""
        robber_id = str(robber_id)
        victim_id = str(victim_id)
        
        if robber_id not in self.economy_data['users'] or victim_id not in self.economy_data['users']:
            return {'success': False, 'reason': 'Invalid user IDs'}
        
        robber = self.economy_data['users'][robber_id]
        victim = self.economy_data['users'][victim_id]
        
        # Update statistics
        robber['stats']['rob_attempts'] += 1
        
        # Check if victim has protection
        if any(effect['type'] == 'rob_protection' for effect in victim.get('active_effects', [])):
            return {'success': False, 'reason': 'protected'}
        
        # Check if victim has money in wallet
        if victim['wallet'] <= 0:
            return {'success': False, 'reason': 'no_money'}
        
        # 40% chance of success
        if random.random() > 0.4:
            # Rob failed
            penalty = min(robber['wallet'], random.randint(50, 200))
            if penalty > 0:
                robber['wallet'] -= penalty
                robber['total_losses'] += penalty
                
            return {'success': False, 'reason': 'failed', 'penalty': penalty}
        
        # Rob successful
        # Can steal up to 30% of victim's wallet
        max_steal = int(victim['wallet'] * 0.3)
        amount = random.randint(1, max_steal) if max_steal > 0 else 1
        
        victim['wallet'] -= amount
        victim['stats']['times_robbed'] += 1
        robber['wallet'] += amount
        robber['total_earnings'] += amount
        robber['stats']['successful_robs'] += 1
        
        self._save_data()
        self._update_leaderboard()
        
        return {'success': True, 'amount': amount}
    
    def gamble(self, user_id, amount, game_type='gamble'):
        """Process a gambling attempt"""
        user_id = str(user_id)
        
        if user_id not in self.economy_data['users']:
            return {'success': False, 'reason': 'no_account'}
        
        user_data = self.economy_data['users'][user_id]
        
        if user_data['wallet'] < amount:
            return {'success': False, 'reason': 'insufficient_funds'}
        
        # Determine win chance based on game type and active effects
        base_win_chance = {
            'gamble': 0.45,
            'supergamble': 0.3,
            'dice': 0.5,
            'coinflip': 0.49,
            'blackjack': 0.47
        }.get(game_type, 0.45)
        
        # Apply effects
        win_chance = base_win_chance
        win_multiplier = 1.0
        
        # Process active effects
        new_active_effects = []
        for effect in user_data.get('active_effects', []):
            # Skip expired effects
            if effect.get('duration', 0) == 0:
                continue
                
            # Apply effect based on type
            if effect['type'] == 'win_chance' and game_type in ['gamble', 'supergamble', 'dice', 'coinflip', 'blackjack']:
                win_chance += effect['value'] / 100  # Convert percentage to decimal
                
            if effect['type'] == 'win_multiplier' and game_type in ['gamble', 'supergamble', 'dice', 'coinflip', 'blackjack']:
                win_multiplier *= effect['value']
                
            if effect['type'] == 'dice_boost' and game_type == 'dice':
                win_chance += effect['value'] / 100  # Convert percentage to decimal
            
            # Decrease duration for temporary effects
            if effect['duration'] > 0:
                effect['duration'] -= 1
                
            # Keep non-expired effects
            if effect['duration'] != 0:
                new_active_effects.append(effect)
                
        # Update active effects
        user_data['active_effects'] = new_active_effects
        
        # Update statistics
        user_data['total_gambles'] += 1
        
        if game_type == 'gamble':
            user_data['stats']['gamble_plays'] += 1
        elif game_type == 'supergamble':
            user_data['stats']['supergamble_plays'] += 1
        elif game_type == 'dice':
            user_data['stats']['dice_plays'] += 1
        elif game_type == 'coinflip':
            user_data['stats']['coinflip_plays'] += 1
        elif game_type == 'blackjack':
            user_data['stats']['blackjack_plays'] += 1
        
        # Determine result
        if random.random() < win_chance:
            # Won
            multiplier = {
                'gamble': 2.0,
                'supergamble': 3.0,
                'dice': 1.8,
                'coinflip': 1.95,
                'blackjack': 2.0
            }.get(game_type, 2.0)
            
            # Apply win multiplier from effects
            multiplier *= win_multiplier
            
            winnings = int(amount * multiplier)
            user_data['wallet'] += winnings - amount  # Add net winnings (already had amount in wallet)
            user_data['total_earnings'] += winnings - amount  # Add net winnings to total earnings
            user_data['wins'] += 1
            
            if game_type == 'gamble':
                user_data['stats']['gamble_wins'] += 1
            elif game_type == 'supergamble':
                user_data['stats']['supergamble_wins'] += 1
            elif game_type == 'dice':
                user_data['stats']['dice_wins'] += 1
            elif game_type == 'coinflip':
                user_data['stats']['coinflip_wins'] += 1
            elif game_type == 'blackjack':
                user_data['stats']['blackjack_wins'] += 1
            
            self._save_data()
            self._update_leaderboard()
            
            return {
                'success': True, 
                'won': True, 
                'net_winnings': winnings - amount,
                'total_winnings': winnings
            }
        else:
            # Lost
            user_data['wallet'] -= amount
            user_data['total_losses'] += amount
            user_data['losses'] += 1
            
            self._save_data()
            self._update_leaderboard()
            
            return {'success': True, 'won': False, 'amount_lost': amount}
    
    def buy_item(self, user_id, item_id, quantity=1):
        """Buy an item from the shop"""
        user_id = str(user_id)
        
        if user_id not in self.economy_data['users']:
            return {'success': False, 'reason': 'no_account'}
        
        if item_id not in self.shop_items:
            return {'success': False, 'reason': 'invalid_item'}
        
        user_data = self.economy_data['users'][user_id]
        item = self.shop_items[item_id]
        total_cost = item['price'] * quantity
        
        if user_data['wallet'] < total_cost:
            return {'success': False, 'reason': 'insufficient_funds'}
        
        # Process purchase
        user_data['wallet'] -= total_cost
        
        # Add item to inventory
        for _ in range(quantity):
            user_data['items'].append({
                'id': item_id,
                'name': item['name'],
                'purchased_at': datetime.utcnow().isoformat(),
                'used': False
            })
        
        self._save_data()
        
        return {'success': True, 'cost': total_cost, 'item': item, 'quantity': quantity}
    
    def use_item(self, user_id, item_id):
        """Use an item from inventory"""
        user_id = str(user_id)
        
        if user_id not in self.economy_data['users']:
            return {'success': False, 'reason': 'no_account'}
        
        if item_id not in self.shop_items:
            return {'success': False, 'reason': 'invalid_item'}
        
        user_data = self.economy_data['users'][user_id]
        
        # Find the first unused item of this type
        found_item_index = None
        for i, item in enumerate(user_data['items']):
            if item['id'] == item_id and not item['used']:
                found_item_index = i
                break
        
        if found_item_index is None:
            return {'success': False, 'reason': 'no_item'}
        
        # Mark item as used
        user_data['items'][found_item_index]['used'] = True
        user_data['items'][found_item_index]['used_at'] = datetime.utcnow().isoformat()
        
        # Apply item effect
        item_effect = self.shop_items[item_id]['effect'].copy()
        
        if item_effect['type'] == 'bank_capacity':
            # Permanent effect on bank capacity
            user_data['bank_capacity'] += item_effect['value']
        else:
            # Add to active effects
            if 'active_effects' not in user_data:
                user_data['active_effects'] = []
                
            user_data['active_effects'].append(item_effect)
        
        self._save_data()
        
        return {'success': True, 'item': self.shop_items[item_id]}
    
    def get_inventory(self, user_id):
        """Get a user's inventory"""
        user_id = str(user_id)
        
        if user_id not in self.economy_data['users']:
            return None
        
        user_data = self.economy_data['users'][user_id]
        
        # Group items by type and count unused ones
        inventory = {}
        for item in user_data['items']:
            if not item['used']:
                if item['id'] not in inventory:
                    inventory[item['id']] = {
                        'id': item['id'],
                        'name': item['name'],
                        'count': 1,
                        'description': self.shop_items[item['id']]['description']
                    }
                else:
                    inventory[item['id']]['count'] += 1
        
        return list(inventory.values())
    
    def get_active_effects(self, user_id):
        """Get a user's active effects"""
        user_id = str(user_id)
        
        if user_id not in self.economy_data['users']:
            return None
        
        return self.economy_data['users'][user_id].get('active_effects', [])
    
    def get_shop_items(self):
        """Get all available shop items"""
        return self.shop_items
    
    def get_leaderboard(self, board_type='balance', limit=10):
        """Get the leaderboard for either balance or earnings"""
        if board_type not in ['balance', 'earnings']:
            return []
        
        # Update leaderboard first
        self._update_leaderboard()
        
        # Return leaderboard
        return self.economy_data['leaderboard'][board_type][:limit]
    
    def _update_leaderboard(self):
        """Update the leaderboard"""
        # Balance leaderboard
        balance_leaderboard = []
        for user_id, user_data in self.economy_data['users'].items():
            total_balance = user_data['wallet'] + user_data['bank']
            balance_leaderboard.append({
                'user_id': user_id,
                'username': user_data['username'],
                'amount': total_balance
            })
        
        # Sort by balance
        balance_leaderboard.sort(key=lambda x: x['amount'], reverse=True)
        
        # Earnings leaderboard
        earnings_leaderboard = []
        for user_id, user_data in self.economy_data['users'].items():
            earnings_leaderboard.append({
                'user_id': user_id,
                'username': user_data['username'],
                'amount': user_data['total_earnings']
            })
        
        # Sort by earnings
        earnings_leaderboard.sort(key=lambda x: x['amount'], reverse=True)
        
        # Update leaderboard data
        self.economy_data['leaderboard'] = {
            'balance': balance_leaderboard,
            'earnings': earnings_leaderboard
        }
        
        # No need to save as this is called from methods that already save 

async def setup(bot):
    # This is a database module, no cog to add
    pass 