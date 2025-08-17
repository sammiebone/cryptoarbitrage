import ccxt.async_support as ccxt
from .exchange_abc import Exchange

class CEXExchange(Exchange):
    def __init__(self, name, api_key=None, secret_key=None):
        super().__init__(name)
        exchange_class = getattr(ccxt, name)
        self._exchange = exchange_class({
            'apiKey': api_key,
            'secret': secret_key,
            'enableRateLimit': True, # Important for respecting API limits
        })
        self._fees = None

    async def get_ticker(self, symbol):
        ticker = await self._exchange.fetch_ticker(symbol)
        return ticker

    async def get_order_book(self, symbol, limit=100):
        order_book = await self._exchange.fetch_order_book(symbol, limit)
        return order_book

    async def get_fees(self):
        if self._fees is None:
            # Load all markets to get fee information
            await self._exchange.load_markets()
            # This is a simplification; fee structures can be complex.
            # We'll assume a universal taker/maker fee for this example.
            # You may need to adapt this for specific exchanges.
            trading_fees = self._exchange.fees.get('trading')
            if trading_fees:
                self._fees = {'maker': trading_fees.get('maker', 0.002), 'taker': trading_fees.get('taker', 0.002)}
            else:
                 self._fees = {'maker': 0.002, 'taker': 0.002} # Default fee
        return self._fees

    async def execute_trade(self, symbol, trade_type, amount, price):
        if price is not None:
            # Limit order
            if trade_type == 'buy':
                order = await self._exchange.create_limit_buy_order(symbol, amount, price)
            elif trade_type == 'sell':
                order = await self._exchange.create_limit_sell_order(symbol, amount, price)
            else:
                raise ValueError(f"Invalid trade type: {trade_type}")
        else:
            # Market order
            if trade_type == 'buy':
                order = await self._exchange.create_market_buy_order(symbol, amount)
            elif trade_type == 'sell':
                order = await self._exchange.create_market_sell_order(symbol, amount)
            else:
                raise ValueError(f"Invalid trade type: {trade_type}")
        return order

    async def get_balance(self, asset):
        balance = await self._exchange.fetch_balance()
        return balance.get(asset, {'free': 0.0, 'total': 0.0})

    def __init__(self, name, api_key=None, secret_key=None):
        super().__init__(name)
        exchange_class = getattr(ccxt, name)
        self._exchange = exchange_class({
            'apiKey': api_key,
            'secret': secret_key,
            'enableRateLimit': True,
        })
        self._fees = None
        self._websocket_task = None

    async def get_ticker(self, symbol):
        ticker = await self._exchange.fetch_ticker(symbol)
        return ticker

    async def get_order_book(self, symbol, limit=100):
        order_book = await self._exchange.fetch_order_book(symbol, limit)
        return order_book

    async def get_fees(self):
        if self._fees is None:
            await self._exchange.load_markets()
            trading_fees = self._exchange.fees.get('trading')
            if trading_fees:
                self._fees = {'maker': trading_fees.get('maker', 0.002), 'taker': trading_fees.get('taker', 0.002)}
            else:
                self._fees = {'maker': 0.002, 'taker': 0.002}
        return self._fees

    async def execute_trade(self, symbol, trade_type, amount, price):
        if trade_type == 'buy':
            order = await self._exchange.create_limit_buy_order(symbol, amount, price)
        elif trade_type == 'sell':
            order = await self._exchange.create_limit_sell_order(symbol, amount, price)
        else:
            raise ValueError(f"Invalid trade type: {trade_type}")
        return order

    async def get_balance(self, asset):
        balance = await self._exchange.fetch_balance()
        return balance.get(asset, {'free': 0.0, 'total': 0.0})

    async def close(self):
        await self._exchange.close()

    async def subscribe_to_tickers(self, symbols, callback):
        """Subscribes to real-time ticker updates using WebSockets."""
        if not self._exchange.has['watchTickers']:
            raise NotImplementedError(f"{self.name} does not support watchTickers.")

        async def subscription_loop():
            while True:
                try:
                    tickers = await self._exchange.watch_tickers(symbols)
                    # The callback expects a single ticker, but watch_tickers returns a dict
                    for symbol, ticker in tickers.items():
                        await callback(ticker)
                except Exception as e:
                    # In a real bot, you would have more robust error handling and reconnection logic here.
                    print(f"An error occurred in the WebSocket subscription for {self.name}: {e}")
                    await asyncio.sleep(5) # Wait before trying to reconnect

        self._websocket_task = asyncio.create_task(subscription_loop())

    async def close_websocket(self):
        if self._websocket_task:
            self._websocket_task.cancel()
            try:
                await self._websocket_task
            except asyncio.CancelledError:
                pass # Expected
        # Also close the underlying ccxt exchange connection, which handles websockets
        await self.close()

    async def get_withdrawal_fee(self, asset_code):
        # This can be slow, so caching is important in a real application
        try:
            fees = await self._exchange.fetch_deposit_withdraw_fees()
            if asset_code in fees and 'withdraw' in fees[asset_code]:
                return fees[asset_code]['withdraw']['fee']
        except Exception as e:
            # Not all exchanges support this method uniformly
            print(f"Could not fetch withdrawal fees for {self.name}: {e}")
        return 0.0 # Default to 0 if not available
