from typing import Dict, Tuple, List, Optional

from .exchange_abc import Exchange

def check_trade_safety(
    opportunity: Dict,
    exchanges: List[Exchange], # Now takes a list of all exchanges
    config: Dict
) -> Tuple[bool, float, Optional[Exchange]]:
    """
    Performs risk management checks for a given arbitrage opportunity.

    Args:
        opportunity: A dictionary representing the arbitrage opportunity.
        exchanges: A list of all available exchange instances.
        config: The application's configuration dictionary.

    Returns:
        A tuple containing:
        - A boolean indicating if the trade is safe to execute.
        - The calculated trade size in the starting currency.
        - The primary exchange object for the trade (for triangular) or None.
    """
    opp_type = opportunity.get('type', 'triangular') # Default to triangular for old format

    # --- Profitability Check (applies to all types) ---
    min_profit = config['risk']['min_profitability_percentage']
    if opportunity['profit_percentage'] < min_profit:
        # This is a common check, so we don't need to be too verbose
        # print(f"[RiskManager] SKIPPING: Profit {opportunity['profit_percentage']:.4f}% is below minimum of {min_profit*100}%.")
        return False, 0.0, None

    if opp_type == 'triangular':
        # Find the correct exchange object
        exchange_name = opportunity.get('exchange')
        exchange = next((ex for ex in exchanges if ex.name == exchange_name), None)
        if not exchange:
            print(f"[RiskManager] ERROR: Could not find exchange object for {exchange_name}.")
            return False, 0.0, None

        start_currency = opportunity['path'].split(' -> ')[0]
        trade_size_percentage = config['trading']['trade_size_percentage']

        try:
            balance = exchange.get_balance(start_currency)
        except Exception as e:
            print(f"[RiskManager] ERROR: Could not fetch balance for {start_currency} on {exchange.name}: {e}")
            return False, 0.0, None

        if balance <= 0:
            return False, 0.0, None

        trade_size = balance * trade_size_percentage

        print(f"[RiskManager] PASSED: Triangular opportunity on {exchange.name} is profitable and has sufficient balance.")
        return True, trade_size, exchange

    elif opp_type == 'direct':
        # TODO: Implement risk checks for direct arbitrage.
        # This would involve checking balances on BOTH exchanges.
        # For now, we will not execute direct arbitrage.
        print(f"[RiskManager] INFO: Direct arbitrage opportunity found, but execution is not yet implemented. Skipping.")
        return False, 0.0, None

    else:
        print(f"[RiskManager] WARNING: Unknown opportunity type '{opp_type}'. Skipping.")
        return False, 0.0, None
