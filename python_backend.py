from pathlib import Path
import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS

DB_PATH = Path(__file__).with_name("emmanuel_tech.db")

app = Flask(__name__)
CORS(app)


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
                created_at TEXT NOT NULL
            )
            """
        )


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


if __name__ == "__main__":
    init_db()
    app.run(host="127.0.0.1", port=5000, debug=True)
