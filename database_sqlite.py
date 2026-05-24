import sqlite3
import json
import os
from logger import log

LEGACY_DATA_DIR = "./data"
DB_FILE = os.path.join(LEGACY_DATA_DIR, "bot_database.sqlite")

class SQLiteDB:
    def __init__(self, db_file):
        self.db_file = db_file
        self.conn = None
        self._connect()

    def _connect(self):
        try:
            os.makedirs(os.path.dirname(self.db_file), exist_ok=True)
            self.conn = sqlite3.connect(self.db_file, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
            self.conn.execute("PRAGMA journal_mode=WAL;")
            log("Соединение с SQLite установлено.")
        except sqlite3.Error as e:
            log(f"Ошибка подключения к SQLite: {e}")
            raise

    def _execute(self, query, params=(), commit=False):
        try:
            cursor = self.conn.cursor()
            cursor.execute(query, params)
            if commit:
                self.conn.commit()
                return cursor.lastrowid
            return cursor
        except sqlite3.Error as e:
            log(f"Ошибка SQL: {e}")
            self.conn.rollback()
            return None

    def _get_setting(self, key, default=None):
        cursor = self._execute("SELECT value FROM settings WHERE key = ?", (key,))
        if cursor:
            row = cursor.fetchone()
            if row and row['value'] != 'None':
                return row['value']
        return default

    def _set_setting(self, key, value):
        self._execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)), commit=True)

    def close(self):
        if self.conn:
            self.conn.close()
            log("Соединение закрыто.")

    def create_tables(self):
        self._execute("CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, user_id INTEGER, is_dunduk BOOLEAN DEFAULT FALSE, notifications_enabled BOOLEAN DEFAULT TRUE);", commit=True)
        self._execute("CREATE TABLE IF NOT EXISTS participants (username TEXT PRIMARY KEY, FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE);", commit=True)
        self._execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);", commit=True)
        self._execute("CREATE TABLE IF NOT EXISTS admins (username TEXT PRIMARY KEY);", commit=True)
        self._execute("CREATE TABLE IF NOT EXISTS bot_messages (chat_id TEXT PRIMARY KEY, message_id INTEGER);", commit=True)
        self._execute("CREATE TABLE IF NOT EXISTS chat_members (username TEXT PRIMARY KEY);", commit=True)
        self._execute("CREATE TABLE IF NOT EXISTS system_stats (timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, cpu_usage REAL, ram_usage REAL, disk_usage REAL, net_rx REAL, net_tx REAL, disk_read REAL, disk_write REAL);", commit=True)
        self._execute("CREATE TABLE IF NOT EXISTS port_stats (timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, port INTEGER, connections INTEGER);", commit=True)
        self._execute("CREATE TABLE IF NOT EXISTS ssh_attacks (ip TEXT PRIMARY KEY, count INTEGER DEFAULT 0, last_attack DATETIME DEFAULT CURRENT_TIMESTAMP);", commit=True)
        log("Таблицы проверены.")

    def log_ssh_attack(self, ip):
        self._execute("""
            INSERT INTO ssh_attacks (ip, count, last_attack) 
            VALUES (?, 1, CURRENT_TIMESTAMP) 
            ON CONFLICT(ip) DO UPDATE SET count = count + 1, last_attack = CURRENT_TIMESTAMP;
        """, (ip,), commit=True)
        cursor = self._execute("SELECT count FROM ssh_attacks WHERE ip = ?", (ip,))
        row = cursor.fetchone()
        return row['count'] if row else 1

    def add_admin(self, username):
        u = username.lstrip('@')
        self._execute("INSERT OR IGNORE INTO admins (username) VALUES (?)", (u,), commit=True)

    def remove_admin(self, username):
        u = username.lstrip('@')
        self._execute("DELETE FROM admins WHERE username = ?", (u,), commit=True)

    def get_admins(self):
        cursor = self._execute("SELECT username FROM admins")
        return [row['username'] for row in cursor.fetchall()] if cursor else []

    def is_admin(self, username):
        u = username.lstrip('@')
        cursor = self._execute("SELECT 1 FROM admins WHERE username = ?", (u,))
        return cursor.fetchone() is not None if cursor else False

    def get_participants(self):
        cursor = self._execute("SELECT username FROM participants ORDER BY rowid")
        return [row['username'] for row in cursor.fetchall()] if cursor else []

    def get_participant_count(self):
        cursor = self._execute("SELECT COUNT(*) FROM participants")
        res = cursor.fetchone()
        return res[0] if res else 0

    def is_participant(self, username):
        cursor = self._execute("SELECT 1 FROM participants WHERE username = ?", (username,))
        return cursor.fetchone() is not None if cursor else False

    def remove_user_completely(self, username):
        self._execute("DELETE FROM participants WHERE username = ?", (username,), commit=True)
        self._execute("DELETE FROM users WHERE username = ?", (username,), commit=True)

    def get_user(self, username):
        cursor = self._execute("SELECT * FROM users WHERE username = ?", (username,))
        return cursor.fetchone() if cursor else None

    def set_dunduk(self, username, status=True):
        self._execute("INSERT OR IGNORE INTO users (username) VALUES (?)", (username,), commit=True)
        self._execute("UPDATE users SET is_dunduk = ? WHERE username = ?", (status, username), commit=True)

    def is_mece_cancelled(self):
        return self._get_setting('mece_cancelled', 'false') == 'true'

    def cancel_mece(self):
        self.clear_list_only()
        self._set_setting('mece_cancelled', 'true')

    def uncancel_mece(self):
        self._set_setting('mece_cancelled', 'false')
        
    def clear_list_only(self):
        self._execute("DELETE FROM participants", commit=True)

    def set_location(self, location):
        self._set_setting('location', location)

    def get_location(self):
        return self._get_setting('location', '')

    def set_schedule(self, schedule):
        self._set_setting('schedule', schedule)
        return True

    def get_schedule(self):
        return self._get_setting('schedule', '0010011')

    def set_max_participants(self, limit):
        self._set_setting('max_participants', limit)
        return True

    def get_max_participants(self):
        return int(self._get_setting('max_participants', '0'))

    def get_last_bot_message_id(self, chat_id):
        cursor = self._execute("SELECT message_id FROM bot_messages WHERE chat_id = ?", (str(chat_id),))
        row = cursor.fetchone()
        return row['message_id'] if row else None

    def save_last_bot_message_id(self, chat_id, message_id):
        self._execute("INSERT OR REPLACE INTO bot_messages (chat_id, message_id) VALUES (?, ?)", (str(chat_id), message_id), commit=True)
        
    def add_chat_member(self, username):
        self._execute("INSERT OR IGNORE INTO chat_members (username) VALUES (?)", (username,), commit=True)

    def remove_chat_member(self, username):
        self._execute("DELETE FROM chat_members WHERE username = ?", (username,), commit=True)

    def is_chat_member(self, username):
        cursor = self._execute("SELECT 1 FROM chat_members WHERE username = ?", (username,))
        return cursor.fetchone() is not None if cursor else False

    def add_user_to_list(self, username, user_id=None):
        self._execute("INSERT OR IGNORE INTO users (username, user_id) VALUES (?, ?)", (username, user_id), commit=True)
        self._execute("INSERT OR IGNORE INTO participants (username) VALUES (?)", (username,), commit=True)

    def remove_user_from_list_only(self, username):
        self._execute("DELETE FROM participants WHERE username = ?", (username,), commit=True)
        
    def toggle_notifications(self, username):
        self._execute("INSERT OR IGNORE INTO users (username) VALUES (?)", (username,), commit=True)
        self._execute("UPDATE users SET notifications_enabled = NOT notifications_enabled WHERE username = ?", (username,), commit=True)
        cursor = self._execute("SELECT notifications_enabled FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        return row['notifications_enabled'] if row else None

    def get_users_with_notifications(self):
        cursor = self._execute("SELECT username, user_id FROM users WHERE notifications_enabled = TRUE")
        return cursor.fetchall() if cursor else []

    def get_last_reminder_date(self):
        return self._get_setting('last_reminder_date')

    def set_last_reminder_date(self, date):
        self._set_setting('last_reminder_date', date)

    def get_last_cat_date(self):
        return self._get_setting('last_cat_date')

    def set_last_cat_date(self, date):
        self._set_setting('last_cat_date', date)

db = SQLiteDB(DB_FILE)
db.create_tables()
