import os
from web3 import Web3
from typing import Optional

_web3_instance: Optional[Web3] = None

def get_web3_instance() -> Web3:
    """
    Initializes and returns a singleton Web3 instance.

    Returns:
        A configured Web3 instance.

    Raises:
        ValueError: If the Web3 provider URI is not set or the connection fails.
    """
    global _web3_instance

    if _web3_instance is None:
        provider_uri = os.environ.get("WEB3_PROVIDER_URI")
        if not provider_uri or 'YOUR_INFURA_PROJECT_ID' in provider_uri:
            print("WARNING: WEB3_PROVIDER_URI is not set or is a placeholder. DEX functionality will be disabled.")
            return None

        try:
            print("Initializing Web3 connection...")
            instance = Web3(Web3.HTTPProvider(provider_uri))

            if not instance.is_connected():
                print(f"WARNING: Failed to connect to Web3 provider at {provider_uri}. DEX functionality will be disabled.")
                return None

            _web3_instance = instance
            print("Web3 connection successful.")

        except Exception as e:
            print(f"WARNING: An error occurred while initializing Web3: {e}. DEX functionality will be disabled.")
            return None

    return _web3_instance
