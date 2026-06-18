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
                language TEXT DEFAULT 'es',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                donate_reminded INTEGER DEFAULT 0,
                last_rain_key TEXT DEFAULT NULL,
                rain_alerts_today INTEGER DEFAULT 0,
                last_alert_date TEXT DEFAULT NULL
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
        cur = self.conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
        row = cur.fetchone()
        return dict(row) if row else None

    def update_location(self, user_id, lat, lon):
        self.conn.execute("UPDATE users SET lat=?, lon=? WHERE user_id=?", (lat, lon, user_id))
        self.conn.commit()

    def set_active(self, user_id, active):
        self.conn.execute("UPDATE users SET active=? WHERE user_id=?", (1 if active else 0, user_id))
        self.conn.commit()

    def set_language(self, user_id, lang):
        self.conn.execute("UPDATE users SET language=? WHERE user_id=?", (lang, user_id))
        self.conn.commit()

    def get_language(self, user_id):
        cur = self.conn.execute("SELECT language FROM users WHERE user_id=?", (user_id,))
        row = cur.fetchone()
        return row["language"] if row else "es"

    def get_active_users(self):
        cur = self.conn.execute("SELECT * FROM users WHERE active=1 AND lat IS NOT NULL")
        return [dict(row) for row in cur.fetchall()]

    def set_donate_reminded(self, user_id):
        self.conn.execute("UPDATE users SET donate_reminded=1 WHERE user_id=?", (user_id,))
        self.conn.commit()

    def days_since_joined(self, user_id):
        user = self.get_user(user_id)
        if not user:
            return 0
        created = datetime.fromisoformat(user["created_at"])
        return (datetime.now() - created).days

    def should_send_rain_alert(self, user_id, rain_key):
        """
        Devuelve True si debemos enviar alerta de lluvia:
        - Es un episodio de lluvia nuevo (rain_key diferente)
        - No hemos superado el límite de 5 alertas hoy
        """
        user = self.get_user(user_id)
        if not user:
            return False

        today = datetime.now().strftime("%Y-%m-%d")

        # Resetear contador si es un nuevo día
        if user["last_alert_date"] != today:
            self.conn.execute("""
                UPDATE users SET rain_alerts_today=0, last_alert_date=?
                WHERE user_id=?
            """, (today, user_id))
            self.conn.commit()
            user = self.get_user(user_id)

        # Máximo 5 alertas por día
        if user["rain_alerts_today"] >= 5:
            return False

        # Ya enviamos alerta para este episodio concreto
        if user["last_rain_key"] == rain_key:
            return False

        return True

    def register_rain_alert(self, user_id, rain_key):
        today = datetime.now().strftime("%Y-%m-%d")
        self.conn.execute("""
            UPDATE users
            SET last_rain_key=?, rain_alerts_today=rain_alerts_today+1, last_alert_date=?
            WHERE user_id=?
        """, (rain_key, today, user_id))
        self.conn.commit()
