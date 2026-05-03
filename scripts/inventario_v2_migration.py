import logging

logger = logging.getLogger(__name__)

DDL = """
ALTER TABLE products ADD COLUMN IF NOT EXISTS external_id VARCHAR(20);

CREATE TABLE IF NOT EXISTS inventory_entries (
    id          SERIAL PRIMARY KEY,
    date        DATE NOT NULL,
    product_id  INT REFERENCES products(id),
    qty         NUMERIC(10,3) NOT NULL,
    responsable VARCHAR(100),
    source      VARCHAR(20) DEFAULT 'sheets',
    created_at  TIMESTAMP DEFAULT NOW(),
    UNIQUE (date, product_id, source)
);

CREATE INDEX IF NOT EXISTS idx_inventory_entries_date
    ON inventory_entries(date);

CREATE INDEX IF NOT EXISTS idx_inventory_entries_product
    ON inventory_entries(product_id);

ALTER TABLE stock_rules ADD COLUMN IF NOT EXISTS provider_name VARCHAR(100);
"""


def run_migration(conn):
    cur = conn.cursor()
    logger.info("[DB] Migración inventario v2...")
    cur.execute(DDL)
    conn.commit()
    cur.close()
    logger.info("[DB] Migración inventario v2 OK")
