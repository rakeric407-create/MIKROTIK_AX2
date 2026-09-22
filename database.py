import sqlite3
from datetime import datetime

DB_PATH = "hotspot.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS clients (
        username TEXT PRIMARY KEY,
        daily_bytes INTEGER DEFAULT 0,
        monthly_bytes INTEGER DEFAULT 0,
        date_debut TEXT,
        date_fin TEXT,
        limit_daily_gb INTEGER DEFAULT 30,
        status TEXT DEFAULT "active",
        last_update TEXT
    )''')
    
    # Vérification et ajout des colonnes si manquantes
    c.execute("PRAGMA table_info(clients)")
    columns = [col[1] for col in c.fetchall()]
    if "date_debut" not in columns:
        c.execute("ALTER TABLE clients ADD COLUMN date_debut TEXT")
    if "date_fin" not in columns:
        c.execute("ALTER TABLE clients ADD COLUMN date_fin TEXT")
    if "limit_daily_gb" not in columns:
        c.execute("ALTER TABLE clients ADD COLUMN limit_daily_gb INTEGER DEFAULT 30")
        
    conn.commit()
    conn.close()

def update_client_usage(username, daily_bytes):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT daily_bytes, monthly_bytes FROM clients WHERE username=?", (username,))
    row = c.fetchone()
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    if row:
        old_daily = row[0]
        old_monthly = row[1]
        diff = daily_bytes - old_daily
        new_monthly = old_monthly + diff if diff > 0 else old_monthly
        c.execute("UPDATE clients SET daily_bytes=?, monthly_bytes=?, last_update=datetime('now', 'localtime') WHERE username=?",
                  (daily_bytes, new_monthly, username))
    else:
        # Nouveau client détecté : date début = aujourd'hui
        c.execute("""INSERT INTO clients (username, daily_bytes, monthly_bytes, date_debut, date_fin, limit_daily_gb, last_update) 
                     VALUES (?, ?, ?, ?, '', 30, datetime('now', 'localtime'))""",
                  (username, daily_bytes, daily_bytes, today_str))
    conn.commit()
    conn.close()

def edit_client_dates(username, date_debut, date_fin, limit_daily_gb, status):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""UPDATE clients 
                 SET date_debut=?, date_fin=?, limit_daily_gb=?, status=? 
                 WHERE username=?""",
              (date_debut, date_fin, limit_daily_gb, status, username))
    conn.commit()
    conn.close()

def get_client(username):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT username, daily_bytes, monthly_bytes, date_debut, date_fin, limit_daily_gb, status, last_update FROM clients WHERE username=?", (username,))
    row = c.fetchone()
    conn.close()
    if row:
        return {
            "username": row[0], "daily_bytes": row[1], "monthly_bytes": row[2],
            "date_debut": row[3] or "Non défini", "date_fin": row[4] or "Non défini",
            "limit_daily_gb": row[5] or 30, "status": row[6] or "active", "last_update": row[7]
        }
    return None

def get_all_clients():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT username, daily_bytes, monthly_bytes, date_debut, date_fin, limit_daily_gb, status, last_update FROM clients ORDER BY monthly_bytes DESC")
    rows = c.fetchall()
    conn.close()
    return [{
        "username": r[0], "daily_bytes": r[1], "monthly_bytes": r[2],
        "date_debut": r[3] or "", "date_fin": r[4] or "",
        "limit_daily_gb": r[5] or 30, "status": r[6] or "active", "last_update": r[7]
    } for r in rows]

def reset_daily():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE clients SET daily_bytes=0")
    conn.commit()
    conn.close()
