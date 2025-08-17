import asyncio
import logging
import yaml
from datetime import datetime
from .mock_exchange import MockExchange
from .cex_exchange import CEXExchange
from .models import Trade
from .database import get_db

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ArbitrageBot:
    def __init__(self, config_path="config/config.yaml"):
        with open(config_path, "r") as f:
            self.config = yaml.safe_load(f)

        self.exchanges = {}
        self.assets = self.config["assets"]
        self.min_profitability_pct = self.config["min_profitability_pct"]
        self.running = False
        self._log_queue = None

    async def initialize(self):
        api_keys = self.config.get("api_keys", {})
        for name in self.config["exchanges"]:
            if "mock" in name:
                self.exchanges[name] = MockExchange(name, self.assets)
            else:
                keys = api_keys.get(name, {})
                self.exchanges[name] = CEXExchange(name, keys.get("apiKey"), keys.get("secret"))

    def set_log_queue(self, log_queue):
        self._log_queue = log_queue

    async def run(self):
        self.running = True
        self.log("Arbitrage bot started.")
        while self.running:
            try:
                await self.find_and_execute_opportunities()
                await asyncio.sleep(10) # Wait before next cycle
            except Exception as e:
                self.log(f"An error occurred: {e}", level="error")
                await asyncio.sleep(30) # Wait longer after an error

    def stop(self):
        self.running = False
        self.log("Arbitrage bot stopping...")

    async def find_and_execute_opportunities(self):
        # In a real implementation, you would check for both triangular and direct arbitrage.
        # For simplicity, we'll focus on direct arbitrage here.
        await self.check_direct_arbitrage()

    async def check_direct_arbitrage(self):
        # Create all possible pairs of exchanges
        exchange_names = list(self.exchanges.keys())
        for i in range(len(exchange_names)):
            for j in range(i + 1, len(exchange_names)):
                ex1_name, ex2_name = exchange_names[i], exchange_names[j]
                ex1 = self.exchanges[ex1_name]
                ex2 = self.exchanges[ex2_name]

                # Check for opportunities for each asset
                for asset in self.assets:
                    if asset != "USD": # Assuming USD is the quote currency
                        symbol = f"{asset}/USD"
                        await self.evaluate_direct_opportunity(ex1, ex2, symbol)

    async def evaluate_direct_opportunity(self, ex1, ex2, symbol):
        try:
            ticker1_task = ex1.get_ticker(symbol)
            ticker2_task = ex2.get_ticker(symbol)

            ticker1, ticker2 = await asyncio.gather(ticker1_task, ticker2_task)

            price1 = ticker1['ask'] # Price to buy on ex1
            price2 = ticker2['bid'] # Price to sell on ex2

            # Opportunity: Buy on ex1, Sell on ex2
            if price2 > price1:
                profit_pct = ((price2 - price1) / price1) * 100
                if profit_pct >= self.min_profitability_pct:
                    self.log(f"Found opportunity: Buy {symbol} on {ex1.name} at {price1}, Sell on {ex2.name} at {price2}. Profit: {profit_pct:.2f}%")
                    # In a real bot, you would execute trades here.
                    # self.execute_direct_arbitrage(ex1, ex2, symbol, price1, price2)

            # Opportunity: Buy on ex2, Sell on ex1
            price1_sell = ticker1['bid']
            price2_buy = ticker2['ask']
            if price1_sell > price2_buy:
                 profit_pct = ((price1_sell - price2_buy) / price2_buy) * 100
                 if profit_pct >= self.min_profitability_pct:
                    self.log(f"Found opportunity: Buy {symbol} on {ex2.name} at {price2_buy}, Sell on {ex1.name} at {price1_sell}. Profit: {profit_pct:.2f}%")

        except Exception as e:
            self.log(f"Could not evaluate {symbol} between {ex1.name} and {ex2.name}: {e}", level="warning")

    def log(self, message, level="info"):
        log_message = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}"
        logging.info(log_message)
        if self._log_queue:
            self._log_queue.put_nowait(log_message)

    async def close_connections(self):
        tasks = [ex.close() for ex in self.exchanges.values()]
        await asyncio.gather(*tasks)
        self.log("All exchange connections closed.")
