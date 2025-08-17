import asyncio
import random
from datetime import datetime
from .exchange_abc import Exchange

class MockExchange(Exchange):
    def __init__(self, name, assets):
        super().__init__(name)
        self._balance = {asset: 1000.0 for asset in assets}
        self._order_books = {}
        self._fees = {'maker': 0.001, 'taker': 0.001} # 0.1% fee

    async def get_ticker(self, symbol):
        await asyncio.sleep(0.01) # Simulate network latency
        base_price = self._get_base_price(symbol)
        bid = base_price * (1 - 0.0005 * random.random())
        ask = base_price * (1 + 0.0005 * random.random())
        return {'symbol': symbol, 'bid': bid, 'ask': ask, 'last': (bid + ask) / 2}

    async def get_order_book(self, symbol, limit=100):
        await asyncio.sleep(0.01)
        if symbol not in self._order_books:
            self._generate_order_book(symbol)
        return self._order_books[symbol]

    async def get_fees(self):
        await asyncio.sleep(0.01)
        return self._fees

    async def execute_trade(self, symbol, trade_type, amount, price):
        await asyncio.sleep(0.01)
        base_asset, quote_asset = symbol.split('/')

        # If price is None, it's a market order. Use the current price.
        if price is None:
            ticker = await self.get_ticker(symbol)
            price = ticker['last']

        if trade_type == 'buy':
            if self._balance[quote_asset] < amount * price:
                raise ValueError("Insufficient funds")
            self._balance[quote_asset] -= amount * price
            self._balance[base_asset] += amount * (1 - self._fees['taker'])
        elif trade_type == 'sell':
            if self._balance[base_asset] < amount:
                raise ValueError("Insufficient funds")
            self._balance[base_asset] -= amount
            self._balance[quote_asset] += amount * price * (1 - self._fees['taker'])

        return {
            'id': str(random.randint(10000, 99999)),
            'datetime': datetime.utcnow().isoformat(),
            'symbol': symbol,
            'type': trade_type,
            'amount': amount,
            'price': price,
            'fee': {
                'cost': amount * price * self._fees['taker'],
                'currency': quote_asset
            }
        }

    async def get_balance(self, asset):
        await asyncio.sleep(0.01)
        return self._balance.get(asset, 0.0)

    def __init__(self, name, assets):
        super().__init__(name)
        self._balance = {asset: 1000.0 for asset in assets}
        self._order_books = {}
        self._fees = {'maker': 0.001, 'taker': 0.001} # 0.1% fee
        self._websocket_task = None

    async def get_ticker(self, symbol):
        await asyncio.sleep(0.01) # Simulate network latency
        base_price = self._get_base_price(symbol)
        bid = base_price * (1 - 0.0005 * random.random())
        ask = base_price * (1 + 0.0005 * random.random())
        return {'symbol': symbol, 'bid': bid, 'ask': ask, 'last': (bid + ask) / 2, 'timestamp': datetime.now().timestamp() * 1000}

    async def get_order_book(self, symbol, limit=100):
        await asyncio.sleep(0.01)
        if symbol not in self._order_books:
            self._generate_order_book(symbol)
        return self._order_books[symbol]

    async def get_fees(self):
        await asyncio.sleep(0.01)
        return self._fees

    async def execute_trade(self, symbol, trade_type, amount, price):
        await asyncio.sleep(0.01)
        base_asset, quote_asset = symbol.split('/')

        if trade_type == 'buy':
            if self._balance[quote_asset] < amount * price:
                raise ValueError("Insufficient funds")
            self._balance[quote_asset] -= amount * price
            self._balance[base_asset] += amount * (1 - self._fees['taker'])
        elif trade_type == 'sell':
            if self._balance[base_asset] < amount:
                raise ValueError("Insufficient funds")
            self._balance[base_asset] -= amount
            self._balance[quote_asset] += amount * price * (1 - self._fees['taker'])

        return {
            'id': str(random.randint(10000, 99999)),
            'datetime': datetime.utcnow().isoformat(),
            'symbol': symbol,
            'type': trade_type,
            'amount': amount,
            'price': price,
            'fee': {
                'cost': amount * price * self._fees['taker'],
                'currency': quote_asset
            }
        }

    async def get_balance(self, asset):
        await asyncio.sleep(0.01)
        return self._balance.get(asset, 0.0)

    async def close(self):
        # No persistent connection to close for the mock exchange
        pass

    async def subscribe_to_tickers(self, symbols, callback):
        """Simulates a WebSocket subscription to tickers."""
        async def subscription_loop():
            while True:
                for symbol in symbols:
                    ticker = await self.get_ticker(symbol)
                    await callback(ticker)
                await asyncio.sleep(1) # New ticker every second

        self._websocket_task = asyncio.create_task(subscription_loop())

    async def close_websocket(self):
        if self._websocket_task:
            self._websocket_task.cancel()
            try:
                await self._websocket_task
            except asyncio.CancelledError:
                pass # Expected

    def _get_base_price(self, symbol):
        # Simple deterministic prices for testing
        if 'BTC' in symbol:
            return 50000.0
        if 'ETH' in symbol:
            return 4000.0
        return 1.0

    def _generate_order_book(self, symbol):
        base_price = self._get_base_price(symbol)
        bids = []
        asks = []
        for i in range(100):
            # Bids are below the base price
            bid_price = base_price * (1 - (i + 1) * 0.0001 * random.random())
            bids.append([bid_price, random.uniform(0.1, 5)])
            # Asks are above the base price
            ask_price = base_price * (1 + (i + 1) * 0.0001 * random.random())
            asks.append([ask_price, random.uniform(0.1, 5)])

        self._order_books[symbol] = {'bids': sorted(bids, key=lambda x: x[0], reverse=True), 'asks': sorted(asks, key=lambda x: x[0])}
