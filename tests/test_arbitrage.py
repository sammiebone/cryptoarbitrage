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

def test_profit_calculation_is_correct_after_fees(mock_exchange):
    """
    Tests the internal _calculate_path_profitability function directly
    to ensure its calculation is accurate for the known opportunity, including fees.
    """
    # The known profitable path
    path = ['USDT', 'BTC', 'ETH', 'USDT']
    symbols = ['BTC/USDT', 'ETH/BTC', 'ETH/USDT']

    profit_percentage = _calculate_path_profitability(mock_exchange, path, symbols)

    assert profit_percentage is not None
    # Gross profit is ~1.8%. With 3x 0.1% taker fees, the net profit is ~1.49%
    assert profit_percentage == pytest.approx(1.4949, abs=1e-4)

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
