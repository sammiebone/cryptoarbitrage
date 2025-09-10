# Deployment Guide

This document provides instructions on how to run the Arbitrage Bot as a hosted web application, allowing you to control it from a browser.

The application is designed to be run via its web interface, which provides "Start" and "Stop" controls, a live log viewer, and a trade history page.

### Step 1: Prepare Your Server

Ensure you have a server (e.g., a VPS or cloud instance) with Python and the project files. Make sure you have installed all the required dependencies by running:
```bash
pip install -r requirements.txt
```

### Step 2: Set Environment Variables

For the application to run, you **must** set the required secret keys as environment variables on your server. This is a critical security measure to protect your credentials.

Please refer to the `SECURITY.md` file for a full explanation of each variable.

**Required for all users:**
```bash
export DB_ENCRYPTION_KEY="your_strong_database_password"
```

**Required for DEX trading:**
```bash
export PRIVATE_KEY="your_wallet_private_key"
```

**Required for CEX trading (example for Binance):**
```bash
export BINANCE_API_KEY="your_binance_api_key"
export BINANCE_SECRET="your_binance_secret_key"
```

### Step 3: Run the Production Web Server

To run the application 24/7 as a hosted solution, you must use the production-grade `gunicorn` web server (which is already in `requirements.txt`).

From the project's root directory, execute the following command:

```bash
gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:8000 src.app:app
```

**Command Breakdown:**
- `gunicorn`: The production WSGI server.
- `--worker-class eventlet -w 1`: This is **required** for Flask-SocketIO to work correctly. It tells Gunicorn to use the `eventlet` worker for handling WebSockets.
- `--bind 0.0.0.0:8000`: This makes the server accessible on port `8000` from any IP address. You can change the port if needed.
- `src.app:app`: This tells Gunicorn to run the `app` object located inside the `src/app.py` module.

For a truly robust deployment, you would typically run this command as a `systemd` service to ensure it restarts automatically if the server reboots.

### Step 4: Access the Dashboard

Once the server is running, you can access the dashboard from any web browser by navigating to:

`http://<your_server_ip>:8000`

(Replace `<your_server_ip>` with the public IP address of your server).

You will be prompted to register a user and log in. Once logged in, you will have full control over starting and stopping the bot from the web interface.
