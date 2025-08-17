import os
from eth_account import Account

class WalletManager:
    """
    Manages the wallet for signing blockchain transactions.

    This class securely loads a private key from an environment variable
    and provides the corresponding public address.
    """
    def __init__(self):
        self.private_key = os.environ.get("PRIVATE_KEY")
        if not self.private_key:
            raise ValueError("PRIVATE_KEY environment variable not set. This is required for DEX trading.")

        try:
            self.account = Account.from_key(self.private_key)
            self.address = self.account.address
        except Exception as e:
            raise ValueError(f"Invalid private key provided: {e}")

    def get_address(self):
        """Returns the public address of the wallet."""
        return self.address

    def get_account(self):
        """Returns the full web3.py account object."""
        return self.account

# For easy access, create a singleton instance
# In a larger application, you might use a more sophisticated dependency injection pattern.
try:
    wallet_manager = WalletManager()
except ValueError as e:
    # This allows the application to start even if the DEX functionality is not used.
    # A warning will be logged by the DEX connector if it's initialized without a key.
    wallet_manager = None
    print(f"WalletManager not initialized: {e}")
