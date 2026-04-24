import sqlite3

DB_NAME = "urls.db"

def get_connection():
    return sqlite3.connect(DB_NAME)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS urls (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        short_code TEXT UNIQUE,
        original_url TEXT,
        clicks INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        expiry TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()