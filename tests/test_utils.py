import pytest
from src.utils import calculate_effective_price, InsufficientLiquidityError

@pytest.fixture
def sample_order_book():
    return {
        "bids": [
            [100, 10], # price, volume
            [99, 5],
            [98, 20],
        ],
        "asks": [
            [101, 10],
            [102, 5],
            [103, 20],
        ]
    }

def test_calculate_effective_price_buy_small(sample_order_book):
    # Buy 5 units, should only take from the best ask
    price = calculate_effective_price(sample_order_book, 'buy', 5)
    assert price == 101

def test_calculate_effective_price_buy_large(sample_order_book):
    # Buy 15 units, takes 10 from first ask, 5 from second ask
    # Total cost = (10 * 101) + (5 * 102) = 1010 + 510 = 1520
    # Average price = 1520 / 15 = 101.333...
    price = calculate_effective_price(sample_order_book, 'buy', 15)
    assert price == pytest.approx(1520 / 15)

def test_calculate_effective_price_sell_large(sample_order_book):
    # Sell 15 units, takes 10 from first bid, 5 from second bid
    # Total value = (10 * 100) + (5 * 99) = 1000 + 495 = 1495
    # Average price = 1495 / 15 = 99.666...
    price = calculate_effective_price(sample_order_book, 'sell', 15)
    assert price == pytest.approx(1495 / 15)

def test_insufficient_liquidity(sample_order_book):
    # Try to buy 100 units, but only 35 are available
    with pytest.raises(InsufficientLiquidityError):
        calculate_effective_price(sample_order_book, 'buy', 100)
