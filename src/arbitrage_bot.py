import asyncio
import logging
import yaml
from datetime import datetime
from .mock_exchange import MockExchange
from .cex_exchange import CEXExchange
from .models import Trade
from .database import get_db

import ccxt
from .market_data_handler import MarketDataHandler

logger = logging.getLogger(__name__)

class ArbitrageBot:
    def __init__(self, config_path="config/config.yaml"):
        with open(config_path, "r") as f:
            self.config = yaml.safe_load(f)

        self.assets = self.config["assets"]
        self.min_profitability_pct = self.config["min_profitability_pct"]
        self.max_trade_size_usd = self.config["max_trade_size_usd"]
        self.slippage_tolerance_pct = self.config.get("slippage_tolerance_pct", 0.05)
        self.dry_run = self.config.get("dry_run", True)

        self.exchanges = self._initialize_exchanges()
        self.market_data_handler = MarketDataHandler(self.exchanges, self._on_ticker_update)

        self.running = False
        self._log_queue = None

    def _initialize_exchanges(self):
        exchanges = {}
        import os
        for name in self.config["exchanges"]:
            if "mock" in name:
                exchanges[name] = MockExchange(name, self.assets)
            else:
                # Load API keys from environment variables
                # Convention: {EXCHANGE_NAME}_API_KEY and {EXCHANGE_NAME}_SECRET
                api_key = os.environ.get(f"{name.upper()}_API_KEY")
                secret = os.environ.get(f"{name.upper()}_SECRET")

                if not api_key or not secret:
                    self.log(f"API key/secret for {name} not found in environment variables. Running in public mode.", level="warning")

                exchanges[name] = CEXExchange(name, api_key, secret)
        return exchanges

    def set_log_queue(self, log_queue):
        self._log_queue = log_queue

    async def run(self):
        self.running = True
        self.log("Arbitrage bot started. Starting WebSocket subscriptions...")

        # Generate the list of symbols to subscribe to
        symbols_to_subscribe = [f"{asset}/USD" for asset in self.assets if asset != "USD"]
        await self.market_data_handler.start_subscriptions(symbols_to_subscribe)

        self.log("Bot is now running in event-driven mode. Waiting for opportunities...")
        while self.running:
            await asyncio.sleep(1)

    def stop(self):
        self.running = False
        self.log("Arbitrage bot stopping...")

    async def _on_ticker_update(self, updated_exchange_name, symbol):
        """This method is called by the MarketDataHandler on each new ticker."""
        # When a ticker updates on one exchange, check it against all other exchanges.
        for exchange_name, exchange in self.exchanges.items():
            if exchange_name == updated_exchange_name:
                continue

            # Opportunity: buy on `exchange`, sell on `updated_exchange`
            await self.evaluate_opportunity(exchange, self.exchanges[updated_exchange_name], symbol)

            # Opportunity: buy on `updated_exchange`, sell on `exchange`
            await self.evaluate_opportunity(self.exchanges[updated_exchange_name], exchange, symbol)

    async def evaluate_opportunity(self, buy_ex, sell_ex, symbol):
        """Evaluates a single pair of exchanges for an arbitrage opportunity."""
        try:
            ticker_buy = self.market_data_handler.get_ticker(buy_ex.name, symbol)
            ticker_sell = self.market_data_handler.get_ticker(sell_ex.name, symbol)

            if not ticker_buy or not ticker_sell:
                return # Not enough data to evaluate

            # --- Fee-Aware Profit Calculation ---
            fees_buy = await buy_ex.get_fees()
            fees_sell = await sell_ex.get_fees()

            buy_fee = fees_buy.get('taker', 0.002) # Default to 0.2% if not found
            sell_fee = fees_sell.get('taker', 0.002)

            price_to_buy = ticker_buy['ask']
            price_to_sell = ticker_sell['bid']

            # The actual amount of quote currency we get after selling
            # e.g., (1 / buy_price) BTC * (1 - buy_fee) = amount_of_btc_received
            # then, amount_of_btc_received * sell_price * (1 - sell_fee) = final_usd
            # Simplified: final_amount = initial_amount * (sell_price/buy_price) * (1-buy_fee) * (1-sell_fee)

            effective_sell_price = price_to_sell * (1 - sell_fee)
            # Incorporate withdrawal fee
            base_asset, quote_asset = symbol.split('/')
            withdrawal_fee = await sell_ex.get_withdrawal_fee(base_asset)

            # Subtract withdrawal fee (converted to quote currency) from the sell price
            effective_sell_price -= (withdrawal_fee * price_to_sell)

            effective_buy_price = price_to_buy / (1 - buy_fee)

            if effective_sell_price > effective_buy_price:
                profit_pct = ((effective_sell_price - effective_buy_price) / effective_buy_price) * 100

                if profit_pct >= self.min_profitability_pct:
                    self.log(f"Found opportunity: Buy {symbol} on {buy_ex.name} at {price_to_buy}, Sell on {sell_ex.name} at {price_to_sell}. Fully-costed Profit: {profit_pct:.2f}%")
                    if not self.dry_run:
                        await self._execute_direct_arbitrage(buy_ex, sell_ex, symbol, price_to_buy, price_to_sell, profit_pct)
                    else:
                        self.log("Dry run mode is enabled. No trade will be executed.", level="info")

        except Exception as e:
            self.log(f"Could not evaluate {symbol} between {buy_ex.name} and {sell_ex.name}: {e}", level="warning")

    async def _execute_direct_arbitrage(self, buy_exchange, sell_exchange, symbol, buy_price, sell_price, profit_pct):
        """Executes a direct arbitrage trade, including pre-trade checks."""
        try:
            # --- Pre-Trade Slippage and Profitability Check ---
            slippage_factor = self.slippage_tolerance_pct / 100.0
            adjusted_buy_price = buy_price * (1 + slippage_factor)
            adjusted_sell_price = sell_price * (1 - slippage_factor)

            adjusted_profit_pct = ((adjusted_sell_price - adjusted_buy_price) / adjusted_buy_price) * 100

            if adjusted_profit_pct < self.min_profitability_pct:
                self.log(
                    f"Trade aborted. Slippage-adjusted profit ({adjusted_profit_pct:.2f}%) is below minimum ({self.min_profitability_pct:.2f}%).",
                    level="warning"
                )
                return

            trade_size = self._calculate_trade_size(buy_price)
            if trade_size == 0:
                self.log("Skipping trade due to zero trade size.", level="warning")
                return

            self.log(f"Attempting to execute trade: Buy {trade_size:.6f} {symbol} on {buy_exchange.name}, Sell on {sell_exchange.name}")

            # To catch specific ccxt errors, we need a wrapper
            async def safe_execute(exchange, *args):
                try:
                    return await exchange.execute_trade(*args)
                except ccxt.InsufficientFunds as e:
                    self.log(f"Insufficient funds on {exchange.name} for {args[0]}: {e}", level="error")
                    raise e
                except ccxt.NetworkError as e:
                    self.log(f"Network error on {exchange.name}: {e}", level="error")
                    raise e
                except ccxt.ExchangeError as e:
                    self.log(f"Exchange error on {exchange.name}: {e}", level="error")
                    raise e

            # Execute trades concurrently with adjusted prices
            buy_order_task = safe_execute(buy_exchange, symbol, 'buy', trade_size, adjusted_buy_price)
            sell_order_task = safe_execute(sell_exchange, symbol, 'sell', trade_size, adjusted_sell_price)

            buy_order, sell_order = await asyncio.gather(
                buy_order_task,
                sell_order_task,
                return_exceptions=True # Continue even if one fails
            )

            # Check for exceptions and log them
            buy_successful = not isinstance(buy_order, Exception)
            sell_successful = not isinstance(sell_order, Exception)

            if not buy_successful:
                self.log(f"Buy order failed on {buy_exchange.name}: {buy_order}", level="error")
            else:
                self.log(f"Buy order successful on {buy_exchange.name}: {buy_order.get('id', 'N/A')}", level="success")

            if not sell_successful:
                self.log(f"Sell order failed on {sell_exchange.name}: {sell_order}", level="error")
            else:
                self.log(f"Sell order successful on {sell_exchange.name}: {sell_order.get('id', 'N/A')}", level="success")

            # If both trades were successful, log to the database
            if buy_successful and sell_successful:
                # Mock exchanges don't return the full data structure, so we need to add it for logging
                buy_order['exchange'] = buy_exchange.name
                sell_order['exchange'] = sell_exchange.name
                buy_order['cost'] = buy_order['amount'] * buy_order['price']
                sell_order['cost'] = sell_order['amount'] * sell_order['price']

                self._log_trade_to_db(buy_order, sell_order, profit_pct)

            # --- FAILED TRADE RECOVERY ---
            # Handle the case where we bought an asset but failed to sell it
            elif buy_successful and not sell_successful:
                self.log(f"CRITICAL: Legged trade detected! Buy on {buy_exchange.name} succeeded, but sell on {sell_exchange.name} failed.", level="error")
                self.log(f"Attempting to sell {buy_order['amount']} of {symbol} on {buy_exchange.name} to recover.", level="warning")
                try:
                    # Execute a market sell order to close the position quickly
                    recovery_order = await buy_exchange.execute_trade(symbol, 'sell', buy_order['amount'], None) # Price=None for market order
                    self.log(f"Recovery sell order placed successfully on {buy_exchange.name}: {recovery_order.get('id', 'N/A')}", level="success")
                except Exception as recovery_e:
                    self.log(f"CRITICAL: Recovery sell order FAILED on {buy_exchange.name}: {recovery_e}", level="error")
                    self.log("Manual intervention required to close open position!", level="error")

        except Exception as e:
            self.log(f"Error during trade execution: {e}", level="error")

    def _log_trade_to_db(self, buy_order, sell_order, profit_pct):
        """Logs a completed arbitrage trade to the database."""
        with get_db() as db:
            trade = Trade(
                timestamp=datetime.utcnow(),
                opportunity_type="direct",
                exchange1=buy_order['exchange'],
                asset1_symbol=buy_order['symbol'],
                asset1_price=buy_order['price'],
                asset1_amount=buy_order['amount'],
                exchange2=sell_order['exchange'],
                asset2_symbol=sell_order['symbol'],
                asset2_price=sell_order['price'],
                asset2_amount=sell_order['amount'],
                initial_investment=buy_order['cost'],
                final_return=sell_order['cost'],
                profit_or_loss=sell_order['cost'] - buy_order['cost'],
                profitability_pct=profit_pct
            )
            db.add(trade)
            db.commit()
            self.log(f"Successfully logged trade {trade.id} to database.")

    def _calculate_trade_size(self, price):
        """Calculates the trade size in the base asset."""
        if price <= 0:
            return 0
        return self.max_trade_size_usd / price

    def log(self, message, level="info"):
        # Central logging
        if level == "info":
            logger.info(message)
        elif level == "warning":
            logger.warning(message)
        elif level == "error":
            logger.error(message)
        elif level == "success": # Custom level, treat as info
            logger.info(message)

        # UI logging via queue
        if self._log_queue:
            log_obj = {
                'timestamp': datetime.now().isoformat(),
                'level': level.upper(),
                'message': message
            }
            self._log_queue.put_nowait(log_obj)

    async def close_connections(self):
        tasks = [ex.close() for ex in self.exchanges.values()]
        await asyncio.gather(*tasks)
        self.log("All exchange connections closed.")
