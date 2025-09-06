# backend/ml/db.py
import sqlite3
from urllib.parse import urlparse
from datetime import datetime

DB_PATH = "backend\\app\\ML\\url_classifier\\training\\training_links.db"

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS training_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT NOT NULL UNIQUE,
    domain TEXT,
    source_email TEXT,
    subject TEXT,
    auto_label TEXT,
    label TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_seen DATETIME,
    scan_count INTEGER DEFAULT 1
);
"""

def init_db_url_trainer():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(CREATE_TABLE_SQL)
    conn.commit()
    conn.close()

def insert_or_update_link(url, domain=None, source_email=None, subject=None, auto_label=None):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    now = datetime.utcnow().isoformat()
    try:
        cur.execute("INSERT INTO training_links (url, domain, source_email, subject, auto_label, last_seen) VALUES (?, ?, ?, ?, ?, ?)",
                    (url, domain, source_email, subject, auto_label, now))
    except sqlite3.IntegrityError:
        # already exists — update last_seen and increment scan_count and possibly auto_label if missing
        cur.execute("SELECT scan_count, auto_label FROM training_links WHERE url = ?", (url,))
        row = cur.fetchone()
        scan_count = row[0] + 1
        existing_auto = row[1]
        # update auto_label only if none exists
        if not existing_auto and auto_label:
            cur.execute("UPDATE training_links SET last_seen = ?, scan_count = ?, auto_label = ? WHERE url = ?",
                        (now, scan_count, auto_label, url))
        else:
            cur.execute("UPDATE training_links SET last_seen = ?, scan_count = ? WHERE url = ?",
                        (now, scan_count, url))
    conn.commit()
    conn.close()

def set_label_by_id(link_id, label):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE training_links SET label = ? WHERE id = ?", (label, link_id))
    conn.commit()
    conn.close()

def set_label_by_url(url, label):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE training_links SET label = ? WHERE url = ?", (label, url))
    conn.commit()
    conn.close()

def fetch_all_for_training():
    """
    Returns list of tuples: (url, label)
    uses human label if present, else auto_label.
    Only returns rows where either is present.
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
    SELECT url, COALESCE(label, auto_label) as final_label
    FROM training_links
    WHERE COALESCE(label, auto_label) IS NOT NULL
    """)
    rows = cur.fetchall()
    conn.close()
    return rows

def fetch_unlabeled(limit=100):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id, url, domain, auto_label FROM training_links WHERE label IS NULL LIMIT ?", (limit,))
    rows = cur.fetchall()
    conn.close()
    return rows
