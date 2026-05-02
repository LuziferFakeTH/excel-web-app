from flask import Flask, request, render_template
import pandas as pd
import psycopg2
import os
from datetime import datetime
import pytz

app = Flask(__name__)

# ---------------------------
# CONNECT DATABASE (PostgreSQL)
# ---------------------------
def get_db():
    DATABASE_URL = os.environ.get("DATABASE_URL")

    if not DATABASE_URL:
        raise Exception("❌ DATABASE_URL not set in environment")

    return psycopg2.connect(DATABASE_URL)

# ---------------------------
# CREATE TABLE (AUTO)
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
    return render_template("index.html", results=None)

# ---------------------------
# UPLOAD
# ---------------------------
@app.route("/upload", methods=["POST"])
def upload():
    file = request.files["file"]
    customer = request.form["customer"]
    game = request.form["game"]

    try:
        df = pd.read_excel(file)
    except Exception as e:
        return f"อ่านไฟล์ไม่ได้: {str(e)}"

    conn = get_db()
    cursor = conn.cursor()

    thai_tz = pytz.timezone("Asia/Bangkok")
    upload_date = datetime.now(thai_tz).strftime("%Y-%m-%d %H:%M:%S")
    file_label = f"{customer} > {game} > {upload_date}"

    # insert files
    cursor.execute("""
        INSERT INTO files (customer, game, file_label, upload_date)
        VALUES (%s, %s, %s, %s)
        RETURNING id
    """, (customer, game, file_label, upload_date))

    file_id = cursor.fetchone()[0]

    # อ่าน A-K (ข้าม header)
    df_data = df.iloc[1:, 0:11].fillna("")

    for _, row in df_data.iterrows():
        cursor.execute("""
            INSERT INTO data_rows (
                file_id, col_A, col_B, col_C, col_D, col_E,
                col_F, col_G, col_H, col_I, col_J, col_K
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            file_id,
            str(row.iloc[0]),
            str(row.iloc[1]),
            str(row.iloc[2]),
            str(row.iloc[3]),
            str(row.iloc[4]),
            str(row.iloc[5]),
            str(row.iloc[6]),
            str(row.iloc[7]),
            str(row.iloc[8]),
            str(row.iloc[9]),
            str(row.iloc[10])
        ))

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
        SELECT 
            data_rows.id,
            files.customer,
            files.game,
            files.upload_date,
            data_rows.col_B
        FROM data_rows
        JOIN files ON data_rows.file_id = files.id
        WHERE col_A ILIKE %s
           OR col_B ILIKE %s
           OR col_C ILIKE %s
           OR col_D ILIKE %s
           OR col_E ILIKE %s
           OR col_F ILIKE %s
           OR col_G ILIKE %s
           OR col_H ILIKE %s
           OR col_I ILIKE %s
           OR col_J ILIKE %s
           OR col_K ILIKE %s
    """, tuple([f"%{keyword}%"] * 11))

    results = cursor.fetchall()
    conn.close()

    return render_template("index.html", results=results)

# ---------------------------
# DETAIL
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
# RUN SERVER
# ---------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
