import time
import click
from pathlib import Path

from src.config import load_config
from src.exchange_factory import create_exchanges
from src.arbitrage import find_all_opportunities
from src.risk import check_trade_safety
from src.execution import execute_arbitrage

@click.group()
def cli():
    """An automated cryptocurrency arbitrage trading bot."""
    pass

@cli.command()
@click.option('--config', 'config_path', default='config/config.yaml', help='Path to the configuration file.')
def run(config_path):
    """Starts the arbitrage bot."""
    try:
        print("🚀 Starting the arbitrage bot...")
        config = load_config(Path(config_path))

        print("\n--- Loading Exchanges ---")
        exchanges = create_exchanges(config)

        if not exchanges:
            print("\nNo exchanges were loaded. Please check your configuration. Exiting.")
            return

        print(f"\nSuccessfully loaded {len(exchanges)} exchange(s): {[ex.name for ex in exchanges]}")

        print("\nBot is running. Press Ctrl+C to stop.")
        while True:
            print("\n" + "="*50)
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Searching for new opportunities...")

            opportunities = find_all_opportunities(exchanges)

            if opportunities:
                print(f"\nFound {len(opportunities)} total opportunities. Evaluating...")
                for opp in opportunities:
                    is_safe, trade_size, exchange_for_trade = check_trade_safety(opp, exchanges, config)

                    if is_safe:
                        execute_arbitrage(opp, exchange_for_trade, config, trade_size)
            else:
                print("No opportunities found in this cycle.")

            sleep_duration = config.get('app', {}).get('poll_interval', 10)
            print(f"\n--- Waiting for {sleep_duration} seconds... ---")
            time.sleep(sleep_duration)

    except FileNotFoundError as e:
        print(f"\n❌ ERROR: {e}")
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user. Goodbye!")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")

if __name__ == "__main__":
    cli()
