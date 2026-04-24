from flask import Flask, request, redirect, jsonify, render_template
from database import init_db, get_connection
from utils import generate_code
import os

app = Flask(__name__)

BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:5000/")

init_db()

# ---------------- FIX URL ----------------
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

    cursor.execute(
        "INSERT INTO urls (short_code, original_url) VALUES (?, ?)",
        (short_code, url)
    )

    conn.commit()
    conn.close()

    return jsonify({
        "short_url": BASE_URL + short_code
    })

# ---------------- REDIRECT ----------------
@app.route("/<short_code>")
def redirect_url(short_code):

    if short_code in ["favicon.ico", "shorten", "stats"]:
        return "", 204

    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT original_url, clicks FROM urls WHERE short_code=?",
            (short_code,)
        )

        result = cursor.fetchone()

        if not result:
            return "Not found", 404

        url, clicks = result

        cursor.execute(
            "UPDATE urls SET clicks=? WHERE short_code=?",
            (clicks + 1, short_code)
        )
        conn.commit()

        return redirect(url)

    except Exception as e:
        return f"ERROR: {str(e)}", 500

    finally:
        if conn:
            conn.close()

# ---------------- STATS ----------------
@app.route("/stats/<short_code>")
def stats(short_code):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT original_url, clicks FROM urls WHERE short_code=?",
        (short_code,)
    )

    result = cursor.fetchone()
    conn.close()

    if not result:
        return jsonify({"error": "Not found"}), 404

    return jsonify({
        "url": result[0],
        "clicks": result[1]
    })

if __name__ == "__main__":
    app.run(debug=True)