from typing import Dict, Tuple, List, Optional

from .exchange_abc import Exchange
from .utils import calculate_effective_price, InsufficientLiquidityError


def _calculate_net_profit(opportunity: Dict, exchanges: List[Exchange], trade_size: float) -> Optional[float]:
    """
    Calculates the final net profit of an opportunity, accounting for trading fees,
    withdrawal fees (for direct), and slippage from the order book.

    Returns:
        The new net profit percentage, or None if the trade is not feasible.
    """
    opp_type = opportunity.get('type')

    try:
        if opp_type == 'triangular':
            # Logic for triangular arbitrage recalculation
            exchange = exchanges[0]
            path = opportunity['path'].split(' -> ')
            symbols = opportunity['symbols']

            fees1 = exchange.get_trading_fees(symbols[0])
            fees2 = exchange.get_trading_fees(symbols[1])
            fees3 = exchange.get_trading_fees(symbols[2])

            # Direct simulation of the trade path
            current_currency = path[0]
            current_amount = trade_size

            # Leg 1
            base, quote = symbols[0].split('/')
            order_book = exchange.get_order_book(symbols[0])
            if current_currency == quote: # Buy base
                amount_to_buy = current_amount / exchange.get_ticker(symbols[0])['ask']
                effective_price = calculate_effective_price(order_book, 'buy', amount_to_buy)
                next_amount = (current_amount / effective_price) * (1 - fees1['taker'])
                current_currency = base
            else: # Sell base
                effective_price = calculate_effective_price(order_book, 'sell', current_amount)
                next_amount = (current_amount * effective_price) * (1 - fees1['taker'])
                current_currency = quote
            current_amount = next_amount

            # Leg 2
            base, quote = symbols[1].split('/')
            order_book = exchange.get_order_book(symbols[1])
            if current_currency == quote:
                amount_to_buy = current_amount / exchange.get_ticker(symbols[1])['ask']
                effective_price = calculate_effective_price(order_book, 'buy', amount_to_buy)
                next_amount = (current_amount / effective_price) * (1 - fees2['taker'])
                current_currency = base
            else:
                effective_price = calculate_effective_price(order_book, 'sell', current_amount)
                next_amount = (current_amount * effective_price) * (1 - fees2['taker'])
                current_currency = quote
            current_amount = next_amount

            # Leg 3
            base, quote = symbols[2].split('/')
            order_book = exchange.get_order_book(symbols[2])
            if current_currency == quote:
                amount_to_buy = current_amount / exchange.get_ticker(symbols[2])['ask']
                effective_price = calculate_effective_price(order_book, 'buy', amount_to_buy)
                final_amount = (current_amount / effective_price) * (1 - fees3['taker'])
            else:
                effective_price = calculate_effective_price(order_book, 'sell', current_amount)
                final_amount = (current_amount * effective_price) * (1 - fees3['taker'])

            return ((final_amount - trade_size) / trade_size) * 100

        elif opp_type == 'direct':
            # Logic for direct arbitrage recalculation
            buy_exchange_name = opportunity['buy_exchange']
            sell_exchange_name = opportunity['sell_exchange']
            symbol = opportunity['symbol']

            buy_exchange = next((ex for ex in exchanges if ex.name == buy_exchange_name), None)
            sell_exchange = next((ex for ex in exchanges if ex.name == sell_exchange_name), None)

            if not buy_exchange or not sell_exchange:
                print(f"[RiskManager] ERROR: Could not find exchange objects for direct arbitrage.")
                return None

            # Fetch all data
            buy_order_book = buy_exchange.get_order_book(symbol)
            sell_order_book = sell_exchange.get_order_book(symbol)
            buy_fees = buy_exchange.get_trading_fees(symbol)
            sell_fees = sell_exchange.get_trading_fees(symbol)
            base_currency, quote_currency = symbol.split('/')
            withdrawal_fee = buy_exchange.get_withdrawal_fee(base_currency)

            if withdrawal_fee == float('inf'):
                print(f"[RiskManager] FAILED: Cannot perform direct arbitrage due to unknown withdrawal fee for {base_currency} on {buy_exchange.name}.")
                return None

            # Full simulation
            initial_amount_quote = trade_size

            # 1. Buy on buy_exchange
            amount_to_buy_base = initial_amount_quote / opportunity['buy_price'] # Approximate amount
            buy_effective_price = calculate_effective_price(buy_order_book, 'buy', amount_to_buy_base)
            amount_base_bought = (initial_amount_quote / buy_effective_price) * (1 - buy_fees['taker'])

            # 2. Withdraw
            amount_base_after_withdrawal = amount_base_bought - withdrawal_fee
            if amount_base_after_withdrawal <= 0:
                print(f"[RiskManager] FAILED: Withdrawal fee ({withdrawal_fee} {base_currency}) is too high for the trade amount.")
                return None

            # 3. Sell on sell_exchange
            sell_effective_price = calculate_effective_price(sell_order_book, 'sell', amount_base_after_withdrawal)
            final_amount_quote = amount_base_after_withdrawal * sell_effective_price * (1 - sell_fees['taker'])

            return ((final_amount_quote - initial_amount_quote) / initial_amount_quote) * 100

    except InsufficientLiquidityError as e:
        print(f"[RiskManager] FAILED: {e}")
        return None
    except Exception as e:
        print(f"[RiskManager] ERROR: Unexpected error during net profit calculation: {e}")
        return None

    return None


def check_trade_safety(
    opportunity: Dict,
    exchanges: List[Exchange],
    config: Dict
) -> Tuple[bool, float, Dict[str, Optional[Exchange]]]:
    """
    Performs risk management checks for a given arbitrage opportunity.
    Returns the trade size and a dictionary of the exchanges involved.
    """
    min_profit = config['risk']['min_profitability_percentage']

    if opportunity['profit_percentage'] < min_profit:
        return False, 0.0, {}

    trade_size = 0.0
    exchanges_for_trade = {}
    opp_type = opportunity.get('type')

    if opp_type == 'triangular':
        exchange_name = opportunity.get('exchange')
        exchange = next((ex for ex in exchanges if ex.name == exchange_name), None)
        if not exchange: return False, 0.0, {}

        start_currency = opportunity['path'].split(' -> ')[0]
        balance = exchange.get_balance(start_currency)
        trade_size = balance * config['trading']['trade_size_percentage']
        exchanges_for_trade['triangular'] = exchange

    elif opp_type == 'direct':
        symbol = opportunity['symbol']
        _, quote_currency = symbol.split('/')
        buy_exchange_name = opportunity['buy_exchange']
        sell_exchange_name = opportunity['sell_exchange']

        buy_exchange = next((ex for ex in exchanges if ex.name == buy_exchange_name), None)
        sell_exchange = next((ex for ex in exchanges if ex.name == sell_exchange_name), None)

        if not buy_exchange or not sell_exchange: return False, 0.0, {}

        # For direct arbitrage, the trade size is determined by the balance on the BUYING exchange.
        balance = buy_exchange.get_balance(quote_currency)
        trade_size = balance * config['trading']['trade_size_percentage']
        exchanges_for_trade['buy'] = buy_exchange
        exchanges_for_trade['sell'] = sell_exchange

    if trade_size <= 0:
        return False, 0.0, {}

    # --- Secondary validation with slippage and all fees ---
    print(f"[RiskManager] INFO: Performing detailed validation for {opp_type} opportunity...")

    net_profit = _calculate_net_profit(opportunity, exchanges, trade_size)

    if net_profit is not None and net_profit > min_profit:
        opportunity['profit_percentage'] = net_profit
        print(f"[RiskManager] PASSED: Net profit after all costs: {net_profit:.4f}%")
        return True, trade_size, exchanges_for_trade
    else:
        print(f"[RiskManager] FAILED: Opportunity not profitable after detailed check. Net profit: {net_profit or 'N/A'}")
        return False, 0.0, {}
