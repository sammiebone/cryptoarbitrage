from typing import Dict

from .exchange_abc import Exchange

def execute_arbitrage(
    opportunity: Dict,
    exchange: Exchange,
    config: Dict,
    trade_size: float
):
    """
    Executes the series of trades for an arbitrage opportunity.

    Operates in 'dry_run' or 'live' mode based on the configuration.

    Args:
        opportunity: The dictionary describing the profitable path.
        exchange: The exchange instance to execute on.
        config: The application's configuration dictionary.
        trade_size: The amount of the starting currency to use.
    """
    is_dry_run = config.get('app', {}).get('dry_run', True)
    mode_prefix = "[DryRun]" if is_dry_run else "[LiveTrade]"

    start_currency = opportunity['path'].split(' -> ')[0]
    print(f"{mode_prefix} Executing arbitrage opportunity: {opportunity['path']} with a size of {trade_size:.4f} {start_currency}")

    if not is_dry_run:
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print("!!! WARNING: LIVE TRADING MODE IS ENABLED.    !!!")
        print("!!! THIS WILL EXECUTE REAL TRADES.            !!!")
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")

    path = opportunity['path'].split(' -> ')
    symbols = opportunity['symbols']

    current_amount = trade_size
    current_currency = path[0]

    for i in range(len(symbols)):
        symbol = symbols[i]
        next_currency = path[i+1]

        base, quote = symbol.split('/')

        # Determine trade parameters
        if current_currency == quote:
            side = 'buy'
            price = exchange.get_ticker(symbol)['ask']
            amount_to_trade = current_amount / price
            target_currency = base
        else:
            side = 'sell'
            price = exchange.get_ticker(symbol)['bid']
            amount_to_trade = current_amount
            target_currency = quote

        print(f"{mode_prefix} -> Leg {i+1}: {side.upper()} {symbol} | Amount: {amount_to_trade:.8f} {base} | Price: ~{price:.4f}")

        if not is_dry_run:
            try:
                order_result = exchange.create_order(
                    symbol=symbol,
                    order_type='market',
                    side=side,
                    amount=amount_to_trade
                )
                print(f"{mode_prefix} SUCCESS: Order {order_result['id']} filled.")

                # Update amount for next leg based on actual execution
                filled_price = order_result.get('price', price) # Use actual filled price if available
                if side == 'buy':
                    current_amount = amount_to_trade
                else:
                    current_amount = amount_to_trade * filled_price
            except Exception as e:
                print(f"{mode_prefix} FAILED: Could not execute trade for leg {i+1}. Aborting path. Reason: {e}")
                return
        else:
            # In dry run, simulate the change in amount
            if side == 'buy':
                current_amount = amount_to_trade
            else:
                current_amount = amount_to_trade * price

        current_currency = next_currency

    print(f"{mode_prefix} Successfully completed all legs of the arbitrage path.")
