import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
from dotenv import load_dotenv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")

def get_real_data():
    hoy = datetime.now().date()
    ayer = hoy - timedelta(days=1)
    
    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Query similar a analizar_diferencias
            cur.execute("""
                SELECT 
                    c.producto, c.categoria, c.stock_minimo,
                    h.cantidad_normalizada AS stock_actual,
                    y.cantidad_normalizada AS stock_ayer,
                    COALESCE(ei.total_entradas, 0) AS entradas
                FROM inventario_catalogo c
                LEFT JOIN inventario_diario h ON h.producto_id = c.id AND h.fecha = %s
                LEFT JOIN inventario_diario y ON y.producto_id = c.id AND y.fecha = %s
                LEFT JOIN (
                    SELECT producto_id, SUM(cantidad) AS total_entradas 
                    FROM entradas_inventario WHERE fecha = %s GROUP BY producto_id
                ) ei ON ei.producto_id = c.id
                WHERE c.activo = TRUE
                ORDER BY c.categoria, c.producto
            """, (hoy, ayer, hoy))
            return cur.fetchall()

def format_table(category, items):
    if not items: return ""
    lines = [f"📦 <b>INVENTARIO: {category.upper()}</b>", "<code>"]
    header = f"{'PRODUCTO':<14} | {'STK':>5} | {'ENT':>5} | {'VTA':>5} | {'EST'}"
    lines.append(header)
    lines.append("-" * len(header))
    
    for d in items:
        prod = (d['producto'][:14]) if len(d['producto']) > 14 else d['producto']
        stk = float(d['stock_actual'] or 0)
        ayer = float(d['stock_ayer'] or 0)
        ent = float(d['entradas'] or 0)
        # Venta = (Ayer + Entradas) - Hoy
        vta = (ayer + ent) - stk
        if vta < 0: vta = 0 # Evitar ventas negativas por errores de conteo
        
        # Estado
        minimo = float(d['stock_minimo'] or 0)
        est = "🚨" if (stk < minimo or (stk <= 0 and minimo >= 0)) else "✅"
        
        lines.append(f"{prod:<14} | {stk:>5.1f} | {ent:>5.1f} | {vta:>5.1f} | {est}")
    
    lines.append("-" * len(header))
    lines.append("</code>\n")
    return "\n".join(lines)

def main():
    data = get_real_data()
    by_cat = {}
    for d in data:
        cat = d['categoria'] or "OTROS"
        by_cat.setdefault(cat, []).append(d)
    
    full_report = ""
    for cat, items in by_cat.items():
        full_report += format_table(cat, items)
    
    print(full_report)

if __name__ == "__main__":
    main()
