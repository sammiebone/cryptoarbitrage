import logging
import queue
import threading
from flask import Flask, jsonify, request
from flask_socketio import SocketIO, emit

# It's important to set up logging before other modules are imported.
log_queue = queue.Queue()
# Note: This setup needs to be run before the bot is instantiated.
# We will need to adjust the application structure slightly.
# For now, let's assume a main script will call setup_logging first.

from src.bot import ArbitrageBot
from src.log_handler import setup_logging


app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret-key-for-production'
socketio = SocketIO(app, async_mode='eventlet')

# --- Global Bot Instance ---
# This setup is simplified. In a larger app, you might use a factory
# or application context to manage the bot instance.
bot = ArbitrageBot()

# --- Logging Setup ---
# It's better to configure logging as soon as the app starts.
setup_logging(log_queue)


def log_emitter_thread(log_queue: queue.Queue):
    """
    A background thread that takes logs from the queue and emits
    them to the dashboard via WebSocket.
    """
    logging.info("Log emitter thread started.")
    while True:
        try:
            # Block until a log message is available
            record = log_queue.get(block=True)
            # Emit the log message to all connected clients
            socketio.emit('log_message', {'data': record})
        except Exception as e:
            # Avoid crashing the thread
            logging.error(f"Error in log emitter thread: {e}")

# --- API Endpoints ---
@app.route('/api/start', methods=['POST'])
def start_bot():
    """Starts the arbitrage bot."""
    if bot.get_status() == 'running':
        return jsonify({"status": "error", "message": "Bot is already running."}), 400

    bot.start()
    return jsonify({"status": "success", "message": "Bot started."})

@app.route('/api/stop', methods=['POST'])
def stop_bot():
    """Stops the arbitrage bot."""
    if bot.get_status() != 'running':
        return jsonify({"status": "error", "message": "Bot is not running."}), 400

    bot.stop()
    return jsonify({"status": "success", "message": "Bot stopped."})

@app.route('/api/status', methods=['GET'])
def get_bot_status():
    """Gets the current status of the bot."""
    return jsonify({"status": bot.get_status()})

# --- WebSocket Events ---
@socketio.on('connect')
def handle_connect():
    """Handles a new client connecting to the WebSocket."""
    logging.info('Dashboard client connected.')
    emit('status_update', {'status': bot.get_status()})

@socketio.on('disconnect')
def handle_disconnect():
    """Handles a client disconnecting from the WebSocket."""
    logging.info('Dashboard client disconnected.')


if __name__ == '__main__':
    # Start the log emitter background thread
    emitter = threading.Thread(target=log_emitter_thread, args=(log_queue,), daemon=True)
    emitter.start()

    # The main entry point is now this script.
    # The old `main.py` CLI is no longer used to run the bot.
    logging.info("Starting dashboard server on http://localhost:5000")
    socketio.run(app, host='0.0.0.0', port=5000)
