from flask import Flask, request, render_template
import pandas as pd
from db import get_db
from utils import get_storage_info
from datetime import datetime
import pytz

app = Flask(__name__)

# ---------------------------
# GLOBAL STORAGE (แก้ปัญหา undefined)
# ---------------------------
@app.context_processor
def inject_storage():
    return dict(storage=get_storage_info())

# ---------------------------
# INIT DB
# ---------------------------
def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS files (
        id SERIAL PRIMARY KEY,
        customer TEXT,
        game TEXT,
        file_label TEXT,
        upload_date TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS data_rows (
        id SERIAL PRIMARY KEY,
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

init_db()

# ---------------------------
# HOME
# ---------------------------
@app.route("/")
def index():
    return render_template("index.html")

# ---------------------------
# UPLOAD
# ---------------------------
@app.route("/upload", methods=["POST"])
def upload():
    file = request.files["file"]
    customer = request.form["customer"]
    game = request.form["game"]

    df = pd.read_excel(file)
    df_data = df.iloc[:, 0:11].fillna("")

    conn = get_db()
    cursor = conn.cursor()

    thai_tz = pytz.timezone("Asia/Bangkok")
    upload_date = datetime.now(thai_tz).strftime("%Y-%m-%d %H:%M:%S")

    file_label = f"{customer} > {game} > {upload_date}"

    cursor.execute("""
        INSERT INTO files (customer, game, file_label, upload_date)
        VALUES (%s, %s, %s, %s)
        RETURNING id
    """, (customer, game, file_label, upload_date))

    file_id = cursor.fetchone()[0]

    for _, row in df_data.iterrows():
        cursor.execute("""
            INSERT INTO data_rows VALUES (DEFAULT,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (file_id, *[str(x) for x in row]))

    conn.commit()
    conn.close()

    return "Upload สำเร็จ <a href='/'>กลับ</a>"

# ---------------------------
# SEARCH
# ---------------------------
@app.route("/search")
def search():
    keyword = request.args.get("q")

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT files.id, data_rows.id, files.customer, files.game,
           files.upload_date, data_rows.col_B
    FROM data_rows
    JOIN files ON data_rows.file_id = files.id
    WHERE col_A ILIKE %s OR col_B ILIKE %s OR col_C ILIKE %s
       OR col_D ILIKE %s OR col_E ILIKE %s OR col_F ILIKE %s
       OR col_G ILIKE %s OR col_H ILIKE %s OR col_I ILIKE %s
       OR col_J ILIKE %s OR col_K ILIKE %s
    """, tuple([f"%{keyword}%"] * 11))

    results = cursor.fetchall()
    conn.close()

    return render_template("index.html", results=results)

# ---------------------------
# DELETE FILE
# ---------------------------
@app.route("/delete_file/<int:file_id>")
def delete_file(file_id):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM data_rows WHERE file_id = %s", (file_id,))
    cursor.execute("DELETE FROM files WHERE id = %s", (file_id,))

    conn.commit()
    conn.close()

    return "<script>alert('ลบสำเร็จ'); window.location.href='/'</script>"

# ---------------------------
# VACUUM
# ---------------------------
@app.route("/vacuum")
def vacuum():
    password = request.args.get("pass")

    if password != "081041":
        return "❌ Unauthorized"

    conn = get_db()
    conn.autocommit = True
    cursor = conn.cursor()

    cursor.execute("VACUUM FULL;")

    conn.close()
    return "✅ ล้าง Storage สำเร็จ"
