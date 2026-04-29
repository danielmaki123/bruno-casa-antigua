BEGIN;

CREATE TABLE IF NOT EXISTS proveedores (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    telefono VARCHAR(30),
    dia_pedido VARCHAR(20),
    notas TEXT,
    activo BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS inventario_catalogo (
    id SERIAL PRIMARY KEY,
    producto VARCHAR(100) NOT NULL UNIQUE,
    categoria VARCHAR(50),
    unidad_tipo VARCHAR(20),
    stock_minimo NUMERIC(10,3) DEFAULT 0,
    proveedor_id INT REFERENCES proveedores(id),
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

CREATE TABLE IF NOT EXISTS alertas_inventario (
    id SERIAL PRIMARY KEY,
    fecha DATE NOT NULL,
    tipo VARCHAR(30),
    producto_id INT REFERENCES inventario_catalogo(id),
    mensaje TEXT,
    enviado BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_inv_diario_fecha
    ON inventario_diario(fecha);

CREATE INDEX IF NOT EXISTS idx_inv_diario_producto
    ON inventario_diario(producto_id);

CREATE INDEX IF NOT EXISTS idx_alertas_fecha
    ON alertas_inventario(fecha, enviado);

CREATE TABLE IF NOT EXISTS entradas_inventario (
    id SERIAL PRIMARY KEY,
    fecha DATE NOT NULL,
    producto_id INT REFERENCES inventario_catalogo(id),
    cantidad NUMERIC(10,3) NOT NULL,
    unidad VARCHAR(20),
    proveedor_id INT REFERENCES proveedores(id),
    responsable VARCHAR(100),
    notas TEXT,
    fuente VARCHAR(20) DEFAULT 'sheets',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_entradas_fecha ON entradas_inventario(fecha);
CREATE INDEX IF NOT EXISTS idx_entradas_producto ON entradas_inventario(producto_id);

CREATE OR REPLACE VIEW stock_vs_minimo AS
SELECT
    c.producto,
    c.categoria,
    c.unidad_tipo,
    c.stock_minimo,
    d.fecha,
    d.cantidad_normalizada AS stock_actual,
    COALESCE(e.total_entradas, 0) AS entradas_hoy,
    LAG(d.cantidad_normalizada) OVER (PARTITION BY c.id ORDER BY d.fecha) AS stock_ayer,
    CASE WHEN d.cantidad_normalizada < c.stock_minimo THEN TRUE ELSE FALSE END AS bajo_minimo,
    p.nombre AS proveedor
FROM inventario_catalogo c
LEFT JOIN inventario_diario d
    ON c.id = d.producto_id
    AND d.fecha = CURRENT_DATE
LEFT JOIN (
    SELECT producto_id, SUM(cantidad) AS total_entradas
    FROM entradas_inventario
    WHERE fecha = CURRENT_DATE
    GROUP BY producto_id
) e ON c.id = e.producto_id
LEFT JOIN proveedores p
    ON c.proveedor_id = p.id
WHERE c.activo = TRUE
ORDER BY bajo_minimo DESC, c.categoria, c.producto;

COMMIT;
