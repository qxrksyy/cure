import discord
from discord.ext import commands
import random
import asyncio
from datetime import datetime
import logging
from .economy_db import EconomyDB

logger = logging.getLogger('bot')

class Economy(commands.Cog):
    """Economy and gambling commands"""
    
    def __init__(self, bot):
        self.bot = bot
        self.db = EconomyDB()
        
    @commands.command(name="open")
    async def open(self, ctx):
        """Open an account to start gambling"""
        if self.db.account_exists(ctx.author.id):
            embed = discord.Embed(
                title="Account Exists",
                description="You already have an economy account!",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        success = self.db.create_account(ctx.author.id, ctx.author.name)
        
        if success:
            embed = discord.Embed(
                title="Account Created",
                description="Your economy account has been created! 💰",
                color=discord.Color.green()
            )
            embed.add_field(name="Starting Balance", value="100 bucks have been added to your wallet.")
            embed.add_field(name="Next Steps", value="Use `!daily` to claim your daily rewards and start gambling!")
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="Error",
                description="There was an error creating your account. Please try again later.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
    
    @commands.command(name="balance", aliases=["bal", "wallet"])
    async def balance(self, ctx, member: discord.Member = None):
        """Show your wallet, bank and graph of growth through gambling"""
        target = member or ctx.author
        
        if not self.db.account_exists(target.id):
            if target.id == ctx.author.id:
                embed = discord.Embed(
                    title="No Account",
                    description="You don't have an economy account! Use `!open` to create one.",
                    color=discord.Color.red()
                )
            else:
                embed = discord.Embed(
                    title="No Account",
                    description=f"{target.name} doesn't have an economy account!",
                    color=discord.Color.red()
                )
            await ctx.send(embed=embed)
            return
            
        balance = self.db.get_balance(target.id)
        
        embed = discord.Embed(
            title=f"{target.name}'s Balance",
            color=discord.Color.gold()
        )
        
        embed.add_field(name="💵 Wallet", value=f"{balance['wallet']} bucks", inline=True)
        embed.add_field(name="🏦 Bank", value=f"{balance['bank']}/{balance['bank_capacity']} bucks", inline=True)
        embed.add_field(name="💰 Total", value=f"{balance['total']} bucks", inline=True)
        
        user_data = self.db._get_user_data(target.id)
        if user_data:
            embed.add_field(name="📈 Total Earnings", value=f"{user_data['total_earnings']} bucks", inline=True)
            embed.add_field(name="📉 Total Losses", value=f"{user_data['total_losses']} bucks", inline=True)
            
            # Calculate net profit
            net_profit = user_data['total_earnings'] - user_data['total_losses']
            embed.add_field(name="📊 Net Profit", value=f"{net_profit} bucks", inline=True)
            
            # Add gambling stats
            if user_data['total_gambles'] > 0:
                win_rate = (user_data['wins'] / user_data['total_gambles']) * 100
                embed.add_field(name="🎲 Gambling Stats", 
                                value=f"Plays: {user_data['total_gambles']}\nWins: {user_data['wins']}\nLosses: {user_data['losses']}\nWin Rate: {win_rate:.1f}%", 
                                inline=False)
        
        embed.set_thumbnail(url=target.display_avatar.url)
        
        await ctx.send(embed=embed)
    
    @commands.command(name="daily")
    async def daily(self, ctx):
        """Collect your daily bucks"""
        if not self.db.account_exists(ctx.author.id):
            embed = discord.Embed(
                title="No Account",
                description="You don't have an economy account! Use `!open` to create one.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        result = self.db.claim_daily(ctx.author.id)
        
        if result['success']:
            embed = discord.Embed(
                title="Daily Reward",
                description=f"You've claimed {result['amount']} bucks! 💰",
                color=discord.Color.green()
            )
            
            balance = self.db.get_balance(ctx.author.id)
            embed.add_field(name="New Balance", value=f"{balance['wallet']} bucks in wallet", inline=False)
            
            await ctx.send(embed=embed)
        else:
            hours = result['time_remaining']['hours']
            minutes = result['time_remaining']['minutes']
            
            embed = discord.Embed(
                title="Daily Already Claimed",
                description=f"You've already claimed your daily reward! Try again in {hours}h {minutes}m.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
    
    @commands.command(name="deposit", aliases=["dep"])
    async def deposit(self, ctx, amount: str):
        """Deposit bucks from your wallet to your bank"""
        if not self.db.account_exists(ctx.author.id):
            embed = discord.Embed(
                title="No Account",
                description="You don't have an economy account! Use `!open` to create one.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        balance = self.db.get_balance(ctx.author.id)
        
        # Handle "all" as input
        if amount.lower() == "all":
            amount = balance['wallet']
        else:
            try:
                amount = int(amount)
                if amount <= 0:
                    raise ValueError("Amount must be positive")
            except ValueError:
                embed = discord.Embed(
                    title="Invalid Amount",
                    description="Please enter a positive number or 'all'.",
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed)
                return
        
        if amount > balance['wallet']:
            embed = discord.Embed(
                title="Insufficient Funds",
                description=f"You only have {balance['wallet']} bucks in your wallet!",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        deposited = self.db.deposit(ctx.author.id, amount)
        
        if deposited:
            new_balance = self.db.get_balance(ctx.author.id)
            
            embed = discord.Embed(
                title="Deposit Successful",
                description=f"You've deposited {deposited} bucks to your bank!",
                color=discord.Color.green()
            )
            
            embed.add_field(name="Wallet", value=f"{new_balance['wallet']} bucks", inline=True)
            embed.add_field(name="Bank", value=f"{new_balance['bank']}/{new_balance['bank_capacity']} bucks", inline=True)
            
            # Check if not all amount was deposited
            if deposited < amount:
                embed.add_field(
                    name="Note", 
                    value=f"Only {deposited} bucks were deposited because your bank reached its capacity.", 
                    inline=False
                )
                
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="Deposit Failed",
                description=f"Failed to deposit. Your bank might be at full capacity.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
    
    @commands.command(name="withdraw", aliases=["wd"])
    async def withdraw(self, ctx, amount: str):
        """Withdraw bucks from your bank to your wallet"""
        if not self.db.account_exists(ctx.author.id):
            embed = discord.Embed(
                title="No Account",
                description="You don't have an economy account! Use `!open` to create one.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        balance = self.db.get_balance(ctx.author.id)
        
        # Handle "all" as input
        if amount.lower() == "all":
            amount = balance['bank']
        else:
            try:
                amount = int(amount)
                if amount <= 0:
                    raise ValueError("Amount must be positive")
            except ValueError:
                embed = discord.Embed(
                    title="Invalid Amount",
                    description="Please enter a positive number or 'all'.",
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed)
                return
        
        if amount > balance['bank']:
            embed = discord.Embed(
                title="Insufficient Funds",
                description=f"You only have {balance['bank']} bucks in your bank!",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        success = self.db.withdraw(ctx.author.id, amount)
        
        if success:
            new_balance = self.db.get_balance(ctx.author.id)
            
            embed = discord.Embed(
                title="Withdrawal Successful",
                description=f"You've withdrawn {amount} bucks from your bank!",
                color=discord.Color.green()
            )
            
            embed.add_field(name="Wallet", value=f"{new_balance['wallet']} bucks", inline=True)
            embed.add_field(name="Bank", value=f"{new_balance['bank']}/{new_balance['bank_capacity']} bucks", inline=True)
                
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="Withdrawal Failed",
                description=f"Failed to withdraw. Please try again later.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
    
    @commands.command(name="transfer", aliases=["give", "pay"])
    async def transfer(self, ctx, member: discord.Member, amount: int):
        """Give another user some of your bucks"""
        if member.id == ctx.author.id:
            embed = discord.Embed(
                title="Invalid Transfer",
                description="You can't transfer money to yourself!",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        if member.bot:
            embed = discord.Embed(
                title="Invalid Transfer",
                description="You can't transfer money to a bot!",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        if not self.db.account_exists(ctx.author.id):
            embed = discord.Embed(
                title="No Account",
                description="You don't have an economy account! Use `!open` to create one.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        if not self.db.account_exists(member.id):
            embed = discord.Embed(
                title="No Account",
                description=f"{member.name} doesn't have an economy account!",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        if amount <= 0:
            embed = discord.Embed(
                title="Invalid Amount",
                description="Please enter a positive number.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        balance = self.db.get_balance(ctx.author.id)
        
        if amount > balance['wallet']:
            embed = discord.Embed(
                title="Insufficient Funds",
                description=f"You only have {balance['wallet']} bucks in your wallet!",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        success = self.db.transfer(ctx.author.id, member.id, amount)
        
        if success:
            embed = discord.Embed(
                title="Transfer Successful",
                description=f"You've transferred {amount} bucks to {member.name}!",
                color=discord.Color.green()
            )
            
            new_balance = self.db.get_balance(ctx.author.id)
            embed.add_field(name="Your New Balance", value=f"{new_balance['wallet']} bucks in wallet", inline=False)
                
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="Transfer Failed",
                description=f"Failed to transfer. Please try again later.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
    
    @commands.command(name="rob")
    async def rob(self, ctx, member: discord.Member):
        """Steal bucks from other users"""
        if member.id == ctx.author.id:
            embed = discord.Embed(
                title="Invalid Target",
                description="You can't rob yourself!",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        if member.bot:
            embed = discord.Embed(
                title="Invalid Target",
                description="You can't rob a bot!",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        if not self.db.account_exists(ctx.author.id):
            embed = discord.Embed(
                title="No Account",
                description="You don't have an economy account! Use `!open` to create one.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        if not self.db.account_exists(member.id):
            embed = discord.Embed(
                title="No Account",
                description=f"{member.name} doesn't have an economy account!",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        # Check if user has minimum amount in wallet
        robber_balance = self.db.get_balance(ctx.author.id)
        if robber_balance['wallet'] < 50:
            embed = discord.Embed(
                title="Insufficient Funds",
                description="You need at least 50 bucks in your wallet to attempt a robbery!",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        # Attempt the robbery
        result = self.db.rob_user(ctx.author.id, member.id)
        
        if result['success']:
            embed = discord.Embed(
                title="Robbery Successful!",
                description=f"You robbed {result['amount']} bucks from {member.name}!",
                color=discord.Color.green()
            )
            
            new_balance = self.db.get_balance(ctx.author.id)
            embed.add_field(name="Your New Balance", value=f"{new_balance['wallet']} bucks in wallet", inline=False)
                
            await ctx.send(embed=embed)
        else:
            if result['reason'] == 'protected':
                embed = discord.Embed(
                    title="Robbery Failed",
                    description=f"{member.name} is protected by a shield! You can't rob them right now.",
                    color=discord.Color.red()
                )
            elif result['reason'] == 'no_money':
                embed = discord.Embed(
                    title="Robbery Failed",
                    description=f"{member.name} has no money in their wallet!",
                    color=discord.Color.red()
                )
            elif result['reason'] == 'failed':
                embed = discord.Embed(
                    title="Robbery Failed",
                    description=f"You were caught trying to rob {member.name}!",
                    color=discord.Color.red()
                )
                
                if 'penalty' in result and result['penalty'] > 0:
                    embed.add_field(
                        name="Penalty", 
                        value=f"You were fined {result['penalty']} bucks.", 
                        inline=False
                    )
                    
                    new_balance = self.db.get_balance(ctx.author.id)
                    embed.add_field(
                        name="Your New Balance", 
                        value=f"{new_balance['wallet']} bucks in wallet", 
                        inline=False
                    )
            else:
                embed = discord.Embed(
                    title="Robbery Failed",
                    description=f"The robbery attempt failed.",
                    color=discord.Color.red()
                )
                
            await ctx.send(embed=embed)
            
    @commands.command(name="leaderboard", aliases=["lb"])
    async def leaderboard(self, ctx, board_type: str = "balance"):
        """Show top users for either earnings or balance"""
        if board_type.lower() not in ["balance", "earnings"]:
            embed = discord.Embed(
                title="Invalid Leaderboard Type",
                description="Please specify either 'balance' or 'earnings'.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        leaderboard = self.db.get_leaderboard(board_type.lower(), 10)
        
        if not leaderboard:
            embed = discord.Embed(
                title="Empty Leaderboard",
                description="There are no users on the leaderboard yet!",
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)
            return
            
        title = "Balance Leaderboard" if board_type.lower() == "balance" else "Earnings Leaderboard"
        embed = discord.Embed(
            title=title,
            color=discord.Color.gold()
        )
        
        description = ""
        for i, entry in enumerate(leaderboard):
            medal = ""
            if i == 0:
                medal = "🥇 "
            elif i == 1:
                medal = "🥈 "
            elif i == 2:
                medal = "🥉 "
            else:
                medal = f"{i+1}. "
                
            # Try to get member from ID
            member = ctx.guild.get_member(int(entry['user_id']))
            name = member.name if member else entry['username']
                
            description += f"{medal}**{name}**: {entry['amount']} bucks\n"
            
        embed.description = description
        
        await ctx.send(embed=embed)
        
    @commands.command(name="bag", aliases=["inventory", "inv"])
    async def bag(self, ctx, member: discord.Member = None):
        """Show items in your bag"""
        target = member or ctx.author
        
        if not self.db.account_exists(target.id):
            if target.id == ctx.author.id:
                embed = discord.Embed(
                    title="No Account",
                    description="You don't have an economy account! Use `!open` to create one.",
                    color=discord.Color.red()
                )
            else:
                embed = discord.Embed(
                    title="No Account",
                    description=f"{target.name} doesn't have an economy account!",
                    color=discord.Color.red()
                )
            await ctx.send(embed=embed)
            return
            
        inventory = self.db.get_inventory(target.id)
        
        if not inventory:
            if target.id == ctx.author.id:
                embed = discord.Embed(
                    title="Empty Inventory",
                    description="You don't have any items in your inventory! Use `!store` to see available items.",
                    color=discord.Color.blue()
                )
            else:
                embed = discord.Embed(
                    title="Empty Inventory",
                    description=f"{target.name} doesn't have any items in their inventory!",
                    color=discord.Color.blue()
                )
            await ctx.send(embed=embed)
            return
            
        if target.id == ctx.author.id:
            title = "Your Inventory"
        else:
            title = f"{target.name}'s Inventory"
            
        embed = discord.Embed(
            title=title,
            color=discord.Color.blue()
        )
        
        for item in inventory:
            embed.add_field(
                name=f"{item['name']} (x{item['count']})",
                value=item['description'],
                inline=False
            )
            
        embed.set_footer(text="Use !use <item_name> to use an item")
        
        await ctx.send(embed=embed)

    # Add gambling commands
    @commands.command(name="gamble", aliases=["bet"])
    async def gamble(self, ctx, amount: str):
        """Gamble your bucks with a 45% chance to win double"""
        if not self.db.account_exists(ctx.author.id):
            embed = discord.Embed(
                title="No Account",
                description="You don't have an economy account! Use `!open` to create one.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        balance = self.db.get_balance(ctx.author.id)
        
        # Handle "all" as input
        if amount.lower() == "all":
            amount = balance['wallet']
        elif amount.lower() == "half":
            amount = balance['wallet'] // 2
        else:
            try:
                amount = int(amount)
                if amount <= 0:
                    raise ValueError("Amount must be positive")
            except ValueError:
                embed = discord.Embed(
                    title="Invalid Amount",
                    description="Please enter a positive number, 'half', or 'all'.",
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed)
                return
        
        if amount > balance['wallet']:
            embed = discord.Embed(
                title="Insufficient Funds",
                description=f"You only have {balance['wallet']} bucks in your wallet!",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        # Gambling animation
        embed = discord.Embed(
            title="🎲 Gambling...",
            description=f"Betting {amount} bucks...",
            color=discord.Color.gold()
        )
        message = await ctx.send(embed=embed)
        
        await asyncio.sleep(2)
        
        # Process the gamble
        result = self.db.gamble(ctx.author.id, amount, game_type='gamble')
        
        if result['won']:
            embed = discord.Embed(
                title="🎉 You Won!",
                description=f"You bet {amount} bucks and won {result['total_winnings']} bucks!",
                color=discord.Color.green()
            )
            
            # Net winnings
            embed.add_field(name="Net Profit", value=f"+{result['net_winnings']} bucks", inline=True)
            
            # New balance
            new_balance = self.db.get_balance(ctx.author.id)
            embed.add_field(name="New Balance", value=f"{new_balance['wallet']} bucks in wallet", inline=True)
        else:
            embed = discord.Embed(
                title="💸 You Lost!",
                description=f"You bet {amount} bucks and lost everything!",
                color=discord.Color.red()
            )
            
            # New balance
            new_balance = self.db.get_balance(ctx.author.id)
            embed.add_field(name="New Balance", value=f"{new_balance['wallet']} bucks in wallet", inline=True)
        
        await message.edit(embed=embed)

    @commands.command(name="dice")
    async def dice(self, ctx, amount: str):
        """Roll dice with a 50% chance to win 1.8x your bet"""
        if not self.db.account_exists(ctx.author.id):
            embed = discord.Embed(
                title="No Account",
                description="You don't have an economy account! Use `!open` to create one.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        balance = self.db.get_balance(ctx.author.id)
        
        # Handle "all" as input
        if amount.lower() == "all":
            amount = balance['wallet']
        elif amount.lower() == "half":
            amount = balance['wallet'] // 2
        else:
            try:
                amount = int(amount)
                if amount <= 0:
                    raise ValueError("Amount must be positive")
            except ValueError:
                embed = discord.Embed(
                    title="Invalid Amount",
                    description="Please enter a positive number, 'half', or 'all'.",
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed)
                return
        
        if amount > balance['wallet']:
            embed = discord.Embed(
                title="Insufficient Funds",
                description=f"You only have {balance['wallet']} bucks in your wallet!",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        # Animation
        embed = discord.Embed(
            title="🎲 Rolling Dice...",
            description=f"Betting {amount} bucks...",
            color=discord.Color.gold()
        )
        message = await ctx.send(embed=embed)
        
        await asyncio.sleep(1)
        
        # Update animation with dice roll
        your_roll = random.randint(1, 6)
        house_roll = random.randint(1, 6)
        
        embed.add_field(name="Your Roll", value=f"🎲 {your_roll}", inline=True)
        await message.edit(embed=embed)
        
        await asyncio.sleep(1)
        
        embed.add_field(name="House Roll", value=f"🎲 {house_roll}", inline=True)
        await message.edit(embed=embed)
        
        await asyncio.sleep(1)
        
        # Process the gamble
        result = self.db.gamble(ctx.author.id, amount, game_type='dice')
        
        if result['won']:
            embed = discord.Embed(
                title="🎉 You Won!",
                description=f"You rolled a {your_roll} and the house rolled a {house_roll}.\nYou win {result['total_winnings']} bucks!",
                color=discord.Color.green()
            )
            
            # Net winnings
            embed.add_field(name="Net Profit", value=f"+{result['net_winnings']} bucks", inline=True)
            
            # New balance
            new_balance = self.db.get_balance(ctx.author.id)
            embed.add_field(name="New Balance", value=f"{new_balance['wallet']} bucks in wallet", inline=True)
        else:
            embed = discord.Embed(
                title="💸 You Lost!",
                description=f"You rolled a {your_roll} and the house rolled a {house_roll}.\nYou lost {amount} bucks!",
                color=discord.Color.red()
            )
            
            # New balance
            new_balance = self.db.get_balance(ctx.author.id)
            embed.add_field(name="New Balance", value=f"{new_balance['wallet']} bucks in wallet", inline=True)
        
        await message.edit(embed=embed)
        
    @commands.command(name="coinflip", aliases=["coin", "flip"])
    async def coinflip(self, ctx, choice: str, amount: str):
        """Flip a coin and bet on heads or tails"""
        if choice.lower() not in ["heads", "tails", "h", "t"]:
            embed = discord.Embed(
                title="Invalid Choice",
                description="Please choose either 'heads' or 'tails'.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        # Normalize choice
        choice = "heads" if choice.lower() in ["heads", "h"] else "tails"
        
        if not self.db.account_exists(ctx.author.id):
            embed = discord.Embed(
                title="No Account",
                description="You don't have an economy account! Use `!open` to create one.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        balance = self.db.get_balance(ctx.author.id)
        
        # Handle "all" as input
        if amount.lower() == "all":
            amount = balance['wallet']
        elif amount.lower() == "half":
            amount = balance['wallet'] // 2
        else:
            try:
                amount = int(amount)
                if amount <= 0:
                    raise ValueError("Amount must be positive")
            except ValueError:
                embed = discord.Embed(
                    title="Invalid Amount",
                    description="Please enter a positive number, 'half', or 'all'.",
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed)
                return
        
        if amount > balance['wallet']:
            embed = discord.Embed(
                title="Insufficient Funds",
                description=f"You only have {balance['wallet']} bucks in your wallet!",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        # Animation
        embed = discord.Embed(
            title="🪙 Flipping Coin...",
            description=f"You bet {amount} bucks on {choice}.",
            color=discord.Color.gold()
        )
        message = await ctx.send(embed=embed)
        
        await asyncio.sleep(2)
        
        # Process the gamble
        result = self.db.gamble(ctx.author.id, amount, game_type='coinflip')
        
        # Determine flip result (just for visual)
        flip_result = "heads" if random.random() < 0.5 else "tails"
        flip_emoji = "⭕" if flip_result == "heads" else "❌"
        
        if result['won']:
            embed = discord.Embed(
                title=f"🎉 {flip_emoji} It's {flip_result.upper()}!",
                description=f"You bet on {choice} and won {result['total_winnings']} bucks!",
                color=discord.Color.green()
            )
            
            # Net winnings
            embed.add_field(name="Net Profit", value=f"+{result['net_winnings']} bucks", inline=True)
            
            # New balance
            new_balance = self.db.get_balance(ctx.author.id)
            embed.add_field(name="New Balance", value=f"{new_balance['wallet']} bucks in wallet", inline=True)
        else:
            embed = discord.Embed(
                title=f"💸 {flip_emoji} It's {flip_result.upper()}!",
                description=f"You bet on {choice} and lost {amount} bucks!",
                color=discord.Color.red()
            )
            
            # New balance
            new_balance = self.db.get_balance(ctx.author.id)
            embed.add_field(name="New Balance", value=f"{new_balance['wallet']} bucks in wallet", inline=True)
        
        await message.edit(embed=embed)

    @commands.command(name="shop", aliases=["store"])
    async def shop(self, ctx):
        """View items available in the shop"""
        if not self.db.account_exists(ctx.author.id):
            embed = discord.Embed(
                title="No Account",
                description="You don't have an economy account! Use `!open` to create one.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        shop_items = self.db.get_shop_items()
        
        if not shop_items:
            embed = discord.Embed(
                title="Shop",
                description="The shop is currently empty. Check back later!",
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)
            return
            
        embed = discord.Embed(
            title="🛒 Item Shop",
            description="Use `!buy <item_id> [quantity]` to purchase an item.",
            color=discord.Color.blue()
        )
        
        for item_id, item in shop_items.items():
            embed.add_field(
                name=f"{item['name']} - {item['price']} bucks",
                value=f"ID: `{item_id}`\n{item['description']}",
                inline=False
            )
            
        balance = self.db.get_balance(ctx.author.id)
        embed.set_footer(text=f"Your wallet balance: {balance['wallet']} bucks")
        
        await ctx.send(embed=embed)
        
    @commands.command(name="buy")
    async def buy(self, ctx, item_id: str, quantity: int = 1):
        """Buy an item from the shop"""
        if not self.db.account_exists(ctx.author.id):
            embed = discord.Embed(
                title="No Account",
                description="You don't have an economy account! Use `!open` to create one.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        if quantity <= 0:
            embed = discord.Embed(
                title="Invalid Quantity",
                description="Please enter a positive number for quantity.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        result = self.db.buy_item(ctx.author.id, item_id, quantity)
        
        if result['success']:
            embed = discord.Embed(
                title="Purchase Successful",
                description=f"You bought {quantity}x {result['item']['name']} for {result['cost']} bucks!",
                color=discord.Color.green()
            )
            
            # New balance
            new_balance = self.db.get_balance(ctx.author.id)
            embed.add_field(name="Remaining Balance", value=f"{new_balance['wallet']} bucks in wallet", inline=True)
                
            await ctx.send(embed=embed)
        else:
            if result['reason'] == 'no_account':
                embed = discord.Embed(
                    title="No Account",
                    description="You don't have an economy account! Use `!open` to create one.",
                    color=discord.Color.red()
                )
            elif result['reason'] == 'invalid_item':
                embed = discord.Embed(
                    title="Invalid Item",
                    description=f"Item ID '{item_id}' doesn't exist in the shop. Use `!shop` to see available items.",
                    color=discord.Color.red()
                )
            elif result['reason'] == 'insufficient_funds':
                embed = discord.Embed(
                    title="Insufficient Funds",
                    description=f"You don't have enough bucks to buy this item.",
                    color=discord.Color.red()
                )
            else:
                embed = discord.Embed(
                    title="Purchase Failed",
                    description=f"Failed to purchase the item. Please try again later.",
                    color=discord.Color.red()
                )
                
            await ctx.send(embed=embed)
            
    @commands.command(name="use")
    async def use(self, ctx, *, item_name: str):
        """Use an item from your inventory"""
        if not self.db.account_exists(ctx.author.id):
            embed = discord.Embed(
                title="No Account",
                description="You don't have an economy account! Use `!open` to create one.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        # Find the item ID from the name provided
        shop_items = self.db.get_shop_items()
        item_id = None
        
        # Try to match by item name
        for id, item in shop_items.items():
            # Check if provided name is in the item name (case insensitive)
            if item_name.lower() in item['name'].lower():
                item_id = id
                break
                
        # If still not found, try matching directly by ID
        if item_id is None and item_name in shop_items:
            item_id = item_name
            
        if item_id is None:
            embed = discord.Embed(
                title="Item Not Found",
                description=f"Could not find an item matching '{item_name}' in your inventory.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        result = self.db.use_item(ctx.author.id, item_id)
        
        if result['success']:
            embed = discord.Embed(
                title="Item Used",
                description=f"You used {result['item']['name']}!",
                color=discord.Color.green()
            )
            
            # Add effect description
            effect = result['item']['effect']
            if effect['type'] == 'win_chance':
                embed.add_field(
                    name="Effect", 
                    value=f"Your gambling win chance is increased by {effect['value']}% for the next {effect['duration']} gambles.", 
                    inline=False
                )
            elif effect['type'] == 'rob_protection':
                embed.add_field(
                    name="Effect", 
                    value=f"You are protected from being robbed for the next 24 hours.", 
                    inline=False
                )
            elif effect['type'] == 'win_multiplier':
                embed.add_field(
                    name="Effect", 
                    value=f"Your gambling winnings are multiplied by {effect['value']}x for the next {effect['duration']} gambles.", 
                    inline=False
                )
            elif effect['type'] == 'dice_boost':
                embed.add_field(
                    name="Effect", 
                    value=f"Your dice win chance is increased by {effect['value']}% for the next {effect['duration']} dice rolls.", 
                    inline=False
                )
            elif effect['type'] == 'bank_capacity':
                embed.add_field(
                    name="Effect", 
                    value=f"Your bank capacity has been increased by {effect['value']} bucks.", 
                    inline=False
                )
                
            await ctx.send(embed=embed)
        else:
            if result['reason'] == 'no_account':
                embed = discord.Embed(
                    title="No Account",
                    description="You don't have an economy account! Use `!open` to create one.",
                    color=discord.Color.red()
                )
            elif result['reason'] == 'invalid_item':
                embed = discord.Embed(
                    title="Invalid Item",
                    description=f"Item '{item_name}' doesn't exist.",
                    color=discord.Color.red()
                )
            elif result['reason'] == 'no_item':
                embed = discord.Embed(
                    title="No Item",
                    description=f"You don't have any unused {shop_items[item_id]['name']} in your inventory.",
                    color=discord.Color.red()
                )
            else:
                embed = discord.Embed(
                    title="Use Failed",
                    description=f"Failed to use the item. Please try again later.",
                    color=discord.Color.red()
                )
                
            await ctx.send(embed=embed)
            
    @commands.command(name="effects")
    async def effects(self, ctx):
        """View all active effects on your account"""
        if not self.db.account_exists(ctx.author.id):
            embed = discord.Embed(
                title="No Account",
                description="You don't have an economy account! Use `!open` to create one.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        active_effects = self.db.get_active_effects(ctx.author.id)
        
        if not active_effects:
            embed = discord.Embed(
                title="Active Effects",
                description="You don't have any active effects.",
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)
            return
            
        embed = discord.Embed(
            title="🔮 Your Active Effects",
            color=discord.Color.purple()
        )
        
        for effect in active_effects:
            effect_type = effect['type']
            value = effect['value']
            duration = effect['duration']
            
            # Format effect description
            if effect_type == 'win_chance':
                name = "🍀 Increased Win Chance"
                value_str = f"+{value}% win chance"
            elif effect_type == 'rob_protection':
                name = "🛡️ Rob Protection"
                value_str = f"{value}% protection"
            elif effect_type == 'win_multiplier':
                name = "💰 Win Multiplier"
                value_str = f"{value}x winnings"
            elif effect_type == 'dice_boost':
                name = "🎲 Dice Boost"
                value_str = f"+{value}% win chance on dice"
            elif effect_type == 'bank_capacity':
                name = "🏦 Increased Bank Capacity"
                value_str = f"+{value} bank capacity"
            else:
                name = f"Unknown Effect ({effect_type})"
                value_str = f"Value: {value}"
                
            # Format duration
            if duration < 0:
                duration_str = "Permanent"
            elif duration == 1:
                duration_str = "1 use remaining"
            else:
                duration_str = f"{duration} uses remaining"
                
            embed.add_field(
                name=name,
                value=f"{value_str}\n{duration_str}",
                inline=False
            )
            
        await ctx.send(embed=embed)

    @commands.command(name="supergamble", aliases=["sg", "highroller"])
    async def supergamble(self, ctx, amount: str):
        """High risk gambling with 30% chance to win 3x your bet"""
        if not self.db.account_exists(ctx.author.id):
            embed = discord.Embed(
                title="No Account",
                description="You don't have an economy account! Use `!open` to create one.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        balance = self.db.get_balance(ctx.author.id)
        
        # Handle "all" as input
        if amount.lower() == "all":
            amount = balance['wallet']
        elif amount.lower() == "half":
            amount = balance['wallet'] // 2
        else:
            try:
                amount = int(amount)
                if amount <= 0:
                    raise ValueError("Amount must be positive")
            except ValueError:
                embed = discord.Embed(
                    title="Invalid Amount",
                    description="Please enter a positive number, 'half', or 'all'.",
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed)
                return
        
        # Minimum bet for supergamble
        if amount < 500:
            embed = discord.Embed(
                title="Bet Too Small",
                description="Super Gamble requires a minimum bet of 500 bucks.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        if amount > balance['wallet']:
            embed = discord.Embed(
                title="Insufficient Funds",
                description=f"You only have {balance['wallet']} bucks in your wallet!",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        # Animation
        embed = discord.Embed(
            title="💎 SUPER GAMBLE 💎",
            description=f"Betting {amount} bucks with a 30% chance to win 3x...",
            color=discord.Color.gold()
        )
        message = await ctx.send(embed=embed)
        
        # Suspense for super gamble
        for i in range(3):
            await asyncio.sleep(1)
            embed.description += "."
            await message.edit(embed=embed)
        
        # Process the gamble
        result = self.db.gamble(ctx.author.id, amount, game_type='supergamble')
        
        if result['won']:
            embed = discord.Embed(
                title="🎉 JACKPOT! 🎉",
                description=f"You bet {amount} bucks and won {result['total_winnings']} bucks!",
                color=discord.Color.green()
            )
            
            # Net winnings
            embed.add_field(name="Net Profit", value=f"+{result['net_winnings']} bucks", inline=True)
            
            # New balance
            new_balance = self.db.get_balance(ctx.author.id)
            embed.add_field(name="New Balance", value=f"{new_balance['wallet']} bucks in wallet", inline=True)
        else:
            embed = discord.Embed(
                title="💸 You Lost!",
                description=f"You bet {amount} bucks and lost everything!",
                color=discord.Color.red()
            )
            
            # New balance
            new_balance = self.db.get_balance(ctx.author.id)
            embed.add_field(name="New Balance", value=f"{new_balance['wallet']} bucks in wallet", inline=True)
        
        await message.edit(embed=embed)
        
    @commands.command(name="stats")
    async def stats(self, ctx, member: discord.Member = None):
        """View detailed gambling stats for a user"""
        target = member or ctx.author
        
        if not self.db.account_exists(target.id):
            if target.id == ctx.author.id:
                embed = discord.Embed(
                    title="No Account",
                    description="You don't have an economy account! Use `!open` to create one.",
                    color=discord.Color.red()
                )
            else:
                embed = discord.Embed(
                    title="No Account",
                    description=f"{target.name} doesn't have an economy account!",
                    color=discord.Color.red()
                )
            await ctx.send(embed=embed)
            return
            
        user_data = self.db._get_user_data(target.id)
        
        if user_data is None:
            embed = discord.Embed(
                title="Error",
                description="Could not retrieve user data.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
            
        embed = discord.Embed(
            title=f"{target.name}'s Gambling Stats",
            color=discord.Color.gold()
        )
        
        # General stats
        general_stats = (
            f"Total Gambles: {user_data['total_gambles']}\n"
            f"Wins: {user_data['wins']}\n"
            f"Losses: {user_data['losses']}\n"
        )
        
        if user_data['total_gambles'] > 0:
            win_rate = (user_data['wins'] / user_data['total_gambles']) * 100
            general_stats += f"Win Rate: {win_rate:.1f}%\n"
            
        # Money stats
        money_stats = (
            f"Total Earnings: {user_data['total_earnings']} bucks\n"
            f"Total Losses: {user_data['total_losses']} bucks\n"
            f"Net Profit: {user_data['total_earnings'] - user_data['total_losses']} bucks\n"
        )
        
        # Game-specific stats
        games_stats = ""
        
        # Dice stats
        if user_data['stats']['dice_plays'] > 0:
            dice_win_rate = (user_data['stats']['dice_wins'] / user_data['stats']['dice_plays']) * 100
            games_stats += f"🎲 Dice: {user_data['stats']['dice_wins']}/{user_data['stats']['dice_plays']} ({dice_win_rate:.1f}%)\n"
            
        # Coinflip stats
        if user_data['stats']['coinflip_plays'] > 0:
            cf_win_rate = (user_data['stats']['coinflip_wins'] / user_data['stats']['coinflip_plays']) * 100
            games_stats += f"🪙 Coinflip: {user_data['stats']['coinflip_wins']}/{user_data['stats']['coinflip_plays']} ({cf_win_rate:.1f}%)\n"
            
        # Regular gamble stats
        if user_data['stats']['gamble_plays'] > 0:
            gamble_win_rate = (user_data['stats']['gamble_wins'] / user_data['stats']['gamble_plays']) * 100
            games_stats += f"🎰 Gamble: {user_data['stats']['gamble_wins']}/{user_data['stats']['gamble_plays']} ({gamble_win_rate:.1f}%)\n"
            
        # Super gamble stats
        if user_data['stats']['supergamble_plays'] > 0:
            sg_win_rate = (user_data['stats']['supergamble_wins'] / user_data['stats']['supergamble_plays']) * 100
            games_stats += f"💎 Super Gamble: {user_data['stats']['supergamble_wins']}/{user_data['stats']['supergamble_plays']} ({sg_win_rate:.1f}%)\n"
            
        # Robbery stats
        robbery_stats = (
            f"Rob Attempts: {user_data['stats']['rob_attempts']}\n"
            f"Successful Robs: {user_data['stats']['successful_robs']}\n"
            f"Times Robbed: {user_data['stats']['times_robbed']}\n"
        )
        
        if user_data['stats']['rob_attempts'] > 0:
            rob_success_rate = (user_data['stats']['successful_robs'] / user_data['stats']['rob_attempts']) * 100
            robbery_stats += f"Rob Success Rate: {rob_success_rate:.1f}%\n"
            
        # Add fields to embed
        embed.add_field(name="📊 General Stats", value=general_stats, inline=False)
        embed.add_field(name="💰 Money Stats", value=money_stats, inline=False)
        
        if games_stats:
            embed.add_field(name="🎮 Games Stats", value=games_stats, inline=False)
            
        embed.add_field(name="🥷 Robbery Stats", value=robbery_stats, inline=False)
        
        # Account age
        created_at = datetime.fromisoformat(user_data['created_at'])
        now = datetime.utcnow()
        days_old = (now - created_at).days
        
        embed.set_footer(text=f"Account created {days_old} days ago")
        embed.set_thumbnail(url=target.display_avatar.url)
        
        await ctx.send(embed=embed)
        
    @commands.command(name="richest")
    async def richest(self, ctx):
        """Show the richest user in the server"""
        leaderboard = self.db.get_leaderboard('balance', 1)
        
        if not leaderboard:
            embed = discord.Embed(
                title="No Data",
                description="There are no economy accounts yet!",
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)
            return
            
        richest_user = leaderboard[0]
        
        # Try to get member from ID
        member = ctx.guild.get_member(int(richest_user['user_id']))
        name = member.mention if member else richest_user['username']
        
        embed = discord.Embed(
            title="💰 Richest User",
            description=f"The richest user is {name} with {richest_user['amount']} bucks!",
            color=discord.Color.gold()
        )
        
        if member:
            embed.set_thumbnail(url=member.display_avatar.url)
            
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Economy(bot)) 