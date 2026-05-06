from db import get_db

def get_storage_info():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT pg_database_size(current_database());")
    used_bytes = cursor.fetchone()[0]

    conn.close()

    total_bytes = 1024 * 1024 * 1024  # 1GB

    remaining_bytes = total_bytes - used_bytes
    percent_used = (used_bytes / total_bytes) * 100

    return {
        "used_kb": round(used_bytes / 1024, 2),
        "remaining_kb": round(remaining_bytes / 1024, 2),
        "percent_used": round(percent_used, 2)
    }
