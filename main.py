import time
import click
from pathlib import Path

from src.config import load_config
from src.mock_exchange import MockExchange
from src.arbitrage import find_triangular_arbitrage
from src.risk import check_trade_safety
from src.execution import execute_arbitrage

@click.group()
def cli():
    """
    An automated cryptocurrency arbitrage trading bot.
    """
    pass

@cli.command()
@click.option(
    '--config',
    'config_path',
    default='config/config.yaml',
    help='Path to the configuration file.'
)
def run(config_path):
    """
    Starts the arbitrage bot.
    """
    try:
        # --- Initialization ---
        print("🚀 Starting the arbitrage bot...")
        config = load_config(Path(config_path))

        # TODO: Implement a factory to load the correct exchange(s) from config
        # For now, we will use the MockExchange for demonstration.
        print("Using MockExchange for this session.")
        exchange = MockExchange()

        # --- Main Application Loop ---
        print("\nBot is running. Press Ctrl+C to stop.")
        while True:
            print("\n" + "="*40)
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Searching for new opportunities...")

            # 1. Find Opportunities
            symbols = list(exchange._market_data.keys()) # In real version, get from exchange
            opportunities = find_triangular_arbitrage(exchange, symbols)

            # 2. Process Opportunities
            if opportunities:
                print(f"Found {len(opportunities)} potential opportunities. Evaluating...")
                for opp in opportunities:
                    # 3. Perform Risk Checks
                    is_safe, trade_size = check_trade_safety(opp, exchange, config)

                    # 4. Execute if safe
                    if is_safe:
                        execute_arbitrage(opp, exchange, config, trade_size)
                    else:
                        print(f"Skipping opportunity {opp['path']} due to risk checks.")
            else:
                print("No opportunities found in this cycle.")

            # 5. Wait for the next cycle
            sleep_duration = config.get('app', {}).get('poll_interval', 5)
            print(f"Waiting for {sleep_duration} seconds...")
            time.sleep(sleep_duration)

    except FileNotFoundError as e:
        print(f"\n❌ ERROR: {e}")
        print("Please ensure your configuration file is set up correctly.")
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user. Goodbye!")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")

if __name__ == "__main__":
    cli()
