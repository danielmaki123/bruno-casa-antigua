"""
db_setup.py — Crea las tablas en PostgreSQL para BrunoBot
Ejecutar una sola vez: python scripts/db_setup.py

Tablas:
  - cierres_caja     → Un registro por cierre de caja diario
  - ventas_detalle   → Un registro por producto vendido por cierre (para analytics)
"""
import os
import sys
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

# ── Config ────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("[ERROR] DATABASE_URL no está configurado en .env")
    sys.exit(1)

# ── SQL ───────────────────────────────────────────────────────────────────────
SQL = """
-- ============================================================
-- Tabla principal: un registro por cierre de caja
-- ============================================================
CREATE TABLE IF NOT EXISTS cierres_caja (
    id                      SERIAL PRIMARY KEY,

    -- Identificación
    documento_id            VARCHAR(20)   NOT NULL UNIQUE,   -- ej: 00000289
    fecha                   DATE          NOT NULL,
    cajero                  VARCHAR(100),
    terminal                VARCHAR(50),
    factura_desde           VARCHAR(20),
    factura_hasta           VARCHAR(20),
    num_facturas            INT           DEFAULT 0,
    facturas_anuladas       INT           DEFAULT 0,
    apertura                TIMESTAMP,
    cierre                  TIMESTAMP,

    -- Datos de venta
    exonerado               NUMERIC(12,2) DEFAULT 0,
    gravado                 NUMERIC(12,2) DEFAULT 0,
    subtotal                NUMERIC(12,2) DEFAULT 0,
    descuento               NUMERIC(12,2) DEFAULT 0,
    iva                     NUMERIC(12,2) DEFAULT 0,
    propina                 NUMERIC(12,2) DEFAULT 0,
    v_total                 NUMERIC(12,2) DEFAULT 0,

    -- Medios de pago
    efectivo_cds            NUMERIC(12,2) DEFAULT 0,
    efectivo_usd            NUMERIC(12,2) DEFAULT 0,
    tarjetas_total          NUMERIC(12,2) DEFAULT 0,
    transferencias_total    NUMERIC(12,2) DEFAULT 0,

    -- Conteo físico de efectivo
    conteo_efectivo_cds     NUMERIC(12,2) DEFAULT 0,
    conteo_efectivo_usd     NUMERIC(12,2) DEFAULT 0,
    total_conteo_cds        NUMERIC(12,2) DEFAULT 0,

    -- Auditoría / reconciliación
    declaracion_pos         NUMERIC(12,2) DEFAULT 0,
    apertura_custodio       NUMERIC(12,2) DEFAULT 0,
    faltante                NUMERIC(12,2) DEFAULT 0,
    sobrante                NUMERIC(12,2) DEFAULT 0,
    diferencia_pos          NUMERIC(12,2) DEFAULT 0,
    tipo_cambio             NUMERIC(8,4)  DEFAULT 0,

    -- Auditoría Bruno
    auditado                BOOLEAN       DEFAULT FALSE,
    alerta_diferencia       BOOLEAN       DEFAULT FALSE,   -- TRUE si diferencia_pos > umbral
    alerta_faltante         BOOLEAN       DEFAULT FALSE,   -- TRUE si faltante > 0
    notas_auditoria         TEXT,

    -- Metadatos
    created_at              TIMESTAMP     DEFAULT NOW(),
    updated_at              TIMESTAMP     DEFAULT NOW()
);

-- ============================================================
-- Tabla de detalle: un registro por producto por cierre
-- Para analytics: top productos, ventas por categoría, etc.
-- ============================================================
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
    created_at      TIMESTAMP     DEFAULT NOW()
);

-- ============================================================
-- Índices para queries de analytics (dashboard futuro)
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_cierres_fecha        ON cierres_caja (fecha);
CREATE INDEX IF NOT EXISTS idx_cierres_cajero       ON cierres_caja (cajero);
CREATE INDEX IF NOT EXISTS idx_cierres_alerta       ON cierres_caja (alerta_diferencia, alerta_faltante);

CREATE INDEX IF NOT EXISTS idx_ventas_cierre_id     ON ventas_detalle (cierre_id);
CREATE INDEX IF NOT EXISTS idx_ventas_fecha         ON ventas_detalle (fecha);
CREATE INDEX IF NOT EXISTS idx_ventas_categoria     ON ventas_detalle (categoria);
CREATE INDEX IF NOT EXISTS idx_ventas_descripcion   ON ventas_detalle (descripcion);

-- ============================================================
-- Vista: ventas por categoría (lista para dashboard)
-- ============================================================
CREATE OR REPLACE VIEW ventas_por_categoria AS
SELECT
    fecha,
    categoria,
    SUM(cantidad)        AS total_unidades,
    SUM(monto)           AS total_monto,
    COUNT(DISTINCT cierre_id) AS num_cierres
FROM ventas_detalle
GROUP BY fecha, categoria
ORDER BY fecha DESC, total_monto DESC;

-- ============================================================
-- Vista: top productos (lista para dashboard)
-- ============================================================
CREATE OR REPLACE VIEW top_productos AS
SELECT
    descripcion,
    categoria,
    SUM(cantidad)    AS total_unidades,
    SUM(monto)       AS total_monto,
    AVG(precio_unitario) AS precio_promedio,
    COUNT(DISTINCT cierre_id) AS dias_vendido
FROM ventas_detalle
GROUP BY descripcion, categoria
ORDER BY total_monto DESC;

-- ============================================================
-- Vista: resumen financiero diario (lista para dashboard)
-- ============================================================
CREATE OR REPLACE VIEW resumen_financiero AS
SELECT
    fecha,
    COUNT(*)             AS num_cierres,
    SUM(v_total)         AS ventas_totales,
    SUM(propina)         AS propinas,
    SUM(efectivo_cds)    AS efectivo_cds,
    SUM(tarjetas_total)  AS tarjetas,
    SUM(transferencias_total) AS transferencias,
    SUM(faltante)        AS faltantes,
    SUM(sobrante)        AS sobrantes,
    SUM(diferencia_pos)  AS diferencias_pos,
    COUNT(*) FILTER (WHERE alerta_diferencia) AS cierres_con_alerta
FROM cierres_caja
GROUP BY fecha
ORDER BY fecha DESC;
"""

# ── Ejecutar ──────────────────────────────────────────────────────────────────
def main():
    print(f"[DB] Conectando a PostgreSQL...")
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute(SQL)
        conn.commit()
        cur.close()
        conn.close()
        print("[OK] Tablas creadas exitosamente:")
        print("     - cierres_caja")
        print("     - ventas_detalle")
        print("     - Vista: ventas_por_categoria")
        print("     - Vista: top_productos")
        print("     - Vista: resumen_financiero")
        print("[OK] Indices de analytics creados.")
        print("[OK] Base de datos lista para el dashboard.")
    except Exception as e:
        print(f"[ERROR] {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
