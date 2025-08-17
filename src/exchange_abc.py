from abc import ABC, abstractmethod
from typing import Dict, Optional

class Exchange(ABC):
    """
    Abstract Base Class for exchange connectors.
    Defines the common interface that all exchange implementations must follow.
    """

    def __init__(self, api_key: str, api_secret: str):
        """
        Initializes the exchange connector with API credentials.
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.name = self.__class__.__name__

    @abstractmethod
    def get_ticker(self, symbol: str) -> Dict:
        """
        Fetches the latest price ticker for a given symbol.

        Args:
            symbol: The trading pair symbol (e.g., 'BTC/USDT').

        Returns:
            A dictionary containing ticker information (e.g., 'ask', 'bid', 'last').
        """
        pass

    @abstractmethod
    def get_order_book(self, symbol: str) -> Dict:
        """
        Fetches the order book for a given symbol.

        Args:
            symbol: The trading pair symbol (e.g., 'BTC/USDT').

        Returns:
            A dictionary representing the order book (e.g., {'bids': [...], 'asks': [...]}).
        """
        pass

    @abstractmethod
    def create_order(self, symbol: str, order_type: str, side: str, amount: float, price: Optional[float] = None) -> Dict:
        """
        Creates a trade order on the exchange.

        Args:
            symbol: The trading pair symbol (e.g., 'BTC/USDT').
            order_type: The type of order (e.g., 'limit', 'market').
            side: The side of the order ('buy' or 'sell').
            amount: The quantity of the asset to trade.
            price: The price at which to place a limit order. Required for limit orders.

        Returns:
            A dictionary containing the order information.
        """
        pass

    @abstractmethod
    def get_balance(self, currency: str) -> float:
        """
        Retrieves the available balance for a specific currency.

        Args:
            currency: The currency symbol (e.g., 'USDT', 'BTC').

        Returns:
            The available balance as a float.
        """
        pass

    @abstractmethod
    def get_symbols(self) -> list[str]:
        """
        Retrieves a list of all available trading symbols from the exchange.

        Returns:
            A list of strings, where each string is a symbol (e.g., 'BTC/USDT').
        """
        pass

    @abstractmethod
    def get_trading_fees(self, symbol: str) -> Dict[str, float]:
        """
        Retrieves the trading fees for a given market symbol.

        Args:
            symbol: The trading pair symbol (e.g., 'BTC/USDT').

        Returns:
            A dictionary containing 'maker' and 'taker' fee rates (e.g., {'maker': 0.001, 'taker': 0.001}).
        """
        pass

    @abstractmethod
    def get_withdrawal_fee(self, currency: str) -> float:
        """
        Retrieves the withdrawal fee for a given currency.

        Args:
            currency: The currency symbol (e.g., 'USDT', 'BTC').

        Returns:
            The withdrawal fee as a float in the currency's units.
        """
        pass
