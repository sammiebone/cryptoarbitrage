import ccxt
from typing import Dict, Optional

from .exchange_abc import Exchange

class CcxtExchange(Exchange):
    """
    A generic exchange connector using the ccxt library.
    This class wraps ccxt to provide a unified interface that matches
    the application's Exchange abstract base class.
    """

    def __init__(self, exchange_id: str, api_key: str, api_secret: str):
        """
        Initializes the ccxt exchange instance.

        Args:
            exchange_id: The ID of the exchange (e.g., 'binance', 'kraken').
            api_key: The API key for the exchange.
            api_secret: The API secret for the exchange.
        """
        super().__init__(api_key, api_secret)

        exchange_class = getattr(ccxt, exchange_id, None)
        if not exchange_class:
            raise ValueError(f"Exchange with ID '{exchange_id}' is not supported by ccxt.")

        self.exchange = exchange_class({
            'apiKey': self.api_key,
            'secret': self.api_secret,
            'options': {
                'adjustForTimeDifference': True,
            },
        })
        self.name = self.exchange.name
        self._fees_cache = {} # Cache for withdrawal fees

    def get_ticker(self, symbol: str) -> Dict:
        """
        Fetches the latest price ticker for a given symbol using ccxt.
        """
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return {
                'symbol': ticker.get('symbol'),
                'ask': ticker.get('ask'),
                'bid': ticker.get('bid'),
                'last': ticker.get('last'),
                'timestamp': ticker.get('timestamp'),
            }
        except ccxt.Error as e:
            print(f"[{self.name}] Error fetching ticker for {symbol}: {e}")
            raise

    def get_order_book(self, symbol: str) -> Dict:
        """
        Fetches the order book for a given symbol using ccxt.
        """
        try:
            order_book = self.exchange.fetch_order_book(symbol)
            return order_book
        except ccxt.Error as e:
            print(f"[{self.name}] Error fetching order book for {symbol}: {e}")
            raise

    def create_order(self, symbol: str, order_type: str, side: str, amount: float, price: Optional[float] = None) -> Dict:
        """
        Creates a trade order on the exchange using ccxt.
        """
        try:
            order = self.exchange.create_order(symbol, order_type, side, amount, price)
            return order
        except ccxt.Error as e:
            print(f"[{self.name}] Error creating order for {symbol}: {e}")
            raise

    def get_balance(self, currency: str) -> float:
        """
        Retrieves the available balance for a specific currency using ccxt.
        """
        try:
            # Note: fetch_balance might require authentication
            balances = self.exchange.fetch_balance()
            return balances.get(currency, {}).get('free', 0.0)
        except ccxt.Error as e:
            print(f"[{self.name}] Error fetching balance for {currency}: {e}")
            raise

    def get_symbols(self) -> list[str]:
        """
        Retrieves a list of all available trading symbols from the exchange using ccxt.
        """
        try:
            # Load markets if they haven't been loaded yet
            if not self.exchange.markets:
                self.exchange.load_markets()
            return self.exchange.symbols
        except ccxt.Error as e:
            print(f"[{self.name}] Error fetching symbols: {e}")
            raise

    def get_trading_fees(self, symbol: str) -> Dict[str, float]:
        """
        Retrieves the trading fees for a given market symbol using ccxt.
        """
        try:
            if not self.exchange.markets:
                self.exchange.load_markets()

            market = self.exchange.market(symbol)

            return {
                "maker": market.get('maker', 0.002), # Default to 0.2% if not provided
                "taker": market.get('taker', 0.002)
            }
        except ccxt.Error as e:
            print(f"[{self.name}] Error fetching trading fees for {symbol}, using default. Error: {e}")
            return {"maker": 0.002, "taker": 0.002}

    def get_withdrawal_fee(self, currency: str) -> float:
        """
        Retrieves the withdrawal fee for a given currency.
        Caches the results to avoid repeated API calls.
        """
        if 'withdrawal_fees' in self._fees_cache:
            return self._fees_cache['withdrawal_fees'].get(currency, float('inf'))

        try:
            print(f"[{self.name}] Fetching all exchange fees (this may be slow)...")
            all_fees = self.exchange.fetch_fees()
            self._fees_cache['withdrawal_fees'] = {}

            if 'withdraw' in all_fees:
                for code, fee in all_fees['withdraw'].items():
                    self._fees_cache['withdrawal_fees'][code] = float(fee)

            return self._fees_cache['withdrawal_fees'].get(currency, float('inf'))

        except (ccxt.NotSupported, ccxt.NetworkError):
            print(f"[{self.name}] WARNING: Exchange does not support fetching withdrawal fees. Assuming high cost.")
            # Cache the fact that it's not supported
            self._fees_cache['withdrawal_fees'] = {}
            return float('inf')
