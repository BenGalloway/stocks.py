import sqlite3
from datetime import datetime

DB_PATH = 'screener_memory.db'

def setup_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scans (
            ticker TEXT PRIMARY KEY,
            last_scanned DATE
        )
    ''')
    conn.commit()
    return conn

def can_scan_ticker(ticker, conn, cooldown_days=21):
    cursor = conn.cursor()
    cursor.execute('SELECT last_scanned FROM scans WHERE ticker = ?', (ticker,))
    result = cursor.fetchone()
    if result:
        last_scan_date = datetime.strptime(result[0], '%Y-%m-%d')
        if (datetime.now() - last_scan_date).days < cooldown_days:
            return False
    return True

def log_scan(ticker, conn):
    cursor = conn.cursor()
    today = datetime.now().strftime('%Y-%m-%d')
    cursor.execute('''
        INSERT INTO scans (ticker, last_scanned)
        VALUES (?, ?)
        ON CONFLICT(ticker) DO UPDATE SET last_scanned = ?
    ''', (ticker, today, today))
    conn.commit()

def reset_db(conn):
    """Clears all scan history so every ticker is re-evaluated on next run."""
    cursor = conn.cursor()
    cursor.execute('DELETE FROM scans')
    conn.commit()
    print("Database reset. All tickers will be re-evaluated.")