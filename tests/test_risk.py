import pytest
from src.risk import check_trade_safety
from src.mock_exchange import MockExchange

@pytest.fixture
def mock_config_low_slippage():
    """Provides a config with a very low slippage tolerance."""
    return {
        'risk': {
            'min_profitability_percentage': 0.1,
            'max_slippage_percentage': 0.05 # 0.05%
        },
        'trading': {'trade_size_percentage': 0.1},
        'app': {}
    }

def test_slippage_tolerance_rejects_trade(mock_config_low_slippage):
    """
    Tests that a trade is rejected if the calculated slippage exceeds the max tolerance.
    We need to use a trade size large enough to walk the book in the mock data.
    """
    mock_exchange = MockExchange()

    # This opportunity is profitable before slippage
    opportunity = {
        'path': 'ETH -> USDT -> BTC -> ETH',
        'symbols': ['ETH/USDT', 'BTC/USDT', 'ETH/BTC'],
        'profit_percentage': 5.0, # High gross profit
        'type': 'triangular',
        'exchange': 'MockExchange'
    }

    # Set a high balance to ensure the trade size is large enough to cause slippage
    # Selling 100 ETH will walk the book in the mock data, causing slippage.
    mock_exchange._balances['ETH'] = 1000.0 # Trade size will be 100 ETH

    is_safe, _, _ = check_trade_safety(opportunity, [mock_exchange], mock_config_low_slippage)

    assert not is_safe, "Trade should have been rejected due to high slippage"
