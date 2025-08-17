import argparse
import asyncio
from .arbitrage_bot import ArbitrageBot
from .models import init_db

async def main():
    parser = argparse.ArgumentParser(description="Cryptocurrency Arbitrage Bot")
    parser.add_argument("--config", type=str, default="config/config.yaml", help="Path to the configuration file.")

    args = parser.parse_args()

    # Initialize the database
    init_db()

    # Initialize and run the bot
    bot = ArbitrageBot(config_path=args.config)
    await bot.initialize()

    try:
        await bot.run()
    except KeyboardInterrupt:
        print("Bot shutting down...")
    finally:
        await bot.close_connections()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Exiting.")
