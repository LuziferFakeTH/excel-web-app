import sqlite3

conn = sqlite3.connect("data.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer TEXT,
    game TEXT,
    file_label TEXT,
    upload_date TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS data_rows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER,
    col_A TEXT,
    col_B TEXT,
    col_C TEXT,
    col_D TEXT,
    col_E TEXT,
    col_F TEXT,
    col_G TEXT,
    col_H TEXT,
    col_I TEXT,
    col_J TEXT,
    col_K TEXT
)
""")

conn.commit()
conn.close()

print("Database ready")