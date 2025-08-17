import threading
import time
import logging
from typing import List, Dict, Optional
from pathlib import Path
from dashboard.models import Trade
from dashboard.app import db, app
from .exchange_factory import create_exchanges
from .arbitrage import find_all_opportunities
from .risk import check_trade_safety
from .execution import execute_arbitrage

class ArbitrageBot:
    """
    A class to encapsulate the arbitrage bot's logic and state,
    allowing it to be run and managed as a background process.
    """
    def __init__(self, on_new_trade=None):
        self.status: str = "stopped"
        self.config: Optional[Dict] = None
        self.exchanges: List = []
        self.bot_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self.on_new_trade = on_new_trade

    def start(self, config_path: str = "config/config.yaml", on_new_trade=None):
        """Starts the bot in a new background thread."""
        if self.status == "running":
            logging.warning("Bot is already running.")
            return

        if on_new_trade:
            self.on_new_trade = on_new_trade

        logging.info("Starting bot...")
        try:
            self.config = load_config(Path(config_path))
            self.exchanges = create_exchanges(self.config)

            if not self.exchanges:
                logging.error("Bot startup failed: No valid exchanges loaded from config.")
                self.status = "error"
                return

            self._stop_event.clear()
            self.bot_thread = threading.Thread(target=self._run_loop, daemon=True)
            self.bot_thread.start()
            self.status = "running"
            logging.info("Bot started successfully in background thread.")
        except Exception as e:
            logging.exception(f"Bot failed to start: {e}")
            self.status = "error"


    def stop(self):
        """Stops the bot's background thread."""
        if self.status != "running":
            logging.warning(f"Bot is not running (status: {self.status}).")
            return

        logging.info("Stopping bot...")
        self._stop_event.set()
        if self.bot_thread:
            self.bot_thread.join(timeout=5) # Wait for the thread to finish
        self.status = "stopped"
        logging.info("Bot stopped.")

    def get_status(self) -> str:
        """Returns the current status of the bot."""
        if self.status == 'running' and self.bot_thread and not self.bot_thread.is_alive():
            self.status = 'error'
            logging.error("Bot thread died unexpectedly.")
        return self.status

    def get_trade_history(self, limit: int = 50) -> List[Dict]:
        """Queries the database for the most recent trades."""
        with app.app_context():
            trades = Trade.query.order_by(Trade.timestamp.desc()).limit(limit).all()
            return [trade.to_dict() for trade in trades]

    def get_performance_summary(self) -> Dict:
        """Calculates performance metrics from the trade history."""
        with app.app_context():
            completed_trades = Trade.query.filter_by(status='completed').all()

            total_pnl = sum(trade.profit_amount for trade in completed_trades)
            total_trades = len(completed_trades)

            return {
                "total_pnl": total_pnl,
                "total_trades": total_trades,
                "win_rate": 0, # TODO: Need to track losses to calculate this
                "average_profit": total_pnl / total_trades if total_trades > 0 else 0,
            }

    def _run_loop(self):
        """The main operational loop of the bot."""
        logging.info("Bot loop started.")
        while not self._stop_event.is_set():
            logging.info("==================== New Cycle ====================")

            try:
                opportunities = find_all_opportunities(self.exchanges)

                if opportunities:
                    logging.info(f"Found {len(opportunities)} total potential opportunities. Evaluating...")
                    for opp in opportunities:
                        if self._stop_event.is_set(): break
                        is_safe, trade_size, exchanges_for_trade = check_trade_safety(opp, self.exchanges, self.config)

                        if is_safe:
                            execute_arbitrage(opp, exchanges_for_trade, self.config, trade_size, on_new_trade=self.on_new_trade)
                else:
                    logging.info("No opportunities found in this cycle.")

                sleep_duration = self.config.get('app', {}).get('poll_interval', 10)

                # Use a loop with a shorter sleep time to make the stop command more responsive
                for _ in range(sleep_duration):
                    if self._stop_event.is_set():
                        break
                    time.sleep(1)

            except Exception as e:
                logging.exception(f"An error occurred in the bot loop: {e}")
                time.sleep(30) # Wait longer after an error

        logging.info("Bot loop finished.")
