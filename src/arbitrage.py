import logging
from typing import List, Dict, Optional

from .exchange_abc import Exchange


def find_all_opportunities(exchanges: List[Exchange], config: dict) -> List[Dict]:
    """
    The main function to find all types of arbitrage opportunities based on config.
    """
    all_opportunities = []
    strategies = config.get('app', {}).get('strategies', {})

    # 1. Find triangular arbitrage on each exchange individually
    if strategies.get('triangular', True):
        logging.info("--- Searching for Triangular Arbitrage Opportunities ---")
        for exchange in exchanges:
            try:
                tri_opps = find_triangular_arbitrage(exchange, config)
                if tri_opps:
                    for opp in tri_opps:
                        opp['exchange'] = exchange.name
                        opp['type'] = 'triangular'
                    all_opportunities.extend(tri_opps)
            except Exception as e:
                logging.error(f"Could not run triangular arbitrage scan on {exchange.name}: {e}")
    else:
        logging.info("--- Skipping Triangular Arbitrage (disabled in config) ---")

    # 2. Find direct arbitrage across all exchanges
    if strategies.get('direct', True):
        logging.info("--- Searching for Direct Arbitrage Opportunities ---")
        direct_opps = find_direct_arbitrage(exchanges, config)
        if direct_opps:
            all_opportunities.extend(direct_opps)
    else:
        logging.info("--- Skipping Direct Arbitrage (disabled in config) ---")

    return all_opportunities


def find_direct_arbitrage(exchanges: List[Exchange], config: dict) -> List[Dict]:
    """
    Finds direct arbitrage opportunities across a list of exchanges.
    """
    all_tickers = {}
    for exchange in exchanges:
        try:
            symbols = exchange.get_symbols()
            for symbol in symbols:
                if symbol not in all_tickers:
                    all_tickers[symbol] = []

                try:
                    ticker = exchange.get_ticker(symbol)
                    if ticker and ticker.get('ask') and ticker.get('bid'):
                        all_tickers[symbol].append({"exchange": exchange, "ticker": ticker})
                except Exception:
                    continue
        except Exception as e:
            logging.error(f"Could not fetch symbols/tickers for {exchange.name}: {e}")
            continue

    monitored_symbols = config.get('trading', {}).get('monitored_symbols', [])
    if monitored_symbols:
        all_tickers = {s: t for s, t in all_tickers.items() if s in monitored_symbols}
        logging.info(f"Scanning {len(all_tickers)} monitored symbols for direct arbitrage...")

    opportunities = []
    for symbol, exchange_tickers in all_tickers.items():
        if len(exchange_tickers) < 2:
            continue

        lowest_ask_item = min(exchange_tickers, key=lambda x: x['ticker']['ask'])
        highest_bid_item = max(exchange_tickers, key=lambda x: x['ticker']['bid'])

        buy_price = lowest_ask_item['ticker']['ask']
        sell_price = highest_bid_item['ticker']['bid']
        buy_exchange = lowest_ask_item['exchange']
        sell_exchange = highest_bid_item['exchange']

        if buy_exchange.name == sell_exchange.name:
            continue

        # This is now a gross profitability check. The detailed calculation will happen in the risk manager.
        if sell_price > buy_price:
            gross_profit_percentage = ((sell_price / buy_price) - 1) * 100

            # We only pass on opportunities that have a chance of being profitable after fees.
            # A threshold of 0% is fine, the risk manager will do the real check.
            if gross_profit_percentage > 0:
                opportunity = {
                    "type": "direct",
                    "symbol": symbol,
                    "profit_percentage": gross_profit_percentage, # This is a gross, preliminary profit
                    "buy_exchange": buy_exchange.name,
                    "sell_exchange": sell_exchange.name,
                    "buy_price": buy_price,
                    "sell_price": sell_price,
                }
                opportunities.append(opportunity)

    return opportunities


def find_triangular_arbitrage(exchange: Exchange, config: dict) -> Optional[List[Dict]]:
    """
    Finds triangular arbitrage opportunities on a given exchange.
    """
    all_symbols = exchange.get_symbols()
    if not all_symbols:
        logging.warning(f"No symbols found for {exchange.name}, skipping triangular scan.")
        return None

    monitored_symbols = config.get('trading', {}).get('monitored_symbols', [])

    symbols_to_scan = all_symbols
    if monitored_symbols:
        symbols_to_scan = [s for s in all_symbols if s in monitored_symbols]
        logging.info(f"[{exchange.name}] Scanning {len(symbols_to_scan)} monitored symbols for triangular arbitrage...")

    markets = _structure_markets(symbols_to_scan)
    currencies = list(markets.keys())

    opportunities = []

    for currency_a in currencies:
        if currency_a not in markets: continue
        for currency_b, symbol_ab in markets[currency_a].items():
            if currency_b not in markets: continue
            for currency_c, symbol_bc in markets[currency_b].items():
                if currency_a in markets[currency_c]:
                    symbol_ca = markets[currency_c][currency_a]

                    if symbol_ab == symbol_bc or symbol_ab == symbol_ca or symbol_bc == symbol_ca:
                        continue

                    path = [currency_a, currency_b, currency_c, currency_a]
                    symbols_path = [symbol_ab, symbol_bc, symbol_ca]

                    profit_percentage = _calculate_path_profitability(exchange, path, symbols_path)

                    if profit_percentage is not None and profit_percentage > 0:
                        opportunity = {
                            "path": " -> ".join(path),
                            "symbols": symbols_path,
                            "profit_percentage": profit_percentage,
                        }
                        opportunities.append(opportunity)
                        logging.info(f"Found triangular opportunity: {opportunity}")

    return opportunities


def _structure_markets(symbols: List[str]) -> Dict[str, Dict[str, str]]:
    """Helper to create a graph-like structure of the markets."""
    markets = {}
    for symbol in symbols:
        try:
            base, quote = symbol.split('/')
        except ValueError:
            continue

        if base not in markets: markets[base] = {}
        if quote not in markets: markets[quote] = {}

        markets[quote][base] = symbol
        markets[base][quote] = symbol

    return markets


def _calculate_path_profitability(exchange: Exchange, path: List[str], symbols: List[str]) -> Optional[float]:
    """
    Calculates the net profitability of a given arbitrage path, including fees.
    """
    try:
        ticker1 = exchange.get_ticker(symbols[0])
        ticker2 = exchange.get_ticker(symbols[1])
        ticker3 = exchange.get_ticker(symbols[2])

        fees1 = exchange.get_trading_fees(symbols[0])
        fees2 = exchange.get_trading_fees(symbols[1])
        fees3 = exchange.get_trading_fees(symbols[2])
    except Exception as e:
        logging.error(f"Could not fetch tickers or fees for path {path}: {e}")
        return None

    initial_amount = 1.0
    amount_a = initial_amount

    # Assume taker fees for all trades
    taker_fee1 = fees1['taker']
    taker_fee2 = fees2['taker']
    taker_fee3 = fees3['taker']

    # Trade 1: A -> B
    base1, quote1 = symbols[0].split('/')
    if path[0] == quote1: # Buying base currency
        amount_b = (amount_a / ticker1['ask']) * (1 - taker_fee1)
    else: # Selling base currency
        amount_b = (amount_a * ticker1['bid']) * (1 - taker_fee1)

    # Trade 2: B -> C
    base2, quote2 = symbols[1].split('/')
    if path[1] == quote2:
        amount_c = (amount_b / ticker2['ask']) * (1 - taker_fee2)
    else:
        amount_c = (amount_b * ticker2['bid']) * (1 - taker_fee2)

    # Trade 3: C -> A
    base3, quote3 = symbols[2].split('/')
    if path[2] == quote3:
        final_amount_a = (amount_c / ticker3['ask']) * (1 - taker_fee3)
    else:
        final_amount_a = (amount_c * ticker3['bid']) * (1 - taker_fee3)

    profit_percentage = ((final_amount_a - initial_amount) / initial_amount) * 100
    return profit_percentage
