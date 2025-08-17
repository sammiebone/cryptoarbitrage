from abc import ABC, abstractmethod
from typing import Dict, List
from web3 import Web3

class DEX(ABC):
    """
    Abstract Base Class for Decentralized Exchange (DEX) connectors.
    Defines the common interface for interacting with AMM-based exchanges.
    """

    def __init__(self, name: str, w3: Web3, router_address: str, router_abi: List[Dict], factory_address: str, factory_abi: List[Dict]):
        """
        Initializes the DEX connector.

        Args:
            name: The name of the DEX (e.g., "UniswapV2").
            w3: A configured Web3 instance.
            router_address: The address of the DEX's router contract.
            router_abi: The ABI of the router contract.
            factory_address: The address of the DEX's factory contract.
            factory_abi: The ABI of the factory contract.
        """
        self.name = name
        self.w3 = w3
        self.router_address = router_address
        self.router_contract = w3.eth.contract(address=router_address, abi=router_abi)
        self.factory_address = factory_address
        self.factory_contract = w3.eth.contract(address=factory_address, abi=factory_abi)


    @abstractmethod
    def get_swap_price(
        self, token_in_address: str, token_out_address: str, amount_in: int
    ) -> int:
        """
        Calculates the expected output amount for a given swap.

        Args:
            token_in_address: The address of the input token.
            token_out_address: The address of the output token.
            amount_in: The amount of the input token (in its smallest unit, e.g., wei).

        Returns:
            The expected amount of the output token (in its smallest unit).
        """
        pass

    @abstractmethod
    def execute_swap(
        self, token_in_address: str, token_out_address: str, amount_in: int, min_amount_out: int, wallet_address: str, private_key: str
    ) -> str:
        """
        Executes a swap on the DEX.

        Args:
            token_in_address: The address of the input token.
            token_out_address: The address of the output token.
            amount_in: The amount of the input token to swap.
            min_amount_out: The minimum amount of the output token you are willing to accept (slippage protection).
            wallet_address: The address of the trading wallet.
            private_key: The private key of the trading wallet.

        Returns:
            The transaction hash as a string.
        """
        pass
