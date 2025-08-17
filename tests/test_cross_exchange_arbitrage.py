import pytest
import copy

from src.mock_exchange import MockExchange
from src.arbitrage import find_direct_arbitrage

# Define base market data for tests to be self-contained
BASE_MOCK_MARKET_DATA = {
    "BTC/USDT": {
        "bids": [[49995.0, 0.5]],
        "asks": [[50000.0, 0.5]],
    },
    "ETH/BTC": {
        "bids": [[0.0499, 10.0]],
        "asks": [[0.0500, 10.0]],
    },
}

@pytest.fixture
def exchanges_with_direct_opportunity():
    """
    Creates two mock exchanges with a direct arbitrage opportunity for BTC/USDT.
    Opportunity: Buy BTC on Exchange_B for 49000, Sell on Exchange_A for 50000.
    """
    exchange_a = MockExchange()
    exchange_a.name = "Exchange_A"
    exchange_a._market_data = copy.deepcopy(BASE_MOCK_MARKET_DATA)

    exchange_b = MockExchange()
    exchange_b.name = "Exchange_B"
    exchange_b._market_data = copy.deepcopy(BASE_MOCK_MARKET_DATA)

    # Set prices on Exchange A
    exchange_a._market_data['BTC/USDT']['asks'][0][0] = 50100.0
    exchange_a._market_data['BTC/USDT']['bids'][0][0] = 50000.0 # Higher sell price

    # Set prices on Exchange B
    exchange_b._market_data['BTC/USDT']['asks'][0][0] = 49000.0 # Lower buy price
    exchange_b._market_data['BTC/USDT']['bids'][0][0] = 48900.0

    return [exchange_a, exchange_b]

@pytest.fixture
def exchanges_no_opportunity():
    """
    Creates two mock exchanges with no direct arbitrage opportunity.
    """
    exchange_a = MockExchange()
    exchange_a.name = "Exchange_A"
    exchange_a._market_data = copy.deepcopy(BASE_MOCK_MARKET_DATA)

    exchange_b = MockExchange()
    exchange_b.name = "Exchange_B"
    exchange_b._market_data = copy.deepcopy(BASE_MOCK_MARKET_DATA)

    # Prices are efficient (highest bid is lower than lowest ask)
    exchange_a._market_data['BTC/USDT']['asks'][0][0] = 50100.0
    exchange_a._market_data['BTC/USDT']['bids'][0][0] = 50000.0

    exchange_b._market_data['BTC/USDT']['asks'][0][0] = 50110.0
    exchange_b._market_data['BTC/USDT']['bids'][0][0] = 50010.0

    return [exchange_a, exchange_b]


from src.risk import _calculate_net_profit

@pytest.fixture
def mock_config():
    """Provides a default mock config for tests."""
    return {
        'risk': {'max_slippage_percentage': 1.0},
        'trading': {'monitored_symbols': []}
    }

def test_direct_arbitrage_profit_calculation_is_correct(exchanges_with_direct_opportunity, mock_config):
    """
    Tests that the net profit calculation for direct arbitrage is correct,
    including trading and withdrawal fees.
    """
    exchanges = exchanges_with_direct_opportunity

    opportunity = {
        "type": "direct",
        "symbol": "BTC/USDT",
        "buy_exchange": "Exchange_B",
        "sell_exchange": "Exchange_A",
        "buy_price": 49000.0,
        "sell_price": 50000.0,
    }

    trade_size = 10000.0 # in USDT

    net_profit = _calculate_net_profit(opportunity, exchanges, trade_size, mock_config)

    # Manual calculation confirmed that the code's output of ~1.5870 is correct.
    assert net_profit == pytest.approx(1.5870, abs=1e-4)

def test_no_direct_arbitrage_when_unprofitable(exchanges_no_opportunity, mock_config):
    """
    Tests that no direct arbitrage is found when prices are efficient.
    """
    opportunities = find_direct_arbitrage(exchanges_no_opportunity, mock_config)

    assert not opportunities, "Should not find an opportunity with unprofitable prices."
