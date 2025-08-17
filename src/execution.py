import logging
from typing import Dict, Optional
from dashboard.app import app, db
from dashboard.models import Trade
import datetime

from .exchange_abc import Exchange

def execute_arbitrage(
    opportunity: Dict,
    exchanges_for_trade: Dict[str, Optional[Exchange]],
    config: Dict,
    trade_size: float,
    on_new_trade=None
):
    """
    Routes an arbitrage opportunity to the correct execution function.
    """
    is_dry_run = config.get('app', {}).get('dry_run', True)
    mode_prefix = "[DryRun]" if is_dry_run else "[LiveTrade]"
    opp_type = opportunity.get('type')

    logging.info(f"{mode_prefix} Attempting to execute {opp_type} opportunity...")

    if not is_dry_run:
        logging.warning("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        logging.warning("!!! WARNING: LIVE TRADING MODE IS ENABLED.    !!!")
        logging.warning("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")

    if opp_type == 'triangular':
        exchange = exchanges_for_trade.get('triangular')
        if not exchange:
            logging.error(f"[Execution] ERROR: No valid exchange object for triangular arbitrage.")
            return
        _execute_triangular_arbitrage(opportunity, exchange, config, trade_size, mode_prefix, on_new_trade)

    elif opp_type == 'direct':
        _execute_direct_arbitrage(opportunity, exchanges_for_trade, config, trade_size, mode_prefix, on_new_trade)

    else:
        logging.error(f"[Execution] ERROR: Unknown opportunity type '{opp_type}'.")


def _execute_direct_arbitrage(opportunity, exchanges, config, trade_size, mode_prefix, on_new_trade=None):
    """Helper function for direct arbitrage execution."""
    buy_exchange = exchanges.get('buy')
    sell_exchange = exchanges.get('sell')
    symbol = opportunity['symbol']

    if not buy_exchange or not sell_exchange:
        logging.error(f"[Execution] Missing buy or sell exchange object for direct arbitrage.")
        return

    logging.info(f"{mode_prefix} Executing: BUY {symbol} on {buy_exchange.name} and SELL on {sell_exchange.name}")

    is_dry_run = config.get('app', {}).get('dry_run', True)
    if is_dry_run:
        logging.info(f"{mode_prefix} -> Leg 1 (BUY): Would buy {symbol} on {buy_exchange.name}")
        logging.info(f"{mode_prefix} -> Leg 2 (SELL): Would sell {symbol} on {sell_exchange.name}")
        logging.info(f"{mode_prefix} Successfully simulated both legs of the direct arbitrage.")
        return

    # --- Live Execution Logic ---
    amount_to_trade = trade_size / opportunity['buy_price'] # Approximate amount
    base_currency, _ = symbol.split('/')
    buy_order_result = None

    # 1. Execute BUY order
    try:
        logging.info(f"{mode_prefix} -> SUBMITTING LEG 1: BUY {amount_to_trade:.8f} {base_currency} on {buy_exchange.name}")
        buy_order_result = buy_exchange.create_order(
            symbol=symbol, order_type='market', side='buy', amount=amount_to_trade
        )
        logging.info(f"{mode_prefix} SUCCESS: Buy order {buy_order_result.get('id')} submitted.")
    except Exception as e:
        logging.critical(f"{mode_prefix} CRITICAL FAILURE: Buy order failed: {e}. The sell order was not placed.")
        return

    # 2. Execute SELL order
    try:
        amount_to_sell = buy_order_result.get('filled', amount_to_trade)
        if amount_to_sell <= 0:
            logging.warning(f"{mode_prefix} Buy order did not fill. Cannot place sell order.")
            return

        logging.info(f"{mode_prefix} -> SUBMITTING LEG 2: SELL {amount_to_sell:.8f} {base_currency} on {sell_exchange.name}")
        sell_order_result = sell_exchange.create_order(
            symbol=symbol, order_type='market', side='sell', amount=amount_to_sell
        )
        logging.info(f"{mode_prefix} SUCCESS: Sell order {sell_order_result.get('id')} submitted.")
    except Exception as e:
        logging.critical(f"{mode_prefix} CRITICAL FAILURE: The BUY order was filled on {buy_exchange.name}, but the SELL order failed on {sell_exchange.name}: {e}.")
        logging.critical(f"{mode_prefix} URGENT: You are now holding an unhedged position of {amount_to_sell} {base_currency} on {buy_exchange.name}.")
        # Record the failed trade
        with app.app_context():
            trade = Trade(
                trade_type='direct',
                symbol=symbol,
                buy_exchange=buy_exchange.name,
                sell_exchange=sell_exchange.name,
                trade_size_quote=trade_size,
                profit_amount=0, # Or calculate loss if possible
                profit_percentage=0,
                status=f"failed_leg_2: {e}"
            )
            db.session.add(trade)
            db.session.commit()
        return

    logging.info(f"{mode_prefix} Successfully submitted both legs of the direct arbitrage.")
    # Record the successful trade
    with app.app_context():
        profit_amount = trade_size * (opportunity['profit_percentage'] / 100)
        trade = Trade(
            trade_type='direct',
            symbol=symbol,
            buy_exchange=buy_exchange.name,
            sell_exchange=sell_exchange.name,
            trade_size_quote=trade_size,
            profit_amount=profit_amount,
            profit_percentage=opportunity['profit_percentage'],
            status="completed"
        )
        db.session.add(trade)
        db.session.commit()
        if on_new_trade:
            on_new_trade(trade.to_dict())


def _execute_triangular_arbitrage(opportunity, exchange, config, trade_size, mode_prefix, on_new_trade=None):
    """Helper function to contain the logic for triangular arbitrage execution."""
    start_currency = opportunity['path'].split(' -> ')[0]
    logging.info(f"{mode_prefix} Executing: {opportunity['path']} on {exchange.name} with {trade_size:.4f} {start_currency}")

    path = opportunity['path'].split(' -> ')
    symbols = opportunity['symbols']
    current_amount = trade_size
    is_dry_run = config.get('app', {}).get('dry_run', True)

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

        logging.info(f"{mode_prefix} -> Leg {i+1}: {side.upper()} {amount_to_trade:.8f} {base if side == 'buy' else quote} using {symbol} at ~{price}")

        if not is_dry_run:
            try:
                order_result = exchange.create_order(
                    symbol=symbol,
                    order_type='market',
                    side=side,
                    amount=amount_to_trade
                )
                logging.info(f"{mode_prefix} SUCCESS: Order {order_result.get('id')} for leg {i+1} submitted.")
                if side == 'buy':
                    current_amount = amount_to_trade
                else: # sell
                    current_amount = amount_to_trade * order_result.get('price', price)
            except Exception as e:
                logging.error(f"{mode_prefix} FAILED: Could not execute trade for leg {i+1}. Aborting path. Reason: {e}")
                with app.app_context():
                    trade = Trade(
                        trade_type='triangular',
                        symbol=opportunity['symbols'][0], # Just use the first symbol as representative
                        exchange=exchange.name,
                        trade_size_quote=trade_size,
                        profit_amount=0,
                        profit_percentage=0,
                        status=f"failed_leg_{i+1}: {e}"
                    )
                    db.session.add(trade)
                    db.session.commit()
                    if on_new_trade:
                        on_new_trade(trade.to_dict())
                return
        else:
            if side == 'buy':
                current_amount = amount_to_trade
            else:
                current_amount = amount_to_trade * price

    logging.info(f"{mode_prefix} Successfully simulated all legs of the triangular path.")
    # Record the successful trade
    with app.app_context():
        profit_amount = trade_size * (opportunity['profit_percentage'] / 100)
        trade = Trade(
            trade_type='triangular',
            symbol=opportunity['symbols'][0],
            exchange=exchange.name,
            trade_size_quote=trade_size,
            profit_amount=profit_amount,
            profit_percentage=opportunity['profit_percentage'],
            status="completed"
        )
        db.session.add(trade)
        db.session.commit()
