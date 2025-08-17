import asyncio
import threading
import queue
from flask import Flask, jsonify, render_template
from flask_socketio import SocketIO, emit
from .arbitrage_bot import ArbitrageBot
from .models import init_db

app = Flask(__name__)
app.config["SECRET_KEY"] = "secret!"
socketio = SocketIO(app, async_mode="eventlet")

bot_thread = None
bot_instance = None
log_queue = queue.Queue()

def run_bot_in_background(bot, log_queue):
    """Runs the bot's async event loop in a separate thread."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    bot.set_log_queue(log_queue)

    loop.run_until_complete(bot.initialize())
    loop.run_until_complete(bot.run())
    loop.run_until_complete(bot.close_connections())
    loop.close()

    log_queue.put_nowait("Bot has shut down.")

@app.route("/")
def index():
    # For simplicity, we'll render a basic template.
    # In a real app, you would have a more complex frontend (e.g., using React).
    return "<h1>Arbitrage Bot Dashboard</h1><p>Connect with a WebSocket client to see logs.</p>"

@app.route("/api/start", methods=["POST"])
def start_bot():
    global bot_thread, bot_instance
    if bot_thread and bot_thread.is_alive():
        return jsonify({"status": "error", "message": "Bot is already running."}), 400

    bot_instance = ArbitrageBot()
    bot_thread = threading.Thread(target=run_bot_in_background, args=(bot_instance, log_queue))
    bot_thread.start()

    return jsonify({"status": "success", "message": "Bot started."})

@app.route("/api/stop", methods=["POST"])
def stop_bot():
    global bot_thread, bot_instance
    if not bot_thread or not bot_thread.is_alive() or not bot_instance:
        return jsonify({"status": "error", "message": "Bot is not running."}), 400

    bot_instance.stop()
    # bot_thread.join() # You might want to wait for the thread to finish

    return jsonify({"status": "success", "message": "Bot stopping..."})

@app.route("/api/status", methods=["GET"])
def bot_status():
    if bot_thread and bot_thread.is_alive():
        return jsonify({"status": "running"})
    return jsonify({"status": "stopped"})

@socketio.on('connect')
def handle_connect():
    emit('status', {'data': 'Connected to log stream.'})
    # Start a background task to send logs from the queue to the client
    socketio.start_background_task(target=log_streamer)

def log_streamer():
    while True:
        try:
            log_message = log_queue.get(timeout=1)
            socketio.emit('log', {'data': log_message})
        except queue.Empty:
            socketio.sleep(0.1) # Don't block the server if the queue is empty

if __name__ == '__main__':
    init_db()
    socketio.run(app, debug=True)
