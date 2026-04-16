from pathlib import Path
import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify, redirect, session
from flask_cors import CORS

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "emmanuel_tech.db"

app = Flask(__name__, static_folder=str(BASE_DIR), static_url_path="")
app.secret_key = "change-this-secret-key"
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
CORS(app)

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contact TEXT NOT NULL,
                service TEXT,
                description TEXT NOT NULL,
                created_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'new',
                notes TEXT DEFAULT ''
            )
            """
        )
        columns = [row[1] for row in conn.execute("PRAGMA table_info(bookings)").fetchall()]
        if 'status' not in columns:
            conn.execute("ALTER TABLE bookings ADD COLUMN status TEXT NOT NULL DEFAULT 'new'")
        if 'notes' not in columns:
            conn.execute("ALTER TABLE bookings ADD COLUMN notes TEXT DEFAULT ''")


@app.route("/book", methods=["POST"])
def book():
    data = request.get_json() or {}
    contact = (data.get("contact") or "").strip()
    service = (data.get("service") or "").strip()
    description = (data.get("description") or "").strip()

    if not contact or not description:
        return jsonify({"error": "contact and description are required"}), 400

    created_at = datetime.utcnow().isoformat()
    with get_db() as conn:
        conn.execute(
            "INSERT INTO bookings (contact, service, description, created_at) VALUES (?, ?, ?, ?)",
            (contact, service, description, created_at),
        )

    return jsonify({"message": "Booking saved successfully"}), 201


@app.route("/bookings", methods=["GET"])
def bookings():
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM bookings ORDER BY created_at DESC").fetchall()
        return jsonify([dict(row) for row in rows])

@app.route("/admin")
def admin_root():
    return redirect("/admin/login")

@app.route("/admin/login", methods=["GET"])
def admin_login_page():
    return app.send_static_file("admin_login.html")

@app.route("/admin/login", methods=["POST"])
def admin_login():
    data = request.get_json() or {}
    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()

    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        session["admin_logged_in"] = True
        return jsonify({"success": True})

    return jsonify({"success": False, "message": "Invalid username or password"}), 401

@app.route("/admin/logout", methods=["POST"])
def admin_logout():
    session.pop("admin_logged_in", None)
    return jsonify({"success": True})

@app.route("/admin/dashboard", methods=["GET"])
def admin_dashboard_page():
    if not session.get("admin_logged_in"):
        return redirect("/admin/login")
    return app.send_static_file("admin_dashboard.html")

@app.route("/admin/bookings", methods=["GET"])
def admin_bookings():
    if not session.get("admin_logged_in"):
        return jsonify({"error": "Unauthorized"}), 401

    with get_db() as conn:
        rows = conn.execute("SELECT * FROM bookings ORDER BY created_at DESC").fetchall()
        return jsonify([dict(row) for row in rows])

@app.route("/admin/bookings/<int:booking_id>", methods=["PATCH"])
def admin_update_booking(booking_id):
    if not session.get("admin_logged_in"):
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json() or {}
    allowed = ['contact', 'service', 'description', 'status', 'notes']
    fields = {k: v for k, v in data.items() if k in allowed}

    if not fields:
        return jsonify({"error": "No valid fields to update"}), 400

    keys = []
    params = []
    for key, value in fields.items():
        if key == 'contact' and not str(value).strip():
            return jsonify({"error": "contact cannot be empty"}), 400
        if key == 'description' and not str(value).strip():
            return jsonify({"error": "description cannot be empty"}), 400
        keys.append(f"{key} = ?")
        params.append(str(value).strip())

    params.append(booking_id)
    with get_db() as conn:
        cursor = conn.execute(
            f"UPDATE bookings SET {', '.join(keys)} WHERE id = ?",
            params,
        )
        if cursor.rowcount == 0:
            return jsonify({"error": "Booking not found"}), 404

    return jsonify({"success": True})

@app.route("/admin/bookings/<int:booking_id>", methods=["DELETE"])
def admin_delete_booking(booking_id):
    if not session.get("admin_logged_in"):
        return jsonify({"error": "Unauthorized"}), 401

    with get_db() as conn:
        cursor = conn.execute("DELETE FROM bookings WHERE id = ?", (booking_id,))
        if cursor.rowcount == 0:
            return jsonify({"error": "Booking not found"}), 404

    return jsonify({"success": True})

@app.route("/")
def index():
    return app.send_static_file("index.html")

if __name__ == "__main__":
    init_db()
    app.run(host="127.0.0.1", port=5001, debug=True)
