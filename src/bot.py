import threading
import time
import logging
from typing import List, Dict, Optional
from pathlib import Path

from .config import load_config
from .exchange_factory import create_exchanges
from .arbitrage import find_all_opportunities
from .risk import check_trade_safety
from .execution import execute_arbitrage

class ArbitrageBot:
    """
    A class to encapsulate the arbitrage bot's logic and state,
    allowing it to be run and managed as a background process.
    """
    def __init__(self):
        self.status: str = "stopped"
        self.config: Optional[Dict] = None
        self.exchanges: List = []
        self.bot_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def start(self, config_path: str = "config/config.yaml"):
        """Starts the bot in a new background thread."""
        if self.status == "running":
            logging.warning("Bot is already running.")
            return

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
                            execute_arbitrage(opp, exchanges_for_trade, self.config, trade_size)
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
