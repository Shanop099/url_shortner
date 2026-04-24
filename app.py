from flask import Flask, request, redirect, jsonify, render_template
import random, string
import qrcode
import io, base64
from urllib.parse import urlparse

app = Flask(__name__)

BASE_URL = "https://url-shortner-gtbu.onrender.com/"

# 🔥 In-memory store (stable)
url_db = {}
clicks_db = {}

# ---------------- UTILS ----------------
def generate_code(length=6):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def fix_url(url):
    if not url.startswith(("http://", "https://")):
        return "https://" + url
    return url

# ---------------- HOME ----------------
@app.route("/")
def index():
    return render_template("index.html")

# ---------------- SHORTEN ----------------
@app.route("/shorten", methods=["POST"])
def shorten():
    data = request.get_json()

    url = data.get("url")
    custom = data.get("custom")

    if not url:
        return jsonify({"error": "URL required"}), 400

    url = fix_url(url)

    if custom:
        if custom in url_db:
            return jsonify({"error": "Custom already exists"}), 400
        short_code = custom
    else:
        short_code = generate_code()
        while short_code in url_db:
            short_code = generate_code()

    url_db[short_code] = url
    clicks_db[short_code] = 0

    # QR code
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

    if short_code not in url_db:
        return "Not found", 404

    clicks_db[short_code] += 1

    return redirect(url_db[short_code])

# ---------------- STATS ----------------
@app.route("/stats/<short_code>")
def stats(short_code):

    if short_code not in url_db:
        return jsonify({"error": "Not found"}), 404

    return jsonify({
        "url": url_db[short_code],
        "clicks": clicks_db[short_code]
    })

if __name__ == "__main__":
    app.run(debug=True)