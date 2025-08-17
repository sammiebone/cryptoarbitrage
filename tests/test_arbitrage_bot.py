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
        "min_profitability_pct": 1.0,
        "max_trade_size_usd": 100.0,
        "slippage_tolerance_pct": 0.0, # Disable slippage for fee tests
        "dry_run": True,
        "api_keys": {}
    }

    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    with open(config_path, "w") as f:
        yaml.dump(test_config, f)

    bot_instance = ArbitrageBot(config_path=config_path)

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

    # Override the mock exchange price generation to create a clear opportunity
    bot.exchanges['mock1']._get_base_price = lambda symbol: 50000.0
    bot.exchanges['mock2']._get_base_price = lambda symbol: 51000.0 # 2% higher

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
    assert "Fully-costed Profit: 1." in caplog.text

@pytest.mark.asyncio
async def test_opportunity_ignored_due_to_fees(bot, caplog):
    """
    Tests that an opportunity is correctly ignored if it is not profitable
    after accounting for trading and withdrawal fees.
    """
    caplog.set_level(logging.INFO)

    # Setup: Create a 2% price difference
    buy_price = 50000.0
    sell_price = 51000.0 # 2% gross profit

    # Setup exchanges with high fees that will negate the profit
    # Total trading fees = 0.5% + 0.5% = 1.0%
    # Withdrawal fee for 1 BTC @ 51k = 0.0002 * 51000 = $10.2 (very small)
    # Let's make trading fees the dominant factor
    mock1 = MockExchange(name="mock1_high_fees", assets=["BTC", "USD"], trading_fee=0.005) # 0.5%
    mock2 = MockExchange(name="mock2_high_fees", assets=["BTC", "USD"], trading_fee=0.005) # 0.5%

    # Override prices
    mock1._get_base_price = lambda symbol: buy_price
    mock2._get_base_price = lambda symbol: sell_price

    # Inject these exchanges into the bot
    bot.exchanges = {"mock1": mock1, "mock2": mock2}
    bot.market_data_handler.exchanges = bot.exchanges

    # Manually trigger an evaluation
    await bot.evaluate_opportunity(mock1, mock2, 'BTC/USD')

    # Assert that NO opportunity was logged because fees made it unprofitable
    assert "Found opportunity" not in caplog.text

@pytest.mark.asyncio
async def test_trade_aborted_due_to_slippage(bot, caplog):
    """
    Tests that a trade is correctly aborted if the slippage tolerance
    makes the opportunity unprofitable.
    """
    caplog.set_level(logging.INFO)

    # Disable dry run for this test to check execution logic
    bot.dry_run = False

    # Set slippage tolerance high enough to wipe out the profit
    bot.slippage_tolerance_pct = 0.2
    bot.min_profitability_pct = 0.1 # Profit must be >= 0.1%

    # Get initial balances to confirm they don't change
    initial_balance = await bot.exchanges['mock1'].get_balance("USD")

    # Manually call the execution method with a trade that is profitable
    # *before* slippage, but not after.
    await bot._execute_direct_arbitrage(
        bot.exchanges['mock1'],
        bot.exchanges['mock2'],
        'BTC/USD',
        buy_price=50000.0,
        sell_price=50050.0, # 0.1% profit, which meets the min requirement
        profit_pct=0.1
    )

    # Check that the trade was aborted and balances are unchanged
    assert "Trade aborted" in caplog.text
    final_balance = await bot.exchanges['mock1'].get_balance("USD")
    assert final_balance == initial_balance
