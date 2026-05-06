from flask import Flask, request, render_template
import pandas as pd
from db import get_db
from utils import get_storage_info
from datetime import datetime
import pytz
import re

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
    keyword = request.args.get("q", "").strip()

    # 🔥 แปลง keyword ให้ clean
    keyword = re.sub(r'[^a-zA-Z0-9 ]', ' ', keyword)

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
    WHERE search_vector @@ plainto_tsquery('simple', %s)
    LIMIT 100
    """, (keyword,))

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
# ---------------------------
# File
# ---------------------------
@app.route("/files")
def all_files():
    from math import ceil

    page = int(request.args.get("page", 1))
    per_page = 20

    filter_date = request.args.get("date", "")
    filter_customer = request.args.get("customer", "")
    filter_game = request.args.get("game", "")

    conn = get_db()
    cursor = conn.cursor()

    query = """
        SELECT id, customer, game, upload_date
        FROM files
        WHERE 1=1
    """
    params = []

    if filter_customer:
        query += " AND customer ILIKE %s"
        params.append(f"%{filter_customer}%")

    if filter_game:
        query += " AND game ILIKE %s"
        params.append(f"%{filter_game}%")

    if filter_date:
        query += " AND DATE(upload_date) = %s"
        params.append(filter_date)

    # count
    count_query = f"SELECT COUNT(*) FROM ({query}) AS sub"
    cursor.execute(count_query, params)
    total_rows = cursor.fetchone()[0]

    total_pages = max(1, ceil(total_rows / per_page))
    offset = (page - 1) * per_page

    # data
    query += " ORDER BY id DESC LIMIT %s OFFSET %s"
    params.extend([per_page, offset])

    cursor.execute(query, params)
    files = cursor.fetchall()

    conn.close()

    return render_template(
        "files.html",
        files=files,
        page=page,
        total_pages=total_pages,
        filter_date=filter_date,
        filter_customer=filter_customer,
        filter_game=filter_game
    )
@app.route("/view_file/<int:file_id>")
def view_file(file_id):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT col_A, col_B, col_C, col_D, col_E,
               col_F, col_G, col_H, col_I, col_J, col_K
        FROM data_rows
        WHERE file_id = %s
    """, (file_id,))

    rows = cursor.fetchall()
    conn.close()

    return render_template("view_file.html", rows=rows)

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

    return "<script>alert('อัปเดตสำเร็จ'); window.location.href='/'</script>"

@app.route("/setup_search")
def setup_search():
    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute("""
        CREATE INDEX idx_search_fast
        ON data_rows
        USING GIN (
            to_tsvector('simple',
                coalesce(col_A,'') || ' ' ||
                coalesce(col_B,'') || ' ' ||
                coalesce(col_C,'') || ' ' ||
                coalesce(col_D,'') || ' ' ||
                coalesce(col_E,'') || ' ' ||
                coalesce(col_F,'') || ' ' ||
                coalesce(col_G,'') || ' ' ||
                coalesce(col_H,'') || ' ' ||
                coalesce(col_I,'') || ' ' ||
                coalesce(col_J,'') || ' ' ||
                coalesce(col_K,'')
            )
        );
        """)
        conn.commit()
        return "✅ สร้าง index สำเร็จ (search จะเร็วขึ้นทันที)"

    except Exception as e:
        conn.rollback()
        return f"❌ Error: {str(e)}"

    finally:
        conn.close()
        
@app.route("/setup_db")
def setup_db():
    conn = get_db()
    cursor = conn.cursor()

    try:
        # 1. เพิ่ม column
        cursor.execute("""
            ALTER TABLE data_rows
            ADD COLUMN search_vector tsvector;
        """)

        conn.commit()
        return "✅ เพิ่ม column สำเร็จ"

    except Exception as e:
        conn.rollback()
        return f"❌ Error: {str(e)}"

    finally:
        conn.close()
        
@app.route("/fill_search")
def fill_search():
    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute("""
        UPDATE data_rows
        SET search_vector = to_tsvector('simple',
            coalesce(col_A,'') || ' ' ||
            coalesce(col_B,'') || ' ' ||
            coalesce(col_C,'') || ' ' ||
            coalesce(col_D,'') || ' ' ||
            coalesce(col_E,'') || ' ' ||
            coalesce(col_F,'') || ' ' ||
            coalesce(col_G,'') || ' ' ||
            coalesce(col_H,'') || ' ' ||
            coalesce(col_I,'') || ' ' ||
            coalesce(col_J,'') || ' ' ||
            coalesce(col_K,'')
        )
        WHERE id IN (
            SELECT id FROM data_rows
            WHERE search_vector IS NULL
            LIMIT 2000
        );
        """)

        conn.commit()
        return "✅ เติม 2000 แถว (กดซ้ำจนกว่าจะครบ)"

    except Exception as e:
        conn.rollback()
        return f"❌ Error: {str(e)}"

    finally:
        conn.close()
        
@app.route("/create_index")
def create_index():
    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute("""
        CREATE INDEX idx_search_vector
        ON data_rows
        USING GIN (search_vector);
        """)

        conn.commit()
        return "✅ สร้าง INDEX สำเร็จ (ตอนนี้ search จะเร็วมาก)"

    except Exception as e:
        conn.rollback()
        return f"❌ Error: {str(e)}"

    finally:
        conn.close()

@app.route("/check_column")
def check_column():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT column_name
    FROM information_schema.columns
    WHERE table_name = 'data_rows';
    """)

    cols = cursor.fetchall()
    conn.close()

    return "<br>".join([c[0] for c in cols])

@app.route("/check_fill")
def check_fill():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT COUNT(*) FROM data_rows
    WHERE search_vector IS NULL
    """)

    count = cursor.fetchone()[0]
    conn.close()

    return f"เหลือ {count} แถวที่ยังไม่ fill"


@app.route("/debug_search")
def debug_search():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT col_A, search_vector
    FROM data_rows
    LIMIT 5
    """)

    rows = cursor.fetchall()
    conn.close()

    return "<br><br>".join([str(r) for r in rows])
