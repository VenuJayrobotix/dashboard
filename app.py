from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_socketio import SocketIO, emit
import os
import time





app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key")

#socketio = SocketIO(app, cors_allowed_origins="*")
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

USERS = {"admin": "password"}
client_last_seen = {}  # Dict to hold last ping time per client

class User(UserMixin):
    def __init__(self, username):
        self.id = username

@login_manager.user_loader
def load_user(user_id):
    if user_id in USERS:
        return User(user_id)
    return None

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if USERS.get(username) == password:
            login_user(User(username))
            return redirect(url_for("dashboard"))
        elif USERS.get(username) != password:
            return "Invalid credentials", 401
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

@app.route("/")
@login_required
def dashboard():
    now = time.time()
    # Build a list of clients with status
    clients = []
    for i in range(1, 501):
        cid = f"Client-{i:03d}"
        last = client_last_seen.get(cid, 0)
        online = (now - last) <= 30
        clients.append({
            "id": cid,
            "status": "🟢 Online" if online else "🔴 Offline",
            "last_seen_seconds_ago": int(now - last) if last else None
        })
    return render_template("dashboard.html", clients=clients)

@app.route("/ping", methods=["POST"])
def ping():
    data = request.get_json()
    client_id = data.get("client_id")
    if not client_id:
        return jsonify({"error": "Missing client_id"}), 400

    client_last_seen[client_id] = time.time()
    # Emit to dashboard clients
    socketio.emit("status_update", {"client_id": client_id, "status": "🟢 Online"})
    return jsonify({"status": "pong"})

@socketio.on("connect")
def on_connect():
    print("Dashboard connected")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port, allow_unsafe_werkzeug=True)
    #socketio.run(app)
