import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from pathlib import Path

# Cargar .env desde la raíz del proyecto
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

def get_db_connection():
    return psycopg2.connect(os.getenv("DATABASE_URL"))

def execute_query(query, params=None, fetch=False):
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            if fetch:
                return cur.fetchall()
            conn.commit()
