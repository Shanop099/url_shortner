from flask import Flask, request, redirect, jsonify, render_template
import random, string
import qrcode
import io, base64
import os
import redis

app = Flask(__name__)

BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:5000/")
REDIS_URL = os.getenv("REDIS_URL")

# ---------------- REDIS ----------------
try:
    r = redis.from_url(REDIS_URL, decode_responses=True)
    r.ping()
    print("✅ Redis connected")
except Exception as e:
    print("❌ Redis error:", e)
    r = None

# ---------------- CONFIG ----------------
RATE_LIMIT = 5
TIME_WINDOW = 60

# ---------------- UTILS ----------------
def generate_code(length=6):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def fix_url(url):
    if not url.startswith(("http://", "https://")):
        return "https://" + url
    return url

# ---------------- RATE LIMIT ----------------
def is_rate_limited(ip):
    if not r:
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

# ---------------- HOME ----------------
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

    # expiry = data.get("expiry")  # 🔴 Disabled for stability

    if not url:
        return jsonify({"error": "URL required"}), 400

    url = fix_url(url)

    # ----- generate / validate code -----
    if custom:
        short_code = custom
        if r and r.exists(f"url:{short_code}"):
            return jsonify({"error": "Custom already exists"}), 400
    else:
        short_code = generate_code()
        if r:
            while r.exists(f"url:{short_code}"):
                short_code = generate_code()

    # ----- EXPIRY LOGIC (COMMENTED FOR FUTURE USE) -----
    """
    try:
        ttl = int(expiry) * 60 if expiry and str(expiry).strip() != "" else None
    except:
        ttl = None
    """

    # ----- STORE -----
    try:
        if r:
            r.set(f"url:{short_code}", url)
            r.set(f"clicks:{short_code}", 0)
    except Exception as e:
        print("STORE ERROR:", e)
        return jsonify({"error": "Storage failed"}), 500

    # ----- QR -----
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

    if short_code in ["favicon.ico", "shorten", "stats"]:
        return "", 204

    try:
        if not r:
            return "Server not configured", 500

        url = r.get(f"url:{short_code}")

        if not url:
            return "Not found", 404

        r.incr(f"clicks:{short_code}")

        return redirect(url)

    except Exception as e:
        print("REDIRECT ERROR:", e)
        return "Server error", 500

# ---------------- STATS ----------------
@app.route("/stats/<short_code>")
def stats(short_code):

    try:
        if not r:
            return jsonify({"error": "Redis not available"}), 500

        url = r.get(f"url:{short_code}")

        if not url:
            return jsonify({"error": "Not found"}), 404

        clicks = int(r.get(f"clicks:{short_code}") or 0)

        return jsonify({
            "url": url,
            "clicks": clicks
        })

    except Exception as e:
        print("STATS ERROR:", e)
        return jsonify({"error": "Server error"}), 500


if __name__ == "__main__":
    app.run(debug=True)