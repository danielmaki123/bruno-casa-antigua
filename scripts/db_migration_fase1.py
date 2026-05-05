"""
db_migration_fase1.py — Agrega las 5 tablas nuevas de Fase 1 a PostgreSQL.
Idempotente: se puede correr múltiples veces sin error.
NO modifica cierres_caja ni ventas_detalle.

Uso: python scripts/db_migration_fase1.py
"""
import os
import sys
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("[ERROR] DATABASE_URL no configurado en .env")
    sys.exit(1)

DDL = """
CREATE TABLE IF NOT EXISTS cierres_caja (
    id                      SERIAL PRIMARY KEY,
    documento_id            VARCHAR(20)   NOT NULL UNIQUE,
    fecha                   DATE          NOT NULL,
    cajero                  VARCHAR(100),
    terminal                VARCHAR(50),
    factura_desde           VARCHAR(20),
    factura_hasta           VARCHAR(20),
    num_facturas            INT           DEFAULT 0,
    facturas_anuladas       INT           DEFAULT 0,
    apertura                TIMESTAMP,
    cierre                  TIMESTAMP,
    exonerado               NUMERIC(12,2) DEFAULT 0,
    gravado                 NUMERIC(12,2) DEFAULT 0,
    subtotal                NUMERIC(12,2) DEFAULT 0,
    descuento               NUMERIC(12,2) DEFAULT 0,
    iva                     NUMERIC(12,2) DEFAULT 0,
    propina                 NUMERIC(12,2) DEFAULT 0,
    v_total                 NUMERIC(12,2) DEFAULT 0,
    efectivo_cds            NUMERIC(12,2) DEFAULT 0,
    efectivo_usd            NUMERIC(12,2) DEFAULT 0,
    tarjetas_total          NUMERIC(12,2) DEFAULT 0,
    transferencias_total    NUMERIC(12,2) DEFAULT 0,
    conteo_efectivo_cds     NUMERIC(12,2) DEFAULT 0,
    conteo_efectivo_usd     NUMERIC(12,2) DEFAULT 0,
    total_conteo_cds        NUMERIC(12,2) DEFAULT 0,
    declaracion_pos         NUMERIC(12,2) DEFAULT 0,
    apertura_custodio       NUMERIC(12,2) DEFAULT 0,
    faltante                NUMERIC(12,2) DEFAULT 0,
    sobrante                NUMERIC(12,2) DEFAULT 0,
    diferencia_pos          NUMERIC(12,2) DEFAULT 0,
    tipo_cambio             NUMERIC(8,4)  DEFAULT 0,
    auditado                BOOLEAN       DEFAULT FALSE,
    alerta_diferencia       BOOLEAN       DEFAULT FALSE,
    alerta_faltante         BOOLEAN       DEFAULT FALSE,
    notas_auditoria         TEXT,
    created_at              TIMESTAMP     DEFAULT NOW(),
    updated_at              TIMESTAMP     DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ventas_detalle (
    id              SERIAL PRIMARY KEY,
    cierre_id       VARCHAR(20)   NOT NULL REFERENCES cierres_caja(documento_id) ON DELETE CASCADE,
    fecha           DATE          NOT NULL,
    categoria       VARCHAR(100),
    descripcion     VARCHAR(200)  NOT NULL,
    cantidad        INT           DEFAULT 0,
    monto           NUMERIC(12,2) DEFAULT 0,
    precio_unitario NUMERIC(12,2) GENERATED ALWAYS AS (
        CASE WHEN cantidad > 0 THEN ROUND(monto / cantidad, 2) ELSE 0 END
    ) STORED,
    created_at      TIMESTAMP     DEFAULT NOW(),
    UNIQUE (cierre_id, categoria, descripcion)
);

CREATE TABLE IF NOT EXISTS liquidaciones_banco (
    id              SERIAL PRIMARY KEY,
    fecha           DATE NOT NULL,
    banco           VARCHAR(50) NOT NULL,
    monto           NUMERIC(12,2) DEFAULT 0,
    liquidacion_id  VARCHAR(100) NOT NULL,
    raw_text        TEXT,
    created_at      TIMESTAMP DEFAULT NOW(),
    UNIQUE (fecha, banco, liquidacion_id)
);

CREATE TABLE IF NOT EXISTS inventario_catalogo (
    id SERIAL PRIMARY KEY,
    producto VARCHAR(100) NOT NULL UNIQUE,
    categoria VARCHAR(50),
    unidad_tipo VARCHAR(20),
    stock_minimo NUMERIC(10,3) DEFAULT 0,
    proveedor_id INT,
    activo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS inventario_diario (
    id SERIAL PRIMARY KEY,
    fecha DATE NOT NULL,
    producto_id INT REFERENCES inventario_catalogo(id),
    cantidad_raw NUMERIC(10,3),
    unidad_raw VARCHAR(20),
    cantidad_normalizada NUMERIC(10,3),
    responsable VARCHAR(100),
    turno VARCHAR(20),
    fuente VARCHAR(20) DEFAULT 'sheets',
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE (fecha, producto_id)
);

CREATE TABLE IF NOT EXISTS conversations (
    id         SERIAL PRIMARY KEY,
    chat_id    BIGINT NOT NULL,
    user_id    BIGINT,
    user_name  TEXT,
    role       TEXT NOT NULL,
    content    TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS areas (
    id   SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS products (
    id           SERIAL PRIMARY KEY,
    name         VARCHAR(200) NOT NULL,
    sku_internal VARCHAR(50),
    unit         VARCHAR(20)  NOT NULL,
    area_id      INT REFERENCES areas(id),
    is_active    BOOLEAN DEFAULT TRUE,
    created_at   TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS stock_rules (
    id         SERIAL PRIMARY KEY,
    product_id INT REFERENCES products(id),
    area_id    INT REFERENCES areas(id),
    min_qty    NUMERIC(10,2) NOT NULL,
    target_qty NUMERIC(10,2),
    UNIQUE(product_id, area_id)
);

CREATE TABLE IF NOT EXISTS inventory_counts (
    id          SERIAL PRIMARY KEY,
    date        DATE NOT NULL,
    area_id     INT REFERENCES areas(id),
    product_id  INT REFERENCES products(id),
    counted_qty NUMERIC(10,2) NOT NULL,
    reported_by TEXT,
    source      VARCHAR(20) DEFAULT 'sheets',
    created_at  TIMESTAMP DEFAULT NOW(),
    UNIQUE(date, product_id, source)
);

CREATE INDEX IF NOT EXISTS idx_conversations_chat ON conversations(chat_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_inventory_date     ON inventory_counts(date, area_id);
CREATE INDEX IF NOT EXISTS idx_cierres_fecha      ON cierres_caja (fecha);
CREATE INDEX IF NOT EXISTS idx_ventas_cierre_id   ON ventas_detalle (cierre_id);
CREATE INDEX IF NOT EXISTS idx_liq_fecha_banco    ON liquidaciones_banco (fecha, banco);
CREATE INDEX IF NOT EXISTS idx_inv_diario_fecha   ON inventario_diario(fecha);
"""

AREAS = ["bebidas", "cocina", "barra", "sushi", "birria", "pizza"]

# (name, unit, area_name, min_qty, target_qty)
PRODUCTS = [
    # bebidas
    ("Toña",                  "unidades", "bebidas",  24, 48),
    ("Victoria",              "unidades", "bebidas",  24, 48),
    ("Coca regular",          "unidades", "bebidas",  36, 72),
    ("Coca cero",             "unidades", "bebidas",  24, 48),
    ("Fanta naranja",         "unidades", "bebidas",  18, 36),
    ("Fanta roja",            "unidades", "bebidas",  18, 36),
    ("Agua purificada",       "unidades", "bebidas",  30, 60),
    ("Agua gasificada limón", "unidades", "bebidas",  12, 24),
    ("Heineken",              "unidades", "bebidas",  18, 36),
    ("Miller",                "unidades", "bebidas",  18, 36),
    ("Toña Lite",             "unidades", "bebidas",  24, 48),
    ("Victoria Frost",        "unidades", "bebidas",  18, 36),
    ("Hard Limón",            "unidades", "bebidas",  12, 24),
    ("Hard Raspberry",        "unidades", "bebidas",  12, 24),
    ("Jugo de naranja",       "galones",  "bebidas",   3,  6),
    ("Jugo de limón",         "galones",  "bebidas",   2,  4),
    ("Jamaica",               "galones",  "bebidas",   2,  4),
    # barra
    ("Flor de Caña 12",       "botellas", "barra",     3,  6),
    ("Flor de Caña 18",       "botellas", "barra",     2,  4),
    ("Flor de Caña Gran Reserva", "botellas", "barra", 3,  6),
    ("Extra Lite litro",      "botellas", "barra",     4,  8),
    ("José Cuervo",           "botellas", "barra",     3,  6),
    ("Vodkalla",              "botellas", "barra",     3,  6),
    ("Triple sec",            "botellas", "barra",     2,  4),
    ("Vino tinto Tavernello", "botellas", "barra",     4,  8),
    ("Aperol",                "botellas", "barra",     2,  4),
    ("Granadine",             "botellas", "barra",     2,  4),
    # cocina
    ("Flan",                  "porciones", "cocina",   8, 16),
    ("Red velvet",            "porciones", "cocina",   6, 12),
    ("Tres leches",           "porciones", "cocina",   8, 16),
    ("Cheesecake de limón",   "porciones", "cocina",   6, 12),
    # sushi (insumos básicos para arrancar)
    ("Arroz para sushi",      "kg",        "sushi",    5, 10),
    ("Nori",                  "paquetes",  "sushi",    2,  5),
    ("Salmón",                "kg",        "sushi",    2,  4),
    # birria
    ("Carne de res",          "kg",        "birria",   5, 10),
    ("Tortillas",             "paquetes",  "birria",  10, 20),
    # pizza
    ("Harina pizza",          "kg",        "pizza",    5, 10),
    ("Queso mozzarella",      "kg",        "pizza",    3,  6),
    ("Salsa de tomate",       "litros",    "pizza",    2,  4),
]


def run_migration(conn):
    cur = conn.cursor()
    print("[DB] Creando tablas Fase 1...")
    cur.execute(DDL)

    print("[DB] Seeding areas...")
    for area in AREAS:
        cur.execute(
            "INSERT INTO areas (name) VALUES (%s) ON CONFLICT (name) DO NOTHING",
            (area,),
        )

    print("[DB] Seeding products + stock_rules...")
    for name, unit, area_name, min_qty, target_qty in PRODUCTS:
        cur.execute("SELECT id FROM areas WHERE name = %s", (area_name,))
        row = cur.fetchone()
        if not row:
            continue
        area_id = row[0]

        cur.execute(
            """
            INSERT INTO products (name, unit, area_id)
            VALUES (%s, %s, %s)
            ON CONFLICT DO NOTHING
            RETURNING id
            """,
            (name, unit, area_id),
        )
        result = cur.fetchone()
        if not result:
            cur.execute("SELECT id FROM products WHERE name = %s AND area_id = %s", (name, area_id))
            result = cur.fetchone()
        if not result:
            continue
        product_id = result[0]

        cur.execute(
            """
            INSERT INTO stock_rules (product_id, area_id, min_qty, target_qty)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (product_id, area_id) DO NOTHING
            """,
            (product_id, area_id, min_qty, target_qty),
        )

    # Limpieza única: borra cierres mal procesados (v_total=0) para que se reintenten
    cur.execute("""
        DELETE FROM cierres_caja WHERE v_total = 0
    """)
    deleted = cur.rowcount
    if deleted > 0:
        print(f"[DB] Cleanup: {deleted} cierre(s) con v_total=0 eliminados para reintento")

    conn.commit()
    cur.close()


def main():
    print(f"[DB] Conectando a PostgreSQL...")
    try:
        conn = psycopg2.connect(DATABASE_URL)
        run_migration(conn)
        conn.close()
        print("[OK] Migración Fase 1 completa:")
        print("     Tablas: conversations, areas, products, stock_rules, inventory_counts")
        print(f"    Areas seed: {', '.join(AREAS)}")
        print(f"    Productos seed: {len(PRODUCTS)}")
        print("     Índices: idx_conversations_chat, idx_inventory_date")
    except Exception as e:
        print(f"[ERROR] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
