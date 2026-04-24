from flask import Flask, request, redirect, jsonify, render_template
from database import init_db, get_connection
from utils import generate_code, is_expired
from datetime import datetime, timedelta
import os
import redis
import qrcode
import io
import base64
import re

app = Flask(__name__)

# ---------------- CONFIG ----------------
BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:5000/")
redis_url = os.getenv("REDIS_URL", "")

# Redis setup
try:
    r = redis.from_url(redis_url, decode_responses=True)
    r.ping()
    REDIS_AVAILABLE = True
    print("✅ Redis connected")
except:
    REDIS_AVAILABLE = False
    print("⚠️ Redis not available")

# Init DB
init_db()

RATE_LIMIT = 5
TIME_WINDOW = 60

# ---------------- RATE LIMIT ----------------
def is_rate_limited(ip):
    if not REDIS_AVAILABLE:
        return False

    key = f"rate:{ip}"
    try:
        if r.exists(key):
            if int(r.get(key)) >= RATE_LIMIT:
                return True
            r.incr(key)
        else:
            r.set(key, 1, ex=TIME_WINDOW)
    except:
        return False

    return False

# ---------------- FIX favicon ----------------
@app.route("/favicon.ico")
def favicon():
    return "", 204

# ---------------- UI ----------------
@app.route("/")
def index():
    return render_template("index.html")

# ---------------- SHORTEN ----------------
@app.route("/shorten", methods=["POST"])
def shorten():
    ip = request.remote_addr

    if is_rate_limited(ip):
        return jsonify({"error": "Rate limit exceeded"}), 429

    data = request.get_json()
    url = data.get("url")
    custom = data.get("custom")
    expiry = data.get("expiry")

    if not url:
        return jsonify({"error": "URL required"}), 400

    if custom:
        custom = custom.strip()
        if custom == "":
            custom = None

    if custom:
        if not re.match("^[a-zA-Z0-9_-]+$", custom):
            return jsonify({"error": "Invalid custom code"}), 400

    conn = get_connection()
    cursor = conn.cursor()

    if custom:
        cursor.execute("SELECT 1 FROM urls WHERE short_code=?", (custom,))
        if cursor.fetchone():
            return jsonify({"error": "Custom already exists"}), 400
        short_code = custom
    else:
        short_code = generate_code()
        while True:
            cursor.execute("SELECT 1 FROM urls WHERE short_code=?", (short_code,))
            if not cursor.fetchone():
                break
            short_code = generate_code()

    expiry_time = None
    if expiry:
        expiry_time = (datetime.utcnow() + timedelta(minutes=int(expiry))).isoformat()

    cursor.execute("""
        INSERT INTO urls (short_code, original_url, expiry)
        VALUES (?, ?, ?)
    """, (short_code, url, expiry_time))

    conn.commit()
    conn.close()

    # Cache
    if REDIS_AVAILABLE:
        try:
            r.set(short_code, url)
        except:
            pass

    # QR Code
    qr = qrcode.make(BASE_URL + short_code)
    buffer = io.BytesIO()
    qr.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode()

    return jsonify({
        "short_url": BASE_URL + short_code,
        "qr": qr_base64
    })

# ---------------- REDIRECT ----------------
@app.route("/<short_code>")
def redirect_url(short_code):

    # ignore invalid paths
    if short_code in ["favicon.ico", "shorten", "stats"]:
        return "", 204

    try:
        # Redis first
        if REDIS_AVAILABLE:
            try:
                cached = r.get(short_code)
                if cached:
                    r.incr(f"clicks:{short_code}")
                    return redirect(cached)
            except:
                pass

        # DB fallback
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT original_url, clicks, expiry FROM urls WHERE short_code=?", (short_code,))
        result = cursor.fetchone()

        if not result:
            return "Not found", 404

        url, clicks, expiry = result

        if expiry and is_expired(expiry):
            return "Expired", 410

        cursor.execute("UPDATE urls SET clicks=? WHERE short_code=?", (clicks+1, short_code))
        conn.commit()
        conn.close()

        # Cache again
        if REDIS_AVAILABLE:
            try:
                r.set(short_code, url)
            except:
                pass

        return redirect(url)

    except Exception as e:
        print("🔥 ERROR:", e)
        return "Internal error", 500

# ---------------- STATS ----------------
@app.route("/stats/<short_code>")
def stats(short_code):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT original_url, clicks FROM urls WHERE short_code=?", (short_code,))
    result = cursor.fetchone()
    conn.close()

    if not result:
        return jsonify({"error": "Not found"}), 404

    redis_clicks = 0
    if REDIS_AVAILABLE:
        try:
            redis_clicks = int(r.get(f"clicks:{short_code}") or 0)
        except:
            redis_clicks = 0

    return jsonify({
        "url": result[0],
        "db_clicks": result[1],
        "redis_clicks": redis_clicks
    })

if __name__ == "__main__":
    app.run(debug=True)