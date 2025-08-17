from typing import List, Dict

from .exchange_abc import Exchange
from .mock_exchange import MockExchange
from .ccxt_exchange import CcxtExchange

def create_exchanges(config: Dict) -> List[Exchange]:
    """
    Creates and returns a list of exchange instances based on the config.

    Args:
        config: The application's configuration dictionary.

    Returns:
        A list of initialized exchange instances.
    """
    exchanges = []

    if 'exchanges' not in config:
        print("Warning: No 'exchanges' section found in the configuration.")
        return []

    for exchange_id, ex_config in config['exchanges'].items():
        api_key = ex_config.get('api_key')
        api_secret = ex_config.get('api_secret')
        enabled = ex_config.get('enabled', True)

        if not enabled:
            print(f"Skipping '{exchange_id}' as it is disabled in the config.")
            continue

        # For non-mock exchanges, check for placeholder credentials
        if exchange_id != 'mock' and (not api_key or 'YOUR_' in api_key or not api_secret or 'YOUR_' in api_secret):
            print(f"Skipping '{exchange_id}' due to missing or placeholder credentials.")
            continue

        try:
            print(f"Initializing exchange: {exchange_id}")
            if exchange_id == 'mock':
                # Mock exchange doesn't need real keys, but we can pass them for consistency
                exchange_instance = MockExchange(api_key=api_key or "mock_key", api_secret=api_secret or "mock_secret")
            else:
                exchange_instance = CcxtExchange(
                    exchange_id=exchange_id,
                    api_key=api_key,
                    api_secret=api_secret
                )
            exchanges.append(exchange_instance)
        except ValueError as e:
            print(f"Error initializing exchange '{exchange_id}': {e}")
        except Exception as e:
            print(f"An unexpected error occurred while initializing '{exchange_id}': {e}")

    if not exchanges:
        print("\nWarning: No valid exchanges were initialized. The bot may not function.")
        print("Please check your `config.yaml` to ensure at least one exchange is enabled and has valid credentials.")

    return exchanges
