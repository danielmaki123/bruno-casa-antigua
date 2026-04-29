import os, psycopg2
from dotenv import load_dotenv
load_dotenv()
conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()
cur.execute("SELECT pg_get_viewdef('stock_vs_minimo')")
print(cur.fetchone()[0])
cur.close()
conn.close()
