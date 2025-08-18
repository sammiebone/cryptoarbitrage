# How the Arbitrage Bot Works

This document provides a comprehensive overview of the architecture and functionality of the Automated Crypto Arbitrage Service.

At its core, this is an **automated arbitrage trading bot**. Its primary goal is to constantly monitor cryptocurrency prices across multiple exchanges to find and exploit small price discrepancies, locking in a profit.

The system is designed to be robust, secure, and scalable. Here’s a breakdown of the key components and how they work together:

### 1. The Core Architecture: Event-Driven and Asynchronous

Instead of inefficiently checking prices every few seconds (a polling model), the bot uses a modern **event-driven architecture**.

*   **Market Data Handler**: This is the bot's central nervous system. It establishes a persistent **WebSocket** connection to every exchange you configure (like Binance, Coinbase, Uniswap, etc.). It listens for real-time price updates.
*   **Arbitrage Bot**: This is the brain. When the Market Data Handler receives a new price tick for an asset, it immediately notifies the Arbitrage Bot. This "event" triggers the bot to wake up and evaluate if this new price has created a profitable arbitrage opportunity against the last known prices on all other exchanges.

This makes the bot extremely fast and efficient, allowing it to react to opportunities in milliseconds.

### 2. The Trade Evaluation & Risk Management Engine

This is the most critical part of the system. Finding a price difference is easy; knowing if it's a *real, executable, and profitable* opportunity is hard. Before any trade is placed, every opportunity goes through a rigorous multi-stage check:

1.  **Liquidity Assessment**: The bot first fetches the live **order book** from the exchanges. It then "walks the book" to calculate the **true effective price** for your configured trade size, accounting for the fact that a large trade might consume multiple price levels (price impact).
2.  **Transaction Cost Analysis**: It then subtracts *all* known costs from the potential profit:
    *   **Trading Fees** (taker fees for both the buy and sell orders).
    *   **Withdrawal Fees** (the cost to eventually rebalance assets between exchanges).
    *   **Gas Fees** (for any trade involving a Decentralized Exchange, it estimates the blockchain transaction fee in USD).
3.  **Slippage Tolerance Check**: Finally, it applies your configured `slippage_tolerance_pct` to the prices. This is a final check to ensure the trade is *still* profitable even if the price moves slightly against us while the order is in transit.

A trade is only executed if it passes **all three** of these checks.

### 3. Secure Trade Execution

*   **CEX & DEX Support**: The bot has a modular design that supports both centralized exchanges (via `ccxt` and REST APIs) and decentralized exchanges (via `web3.py` and direct blockchain interaction).
*   **Concurrent Orders**: When a valid opportunity is confirmed, the bot places the buy and sell orders simultaneously using `asyncio.gather` to minimize the risk of the price changing between the two legs of the trade.
*   **Failed Trade Recovery**: If one leg of the trade succeeds but the other fails (a "legged" trade), the bot automatically enters a "damage control" mode. It will immediately try to sell the asset it just bought back on the same exchange to close the unintended open position and minimize risk.

### 4. Security First

Security was a top priority throughout the build:

*   **API & Private Keys**: All sensitive credentials (CEX API keys, DEX private keys, database encryption keys) are loaded exclusively from **environment variables**. They are never stored in configuration files, preventing them from being accidentally committed to version control.
*   **Database Encryption**: All financial data in the trade history database (prices, amounts, profits) is **encrypted at the application level** before being written to disk.
*   **Secure Web Dashboard**: The web interface is protected by a full user authentication system, including password hashing and **Two-Factor Authentication (2FA)**, ensuring only you can control the bot.

In summary, the bot operates as a sophisticated, event-driven system that combines real-time data handling with a multi-stage risk management engine to safely and efficiently execute arbitrage trades. It's all controlled and monitored through a secure web dashboard.
