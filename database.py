import sqlite3

DB_PATH = "/tmp/urls.db"  # Render-safe path

def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False, timeout=10)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS urls (
        short_code TEXT PRIMARY KEY,
        original_url TEXT NOT NULL,
        clicks INTEGER DEFAULT 0
    )
    """)

    conn.commit()
    conn.close()