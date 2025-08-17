from typing import List, Dict

class InsufficientLiquidityError(Exception):
    """Custom exception for when a trade is too large for the order book."""
    pass

def calculate_effective_price(
    order_book: Dict[str, List[List[float]]],
    side: str,
    amount: float
) -> float:
    """
    Calculates the effective price for a trade by walking the order book.

    Args:
        order_book: A dictionary with 'bids' and 'asks'.
        side: 'buy' or 'sell'.
        amount: The amount of the base currency to be bought or sold.

    Returns:
        The average execution price.

    Raises:
        InsufficientLiquidityError: If the trade size exceeds available liquidity.
        ValueError: If the side is invalid.
    """
    total_cost = 0.0
    amount_filled = 0.0

    if side == 'buy':
        # For a buy, we use the 'asks' side (sorted low to high price)
        book_side = sorted(order_book['asks'], key=lambda x: x[0])
        for price, volume in book_side:
            if amount_filled >= amount:
                break

            amount_to_fill = min(amount - amount_filled, volume)
            total_cost += amount_to_fill * price
            amount_filled += amount_to_fill

    elif side == 'sell':
        # For a sell, we use the 'bids' side (sorted high to low price)
        book_side = sorted(order_book['bids'], key=lambda x: x[0], reverse=True)
        for price, volume in book_side:
            if amount_filled >= amount:
                break

            amount_to_fill = min(amount - amount_filled, volume)
            total_cost += amount_to_fill * price
            amount_filled += amount_to_fill
    else:
        raise ValueError("Side must be 'buy' or 'sell'.")

    if amount_filled < (amount * 0.999): # Allow for tiny precision errors
        raise InsufficientLiquidityError(
            f"Not enough liquidity to fill the order. "
            f"Requested: {amount}, available: {amount_filled}."
        )

    return total_cost / amount_filled
