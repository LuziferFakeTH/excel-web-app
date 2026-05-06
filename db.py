import psycopg2
import os

def get_db():
    DATABASE_URL = os.environ.get("DATABASE_URL")

    if not DATABASE_URL:
        raise Exception("❌ DATABASE_URL not set")

    return psycopg2.connect(DATABASE_URL)
