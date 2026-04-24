from flask import Flask, request, redirect, jsonify, render_template
import random, string
import qrcode
import io, base64
import os
import redis

app = Flask(__name__)

BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:5000/")
REDIS_URL = os.getenv("REDIS_URL")

# -------- REDIS SAFE SETUP --------
try:
    if REDIS_URL:
        r = redis.from_url(REDIS_URL, decode_responses=True)
        r.ping()
        REDIS_AVAILABLE = True
        print("✅ Redis connected")
    else:
        REDIS_AVAILABLE = False
        print("❌ REDIS_URL not set")
except Exception as e:
    REDIS_AVAILABLE = False
    print("❌ Redis failed:", e)

# -------- FALLBACK MEMORY --------
url_db = {}
clicks_db = {}

# -------- CONFIG --------
RATE_LIMIT = 5
TIME_WINDOW = 60

# -------- UTILS --------
def generate_code(length=6):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def fix_url(url):
    if not url.startswith(("http://", "https://")):
        return "https://" + url
    return url

# -------- RATE LIMIT --------
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

# -------- HOME --------
@app.route("/")
def index():
    return render_template("index.html")

# -------- SHORTEN --------
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

    url = fix_url(url)

    # generate code
    if custom:
        short_code = custom
    else:
        short_code = generate_code()

    ttl = int(expiry) * 60 if expiry else None

    # -------- STORE --------
    if REDIS_AVAILABLE:
        try:
            if ttl:
                r.setex(f"url:{short_code}", ttl, url)
            else:
                r.set(f"url:{short_code}", url)

            r.set(f"clicks:{short_code}", 0)
        except:
            REDIS_AVAILABLE = False

    # fallback
    url_db[short_code] = url
    clicks_db[short_code] = 0

    # -------- QR --------
    qr = qrcode.make(BASE_URL + short_code)
    buffer = io.BytesIO()
    qr.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode()

    return jsonify({
        "short_url": BASE_URL + short_code,
        "qr": qr_base64
    })

# -------- REDIRECT --------
@app.route("/<short_code>")
def redirect_url(short_code):

    if short_code in ["favicon.ico", "shorten", "stats"]:
        return "", 204

    # Redis first
    if REDIS_AVAILABLE:
        try:
            url = r.get(f"url:{short_code}")
            if url:
                r.incr(f"clicks:{short_code}")
                return redirect(url)
        except:
            pass

    # fallback
    if short_code in url_db:
        clicks_db[short_code] += 1
        return redirect(url_db[short_code])

    return "Not found", 404

# -------- STATS --------
@app.route("/stats/<short_code>")
def stats(short_code):

    if REDIS_AVAILABLE:
        try:
            url = r.get(f"url:{short_code}")
            clicks = int(r.get(f"clicks:{short_code}") or 0)

            if url:
                return jsonify({"url": url, "clicks": clicks})
        except:
            pass

    if short_code in url_db:
        return jsonify({
            "url": url_db[short_code],
            "clicks": clicks_db[short_code]
        })

    return jsonify({"error": "Not found"}), 404


if __name__ == "__main__":
    app.run(debug=True)