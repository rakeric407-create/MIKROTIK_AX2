import sqlite3
from datetime import datetime, timedelta

DB_PATH = "hotspot.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS clients (
        username TEXT PRIMARY KEY,
        daily_bytes INTEGER DEFAULT 0,
        monthly_bytes INTEGER DEFAULT 0,
        date_debut TEXT DEFAULT "",
        date_fin TEXT DEFAULT "",
        limit_daily_gb INTEGER DEFAULT 30,
        client_type TEXT DEFAULT "Hotspot",
        status TEXT DEFAULT "active",
        last_update TEXT DEFAULT ""
    )''')
    
    # Vérification colonne client_type
    c.execute("PRAGMA table_info(clients)")
    cols = [col[1] for col in c.fetchall()]
    if "client_type" not in cols:
        c.execute("ALTER TABLE clients ADD COLUMN client_type TEXT DEFAULT 'Hotspot'")
        
    conn.commit()
    conn.close()

def update_client_usage(username, daily_bytes, client_type="Hotspot"):
    if not username:
        return
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT daily_bytes, monthly_bytes FROM clients WHERE username=?", (username,))
    row = c.fetchone()
    today_str = datetime.now().strftime("%Y-%m-%d")
    daily_bytes = int(daily_bytes or 0)
    
    if row:
        old_daily = int(row[0] or 0)
        old_monthly = int(row[1] or 0)
        diff = daily_bytes - old_daily
        new_monthly = old_monthly + diff if diff > 0 else old_monthly
        c.execute("UPDATE clients SET daily_bytes=?, monthly_bytes=?, client_type=?, last_update=datetime('now', 'localtime') WHERE username=?",
                  (daily_bytes, new_monthly, client_type, username))
    else:
        c.execute("""INSERT INTO clients (username, daily_bytes, monthly_bytes, date_debut, date_fin, limit_daily_gb, client_type, status, last_update) 
                     VALUES (?, ?, ?, ?, '', 30, ?, 'active', datetime('now', 'localtime'))""",
                  (username, daily_bytes, daily_bytes, today_str, client_type))
    conn.commit()
    conn.close()

def edit_client_dates(username, date_debut, date_fin, limit_daily_gb, client_type, status):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""UPDATE clients 
                 SET date_debut=?, date_fin=?, limit_daily_gb=?, client_type=?, status=? 
                 WHERE username=?""",
              (date_debut or "", date_fin or "", int(limit_daily_gb or 30), client_type or "Hotspot", status or "active", username))
    conn.commit()
    conn.close()

def add_days_to_client(username, days=30):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT date_fin FROM clients WHERE username=?", (username,))
    row = c.fetchone()
    today = datetime.now().date()
    
    if row and row[0]:
        try:
            current_fin = datetime.strptime(row[0], "%Y-%m-%d").date()
            base_date = current_fin if current_fin > today else today
        except:
            base_date = today
    else:
        base_date = today
    
    new_fin = (base_date + timedelta(days=days)).strftime("%Y-%m-%d")
    c.execute("UPDATE clients SET date_fin=?, status='active' WHERE username=?", (new_fin, username))
    conn.commit()
    conn.close()

def get_client(username):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT username, daily_bytes, monthly_bytes, date_debut, date_fin, limit_daily_gb, client_type, status, last_update FROM clients WHERE username=?", (username,))
    row = c.fetchone()
    conn.close()
    if row:
        return {
            "username": row[0],
            "daily_bytes": row[1] or 0,
            "monthly_bytes": row[2] or 0,
            "date_debut": row[3] or "",
            "date_fin": row[4] or "",
            "limit_daily_gb": row[5] or 30,
            "client_type": row[6] or "Hotspot",
            "status": row[7] or "active",
            "last_update": row[8] or ""
        }
    return None

def get_all_clients():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT username, daily_bytes, monthly_bytes, date_debut, date_fin, limit_daily_gb, client_type, status, last_update FROM clients ORDER BY monthly_bytes DESC")
    rows = c.fetchall()
    conn.close()
    return [{
        "username": r[0],
        "daily_bytes": r[1] or 0,
        "monthly_bytes": r[2] or 0,
        "date_debut": r[3] or "",
        "date_fin": r[4] or "",
        "limit_daily_gb": r[5] or 30,
        "client_type": r[6] or "Hotspot",
        "status": r[7] or "active",
        "last_update": r[8] or ""
    } for r in rows]

def reset_daily():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE clients SET daily_bytes=0")
    conn.commit()
    conn.close()
