import sqlite3
import json
import time
import atexit
from config import Config

class Database:
    def __init__(self):
        self.conn = sqlite3.connect(Config.DB_NAME)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS players (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                wins INTEGER DEFAULT 0,
                games_played INTEGER DEFAULT 0,
                coins INTEGER DEFAULT 0,
                inventory TEXT DEFAULT '[]',
                last_daily INTEGER DEFAULT 0
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS sudo_users (
                user_id INTEGER PRIMARY KEY
            )
        ''')
        self.conn.commit()

    def update_score(self, user_id, username, is_win):
        self.cursor.execute('''
            INSERT INTO players (user_id, username, wins, games_played)
            VALUES (?, ?, ?, 1)
            ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username,
                wins = wins + ?,
                games_played = games_played + 1
        ''', (user_id, username, 1 if is_win else 0, 1 if is_win else 0))
        self.conn.commit()

    def add_coins(self, user_id, amount):
        self.cursor.execute("UPDATE players SET coins = coins + ? WHERE user_id = ?", (amount, user_id))
        self.conn.commit()

    def get_user_data(self, user_id):
        self.cursor.execute("SELECT username, wins, games_played, coins, inventory FROM players WHERE user_id = ?", (user_id,))
        return self.cursor.fetchone()

    def get_coins(self, user_id):
        data = self.get_user_data(user_id)
        return data[3] if data else 0

    def get_inventory(self, user_id):
        data = self.get_user_data(user_id)
        return json.loads(data[4]) if data else []

    def add_to_inventory(self, user_id, item):
        inv = self.get_inventory(user_id)
        if item not in inv:
            inv.append(item)
            self.cursor.execute("UPDATE players SET inventory = ? WHERE user_id = ?", (json.dumps(inv), user_id))
            self.conn.commit()

    def claim_daily(self, user_id):
        now = int(time.time())
        self.cursor.execute("SELECT last_daily FROM players WHERE user_id = ?", (user_id,))
        last = self.cursor.fetchone()
        if last and now - last[0] < 86400:
            return False
        self.add_coins(user_id, 50)
        self.cursor.execute("UPDATE players SET last_daily = ? WHERE user_id = ?", (now, user_id))
        self.conn.commit()
        return True

    def is_sudo(self, user_id):
        if user_id == Config.OWNER_ID:
            return True
        self.cursor.execute("SELECT user_id FROM sudo_users WHERE user_id = ?", (user_id,))
        return bool(self.cursor.fetchone())

    def add_sudo(self, user_id):
        self.cursor.execute("INSERT OR IGNORE INTO sudo_users (user_id) VALUES (?)", (user_id,))
        self.conn.commit()

    def remove_sudo(self, user_id):
        self.cursor.execute("DELETE FROM sudo_users WHERE user_id = ?", (user_id,))
        self.conn.commit()

    def get_leaderboard(self):
        self.cursor.execute("SELECT username, wins, games_played FROM players ORDER BY wins DESC LIMIT 10")
        return self.cursor.fetchall()

db = Database()
atexit.register(lambda: db.conn.close())