from typing import Dict, Optional

from .exchange_abc import Exchange

def execute_arbitrage(
    opportunity: Dict,
    exchange: Optional[Exchange], # Now optional
    config: Dict,
    trade_size: float
):
    """
    Executes the series of trades for an arbitrage opportunity.
    """
    is_dry_run = config.get('app', {}).get('dry_run', True)
    mode_prefix = "[DryRun]" if is_dry_run else "[LiveTrade]"
    opp_type = opportunity.get('type', 'triangular')

    print(f"{mode_prefix} Attempting to execute {opp_type} opportunity...")

    if opp_type == 'triangular':
        if not exchange:
            print(f"[Execution] ERROR: Cannot execute triangular arbitrage on {opportunity.get('exchange')} without a valid exchange object.")
            return
        _execute_triangular_arbitrage(opportunity, exchange, config, trade_size, mode_prefix)
    elif opp_type == 'direct':
        print(f"[Execution] INFO: Execution for direct arbitrage is not yet implemented.")
        # When implemented, this would need logic to handle two exchanges.
    else:
        print(f"[Execution] ERROR: Unknown opportunity type '{opp_type}'.")


def _execute_triangular_arbitrage(opportunity, exchange, config, trade_size, mode_prefix):
    """Helper function to contain the logic for triangular arbitrage execution."""
    start_currency = opportunity['path'].split(' -> ')[0]
    print(f"{mode_prefix} Executing: {opportunity['path']} on {exchange.name} with {trade_size:.4f} {start_currency}")

    is_dry_run = config.get('app', {}).get('dry_run', True)
    if not is_dry_run:
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print("!!! WARNING: LIVE TRADING MODE IS ENABLED.    !!!")
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")

    path = opportunity['path'].split(' -> ')
    symbols = opportunity['symbols']
    current_amount = trade_size

    for i in range(len(symbols)):
        symbol = symbols[i]
        base, quote = symbol.split('/')

        if path[i] == quote: # We have quote, need to buy base
            side = 'buy'
            price = exchange.get_ticker(symbol)['ask']
            amount_to_trade = current_amount / price
        else: # We have base, need to sell for quote
            side = 'sell'
            price = exchange.get_ticker(symbol)['bid']
            amount_to_trade = current_amount

        print(f"{mode_prefix} -> Leg {i+1}: {side.upper()} {amount_to_trade:.8f} {base if side == 'buy' else quote} using {symbol} at ~{price}")

        if not is_dry_run:
            try:
                order_result = exchange.create_order('market', side, amount_to_trade, symbol, price)
                filled_price = order_result.get('price', price)
                if side == 'buy':
                    current_amount = amount_to_trade
                else:
                    current_amount = amount_to_trade * filled_price
            except Exception as e:
                print(f"{mode_prefix} FAILED: Leg {i+1} failed: {e}. Aborting.")
                return
        else:
            if side == 'buy':
                current_amount = amount_to_trade
            else:
                current_amount = amount_to_trade * price

    print(f"{mode_prefix} Successfully simulated all legs of the triangular path.")
