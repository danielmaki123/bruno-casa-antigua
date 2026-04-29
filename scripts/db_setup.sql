-- ============================================================
-- BrunoBot — Setup de base de datos
-- Correr en EasyPanel > PostgreSQL service > SQL console
-- ============================================================

-- Tabla principal: un registro por cierre de caja
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

-- Tabla de detalle: un registro por producto por cierre
CREATE TABLE IF NOT EXISTS ventas_detalle (
    id              SERIAL PRIMARY KEY,
    cierre_id       VARCHAR(20)   NOT NULL REFERENCES cierres_caja(documento_id) ON DELETE CASCADE,
    fecha           DATE          NOT NULL,
    categoria       VARCHAR(100),
    descripcion     VARCHAR(200)  NOT NULL,
    cantidad        INT           DEFAULT 0,
    monto           NUMERIC(12,2) DEFAULT 0,
    created_at      TIMESTAMP     DEFAULT NOW()
);

-- Índices para analytics
CREATE INDEX IF NOT EXISTS idx_cierres_fecha     ON cierres_caja (fecha);
CREATE INDEX IF NOT EXISTS idx_cierres_cajero    ON cierres_caja (cajero);
CREATE INDEX IF NOT EXISTS idx_cierres_alerta    ON cierres_caja (alerta_diferencia, alerta_faltante);
CREATE INDEX IF NOT EXISTS idx_ventas_cierre_id  ON ventas_detalle (cierre_id);
CREATE INDEX IF NOT EXISTS idx_ventas_fecha      ON ventas_detalle (fecha);
CREATE INDEX IF NOT EXISTS idx_ventas_categoria  ON ventas_detalle (categoria);
CREATE INDEX IF NOT EXISTS idx_ventas_desc       ON ventas_detalle (descripcion);

-- Vista: ventas por categoría
CREATE OR REPLACE VIEW ventas_por_categoria AS
SELECT
    fecha,
    categoria,
    SUM(cantidad)             AS total_unidades,
    SUM(monto)                AS total_monto,
    COUNT(DISTINCT cierre_id) AS num_cierres
FROM ventas_detalle
GROUP BY fecha, categoria
ORDER BY fecha DESC, total_monto DESC;

-- Vista: top productos
CREATE OR REPLACE VIEW top_productos AS
SELECT
    descripcion,
    categoria,
    SUM(cantidad)                               AS total_unidades,
    SUM(monto)                                  AS total_monto,
    ROUND(SUM(monto) / NULLIF(SUM(cantidad),0), 2) AS precio_promedio,
    COUNT(DISTINCT cierre_id)                   AS dias_vendido
FROM ventas_detalle
GROUP BY descripcion, categoria
ORDER BY total_monto DESC;

-- Vista: resumen financiero diario
CREATE OR REPLACE VIEW resumen_financiero AS
SELECT
    fecha,
    COUNT(*)              AS num_cierres,
    SUM(v_total)          AS ventas_totales,
    SUM(propina)          AS propinas,
    SUM(efectivo_cds)     AS efectivo_cds,
    SUM(tarjetas_total)   AS tarjetas,
    SUM(transferencias_total)  AS transferencias,
    SUM(faltante)         AS faltantes,
    SUM(sobrante)         AS sobrantes,
    SUM(diferencia_pos)   AS diferencias_pos,
    COUNT(*) FILTER (WHERE alerta_diferencia OR alerta_faltante) AS cierres_con_alerta
FROM cierres_caja
GROUP BY fecha
ORDER BY fecha DESC;
