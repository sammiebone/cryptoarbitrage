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
