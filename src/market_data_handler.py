import asyncio
from collections import defaultdict
import threading

class MarketDataHandler:
    def __init__(self, exchanges, notification_callback=None):
        self.exchanges = exchanges
        self._market_data = defaultdict(dict)
        self._lock = threading.Lock()
        self._notification_callback = notification_callback

    async def _handle_ticker(self, exchange_name, ticker):
        """Callback function to update the market data cache and notify."""
        with self._lock:
            symbol = ticker['symbol']
            self._market_data[exchange_name][symbol] = ticker

        if self._notification_callback:
            # Notify the bot that a new ticker has arrived
            await self._notification_callback(exchange_name, symbol)

    def get_ticker(self, exchange_name, symbol):
        """Gets the latest ticker from the cache."""
        with self._lock:
            return self._market_data.get(exchange_name, {}).get(symbol)

    async def start_subscriptions(self, symbols):
        """Starts the WebSocket subscriptions for all exchanges."""
        for exchange in self.exchanges.values():
            # Create a partial function to pass the exchange name to the callback
            callback = lambda ticker, ex_name=exchange.name: self._handle_ticker(ex_name, ticker)

            # The subscribe_to_tickers method from the exchange interface will start a background task
            await exchange.subscribe_to_tickers(symbols, callback)

        self.log(f"Started WebSocket subscriptions for {len(self.exchanges)} exchanges.")

    async def stop_subscriptions(self):
        """Stops all WebSocket subscriptions."""
        for exchange in self.exchanges.values():
            await exchange.close_websocket()
        self.log("Stopped all WebSocket subscriptions.")

    def log(self, message):
        # Simple logger for now
        print(f"[MarketDataHandler] {message}")
