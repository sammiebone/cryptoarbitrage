import time
from typing import Dict, Optional

from .exchange_abc import Exchange

# Pre-defined, simplified market data for a triangular arbitrage opportunity.
# BTC/USDT: buy BTC with USDT
# ETH/BTC: buy ETH with BTC
# ETH/USDT: sell ETH for USDT
#
# Opportunity: USDT -> BTC -> ETH -> USDT
# 1. Buy BTC with USDT: Price = 50000 USDT for 1 BTC
# 2. Buy ETH with BTC: Price = 0.05 BTC for 1 ETH
# 3. Sell ETH for USDT: Price = 2550 USDT for 1 ETH
#
# Path:
# Start with 2550 USDT.
# Buy 1 ETH for 2550 USDT (using ETH/USDT market in reverse).
# In a real scenario, we'd buy BTC first.
# Let's start with 50000 USDT.
# Buy 1 BTC for 50000 USDT.
# Use 1 BTC to buy 20 ETH (1 / 0.05).
# Sell 20 ETH for 20 * 2550 = 51000 USDT.
# Profit = 51000 - 50000 = 1000 USDT.
MOCK_MARKET_DATA = {
    "BTC/USDT": {
        "bids": [[49995.0, 0.5], [49990.0, 1.0]],  # Price, Amount
        "asks": [[50000.0, 0.5], [50005.0, 1.0]],
    },
    "ETH/BTC": {
        "bids": [[0.0499, 10.0], [0.0498, 20.0]],
        "asks": [[0.0500, 10.0], [0.0501, 20.0]],
    },
    "ETH/USDT": {
        "bids": [[2545.0, 5.0], [2540.0, 10.0]],
        "asks": [[2550.0, 5.0], [2555.0, 10.0]],
    },
}

class MockExchange(Exchange):
    """
    A mock exchange implementation for testing and development.
    It simulates an exchange's behavior without making real API calls.
    """

    def __init__(self, api_key: str = "mock_key", api_secret: str = "mock_secret"):
        super().__init__(api_key, api_secret)
        self._balances = {"USDT": 100000.0, "BTC": 5.0, "ETH": 100.0}
        self._market_data = MOCK_MARKET_DATA

    def get_ticker(self, symbol: str) -> Dict:
        if symbol not in self._market_data:
            raise ValueError(f"Symbol '{symbol}' not found on {self.name}")

        order_book = self._market_data[symbol]
        best_ask = order_book["asks"][0][0]
        best_bid = order_book["bids"][0][0]

        return {
            "symbol": symbol,
            "ask": best_ask,
            "bid": best_bid,
            "last": (best_ask + best_bid) / 2, # A simplified last price
            "timestamp": int(time.time() * 1000),
        }

    def get_order_book(self, symbol: str) -> Dict:
        if symbol not in self._market_data:
            raise ValueError(f"Symbol '{symbol}' not found on {self.name}")
        return self._market_data[symbol]

    def create_order(self, symbol: str, order_type: str, side: str, amount: float, price: Optional[float] = None) -> Dict:
        print(
            f"[{self.name}] INFO: Simulating creating order: "
            f"{side.upper()} {amount} {symbol} at {'market price' if order_type == 'market' else f'price {price}'}"
        )

        if symbol not in self._market_data:
            raise ValueError(f"Symbol '{symbol}' not found on {self.name}")

        base_currency, quote_currency = symbol.split('/')

        # For simplicity, we'll assume market orders execute at the best price
        effective_price = price
        if order_type == 'market':
            if side == 'buy':
                effective_price = self._market_data[symbol]['asks'][0][0]
            else: # sell
                effective_price = self._market_data[symbol]['bids'][0][0]

        trade_value = amount * effective_price

        # Update balances
        if side == 'buy':
            if self._balances[quote_currency] < trade_value:
                raise ValueError("Insufficient funds")
            self._balances[quote_currency] -= trade_value
            self._balances[base_currency] += amount
        else: # sell
            if self._balances[base_currency] < amount:
                raise ValueError("Insufficient funds")
            self._balances[base_currency] -= amount
            self._balances[quote_currency] += trade_value

        print(f"[{self.name}] INFO: Order filled. New balances: {self._balances}")

        return {
            "id": str(int(time.time() * 1000)),
            "symbol": symbol,
            "type": order_type,
            "side": side,
            "amount": amount,
            "price": effective_price,
            "status": "closed",
        }

    def get_balance(self, currency: str) -> float:
        return self._balances.get(currency, 0.0)

    def get_symbols(self) -> list[str]:
        """Returns the list of symbols available in the mock market data."""
        return list(self._market_data.keys())
