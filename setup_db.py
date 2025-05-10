import sqlite3

conn = sqlite3.connect("minus.db")
c = conn.cursor()

# minusテーブル作成
c.execute("""
CREATE TABLE IF NOT EXISTS minus (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,
    date_display TEXT NOT NULL,
    date_origin TEXT NOT NULL,
    time_range TEXT NOT NULL,
    minus_count INTEGER NOT NULL
);
""")

# notified_logテーブル作成
c.execute("""
CREATE TABLE IF NOT EXISTS notified_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    unique_key TEXT NOT NULL
);
""")

conn.commit()
conn.close()
