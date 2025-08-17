from abc import ABC, abstractmethod
import asyncio

class Exchange(ABC):
    def __init__(self, name):
        self.name = name

    @abstractmethod
    async def get_ticker(self, symbol):
        """
        Fetches the ticker for a given symbol.
        A ticker includes information like bid, ask, and last price.
        """
        pass

    @abstractmethod
    async def get_order_book(self, symbol, limit=100):
        """
        Fetches the order book for a given symbol.
        The order book contains a list of buy (bids) and sell (asks) orders.
        """
        pass

    @abstractmethod
    async def get_fees(self):
        """
        Fetches the trading fees for the exchange.
        This should return a dictionary with 'maker' and 'taker' fees.
        """
        pass

    @abstractmethod
    async def execute_trade(self, symbol, trade_type, amount, price):
        """
        Executes a trade on the exchange.

        :param symbol: The trading symbol (e.g., 'BTC/USD').
        :param trade_type: 'buy' or 'sell'.
        :param amount: The amount of the asset to trade.
        :param price: The price at which to execute the trade.
        :return: A dictionary representing the executed trade.
        """
        pass

    @abstractmethod
    async def get_balance(self, asset):
        """
        Fetches the balance for a specific asset.
        """
        pass

    @abstractmethod
    async def close(self):
        """
        Closes the connection to the exchange.
        """
        pass
