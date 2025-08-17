import asyncio
import threading
import queue
from flask import Flask, jsonify, render_template_string, request, redirect, url_for, flash
from flask_socketio import SocketIO, emit
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from .arbitrage_bot import ArbitrageBot
from .models import init_db, User
from .database import get_db

app = Flask(__name__)
# In a real app, this key should be a long, random, secret value loaded from env
app.config["SECRET_KEY"] = "a-very-secret-key-that-should-be-changed"
socketio = SocketIO(app, async_mode="eventlet")

# --- Authentication Setup ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id):
    with get_db() as db:
        return db.query(User).get(int(user_id))

# --- Bot Management ---
bot_thread = None
bot_instance = None
log_queue = queue.Queue()

def run_bot_in_background():
    """Runs the bot's async event loop in a separate thread."""
    global bot_instance
    bot_instance = ArbitrageBot()
    bot_instance.set_log_queue(log_queue)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    loop.run_until_complete(bot_instance.run())
    loop.run_until_complete(bot_instance.market_data_handler.stop_subscriptions())
    loop.close()

    log_queue.put_nowait("Bot has shut down.")

# --- Routes ---

import io
import base64
import pyotp
import qrcode
from flask import session

@app.route("/")
@login_required
def index():
    # A simple dashboard page
    return render_template_string("""
        <h1>Arbitrage Bot Dashboard</h1>
        <p>Welcome, {{ current_user.username }}!</p>
        <p><a href="{{ url_for('setup_2fa') }}">Setup 2FA</a></p>
        <p>Bot status: <span id="status">checking...</span></p>
        <button onclick="startBot()">Start Bot</button>
        <button onclick="stopBot()">Stop Bot</button>
        <a href="{{ url_for('logout') }}">Logout</a>
        <h2>Logs</h2>
        <pre id="logs"></pre>
        <script src="https://cdn.socket.io/4.0.0/socket.io.min.js"></script>
        <script>
            var socket = io();
            socket.on('log', function(msg) {
                document.getElementById('logs').innerHTML += msg.data + '\\n';
            });
            function updateStatus() {
                fetch('/api/status').then(res => res.json()).then(data => {
                    document.getElementById('status').innerText = data.status;
                });
            }
            function startBot() { fetch('/api/start', {method: 'POST'}); }
            function stopBot() { fetch('/api/stop', {method: 'POST'}); }
            setInterval(updateStatus, 5000);
            updateStatus();
        </script>
    """)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        with get_db() as db:
            user = db.query(User).filter_by(username=username).first()
            if user and user.check_password(password):
                if user.otp_enabled:
                    # Store user ID in session and redirect to 2FA verification
                    session['user_id_2fa'] = user.id
                    return redirect(url_for('verify_2fa'))
                else:
                    login_user(user)
                    return redirect(url_for("index"))
            flash("Invalid username or password")
    return render_template_string("""
        <h2>Login</h2>
        <form method="post">
            Username: <input type="text" name="username"><br>
            Password: <input type="password" name="password"><br>
            <input type="submit" value="Login">
        </form>
        <p>Don't have an account? <a href="{{ url_for('register') }}">Register here</a>.</p>
    """)

@app.route('/2fa/setup', methods=['GET', 'POST'])
@login_required
def setup_2fa():
    if request.method == 'POST':
        # User is trying to verify and enable 2FA
        secret = current_user.otp_secret
        token = request.form.get('token')
        totp = pyotp.TOTP(secret)
        if totp.verify(token):
            with get_db() as db:
                user_to_update = db.query(User).get(current_user.id)
                user_to_update.otp_enabled = True
                db.commit()
            flash('2FA enabled successfully!')
            return redirect(url_for('index'))
        else:
            flash('Invalid token, please try again.')

    # Generate a new secret if the user doesn't have one
    if not current_user.otp_secret:
        with get_db() as db:
            user_to_update = db.query(User).get(current_user.id)
            user_to_update.otp_secret = pyotp.random_base32()
            db.commit()

    # Generate QR code
    otp_uri = pyotp.totp.TOTP(current_user.otp_secret).provisioning_uri(
        name=current_user.username, issuer_name='ArbitrageBot'
    )
    img = qrcode.make(otp_uri)
    buf = io.BytesIO()
    img.save(buf)
    buf.seek(0)
    qr_code_data = base64.b64encode(buf.read()).decode('ascii')

    return render_template_string('''
        <h2>Setup Two-Factor Authentication</h2>
        <p>Scan the QR code with your authenticator app (e.g., Google Authenticator).</p>
        <img src="data:image/png;base64,{{ qr_code_data }}">
        <p>Then, enter a code from the app to verify.</p>
        <form method="post">
            <input type="text" name="token" placeholder="6-digit code">
            <input type="submit" value="Verify and Enable">
        </form>
    ''', qr_code_data=qr_code_data)

@app.route('/2fa/verify', methods=['GET', 'POST'])
def verify_2fa():
    user_id = session.get('user_id_2fa')
    if not user_id:
        return redirect(url_for('login'))

    if request.method == 'POST':
        with get_db() as db:
            user = db.query(User).get(user_id)
            token = request.form.get('token')
            totp = pyotp.TOTP(user.otp_secret)
            if totp.verify(token):
                session.pop('user_id_2fa', None)
                login_user(user)
                return redirect(url_for('index'))
            else:
                flash('Invalid token.')

    return render_template_string('''
        <h2>Enter 2FA Code</h2>
        <form method="post">
            <input type="text" name="token" placeholder="6-digit code">
            <input type="submit" value="Verify">
        </form>
    ''')

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        with get_db() as db:
            if db.query(User).filter_by(username=username).first():
                flash("Username already exists")
            else:
                new_user = User(username=username)
                new_user.set_password(password)
                db.add(new_user)
                db.commit()
                flash("Registration successful! Please login.")
                return redirect(url_for("login"))
    return render_template_string("""
        <h2>Register</h2>
        <form method="post">
            Username: <input type="text" name="username"><br>
            Password: <input type="password" name="password"><br>
            <input type="submit" value="Register">
        </form>
    """)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

@app.route("/api/start", methods=["POST"])
@login_required
def start_bot():
    global bot_thread
    if bot_thread and bot_thread.is_alive():
        return jsonify({"status": "error", "message": "Bot is already running."}), 400

    bot_thread = threading.Thread(target=run_bot_in_background)
    bot_thread.start()
    return jsonify({"status": "success", "message": "Bot started."})

@app.route("/api/stop", methods=["POST"])
@login_required
def stop_bot():
    global bot_thread, bot_instance
    if not bot_thread or not bot_thread.is_alive() or not bot_instance:
        return jsonify({"status": "error", "message": "Bot is not running."}), 400

    bot_instance.stop()
    return jsonify({"status": "success", "message": "Bot stopping..."})

@app.route("/api/status", methods=["GET"])
@login_required
def bot_status():
    if bot_thread and bot_thread.is_alive():
        return jsonify({"status": "running"})
    return jsonify({"status": "stopped"})

@socketio.on('connect')
def handle_connect():
    if not current_user.is_authenticated:
        return False # Reject connection
    emit('status', {'data': 'Connected to log stream.'})
    socketio.start_background_task(target=log_streamer)

def log_streamer():
    while True:
        try:
            log_message = log_queue.get(timeout=1)
            socketio.emit('log', {'data': log_message})
        except queue.Empty:
            socketio.sleep(0.1)

if __name__ == '__main__':
    init_db()
    socketio.run(app, debug=True)
