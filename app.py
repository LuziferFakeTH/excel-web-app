from flask import Flask, request, render_template
import pandas as pd
import psycopg2
import os
from datetime import datetime
import pytz

app = Flask(__name__)
def get_storage_info():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT pg_database_size(current_database());")
    used_bytes = cursor.fetchone()[0]

    conn.close()

    total_bytes = 1024 * 1024 * 1024  # 1GB

    return {
        "percent_used": round((used_bytes / total_bytes) * 100, 2),
        "remaining_kb": round((total_bytes - used_bytes) / 1024, 2)
    }

@app.context_processor
def inject_storage():
    return dict(storage=get_storage_info())

# ---------------------------
# CONNECT DB
# ---------------------------
def get_db():
    DATABASE_URL = os.environ.get("DATABASE_URL")
    return psycopg2.connect(DATABASE_URL)

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
    storage = get_storage_info()
    return render_template("index.html", storage=storage)

# ---------------------------
# UPLOAD
# ---------------------------
@app.route("/upload", methods=["POST"])
def upload():
    file = request.files["file"]
    customer = request.form["customer"]
    game = request.form["game"]

    df = pd.read_excel(file, dtype=str)
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
            INSERT INTO data_rows VALUES (
                DEFAULT,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s
            )
        """, (file_id, *[str(x) for x in row]))

    conn.commit()
    conn.close()

    return "Upload สำเร็จ <a href='/'>กลับ</a>"

# ---------------------------
# SEARCH (เวอร์ชันเดิม เสถียร)
# ---------------------------
@app.route("/search")
def search():
    keyword = request.args.get("q", "").strip()

    if not keyword:
        return render_template("index.html", results=[])

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT 
        files.id,
        data_rows.id,
        files.customer,
        files.game,
        files.upload_date,
        data_rows.col_B
    FROM data_rows
    JOIN files ON data_rows.file_id = files.id
    WHERE 
        col_A ILIKE %s OR
        col_B ILIKE %s OR
        col_C ILIKE %s OR
        col_D ILIKE %s OR
        col_E ILIKE %s OR
        col_F ILIKE %s OR
        col_G ILIKE %s OR
        col_H ILIKE %s OR
        col_I ILIKE %s OR
        col_J ILIKE %s OR
        col_K ILIKE %s
    ORDER BY data_rows.id DESC
    LIMIT 100
    """, tuple([f"%{keyword}%"] * 11))

    results = cursor.fetchall()
    conn.close()

    return render_template("index.html", results=results)

# ---------------------------
# FILE LIST
# ---------------------------
@app.route("/files")
def files():
    from math import ceil

    page = int(request.args.get("page", 1))
    per_page = 20

    conn = get_db()
    cursor = conn.cursor()

    # นับจำนวนทั้งหมด
    cursor.execute("SELECT COUNT(*) FROM files")
    total_rows = cursor.fetchone()[0]

    total_pages = max(1, ceil(total_rows / per_page))
    offset = (page - 1) * per_page

    # ดึงข้อมูล
    cursor.execute("""
        SELECT id, customer, game, upload_date
        FROM files
        ORDER BY id DESC
        LIMIT %s OFFSET %s
    """, (per_page, offset))

    files_data = cursor.fetchall()
    conn.close()

    return render_template(
        "files.html",
        files=files_data,
        page=page,
        total_pages=total_pages
    )

# ---------------------------
# VIEW FILE
# ---------------------------
@app.route("/view_file/<int:file_id>")
def view_file(file_id):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, col_A, col_B, col_C, col_D, col_E,
               col_F, col_G, col_H, col_I, col_J, col_K
        FROM data_rows
        WHERE file_id = %s
    """, (file_id,))

    rows = cursor.fetchall()
    conn.close()

    return render_template("view_file.html", rows=rows)

# ---------------------------
# DETAIL (แก้ไข)
# ---------------------------
@app.route("/detail/<int:row_id>")
def detail(row_id):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT col_A, col_B, col_C, col_D, col_E,
               col_F, col_G, col_H, col_I, col_J, col_K
        FROM data_rows
        WHERE id = %s
    """, (row_id,))

    row = cursor.fetchone()
    conn.close()

    return render_template("detail.html", row=row, row_id=row_id)

# ---------------------------
# UPDATE
# ---------------------------
@app.route("/update/<int:row_id>", methods=["POST"])
def update(row_id):
    conn = get_db()
    cursor = conn.cursor()

    values = [request.form[f"col{i}"] for i in range(11)]

    cursor.execute("""
        UPDATE data_rows SET
            col_A=%s, col_B=%s, col_C=%s, col_D=%s, col_E=%s,
            col_F=%s, col_G=%s, col_H=%s, col_I=%s, col_J=%s, col_K=%s
        WHERE id=%s
    """, (*values, row_id))

    conn.commit()
    conn.close()

    return "อัปเดตสำเร็จ <a href='/'>กลับ</a>"

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

    return "<script>alert('ลบสำเร็จ'); window.location.href='/files'</script>"

@app.route("/vacuum")
def vacuum():
    try:
        conn = get_db()
        conn.autocommit = True  # สำคัญ
        cursor = conn.cursor()

        cursor.execute("VACUUM FULL;")

        conn.close()
        return "✅ ล้าง Storage สำเร็จ"

    except Exception as e:
        return f"❌ Error: {str(e)}"


# ---------------------------
# RUN
# ---------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
