# Agent Instructions for Crypto Arbitrage Bot

This file provides instructions for AI agents working on this repository.

## Project Overview

This project is a cryptocurrency arbitrage bot. It's designed to find and execute arbitrage opportunities across multiple cryptocurrency exchanges. The project is built in Python and uses the `ccxt` library to connect to exchanges.

The project has several key components:
- **Arbitrage Bot Engine**: The core logic for finding and executing arbitrage opportunities.
- **Exchange Connectors**: Modules for connecting to different exchanges (both real and mock).
- **Web Dashboard**: A Flask-based web dashboard for monitoring and controlling the bot.
- **Database**: A SQLite database for storing trade history.

## Development Guidelines

- **Code Style**: Follow PEP 8 for Python code.
- **Testing**: All new features should be accompanied by unit tests. The project uses `pytest` for testing.
- **Dependencies**: All Python dependencies should be listed in `requirements.txt`.

## How to Run Tests

To run the tests, use the following command:

```bash
python -m pytest
```

## Project Structure

The project is organized as follows:

- `config/`: Contains configuration files.
- `src/`: Contains the main source code.
  - `app.py`: The Flask web server.
  - `arbitrage_bot.py`: The core arbitrage bot logic.
  - `cex_exchange.py`: The connector for real CEX exchanges.
  - `database.py`: Database connection and session management.
  - `exchange_abc.py`: The abstract base class for exchanges.
  - `main.py`: The main entry point for the application.
  - `mock_exchange.py`: The mock exchange for testing.
  - `models.py`: The SQLAlchemy database models.
- `tests/`: Contains the unit tests.

## Final Verification Step

Before submitting your final work, you **must** run the test suite to ensure that all tests pass.

```bash
python -m pytest
```

If any tests fail, you must fix them before submitting.
