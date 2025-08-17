from typing import List, Dict, Optional

from .exchange_abc import Exchange


def find_triangular_arbitrage(exchange: Exchange, symbols: List[str]) -> Optional[List[Dict]]:
    """
    Finds triangular arbitrage opportunities on a given exchange.

    Args:
        exchange: An instance of an exchange connector.
        symbols: A list of all available trading symbols on the exchange.

    Returns:
        A list of dictionaries, where each dictionary represents a profitable
        arbitrage opportunity. Returns an empty list if no opportunities are found.
    """
    print(f"[{exchange.name}] Searching for triangular arbitrage opportunities...")

    markets = _structure_markets(symbols)
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
                        print(f"Found profitable opportunity: {opportunity}")

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
    Calculates the profitability of a given arbitrage path.
    """
    # TODO: Factor in trading fees for a more accurate calculation.

    try:
        ticker1 = exchange.get_ticker(symbols[0])
        ticker2 = exchange.get_ticker(symbols[1])
        ticker3 = exchange.get_ticker(symbols[2])
    except Exception as e:
        print(f"Could not fetch tickers for path {path}: {e}")
        return None

    initial_amount = 1.0
    amount_a = initial_amount

    # Trade 1: A -> B
    base1, quote1 = symbols[0].split('/')
    if path[0] == quote1: # Buying base currency (e.g., USDT -> BTC in BTC/USDT)
        amount_b = amount_a / ticker1['ask']
    else: # Selling base currency (e.g., BTC -> USDT in BTC/USDT)
        amount_b = amount_a * ticker1['bid']

    # Trade 2: B -> C
    base2, quote2 = symbols[1].split('/')
    if path[1] == quote2:
        amount_c = amount_b / ticker2['ask']
    else:
        amount_c = amount_b * ticker2['bid']

    # Trade 3: C -> A
    base3, quote3 = symbols[2].split('/')
    if path[2] == quote3:
        final_amount_a = amount_c / ticker3['ask']
    else:
        final_amount_a = amount_c * ticker3['bid']

    profit = ((final_amount_a - initial_amount) / initial_amount) * 100
    return profit
