import discord
from discord.ext import commands, tasks
import aiohttp
import json
import logging
import datetime
from typing import Dict, List, Optional, Set

logger = logging.getLogger('bot')

# Constants
COINGECKO_API_URL = "https://api.coingecko.com/api/v3"
BLOCKCHAIR_API_URL = "https://api.blockchair.com"
BLOCKCHAIN_INFO_API_URL = "https://blockchain.info"

# Supported coin IDs and symbols for mapping
COIN_MAPPING = {
    "btc": "bitcoin",
    "eth": "ethereum",
    "ltc": "litecoin",
    "doge": "dogecoin",
    "ada": "cardano",
    "sol": "solana",
    "xrp": "ripple",
    "dot": "polkadot",
    "bnb": "binancecoin",
    "link": "chainlink",
    "matic": "matic-network",
    "avax": "avalanche-2",
    "shib": "shiba-inu",
    "atom": "cosmos",
    "uni": "uniswap",
    "algo": "algorand",
    "xlm": "stellar",
    "near": "near",
    "icp": "internet-computer",
    "fil": "filecoin",
}

class Crypto(commands.Cog):
    """Cryptocurrency price checks and transaction monitoring"""
    
    def __init__(self, bot):
        self.bot = bot
        self.session = None
        self.btc_subscriptions: Dict[str, List[discord.TextChannel]] = {}  # tx_hash -> list of channels
        self.completed_transactions: Set[str] = set()
        
        # Start the background tasks
        self.create_session.start()
        self.check_subscriptions.start()
    
    def cog_unload(self):
        # Clean up tasks and session when cog is unloaded
        self.check_subscriptions.cancel()
        self.create_session.cancel()
        if self.session and not self.session.closed:
            self.bot.loop.create_task(self.session.close())
            
    @tasks.loop(seconds=1, count=1)
    async def create_session(self):
        """Create an aiohttp session when the cog starts"""
        self.session = aiohttp.ClientSession()
        logger.info("Created aiohttp session for crypto cog")
            
    @tasks.loop(minutes=1)
    async def check_subscriptions(self):
        """Check Bitcoin transaction confirmations periodically"""
        if not self.btc_subscriptions:
            return  # Skip if no active subscriptions
        
        for tx_hash, channels in list(self.btc_subscriptions.items()):
            if not channels or tx_hash in self.completed_transactions:
                if tx_hash in self.btc_subscriptions:
                    del self.btc_subscriptions[tx_hash]
                continue
                
            # Get transaction info
            try:
                transaction_data = await self.get_btc_transaction(tx_hash)
                if transaction_data and transaction_data.get('confirmations', 0) >= 1:
                    # Transaction confirmed at least once
                    for channel in channels:
                        if channel:
                            embed = self.create_btc_confirmation_embed(tx_hash, transaction_data)
                            try:
                                await channel.send(embed=embed)
                            except discord.HTTPException as e:
                                logger.error(f"Failed to send confirmation message: {e}")
                                
                    # Mark as completed
                    self.completed_transactions.add(tx_hash)
                    del self.btc_subscriptions[tx_hash]
            except Exception as e:
                logger.error(f"Error checking BTC transaction {tx_hash}: {e}")
    
    @check_subscriptions.before_loop
    async def before_check_subscriptions(self):
        """Wait for the bot to be ready before starting the task"""
        await self.bot.wait_until_ready()
        
    async def get_btc_transaction(self, tx_hash: str) -> Optional[Dict]:
        """Get information about a Bitcoin transaction"""
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        url = f"{BLOCKCHAIN_INFO_API_URL}/rawtx/{tx_hash}"
        
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    logger.warning(f"BTC transaction API returned status {response.status}")
                    return None
        except aiohttp.ClientError as e:
            logger.error(f"Error fetching BTC transaction {tx_hash}: {e}")
            return None
            
    async def get_eth_transaction(self, tx_hash: str) -> Optional[Dict]:
        """Get information about an Ethereum transaction"""
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        url = f"{BLOCKCHAIR_API_URL}/ethereum/dashboards/transaction/{tx_hash}"
        
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    logger.warning(f"ETH transaction API returned status {response.status}")
                    return None
        except aiohttp.ClientError as e:
            logger.error(f"Error fetching ETH transaction {tx_hash}: {e}")
            return None
            
    async def get_crypto_price(self, coin_id: str) -> Optional[Dict]:
        """Get price information for a cryptocurrency"""
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        url = f"{COINGECKO_API_URL}/coins/{coin_id}"
        params = {
            "localization": "false",
            "tickers": "false",
            "market_data": "true",
            "community_data": "false",
            "developer_data": "false"
        }
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    logger.warning(f"Crypto price API returned status {response.status}")
                    return None
        except aiohttp.ClientError as e:
            logger.error(f"Error fetching price for {coin_id}: {e}")
            return None
            
    def create_btc_transaction_embed(self, tx_hash: str, tx_data: Dict) -> discord.Embed:
        """Create an embed for BTC transaction information"""
        embed = discord.Embed(
            title="Bitcoin Transaction Information",
            description=f"Details for transaction `{tx_hash}`",
            color=discord.Color.gold(),
            timestamp=datetime.datetime.utcnow()
        )
        
        # Transaction details
        timestamp = datetime.datetime.fromtimestamp(tx_data.get('time', 0))
        embed.add_field(name="Timestamp", value=timestamp.strftime("%Y-%m-%d %H:%M:%S UTC"), inline=True)
        
        confirmations = tx_data.get('confirmations', 0)
        conf_status = "✅ Confirmed" if confirmations > 0 else "⏳ Pending"
        embed.add_field(name="Status", value=f"{conf_status} ({confirmations} confirmations)", inline=True)
        
        # Format value in BTC
        value_btc = sum(out.get('value', 0) for out in tx_data.get('out', [])) / 100000000  # Convert satoshis to BTC
        embed.add_field(name="Value", value=f"₿ {value_btc:.8f} BTC", inline=True)
        
        # Add fee if available
        if 'fee' in tx_data:
            fee_btc = tx_data['fee'] / 100000000  # Convert satoshis to BTC
            embed.add_field(name="Fee", value=f"₿ {fee_btc:.8f} BTC", inline=True)
            
        # Block info if confirmed
        if 'block_height' in tx_data:
            embed.add_field(name="Block", value=tx_data['block_height'], inline=True)
            
        # Add transaction link
        embed.add_field(
            name="View Transaction",
            value=f"[Blockchain.com](https://www.blockchain.com/btc/tx/{tx_hash})",
            inline=False
        )
        
        return embed
    
    def create_eth_transaction_embed(self, tx_hash: str, tx_data: Dict) -> discord.Embed:
        """Create an embed for ETH transaction information"""
        data = tx_data.get('data', {}).get('transaction', {}).get(tx_hash, {})
        if not data:
            return discord.Embed(
                title="Ethereum Transaction Not Found",
                description=f"No data found for transaction `{tx_hash}`",
                color=discord.Color.red()
            )
            
        embed = discord.Embed(
            title="Ethereum Transaction Information",
            description=f"Details for transaction `{tx_hash}`",
            color=discord.Color.blue(),
            timestamp=datetime.datetime.utcnow()
        )
        
        # Transaction details
        if 'time' in data:
            timestamp = datetime.datetime.fromtimestamp(data['time'])
            embed.add_field(name="Timestamp", value=timestamp.strftime("%Y-%m-%d %H:%M:%S UTC"), inline=True)
        
        status = data.get('transaction_status', 'unknown')
        status_emoji = "✅" if status == "success" else "❌" if status == "failed" else "⏳"
        embed.add_field(name="Status", value=f"{status_emoji} {status.capitalize()}", inline=True)
        
        # Format value in ETH
        if 'value' in data:
            value_eth = float(data['value']) / 1e18  # Convert wei to ETH
            embed.add_field(name="Value", value=f"Ξ {value_eth:.6f} ETH", inline=True)
        
        # Add gas info
        if 'gas_used' in data and 'gas_price' in data:
            gas_used = int(data['gas_used'])
            gas_price = int(data['gas_price'])
            gas_fee_eth = (gas_used * gas_price) / 1e18  # Convert wei to ETH
            embed.add_field(name="Gas Used", value=f"{gas_used:,}", inline=True)
            embed.add_field(name="Gas Fee", value=f"Ξ {gas_fee_eth:.6f} ETH", inline=True)
            
        # Add block info
        if 'block_id' in data:
            embed.add_field(name="Block", value=data['block_id'], inline=True)
            
        # Add from/to addresses (shortened)
        if 'sender' in data:
            from_addr = data['sender']
            embed.add_field(name="From", value=f"`{from_addr[:10]}...{from_addr[-6:]}`", inline=True)
            
        if 'recipient' in data:
            to_addr = data['recipient']
            embed.add_field(name="To", value=f"`{to_addr[:10]}...{to_addr[-6:]}`", inline=True)
            
        # Add transaction link
        embed.add_field(
            name="View Transaction",
            value=f"[Etherscan](https://etherscan.io/tx/{tx_hash})",
            inline=False
        )
        
        return embed
    
    def create_btc_confirmation_embed(self, tx_hash: str, tx_data: Dict) -> discord.Embed:
        """Create an embed for BTC transaction confirmation notification"""
        embed = discord.Embed(
            title="Bitcoin Transaction Confirmed",
            description=f"Your transaction `{tx_hash}` has received its first confirmation.",
            color=discord.Color.green(),
            timestamp=datetime.datetime.utcnow()
        )
        
        # Format value in BTC
        value_btc = sum(out.get('value', 0) for out in tx_data.get('out', [])) / 100000000  # Convert satoshis to BTC
        embed.add_field(name="Value", value=f"₿ {value_btc:.8f} BTC", inline=True)
        
        # Add block info
        if 'block_height' in tx_data:
            embed.add_field(name="Confirmed in Block", value=tx_data['block_height'], inline=True)
            
        # Add transaction link
        embed.add_field(
            name="View Transaction",
            value=f"[Blockchain.com](https://www.blockchain.com/btc/tx/{tx_hash})",
            inline=False
        )
        
        return embed
        
    def create_crypto_price_embed(self, coin_data: Dict) -> discord.Embed:
        """Create an embed for cryptocurrency price information"""
        # Get basic coin info
        name = coin_data.get('name', 'Unknown')
        symbol = coin_data.get('symbol', 'unknown').upper()
        image_url = coin_data.get('image', {}).get('large', '')
        
        # Get price data
        market_data = coin_data.get('market_data', {})
        current_price = market_data.get('current_price', {})
        price_change_24h_percentage = market_data.get('price_change_percentage_24h', 0)
        
        # Format the price in USD
        price_usd = current_price.get('usd', 0)
        price_usd_formatted = f"${price_usd:,.2f}" if price_usd >= 1 else f"${price_usd:.8f}"
        
        # Determine color based on price change
        if price_change_24h_percentage > 0:
            color = discord.Color.green()
            change_emoji = "📈"
        elif price_change_24h_percentage < 0:
            color = discord.Color.red()
            change_emoji = "📉"
        else:
            color = discord.Color.light_grey()
            change_emoji = "➡️"
            
        # Create the embed
        embed = discord.Embed(
            title=f"{name} ({symbol}) Price",
            description=f"Current price: **{price_usd_formatted}**",
            color=color,
            timestamp=datetime.datetime.utcnow()
        )
        
        if image_url:
            embed.set_thumbnail(url=image_url)
            
        # Add price changes
        embed.add_field(
            name="24h Change", 
            value=f"{change_emoji} {price_change_24h_percentage:.2f}%", 
            inline=True
        )
        
        # Add additional price data in other currencies
        btc_price = current_price.get('btc', 0)
        eth_price = current_price.get('eth', 0)
        
        if symbol != 'BTC' and btc_price:
            embed.add_field(name="BTC Value", value=f"₿ {btc_price:.8f}", inline=True)
            
        if symbol != 'ETH' and eth_price:
            embed.add_field(name="ETH Value", value=f"Ξ {eth_price:.8f}", inline=True)
            
        # Add market cap if available
        market_cap = market_data.get('market_cap', {}).get('usd', 0)
        if market_cap:
            embed.add_field(name="Market Cap", value=f"${market_cap:,.0f}", inline=True)
            
        # Add volume if available
        volume = market_data.get('total_volume', {}).get('usd', 0)
        if volume:
            embed.add_field(name="24h Volume", value=f"${volume:,.0f}", inline=True)
            
        # Add highest and lowest price in 24h
        high_24h = market_data.get('high_24h', {}).get('usd', 0)
        low_24h = market_data.get('low_24h', {}).get('usd', 0)
        
        if high_24h and low_24h:
            embed.add_field(name="24h High", value=f"${high_24h:,.2f}", inline=True)
            embed.add_field(name="24h Low", value=f"${low_24h:,.2f}", inline=True)
            
        # Add data source and disclaimer
        embed.set_footer(text="Data provided by CoinGecko API")
        
        return embed
    
    @commands.command(name="crypto")
    async def crypto(self, ctx, *, crypto_name: str):
        """Checks the current price of the specified cryptocurrency"""
        # Convert to lowercase and strip spaces
        crypto_name = crypto_name.lower().strip()
        
        # Check if we have the coin in our mapping
        coin_id = COIN_MAPPING.get(crypto_name, crypto_name)
        
        # Send a typing indicator while fetching data
        async with ctx.typing():
            try:
                coin_data = await self.get_crypto_price(coin_id)
                if not coin_data:
                    return await ctx.send(f"Could not find price data for '{crypto_name}'. Try using a valid coin ID or symbol.")
                    
                embed = self.create_crypto_price_embed(coin_data)
                await ctx.send(embed=embed)
                
            except Exception as e:
                logger.error(f"Error in crypto command: {e}")
                await ctx.send(f"An error occurred while fetching crypto price data: {str(e)}")
    
    @commands.command(name="transaction")
    async def transaction(self, ctx, tx_hash: str):
        """Get information about a BTC or ETH transaction"""
        if not tx_hash:
            return await ctx.send("Please provide a transaction hash.")
            
        # Send a typing indicator while fetching data
        async with ctx.typing():
            # Try as BTC transaction first
            btc_data = await self.get_btc_transaction(tx_hash)
            if btc_data:
                embed = self.create_btc_transaction_embed(tx_hash, btc_data)
                return await ctx.send(embed=embed)
                
            # If not found, try as ETH transaction
            eth_data = await self.get_eth_transaction(tx_hash)
            if eth_data and eth_data.get('data', {}).get('transaction', {}):
                embed = self.create_eth_transaction_embed(tx_hash, eth_data)
                return await ctx.send(embed=embed)
                
            # If we get here, the transaction wasn't found
            await ctx.send(f"Transaction `{tx_hash}` not found in either Bitcoin or Ethereum blockchains.")
    
    @commands.command(name="subscribe")
    async def subscribe(self, ctx, tx_hash: str):
        """Subscribe to a bitcoin transaction for one confirmation"""
        if not tx_hash:
            return await ctx.send("Please provide a transaction hash.")
            
        # Check if already subscribed
        if tx_hash in self.btc_subscriptions and ctx.channel in self.btc_subscriptions[tx_hash]:
            return await ctx.send("This channel is already subscribed to that transaction.")
            
        # Check if already confirmed
        if tx_hash in self.completed_transactions:
            return await ctx.send("This transaction has already been confirmed.")
            
        # Send a typing indicator while checking the transaction
        async with ctx.typing():
            btc_data = await self.get_btc_transaction(tx_hash)
            if not btc_data:
                return await ctx.send(f"Bitcoin transaction `{tx_hash}` not found.")
                
            # Check if it already has confirmations
            confirmations = btc_data.get('confirmations', 0)
            if confirmations >= 1:
                embed = self.create_btc_confirmation_embed(tx_hash, btc_data)
                return await ctx.send("This transaction already has confirmations:", embed=embed)
                
            # Add to subscription list
            if tx_hash not in self.btc_subscriptions:
                self.btc_subscriptions[tx_hash] = []
                
            self.btc_subscriptions[tx_hash].append(ctx.channel)
            
            # Confirmation message
            await ctx.send(f"✅ Subscribed to Bitcoin transaction `{tx_hash}`. You will be notified when it receives its first confirmation.")

async def setup(bot):
    await bot.add_cog(Crypto(bot)) 