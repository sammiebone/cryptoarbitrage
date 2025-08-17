import asyncio
from datetime import datetime
from web3 import Web3
from .exchange_abc import Exchange
from .wallet_manager import wallet_manager

# A simple, hardcoded registry of token addresses on Ethereum Mainnet
# In a real application, this would be much more extensive.
TOKEN_REGISTRY = {
    "WETH": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
    "DAI": "0x6B175474E89094C44Da98b954EedeAC495271d0F",
    "USDC": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
}

class DEXExchange(Exchange):
    def __init__(self, name, rpc_url, chain_id, router_address, router_abi):
        super().__init__(name)
        if not wallet_manager:
            raise ValueError("DEXExchange requires a configured private key.")

        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        if not self.w3.is_connected():
            raise ConnectionError(f"Failed to connect to Ethereum node at {rpc_url}.")

        self.wallet = wallet_manager.get_account()
        self.address = wallet_manager.get_address()
        self.chain_id = chain_id

        self.router = self.w3.eth.contract(address=Web3.to_checksum_address(router_address), abi=router_abi)

    def _get_token_address(self, symbol):
        address = TOKEN_REGISTRY.get(symbol)
        if not address:
            raise ValueError(f"Token {symbol} not found in registry.")
        return Web3.to_checksum_address(address)

    async def get_ticker(self, symbol):
        raise NotImplementedError("get_ticker is not directly applicable to DEXs. Use get_order_book.")

    async def get_order_book(self, symbol, limit=100):
        """
        Calculates the current price from the DEX and formats it as a mock order book.
        """
        base_asset, quote_asset = symbol.split('/')
        try:
            base_address = self._get_token_address(base_asset)
            quote_address = self._get_token_address(quote_asset)
        except ValueError as e:
            print(f"Error getting token address for {symbol}: {e}")
            return None

        try:
            # Get price for selling 1 unit of the base asset (e.g., 1 WETH)
            # The amount is in the smallest unit of the token (e.g., wei for ETH)
            # We assume 18 decimals for this example.
            amount_in = 1 * (10**18)
            amounts_out = self.router.functions.getAmountsOut(amount_in, [base_address, quote_address]).call()
            price = amounts_out[1] / (10**18) # Also assume 18 decimals for the quote token

            # Create a mock order book with deep liquidity at the calculated price
            # This simulates a deep AMM pool for small trades.
            return {
                "bids": [[price * 0.999, 1000]], # A slightly lower bid
                "asks": [[price * 1.001, 1000]], # A slightly higher ask
                "timestamp": datetime.now().timestamp() * 1000,
                "symbol": symbol
            }
        except Exception as e:
            print(f"Error fetching price from DEX {self.name} for {symbol}: {e}")
            return None

    async def get_fees(self):
        # For DEXs, fees are gas costs + protocol fees. This will be complex.
        # For now, we'll return a placeholder.
        return {'maker': 0.003, 'taker': 0.003} # Uniswap V2 LP fee is 0.3%

    async def execute_trade(self, symbol, trade_type, amount, price):
        """Builds, signs, and sends a swap transaction to the DEX router."""
        base_asset, quote_asset = symbol.split('/')

        # For this example, we'll assume we are selling the base for the quote
        # e.g., for BTC/USD, we are selling BTC to get USD(C/AI).
        # A full implementation would handle both directions.
        if trade_type != 'sell':
            raise NotImplementedError("DEX trading example only implements selling the base asset.")

        token_in_address = self._get_token_address(base_asset)
        token_out_address = self._get_token_address(quote_asset)

        # Amount in smallest unit
        amount_in_wei = self.w3.to_wei(amount, 'ether') # Assuming 18 decimals

        # Build transaction
        tx_data = self.router.functions.swapExactTokensForTokens(
            amount_in_wei,
            0, # amountOutMin - we accept any amount for this example, but in production this should be set based on slippage tolerance
            [token_in_address, token_out_address],
            self.address,
            int(datetime.now().timestamp()) + 300 # Deadline 5 minutes from now
        ).build_transaction({
            'from': self.address,
            'gas': 250000, # A reasonable gas limit for a swap
            'gasPrice': self.w3.eth.gas_price,
            'nonce': self.w3.eth.get_transaction_count(self.address),
            'chainId': self.chain_id
        })

        # Sign transaction
        signed_tx = self.w3.eth.account.sign_transaction(tx_data, self.wallet.key)

        # Send transaction
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)

        # Wait for receipt
        tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

        if tx_receipt.status != 1:
            raise Exception(f"DEX trade transaction failed: {tx_hash.hex()}")

        # Return a mock trade object
        return {
            'id': tx_hash.hex(),
            'datetime': datetime.now().isoformat(),
            'symbol': symbol,
            'type': trade_type,
            'amount': amount,
            'price': price, # This is the target price, not the executed price
        }

    async def get_balance(self, asset_code):
        # This will be implemented to check ERC20 token balance.
        pass

    async def get_withdrawal_fee(self, asset_code):
        # Not applicable to DEXs in the same way as CEXs.
        return 0.0

    async def subscribe_to_tickers(self, symbols, callback):
        # Real-time DEX data requires subscribing to blockchain events, which is advanced.
        # We will simulate this for now.
        pass

    async def close(self):
        # No persistent connection to close for web3.py HTTPProvider
        pass

    async def close_websocket(self):
        # No websocket connection to close in this basic implementation
        pass
