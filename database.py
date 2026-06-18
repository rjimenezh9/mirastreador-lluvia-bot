import sqlite3
from datetime import datetime

DB_PATH = "bot_data.db"

class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                lat REAL,
                lon REAL,
                active INTEGER DEFAULT 1,
                premium INTEGER DEFAULT 0,
                language TEXT DEFAULT 'es',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()

    def create_user_if_not_exists(self, user_id):
        self.conn.execute("""
            INSERT OR IGNORE INTO users (user_id, created_at)
            VALUES (?, ?)
        """, (user_id, datetime.now().isoformat()))
        self.conn.commit()

    def get_user(self, user_id):
        cur = self.conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
        return dict(row) if row else None

    def update_location(self, user_id, lat, lon):
        self.conn.execute("""
            UPDATE users SET lat = ?, lon = ? WHERE user_id = ?
        """, (lat, lon, user_id))
        self.conn.commit()

    def set_active(self, user_id, active):
        self.conn.execute("""
            UPDATE users SET active = ? WHERE user_id = ?
        """, (1 if active else 0, user_id))
        self.conn.commit()

    def set_premium(self, user_id, premium):
        self.conn.execute("""
            UPDATE users SET premium = ? WHERE user_id = ?
        """, (1 if premium else 0, user_id))
        self.conn.commit()

    def set_language(self, user_id, lang):
        self.conn.execute("""
            UPDATE users SET language = ? WHERE user_id = ?
        """, (lang, user_id))
        self.conn.commit()

    def get_language(self, user_id):
        cur = self.conn.execute("SELECT language FROM users WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
        return row["language"] if row else "es"

    def get_active_users(self):
        cur = self.conn.execute("SELECT * FROM users WHERE active = 1 AND lat IS NOT NULL")
        return [dict(row) for row in cur.fetchall()]
