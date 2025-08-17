import pytest
import asyncio
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
    """Fixture to create and initialize an ArbitrageBot instance."""
    import yaml
    import os

    test_config = {
        "exchanges": ["mock1", "mock2"],
        "assets": ["BTC", "ETH", "USD"],
        "min_profitability_pct": 0.5,
        "api_keys": {}
    }

    config_path = f"tests/test_config_{request.node.name}.yaml"
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    with open(config_path, "w") as f:
        yaml.dump(test_config, f)

    bot_instance = ArbitrageBot(config_path=config_path)

    # Manually create and assign mock exchanges for predictable testing
    bot_instance.exchanges = {
        "mock1": MockExchange("mock1", test_config["assets"]),
        "mock2": MockExchange("mock2", test_config["assets"])
    }

    # Override prices for testing arbitrage
    # Opportunity: Buy BTC on mock1, Sell on mock2
    bot_instance.exchanges["mock1"]._get_base_price = lambda symbol: 50000.0 if symbol == "BTC/USD" else 4000.0
    bot_instance.exchanges["mock2"]._get_base_price = lambda symbol: 51000.0 if symbol == "BTC/USD" else 4000.0

    yield bot_instance

    # Cleanup the dummy config file
    os.remove(config_path)


@pytest.mark.asyncio
async def test_bot_initialization(bot):
    """Test if the bot and its exchanges are initialized correctly."""
    assert bot is not None
    assert "mock1" in bot.exchanges
    assert "mock2" in bot.exchanges
    assert isinstance(bot.exchanges["mock1"], MockExchange)

@pytest.mark.asyncio
async def test_direct_arbitrage_opportunity(bot, caplog):
    """Test that the bot can identify a direct arbitrage opportunity."""
    import logging

    # Set the capture level for the test
    caplog.set_level(logging.INFO)

    await bot.check_direct_arbitrage()

    # Assert that the expected message appeared in the logs
    assert "Found opportunity" in caplog.text
    assert "Buy BTC/USD on mock1" in caplog.text
    assert "Sell on mock2" in caplog.text

@pytest.mark.asyncio
async def test_no_arbitrage_opportunity(bot, capsys):
    """Test that the bot does not flag an opportunity when none exists."""

    # Set prices to be the same
    bot.exchanges["mock1"]._get_base_price = lambda symbol: 50000.0
    bot.exchanges["mock2"]._get_base_price = lambda symbol: 50000.0

    await bot.check_direct_arbitrage()

    captured = capsys.readouterr()
    assert "Found opportunity" not in captured.out
