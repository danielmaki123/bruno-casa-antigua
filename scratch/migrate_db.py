import os, psycopg2
from dotenv import load_dotenv
load_dotenv()
conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()

try:
    cur.execute("DROP VIEW IF EXISTS stock_vs_minimo;")
    
    cur.execute("ALTER TABLE inventario_catalogo DROP CONSTRAINT IF EXISTS inventario_catalogo_proveedor_id_fkey;")
    cur.execute("ALTER TABLE inventario_catalogo ALTER COLUMN proveedor_id TYPE VARCHAR USING proveedor_id::VARCHAR;")
    cur.execute("ALTER TABLE inventario_catalogo RENAME COLUMN proveedor_id TO proveedor;")
    
    cur.execute("ALTER TABLE entradas_inventario DROP CONSTRAINT IF EXISTS entradas_inventario_proveedor_id_fkey;")
    cur.execute("ALTER TABLE entradas_inventario ALTER COLUMN proveedor_id TYPE VARCHAR USING proveedor_id::VARCHAR;")
    cur.execute("ALTER TABLE entradas_inventario RENAME COLUMN proveedor_id TO proveedor;")

    view_def = """
    CREATE OR REPLACE VIEW stock_vs_minimo AS
    SELECT c.id AS producto_id,
        c.producto,
        c.categoria,
        c.stock_minimo,
        COALESCE(d.cantidad_normalizada, (0)::numeric) AS stock_actual,
        COALESCE(e.total_entradas, (0)::numeric) AS entradas_hoy,
        lag(d.cantidad_normalizada) OVER (PARTITION BY c.id ORDER BY d.fecha) AS stock_ayer,
            CASE
                WHEN (d.cantidad_normalizada < c.stock_minimo) THEN true
                ELSE false
            END AS bajo_minimo,
        c.proveedor
    FROM (((inventario_catalogo c
        LEFT JOIN inventario_diario d ON (((c.id = d.producto_id) AND (d.fecha = CURRENT_DATE))))
        LEFT JOIN ( SELECT entradas_inventario.producto_id,
                sum(entradas_inventario.cantidad) AS total_entradas
            FROM entradas_inventario
            WHERE (entradas_inventario.fecha = CURRENT_DATE)
            GROUP BY entradas_inventario.producto_id) e ON ((c.id = e.producto_id))))
    WHERE (c.activo = true)
    ORDER BY
            CASE
                WHEN (d.cantidad_normalizada < c.stock_minimo) THEN true
                ELSE false
            END DESC, c.categoria, c.producto;
    """
    cur.execute(view_def)
    conn.commit()
    print("Migration successful")
except Exception as e:
    conn.rollback()
    print("Migration failed:", e)
finally:
    cur.close()
    conn.close()
