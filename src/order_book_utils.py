def calculate_effective_price(order_book_side, volume_to_trade):
    """
    Calculates the effective price for a given trade volume by walking the order book.

    :param order_book_side: A list of [price, volume] pairs (either bids or asks).
                            Asks should be sorted from lowest price to highest.
                            Bids should be sorted from highest price to lowest.
    :param volume_to_trade: The amount of the asset to be bought or sold.
    :return: The volume-weighted average price, or None if the volume cannot be met.
    """
    if not order_book_side or volume_to_trade <= 0:
        return None

    total_cost = 0
    volume_filled = 0

    for price, volume in order_book_side:
        volume_at_this_level = min(volume, volume_to_trade - volume_filled)

        total_cost += volume_at_this_level * price
        volume_filled += volume_at_this_level

        if volume_filled >= volume_to_trade:
            break

    # Check if the desired volume was met
    if volume_filled < volume_to_trade:
        return None # Not enough liquidity

    return total_cost / volume_filled
