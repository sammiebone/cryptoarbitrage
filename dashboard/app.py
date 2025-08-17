import logging
import queue
import threading
import os
from flask import Flask, jsonify, request, send_from_directory
from flask_socketio import SocketIO, emit
from flask_sqlalchemy import SQLAlchemy

from src.bot import ArbitrageBot
from src.log_handler import setup_logging

# --- App Setup ---
# The static_folder points to the build of the React app.
app = Flask(__name__, static_folder='frontend/public')
app.config['SECRET_KEY'] = 'secret-key-for-production'
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or \
    'sqlite:///' + os.path.join(app.instance_path, 'app.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
socketio = SocketIO(app, async_mode='eventlet')

# Import and initialize DB after app is created to avoid circular imports
from .models import db
db.init_app(app)

# --- Global Bot Instance & Logging ---
log_queue = queue.Queue()
setup_logging(log_queue)

def new_trade_callback(trade_data):
    """Callback function to emit new trade data via WebSocket."""
    logging.info(f"New trade recorded: {trade_data['symbol']}. Emitting to dashboard.")
    socketio.emit('new_trade', trade_data)
    # Also push a performance update
    with app.app_context():
        summary = bot.get_performance_summary()
        socketio.emit('performance_update', summary)

bot = ArbitrageBot(on_new_trade=new_trade_callback)

def log_emitter_thread(log_queue: queue.Queue):
    """A background thread that emits logs to the dashboard via WebSocket."""
    logging.info("Log emitter thread started.")
    while True:
        try:
            record = log_queue.get(block=True)
            socketio.emit('log_message', {'data': record})
        except Exception as e:
            logging.error(f"Error in log emitter thread: {e}")

# --- API Endpoints ---
@app.route('/api/start', methods=['POST'])
def start_bot():
    if bot.get_status() == 'running':
        return jsonify({"status": "error", "message": "Bot is already running."}), 400
    bot.start()
    return jsonify({"status": "success", "message": "Bot started."})

@app.route('/api/stop', methods=['POST'])
def stop_bot():
    if bot.get_status() != 'running':
        return jsonify({"status": "error", "message": "Bot is not running."}), 400
    bot.stop()
    return jsonify({"status": "success", "message": "Bot stopped."})

@app.route('/api/status', methods=['GET'])
def get_bot_status():
    return jsonify({"status": bot.get_status()})

@app.route('/api/trade_history', methods=['GET'])
def trade_history():
    """Returns a list of recent trades from the database."""
    limit = request.args.get('limit', 50, type=int)
    trades = bot.get_trade_history(limit=limit)
    return jsonify(trades)

@app.route('/api/performance', methods=['GET'])
def performance_metrics():
    """Returns a summary of performance metrics."""
    summary = bot.get_performance_summary()
    return jsonify(summary)

# --- WebSocket Events ---
@socketio.on('connect')
def handle_connect():
    logging.info('Dashboard client connected.')
    emit('status_update', {'status': bot.get_status()})

@socketio.on('disconnect')
def handle_disconnect():
    logging.info('Dashboard client disconnected.')

# --- Serve React App ---
# This serves the main index.html for any route not caught by the API.
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')

if __name__ == '__main__':
    # Ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # Create the database and tables if they don't exist
    with app.app_context():
        db.create_all()

    emitter = threading.Thread(target=log_emitter_thread, args=(log_queue,), daemon=True)
    emitter.start()

    logging.info("Starting dashboard server on http://localhost:5000")
    socketio.run(app, host='0.0.0.0', port=5000)
