import pytest
import asyncio
import logging
from src.arbitrage_bot import ArbitrageBot
from src.mock_exchange import MockExchange

@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def bot(request):
    """Fixture to create and initialize an ArbitrageBot instance for event-driven tests."""
    import yaml
    import os

    config_path = f"tests/test_config_{request.node.name}.yaml"
    test_config = {
        "exchanges": ["mock1", "mock2"],
        "assets": ["BTC", "USD"],
        "min_profitability_pct": 1.0, # Set a specific threshold for the test
        "max_trade_size_usd": 100.0,
        "dry_run": True,
        "api_keys": {}
    }

    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    with open(config_path, "w") as f:
        yaml.dump(test_config, f)

    bot_instance = ArbitrageBot(config_path=config_path)

    # Override the mock exchange price generation to create a clear opportunity
    # mock1 will have a consistently lower price than mock2
    original_mock1_price_fn = bot_instance.exchanges['mock1']._get_base_price
    bot_instance.exchanges['mock1']._get_base_price = lambda symbol: 50000.0
    bot_instance.exchanges['mock2']._get_base_price = lambda symbol: 51000.0 # 2% higher

    yield bot_instance

    # Cleanup
    os.remove(config_path)


@pytest.mark.asyncio
async def test_event_driven_opportunity_detection(bot, caplog):
    """
    Tests the full event-driven flow:
    1. MockExchange simulates a WebSocket stream.
    2. MarketDataHandler receives the stream and calls the bot's callback.
    3. The bot's callback evaluates the opportunity.
    4. A log message is generated if an opportunity is found.
    """
    caplog.set_level(logging.INFO)

    # Start the bot's main loop in the background
    bot_task = asyncio.create_task(bot.run())

    # Let the bot run for a short period to process streamed tickers
    await asyncio.sleep(2.5)

    # Stop the bot
    bot.stop()
    await bot.market_data_handler.stop_subscriptions()
    await bot_task

    # Check the logs for the expected opportunity message
    assert "Found opportunity" in caplog.text
    assert "Buy BTC/USD on mock1" in caplog.text
    assert "Sell on mock2" in caplog.text
    # The profit should be approx 2%, but can vary slightly due to mock randomness
    assert "Profit: 1." in caplog.text or "Profit: 2." in caplog.text
