import logging
from typing import Dict, Tuple, List, Optional

from .exchange_abc import Exchange
from .utils import calculate_effective_price, InsufficientLiquidityError

def _check_slippage(exchange: Exchange, symbol: str, side: str, amount_to_trade: float, config: dict) -> Optional[float]:
    """Checks if the slippage for a trade is within the acceptable limit."""
    try:
        order_book = exchange.get_order_book(symbol)
        ticker = exchange.get_ticker(symbol)

        # Determine the ticker price to compare against
        ticker_price = ticker['ask'] if side == 'buy' else ticker['bid']
        if not ticker_price:
            logging.warning(f"[RiskManager] Could not get ticker price for {symbol} on {exchange.name}.")
            return None

        effective_price = calculate_effective_price(order_book, side, amount_to_trade)

        slippage = abs(effective_price / ticker_price - 1) * 100
        max_slippage = config.get('risk', {}).get('max_slippage_percentage', 1.0)

        if slippage > max_slippage:
            logging.warning(f"[RiskManager] Slippage for {symbol} is {slippage:.2f}%, which exceeds the limit of {max_slippage}%.")
            return None

        return effective_price
    except InsufficientLiquidityError as e:
        logging.warning(f"[RiskManager] Insufficient liquidity for trade: {e}")
        return None
    except Exception as e:
        logging.exception(f"[RiskManager] Unexpected error during slippage check for {symbol}: {e}")
        return None

def _calculate_net_profit(opportunity: Dict, exchanges: List[Exchange], trade_size: float, config: dict) -> Optional[float]:
    """
    Calculates the final net profit of an opportunity, accounting for all fees and slippage.
    """
    opp_type = opportunity.get('type')

    try:
        if opp_type == 'triangular':
            exchange = exchanges[0]
            path = opportunity['path'].split(' -> ')
            symbols = opportunity['symbols']
            fees = [exchange.get_trading_fees(s) for s in symbols]

            current_currency = path[0]
            current_amount = trade_size

            for i in range(3):
                symbol = symbols[i]
                base, quote = symbol.split('/')
                side = 'buy' if current_currency == quote else 'sell'

                # Approximate amount in base currency to check slippage
                amount_in_base = current_amount / exchange.get_ticker(symbol)['ask'] if side == 'buy' else current_amount

                effective_price = _check_slippage(exchange, symbol, side, amount_in_base, config)
                if effective_price is None: return None

                if side == 'buy':
                    next_amount = (current_amount / effective_price) * (1 - fees[i]['taker'])
                    current_currency = base
                else:
                    next_amount = (current_amount * effective_price) * (1 - fees[i]['taker'])
                    current_currency = quote
                current_amount = next_amount

            return ((current_amount - trade_size) / trade_size) * 100

        elif opp_type == 'direct':
            buy_ex = next(ex for ex in exchanges if ex.name == opportunity['buy_exchange'])
            sell_ex = next(ex for ex in exchanges if ex.name == opportunity['sell_exchange'])
            symbol = opportunity['symbol']
            base, quote = symbol.split('/')

            # --- Check slippage on BUY leg ---
            amount_to_buy_base = trade_size / opportunity['buy_price']
            buy_effective_price = _check_slippage(buy_ex, symbol, 'buy', amount_to_buy_base, config)
            if buy_effective_price is None: return None

            # --- Check slippage on SELL leg ---
            # First, calculate how much base we'd have after buying and withdrawing
            buy_fees = buy_ex.get_trading_fees(symbol)
            withdrawal_fee = buy_ex.get_withdrawal_fee(base)
            if withdrawal_fee == float('inf'): return None
            amount_bought = (trade_size / buy_effective_price) * (1 - buy_fees['taker'])
            amount_to_sell = amount_bought - withdrawal_fee
            if amount_to_sell <= 0: return None

            sell_effective_price = _check_slippage(sell_ex, symbol, 'sell', amount_to_sell, config)
            if sell_effective_price is None: return None

            # --- Recalculate final profit with effective prices ---
            sell_fees = sell_ex.get_trading_fees(symbol)
            final_amount_quote = amount_to_sell * sell_effective_price * (1 - sell_fees['taker'])

            return ((final_amount_quote - trade_size) / trade_size) * 100

    except Exception as e:
        logging.exception(f"[RiskManager] Unexpected error during net profit calculation: {e}")
        return None
    return None


def check_trade_safety(
    opportunity: Dict,
    exchanges: List[Exchange],
    config: Dict
) -> Tuple[bool, float, Dict[str, Optional[Exchange]]]:
    min_profit = config['risk']['min_profitability_percentage']
    if opportunity['profit_percentage'] < min_profit:
        return False, 0.0, {}

    trade_size = 0.0
    exchanges_for_trade = {}
    opp_type = opportunity.get('type')

    if opp_type == 'triangular':
        exchange = next((ex for ex in exchanges if ex.name == opportunity.get('exchange')), None)
        if not exchange: return False, 0.0, {}
        start_currency = opportunity['path'].split(' -> ')[0]
        balance = exchange.get_balance(start_currency)
        trade_size = balance * config['trading']['trade_size_percentage']
        exchanges_for_trade['triangular'] = exchange

    elif opp_type == 'direct':
        buy_exchange = next((ex for ex in exchanges if ex.name == opportunity['buy_exchange']), None)
        sell_exchange = next((ex for ex in exchanges if ex.name == opportunity['sell_exchange']), None)
        if not buy_exchange or not sell_exchange: return False, 0.0, {}

        _, quote_currency = opportunity['symbol'].split('/')
        balance = buy_exchange.get_balance(quote_currency)
        trade_size = balance * config['trading']['trade_size_percentage']
        exchanges_for_trade.update({'buy': buy_exchange, 'sell': sell_exchange})

    if trade_size <= 0:
        return False, 0.0, {}

    logging.info(f"[RiskManager] Performing detailed validation for {opp_type} opportunity...")
    net_profit = _calculate_net_profit(opportunity, exchanges, trade_size, config)

    if net_profit is not None and net_profit > min_profit:
        opportunity['profit_percentage'] = net_profit
        logging.info(f"[RiskManager] PASSED: Net profit after all costs: {net_profit:.4f}%")
        return True, trade_size, exchanges_for_trade
    else:
        logging.warning(f"[RiskManager] FAILED: Opportunity not profitable after detailed check. Net profit: {net_profit or 'N/A'}")
        return False, 0.0, {}
