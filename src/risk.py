from typing import Dict, Tuple

from .exchange_abc import Exchange

def check_trade_safety(
    opportunity: Dict,
    exchange: Exchange,
    config: Dict
) -> Tuple[bool, float]:
    """
    Performs risk management checks for a given arbitrage opportunity.

    Args:
        opportunity: A dictionary representing the arbitrage opportunity.
        exchange: The exchange instance where the trade will be executed.
        config: The application's configuration dictionary.

    Returns:
        A tuple containing:
        - A boolean indicating if the trade is safe to execute.
        - The calculated trade size in the starting currency. Returns 0.0 if not safe.
    """
    # 1. Profitability Check
    min_profit = config['risk']['min_profitability_percentage']
    if opportunity['profit_percentage'] < min_profit:
        print(f"[RiskManager] SKIPPING: Profit {opportunity['profit_percentage']:.4f}% is below minimum of {min_profit*100}%.")
        return False, 0.0

    # 2. Balance and Trade Size Check
    start_currency = opportunity['path'].split(' -> ')[0]
    trade_size_percentage = config['trading']['trade_size_percentage']

    try:
        balance = exchange.get_balance(start_currency)
    except Exception as e:
        print(f"[RiskManager] ERROR: Could not fetch balance for {start_currency}: {e}")
        return False, 0.0

    if balance <= 0:
        print(f"[RiskManager] SKIPPING: Zero balance for starting currency {start_currency}.")
        return False, 0.0

    # Calculate the amount of the starting currency to use in the trade
    trade_size = balance * trade_size_percentage

    print(f"[RiskManager] INFO: Balance for {start_currency} is {balance:.4f}. "
          f"Calculated trade size is {trade_size:.4f} (using {trade_size_percentage*100}% of balance).")

    # TODO: Add more checks here in the future, e.g., checking order book depth for slippage.

    return True, trade_size
