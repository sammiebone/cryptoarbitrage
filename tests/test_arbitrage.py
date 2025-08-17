import pytest

from src.mock_exchange import MockExchange
from src.arbitrage import find_triangular_arbitrage, _calculate_path_profitability

@pytest.fixture
def mock_exchange():
    """Provides a MockExchange instance for tests."""
    return MockExchange()

def test_find_triangular_arbitrage_identifies_opportunity(mock_exchange):
    """
    Tests that the main arbitrage function correctly identifies a known
    profitable opportunity in the mock data.
    """
    symbols = list(mock_exchange._market_data.keys())

    opportunities = find_triangular_arbitrage(mock_exchange, symbols)

    assert opportunities is not None
    assert isinstance(opportunities, list)
    assert len(opportunities) > 0

    # Check for the specific known opportunity
    usdt_path_found = any(opp['path'] == 'USDT -> BTC -> ETH -> USDT' for opp in opportunities)
    assert usdt_path_found, "The specific USDT->BTC->ETH->USDT path was not found."

def test_profit_calculation_is_correct(mock_exchange):
    """
    Tests the internal _calculate_path_profitability function directly
    to ensure its calculation is accurate for the known opportunity.
    """
    # The known profitable path
    path = ['USDT', 'BTC', 'ETH', 'USDT']
    symbols = ['BTC/USDT', 'ETH/BTC', 'ETH/USDT']

    profit_percentage = _calculate_path_profitability(mock_exchange, path, symbols)

    assert profit_percentage is not None
    # We expect a profit of 1.8% from our mock data
    # 10000 USDT -> 0.2 BTC -> 4 ETH -> 10180 USDT. Profit = 180. (180/10000)*100 = 1.8%
    # The calculation is actually (10180 - 10000) / 10000 = 0.018 * 100 = 1.8
    # My previous run showed 1.8000000000000016
    assert profit_percentage == pytest.approx(1.8)

def test_no_opportunity_if_prices_are_unfavorable(mock_exchange):
    """
    Tests that no opportunity is found if the prices do not result in a profit.
    We can simulate this by manually changing the mock data.
    """
    # Make one price worse, breaking the arbitrage opportunity
    mock_exchange._market_data['ETH/USDT']['bids'][0][0] = 2500.0 # Lower the sell price

    symbols = list(mock_exchange._market_data.keys())
    opportunities = find_triangular_arbitrage(mock_exchange, symbols)

    assert not opportunities, "Should not find an opportunity with unfavorable prices."
