from flask import Flask, request, redirect, jsonify, render_template
import random, string
import qrcode
import io, base64
import os
import redis

app = Flask(__name__)

BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:5000/")
REDIS_URL = os.getenv("REDIS_URL")

r = redis.from_url(REDIS_URL, decode_responses=True)

RATE_LIMIT = 5
TIME_WINDOW = 60  # seconds

# ----------- UTILS -----------
def generate_code(length=6):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def fix_url(url):
    if not url.startswith(("http://", "https://")):
        return "https://" + url
    return url

# ----------- RATE LIMIT -----------
def is_rate_limited(ip):
    key = f"rate:{ip}"

    if r.exists(key):
        if int(r.get(key)) >= RATE_LIMIT:
            return True
        r.incr(key)
    else:
        r.set(key, 1, ex=TIME_WINDOW)

    return False

# ----------- HOME -----------
@app.route("/")
def index():
    return render_template("index.html")

# ----------- SHORTEN -----------
@app.route("/shorten", methods=["POST"])
def shorten():
    ip = request.remote_addr

    if is_rate_limited(ip):
        return jsonify({"error": "Rate limit exceeded"}), 429

    data = request.get_json()
    url = data.get("url")
    custom = data.get("custom")
    expiry = data.get("expiry")  # minutes

    if not url:
        return jsonify({"error": "URL required"}), 400

    url = fix_url(url)

    # generate code
    if custom:
        short_code = custom
        if r.exists(f"url:{short_code}"):
            return jsonify({"error": "Custom already exists"}), 400
    else:
        short_code = generate_code()
        while r.exists(f"url:{short_code}"):
            short_code = generate_code()

    ttl = int(expiry) * 60 if expiry else None

    if ttl:
        r.setex(f"url:{short_code}", ttl, url)
    else:
        r.set(f"url:{short_code}", url)

    r.set(f"clicks:{short_code}", 0)

    # QR code
    qr = qrcode.make(BASE_URL + short_code)
    buffer = io.BytesIO()
    qr.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode()

    return jsonify({
        "short_url": BASE_URL + short_code,
        "qr": qr_base64
    })

# ----------- REDIRECT -----------
@app.route("/<short_code>")
def redirect_url(short_code):

    if short_code in ["favicon.ico", "shorten", "stats"]:
        return "", 204

    url = r.get(f"url:{short_code}")

    if not url:
        return "Not found or expired", 404

    r.incr(f"clicks:{short_code}")

    return redirect(url)

# ----------- STATS -----------
@app.route("/stats/<short_code>")
def stats(short_code):

    url = r.get(f"url:{short_code}")

    if not url:
        return jsonify({"error": "Not found"}), 404

    clicks = int(r.get(f"clicks:{short_code}") or 0)

    return jsonify({
        "url": url,
        "clicks": clicks
    })

if __name__ == "__main__":
    app.run(debug=True)