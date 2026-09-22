import sqlite3
import os

DB_PATH = "hotspot.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS clients (
        username TEXT PRIMARY KEY,
        daily_bytes INTEGER DEFAULT 0,
        monthly_bytes INTEGER DEFAULT 0,
        limit_daily INTEGER DEFAULT 32212254720,
        status TEXT DEFAULT "active",
        last_update TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        date TEXT,
        bytes_used INTEGER
    )''')
    conn.commit()
    conn.close()

def update_client(username, daily_bytes):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT monthly_bytes FROM clients WHERE username=?", (username,))
    row = c.fetchone()
    if row:
        new_monthly = row[0] + (daily_bytes - c.execute(
            "SELECT daily_bytes FROM clients WHERE username=?", (username,)
        ).fetchone()[0])
        if new_monthly < 0:
            new_monthly = row[0]
        c.execute("UPDATE clients SET daily_bytes=?, monthly_bytes=?, last_update=datetime('now') WHERE username=?",
                  (daily_bytes, new_monthly, username))
    else:
        c.execute("INSERT INTO clients (username, daily_bytes, monthly_bytes, last_update) VALUES (?,?,?,datetime('now'))",
                  (username, daily_bytes, daily_bytes))
    conn.commit()
    conn.close()

def get_client(username):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM clients WHERE username=?", (username,))
    row = c.fetchone()
    conn.close()
    if row:
        return {"username": row[0], "daily_bytes": row[1], "monthly_bytes": row[2],
                "limit_daily": row[3], "status": row[4], "last_update": row[5]}
    return None

def get_all_clients():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM clients ORDER BY monthly_bytes DESC")
    rows = c.fetchall()
    conn.close()
    return [{"username": r[0], "daily_bytes": r[1], "monthly_bytes": r[2],
             "limit_daily": r[3], "status": r[4], "last_update": r[5]} for r in rows]

def reset_daily():
    """Appelé à minuit : sauvegarde la journée et remet daily à 0"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT username, daily_bytes FROM clients")
    for row in c.fetchall():
        c.execute("INSERT INTO history (username, date, bytes_used) VALUES (?, date('now'), ?)",
                  (row[0], row[1]))
    c.execute("UPDATE clients SET daily_bytes=0")
    conn.commit()
    conn.close()
