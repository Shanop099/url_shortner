import sqlite3
import os

# Use writable path on Render
DB_PATH = "/tmp/urls.db"

def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS urls (
        short_code TEXT PRIMARY KEY,
        original_url TEXT NOT NULL,
        clicks INTEGER DEFAULT 0,
        expiry TEXT
    )
    """)

    conn.commit()
    conn.close()