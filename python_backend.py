from pathlib import Path
import csv
import os
import re
import sqlite3
import uuid
from datetime import datetime
from urllib.parse import quote
import requests
from flask import Flask, request, jsonify, redirect, session, send_file
from flask_cors import CORS
from flask_mail import Mail, Message
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from io import BytesIO, StringIO
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "emmanuel_tech.db"

app = Flask(__name__, static_folder=str(BASE_DIR), static_url_path="")
app.secret_key = os.getenv("SECRET_KEY", "change-this-secret-key")
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

CORS(app)

# Email Configuration
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com').strip()
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', '587').strip())
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True').strip().lower() in {'1', 'true', 'yes', 'on'}
app.config['MAIL_USE_SSL'] = os.getenv('MAIL_USE_SSL', 'False').strip().lower() in {'1', 'true', 'yes', 'on'}
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME', 'your-email@gmail.com').strip()
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD', 'your-app-password').strip().replace(' ', '')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER', app.config['MAIL_USERNAME']).strip()

mail = Mail(app)

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"


def get_confirmation_channel(contact, preferred_channel=""):
    normalized = (preferred_channel or "").strip().lower()
    if normalized in {"email", "whatsapp"}:
        return normalized
    if '@' in str(contact or ""):
        return "email"
    if re.search(r"\d", str(contact or "")):
        return "whatsapp"
    return "email"


def build_confirmation_link(contact, booking, preferred_channel=""):
    channel = get_confirmation_channel(contact, preferred_channel)
    booking_name = (booking or {}).get("name") or "there"
    ticket_code = (booking or {}).get("ticket_code") or "your booking"
    service = (booking or {}).get("service") or "service"
    service_datetime = (booking or {}).get("service_datetime") or "your scheduled time"
    description = (booking or {}).get("description") or "your request"
    message = (
        f"Hello {booking_name}! Your booking {ticket_code} for {service} on {service_datetime} "
        f"is confirmed. Description: {description}. Thank you for choosing Emmanuel Tech ICT Solutions."
    )

    if channel == "whatsapp":
        digits = re.sub(r"\D", "", str(contact or ""))
        if digits.startswith("0"):
            digits = "254" + digits[1:]
        if not digits:
            digits = "254716205974"
        return f"https://wa.me/{digits}?text={quote(message)}"

    email_address = str(contact or "").strip()
    if not email_address or '@' not in email_address:
        email_address = "emmanueltechictsolutions@gmail.com"
    return f"mailto:{email_address}?subject={quote(f'Booking confirmed - {ticket_code}')}&body={quote(message)}"


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
                ticket_code TEXT,
                price TEXT,
                service_datetime TEXT,
                problems_found TEXT DEFAULT '',
                solutions TEXT DEFAULT '',
                recommendations TEXT DEFAULT '',
                amount_paid TEXT DEFAULT '',
                paid_at TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'new',
                notes TEXT DEFAULT ''
            )
            """
        )
        columns = [row[1] for row in conn.execute("PRAGMA table_info(bookings)").fetchall()]
        if 'name' not in columns:
            conn.execute("ALTER TABLE bookings ADD COLUMN name TEXT DEFAULT ''")
        if 'ticket_code' not in columns:
            conn.execute("ALTER TABLE bookings ADD COLUMN ticket_code TEXT DEFAULT ''")
        if 'price' not in columns:
            conn.execute("ALTER TABLE bookings ADD COLUMN price TEXT DEFAULT ''")
        if 'service_datetime' not in columns:
            conn.execute("ALTER TABLE bookings ADD COLUMN service_datetime TEXT DEFAULT ''")
        if 'problems_found' not in columns:
            conn.execute("ALTER TABLE bookings ADD COLUMN problems_found TEXT DEFAULT ''")
        if 'solutions' not in columns:
            conn.execute("ALTER TABLE bookings ADD COLUMN solutions TEXT DEFAULT ''")
        if 'recommendations' not in columns:
            conn.execute("ALTER TABLE bookings ADD COLUMN recommendations TEXT DEFAULT ''")
        if 'amount_paid' not in columns:
            conn.execute("ALTER TABLE bookings ADD COLUMN amount_paid TEXT DEFAULT ''")
        if 'paid_at' not in columns:
            conn.execute("ALTER TABLE bookings ADD COLUMN paid_at TEXT DEFAULT ''")
        if 'status' not in columns:
            conn.execute("ALTER TABLE bookings ADD COLUMN status TEXT NOT NULL DEFAULT 'new'")
        if 'notes' not in columns:
            conn.execute("ALTER TABLE bookings ADD COLUMN notes TEXT DEFAULT ''")


def generate_ticket_code():
    return f"TKT-{datetime.utcnow():%Y%m%d%H%M%S}-{uuid.uuid4().hex[:6].upper()}"


def get_chatbot_fallback_reply(message):
    text = (message or "").strip().lower()
    if any(keyword in text for keyword in ["hi", "hello", "hey", "greetings", "good morning", "good afternoon", "good evening"]):
        return "Hello! I'm E-Tech, your friendly support assistant for Emmanuel Tech ICT Solutions. How can I help you today?"
    if any(keyword in text for keyword in ["book", "booking", "appointment"]):
        return "You can book a service by filling out the booking form on the site. Choose a service, add your details, and submit it."
    if any(keyword in text for keyword in ["service", "services", "repair", "design", "consult"]):
        return "We offer ICT consulting, computer and printer repairs, graphics design, and e-cyber services."
    if any(keyword in text for keyword in ["contact", "phone", "email", "reach"]):
        return "You can reach us at emmanueltechictsolutions@gmail.com or call 0716205974."
    if any(keyword in text for keyword in ["price", "cost", "quote", "pricing"]):
        return "Pricing depends on the service and issue. Please use the booking form and we will provide a quote."
    return "I can help with booking, services, pricing, and contact information. What would you like to know about Emmanuel Tech ICT Solutions?"


def normalize_phone_number(phone):
    digits = re.sub(r"\D", "", str(phone or ""))
    if not digits:
        return ""
    if digits.startswith("0"):
        digits = "254" + digits[1:]
    elif digits.startswith("254"):
        digits = digits
    elif len(digits) == 9:
        digits = "254" + digits
    return digits


def build_mpesa_password(shortcode, passkey):
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    encoded = f"{shortcode}{passkey}{timestamp}".encode("utf-8")
    import base64
    return base64.b64encode(encoded).decode("utf-8")


def get_mpesa_access_token():
    access_token = (os.getenv("MPESA_ACCESS_TOKEN") or "").strip()
    if access_token:
        return access_token

    consumer_key = (os.getenv("MPESA_CONSUMER_KEY") or "").strip()
    consumer_secret = (os.getenv("MPESA_CONSUMER_SECRET") or "").strip()
    if not consumer_key or not consumer_secret:
        return ""

    auth = requests.auth._basic_auth_str(consumer_key, consumer_secret)
    response = requests.get(
        "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials",
        headers={"Authorization": auth},
        timeout=20,
    )
    response.raise_for_status()
    return response.json().get("access_token", "")


def build_mpesa_stk_payload(phone, amount, account_reference):
    normalized_phone = normalize_phone_number(phone)
    shortcode = (os.getenv("MPESA_SHORTCODE") or "174379").strip()
    passkey = (os.getenv("MPESA_PASSKEY") or "").strip()
    password = (os.getenv("MPESA_PASSWORD") or "").strip()
    if not password and shortcode and passkey:
        password = build_mpesa_password(shortcode, passkey)
    return {
        "BusinessShortCode": shortcode,
        "Password": password,
        "Timestamp": datetime.utcnow().strftime("%Y%m%d%H%M%S"),
        "TransactionType": "CustomerPayBillOnline",
        "Amount": int(amount),
        "PartyA": normalized_phone,
        "PartyB": shortcode,
        "PhoneNumber": normalized_phone,
        "CallBackURL": os.getenv("MPESA_CALLBACK_URL", ""),
        "AccountReference": str(account_reference or "EMMANUEL TECH"),
        "TransactionDesc": "Service payment"
    }


def get_chatbot_ai_reply(message, api_key, model="gpt-4o-mini"):
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are E-Tech, a helpful support assistant for Emmanuel Tech ICT Solutions. Keep answers concise, friendly, and practical."},
            {"role": "user", "content": message},
        ],
        "temperature": 0.3,
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    response = requests.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers, timeout=12)
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"].strip()
    return content or None


@app.route("/chatbot", methods=["POST"])
def chatbot():
    data = request.get_json() or {}
    message = (data.get("message") or "").strip()
    if not message:
        return jsonify({"reply": "Please type a message so I can help you."}), 400

    reply = get_chatbot_fallback_reply(message)

    api_key = (os.getenv("OPENAI_API_KEY") or os.getenv("GEMINI_API_KEY") or "").strip()
    if api_key:
        try:
            model = (os.getenv("CHATBOT_MODEL") or "gpt-4o-mini").strip() or "gpt-4o-mini"
            ai_reply = get_chatbot_ai_reply(message, api_key, model=model)
            if ai_reply:
                reply = ai_reply
        except Exception as exc:
            print(f"AI chatbot fallback error: {exc}")

    return jsonify({"reply": reply})


@app.route("/book", methods=["POST"])
def book():
    data = request.get_json() or {}
    contact = (data.get("contact") or "").strip()
    name = (data.get("name") or "").strip()
    service = (data.get("service") or "").strip()
    description = (data.get("description") or "").strip()
    service_datetime = (data.get("service_datetime") or "").strip()
    preferred_channel = (data.get("preferred_channel") or "").strip().lower()

    if not contact or not name or not service or not description or not service_datetime:
        return jsonify({"error": "name, contact, service, description, and service date/time are required"}), 400

    ticket_code = generate_ticket_code()
    created_at = datetime.utcnow().isoformat()
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO bookings (name, contact, service, description, ticket_code, service_datetime, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (name, contact, service, description, ticket_code, service_datetime, created_at),
        )
        booking_id = cursor.lastrowid

    booking_data = {
        'id': booking_id,
        'name': name,
        'contact': contact,
        'service': service,
        'description': description,
        'ticket_code': ticket_code,
        'service_datetime': service_datetime,
        'created_at': created_at
    }

    confirmation = send_booking_confirmation(booking_data, preferred_channel)

    return jsonify({
        "message": "Booking saved successfully",
        "ticket_code": ticket_code,
        "service_datetime": service_datetime,
        "service": service,
        "description": description,
        "contact": contact,
        "name": name,
        "email_sent": confirmation.get("channel") == "email" and confirmation.get("sent", False),
        "confirmation": confirmation,
    }), 201


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

@app.route("/admin/report", methods=["GET"])
def admin_report_page():
    if not session.get("admin_logged_in"):
        return redirect("/admin/login")
    return app.send_static_file("admin_report.html")

@app.route("/admin/bookings", methods=["GET"])
def admin_bookings():
    if not session.get("admin_logged_in"):
        return jsonify({"error": "Unauthorized"}), 401

    with get_db() as conn:
        rows = conn.execute("SELECT * FROM bookings ORDER BY created_at DESC").fetchall()
        return jsonify([dict(row) for row in rows])

@app.route("/admin/bookings/export", methods=["GET"])
def admin_export_bookings():
    if not session.get("admin_logged_in"):
        return jsonify({"error": "Unauthorized"}), 401

    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, name, contact, service, description, ticket_code, price, service_datetime, amount_paid, paid_at, created_at, status, notes FROM bookings ORDER BY created_at DESC"
        ).fetchall()

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id",
        "name",
        "contact",
        "service",
        "description",
        "ticket_code",
        "price",
        "service_datetime",
        "amount_paid",
        "paid_at",
        "created_at",
        "status",
        "notes",
    ])

    for row in rows:
        writer.writerow([row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9], row[10], row[11], row[12]])

    csv_bytes = output.getvalue().encode("utf-8")
    return send_file(
        BytesIO(csv_bytes),
        mimetype="text/csv",
        as_attachment=True,
        download_name="bookings.csv",
    )

@app.route("/admin/bookings/<int:booking_id>", methods=["GET"])
def admin_get_booking(booking_id):
    if not session.get("admin_logged_in"):
        return jsonify({"error": "Unauthorized"}), 401

    with get_db() as conn:
        row = conn.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,)).fetchone()
        if row is None:
            return jsonify({"error": "Booking not found"}), 404
        return jsonify(dict(row))

@app.route("/admin/bookings/<int:booking_id>", methods=["PATCH"])
def admin_update_booking(booking_id):
    if not session.get("admin_logged_in"):
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json() or {}
    allowed = ['contact', 'service', 'description', 'status', 'notes', 'price', 'service_datetime', 'amount_paid', 'problems_found', 'solutions', 'recommendations']
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

@app.route("/admin/bookings/<int:booking_id>/report", methods=["POST"])
def admin_save_report(booking_id):
    if not session.get("admin_logged_in"):
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json() or {}
    allowed = ['problems_found', 'solutions', 'recommendations', 'price', 'service_datetime', 'notes']
    fields = {k: v for k, v in data.items() if k in allowed}

    if not fields:
        return jsonify({"error": "No valid report fields to save"}), 400

    keys = []
    params = []
    for key, value in fields.items():
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

        row = conn.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,)).fetchone()
        return jsonify(dict(row))

@app.route("/admin/bookings/<int:booking_id>/payment-request", methods=["POST"])
def admin_request_payment(booking_id):
    if not session.get("admin_logged_in"):
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json() or {}
    phone = (data.get("phone") or "").strip()
    amount = (data.get("amount") or "").strip()
    if not phone or not amount:
        return jsonify({"error": "phone and amount are required"}), 400

    with get_db() as conn:
        booking = conn.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,)).fetchone()
        if booking is None:
            return jsonify({"error": "Booking not found"}), 404

    normalized_phone = normalize_phone_number(phone)
    if not normalized_phone:
        return jsonify({"error": "Phone number is invalid"}), 400

    account_reference = (booking["ticket_code"] or f"BOOKING-{booking['id']}") if booking else f"BOOKING-{booking_id}"
    payload = build_mpesa_stk_payload(normalized_phone, amount, account_reference)
    auth_token = get_mpesa_access_token()
    if not auth_token:
        return jsonify({"error": "M-Pesa credentials are not configured", "phone": normalized_phone, "amount": amount}), 503

    try:
        response = requests.post(
            os.getenv("MPESA_STK_PUSH_URL", "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"),
            json=payload,
            headers={
                "Authorization": f"Bearer {auth_token}",
                "Content-Type": "application/json",
            },
            timeout=20,
        )
        response.raise_for_status()
        result = response.json()
    except Exception as exc:
        return jsonify({"error": "M-Pesa request failed", "details": str(exc), "phone": normalized_phone, "amount": amount}), 502

    return jsonify({"success": True, "phone": normalized_phone, "amount": amount, "mpesa_response": result})


@app.route("/admin/bookings/<int:booking_id>/payment", methods=["POST"])
def admin_record_payment(booking_id):
    if not session.get("admin_logged_in"):
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json() or {}
    amount_paid = (data.get('amount_paid') or '').strip()
    price = (data.get('price') or '').strip()
    if not amount_paid:
        return jsonify({"error": "amount_paid is required"}), 400

    paid_at = datetime.utcnow().isoformat()
    sql = "UPDATE bookings SET amount_paid = ?, paid_at = ?, status = 'done'"
    params = [amount_paid, paid_at]
    if price:
        sql += ", price = ?"
        params.append(price)
    sql += " WHERE id = ?"
    params.append(booking_id)

    with get_db() as conn:
        cursor = conn.execute(sql, params)
        if cursor.rowcount == 0:
            return jsonify({"error": "Booking not found"}), 404
        row = conn.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,)).fetchone()
        return jsonify(dict(row))

@app.route("/admin/bookings/<int:booking_id>", methods=["DELETE"])
def admin_delete_booking(booking_id):
    if not session.get("admin_logged_in"):
        return jsonify({"error": "Unauthorized"}), 401

    with get_db() as conn:
        cursor = conn.execute("DELETE FROM bookings WHERE id = ?", (booking_id,))
        if cursor.rowcount == 0:
            return jsonify({"error": "Booking not found"}), 404

    return jsonify({"success": True})

def generate_ticket_pdf(booking_or_id):
    """Generate a PDF ticket for a booking from either an ID or a booking dictionary."""
    booking = None

    if isinstance(booking_or_id, dict):
        booking = dict(booking_or_id)
    else:
        with get_db() as conn:
            row = conn.execute("SELECT * FROM bookings WHERE id = ?", (booking_or_id,)).fetchone()
            if row:
                booking = dict(row)

    if not booking:
        return None

    # Create PDF in memory
    pdf_buffer = BytesIO()
    doc = SimpleDocTemplate(pdf_buffer, pagesize=letter, rightMargin=0.5*inch, leftMargin=0.5*inch,
                            topMargin=0.5*inch, bottomMargin=0.5*inch)
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#0a3d62'),
        spaceAfter=6,
        alignment=1  # center
    )
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=colors.HexColor('#0a3d62'),
        spaceAfter=12,
    )
    
    # Build PDF content
    elements = []
    elements.append(Paragraph("EMMANUEL TECH ICT SOLUTIONS", title_style))
    elements.append(Spacer(1, 0.2*inch))
    elements.append(Paragraph("Service Booking Ticket", heading_style))
    elements.append(Spacer(1, 0.1*inch))
    
    created_at = booking.get('created_at') or datetime.utcnow().isoformat()
    try:
        issued_date = datetime.fromisoformat(created_at).strftime('%B %d, %Y at %I:%M %p')
    except Exception:
        issued_date = str(created_at)

    # Ticket details table
    ticket_data = [
        ["Ticket Number:", booking.get('ticket_code', '')],
        ["Customer Name:", booking.get('name', '')],
        ["Contact:", booking.get('contact', '')],
        ["Service:", booking.get('service', '')],
        ["Service Date & Time:", booking.get('service_datetime', '')],
        ["Issue Description:", booking.get('description', '')],
        ["Issued Date:", issued_date],
        ["Status:", (booking.get('status') or 'pending').upper()],
    ]
    
    table = Table(ticket_data, colWidths=[2*inch, 4*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
    ]))
    
    elements.append(table)
    elements.append(Spacer(1, 0.2*inch))
    elements.append(Paragraph(
        "<b>Important:</b> Please keep this ticket for your reference during service. "
        "Contact us with your ticket number for any inquiries.",
        styles['Normal']
    ))
    elements.append(Spacer(1, 0.1*inch))
    elements.append(Paragraph(
        "<b>Contact Information:</b><br/>Email: emmanueltechictsolutions@gmail.com<br/>Phone: 0716205974",
        styles['Normal']
    ))
    
    doc.build(elements)
    pdf_buffer.seek(0)
    return pdf_buffer

def send_booking_confirmation(booking_data, preferred_channel=""):
    """Send a confirmation response by email or prepare a WhatsApp link."""
    contact = (booking_data.get("contact") or "").strip()
    channel = get_confirmation_channel(contact, preferred_channel)

    if channel == "email" and '@' in contact:
        try:
            return {"channel": "email", "sent": send_booking_confirmation_email(booking_data), "link": None}
        except Exception as e:
            print(f"Email sending failed but booking was successful: {str(e)}")
            return {"channel": "email", "sent": False, "link": None}

    if channel == "whatsapp":
        return {"channel": "whatsapp", "sent": False, "link": build_confirmation_link(contact, booking_data, "whatsapp")}

    return {"channel": "email", "sent": False, "link": None}


def send_booking_confirmation_email(booking_data):
    """Send booking confirmation email with PDF ticket attachment"""
    try:
        print(f"Attempting to send email to: {booking_data['contact']}")

        # Generate PDF ticket
        pdf_buffer = generate_ticket_pdf(booking_data)
        if not pdf_buffer:
            print("Failed to generate PDF for email")
            return False

        with app.app_context():
            # Create email message
            msg = Message(
                subject=f"Service Booking Confirmation - {booking_data['ticket_code']}",
                recipients=[booking_data['contact']] if '@' in booking_data['contact'] else []
            )

            print(f"Email recipients: {msg.recipients}")

            if not msg.recipients:
                print("No valid email recipients found")
                return False

            # Email body
            email_body = f"""
Dear {booking_data['name']},

Thank you for choosing Emmanuel Tech ICT Solutions!

Your service booking has been successfully confirmed and is now in progress.

Booking Details:
- Ticket Number: {booking_data['ticket_code']}
- Service: {booking_data['service']}
- Scheduled Date & Time: {booking_data['service_datetime']}
- Issue Description: {booking_data['description']}

Your service is currently being processed. Our team will contact you shortly to arrange the service visit.

Please keep this ticket number ({booking_data['ticket_code']}) for your reference during the service.

If you have any questions or need to reschedule, please contact us:
- Email: emmanueltechictsolutions@gmail.com
- Phone: 0716205974

The ticket receipt is attached to this email for your records.

Best regards,
Emmanuel Tech ICT Solutions Team
"""

            msg.body = email_body

            # Attach PDF
            pdf_buffer.seek(0)
            msg.attach(
                filename=f"{booking_data['ticket_code']}.pdf",
                content_type="application/pdf",
                data=pdf_buffer.getvalue()
            )

            # Send email
            print("Sending email...")
            mail.send(msg)
            print(f"Booking confirmation email sent to {booking_data['contact']}")
            return True

    except Exception as e:
        print(f"Failed to send booking confirmation email: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

@app.route("/ticket/<ticket_code>/download", methods=["GET"])
def download_ticket(ticket_code):
    """Download ticket as PDF"""
    with get_db() as conn:
        booking = conn.execute("SELECT id FROM bookings WHERE ticket_code = ?", (ticket_code,)).fetchone()
        if not booking:
            return jsonify({"error": "Ticket not found"}), 404
    
    pdf_buffer = generate_ticket_pdf(booking['id'])
    if not pdf_buffer:
        return jsonify({"error": "Could not generate ticket"}), 500
    
    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f"{ticket_code}.pdf"
    )

@app.route("/")
def index():
    return app.send_static_file("index.html")

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5001)), debug=False)
