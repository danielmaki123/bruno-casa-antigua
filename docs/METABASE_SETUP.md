# METABASE_SETUP.md — Casa Antigua Dashboard

## 1. EasyPanel — Nuevo Servicio `metabase`

| Campo | Valor |
|---|---|
| Nombre | `metabase` |
| Imagen | `metabase/metabase:latest` |
| Puerto | `3000` |

### Variables de entorno
```
MB_DB_TYPE=h2
MB_DB_FILE=/data/metabase.db
MB_JETTY_HOST=0.0.0.0
MB_ENCRYPTION_SECRET_KEY=<generar_clave_aleatoria_32chars>
```

### Volume Mount
- Container path: `/data`
- Persistir datos de Metabase entre reinicios

### Conexión a PostgreSQL (configurar dentro de Metabase UI)
```
Host: brunobot_bruno  (o 76.13.250.83 si acceso externo)
Port: 5432 (o 5435 externo)
Database: brunobot
User: postgres
Password: 06c5f13aaaaa58a7f6f1
SSL: disable
```

---

## 2. Dashboards a Crear

### Dashboard 1: Ventas Diarias
**Cards:**

Tendencia diaria:
```sql
SELECT fecha, total_ventas
FROM cierres_caja
ORDER BY fecha DESC
LIMIT 30;
```

Top 5 mejores días:
```sql
SELECT fecha, total_ventas
FROM cierres_caja
ORDER BY total_ventas DESC
LIMIT 5;
```

Efectivo vs Tarjeta esta semana:
```sql
SELECT
  SUM(efectivo_declarado) AS efectivo,
  SUM(total_ventas - efectivo_declarado) AS tarjeta
FROM cierres_caja
WHERE fecha >= CURRENT_DATE - INTERVAL '7 days';
```

Diferencia promedio de caja:
```sql
SELECT
  AVG(ABS(diferencia)) AS diferencia_promedio,
  MAX(ABS(diferencia)) AS diferencia_max
FROM cierres_caja
WHERE fecha >= CURRENT_DATE - INTERVAL '30 days';
```

---

### Dashboard 2: Inventario Bebidas

Stock actual vs mínimo:
```sql
SELECT producto, categoria, stock_actual, stock_minimo, bajo_minimo, entradas_hoy
FROM stock_vs_minimo
ORDER BY bajo_minimo DESC, categoria, producto;
```

Productos críticos hoy:
```sql
SELECT producto, categoria, stock_actual, stock_minimo,
  ROUND(((stock_minimo - stock_actual) / stock_minimo * 100)::numeric, 1) AS deficit_pct
FROM stock_vs_minimo
WHERE bajo_minimo = TRUE
ORDER BY deficit_pct DESC;
```

Histórico de stock por producto (últimos 14 días):
```sql
SELECT d.fecha, c.producto, d.cantidad_normalizada AS stock
FROM inventario_diario d
JOIN inventario_catalogo c ON c.id = d.producto_id
WHERE d.fecha >= CURRENT_DATE - INTERVAL '14 days'
ORDER BY c.producto, d.fecha;
```

---

### Dashboard 3: Discrepancias

Discrepancias activas (no resueltas):
```sql
SELECT a.fecha, c.producto, a.tipo_alerta, a.mensaje
FROM alertas_inventario a
JOIN inventario_catalogo c ON c.id = a.producto_id
WHERE a.resuelta = FALSE
ORDER BY a.fecha DESC;
```

Discrepancias por semana:
```sql
SELECT
  DATE_TRUNC('week', fecha) AS semana,
  COUNT(*) AS total_alertas,
  COUNT(*) FILTER (WHERE tipo_alerta = 'discrepancia') AS discrepancias,
  COUNT(*) FILTER (WHERE tipo_alerta = 'stock_bajo') AS stock_bajo
FROM alertas_inventario
GROUP BY semana
ORDER BY semana DESC
LIMIT 8;
```

---

### Dashboard 4: Entradas & Proveedores

Entradas esta semana:
```sql
SELECT e.fecha, c.producto, c.categoria, e.cantidad, c.unidad_tipo,
  p.nombre AS proveedor, e.responsable
FROM entradas_inventario e
JOIN inventario_catalogo c ON c.id = e.producto_id
LEFT JOIN proveedores p ON p.id = e.proveedor_id
WHERE e.fecha >= CURRENT_DATE - INTERVAL '7 days'
ORDER BY e.fecha DESC, c.categoria;
```

Total por proveedor este mes:
```sql
SELECT p.nombre AS proveedor,
  COUNT(DISTINCT e.fecha) AS dias_entrega,
  COUNT(*) AS productos_entregados
FROM entradas_inventario e
JOIN proveedores p ON p.id = e.proveedor_id
WHERE e.fecha >= DATE_TRUNC('month', CURRENT_DATE)
GROUP BY p.nombre
ORDER BY dias_entrega DESC;
```

---

### Dashboard 5: Resumen Ejecutivo (KPIs)

Ventas semana actual:
```sql
SELECT COALESCE(SUM(total_ventas), 0) AS ventas_semana
FROM cierres_caja
WHERE fecha >= DATE_TRUNC('week', CURRENT_DATE);
```

Ventas mes actual:
```sql
SELECT COALESCE(SUM(total_ventas), 0) AS ventas_mes
FROM cierres_caja
WHERE fecha >= DATE_TRUNC('month', CURRENT_DATE);
```

Alertas activas:
```sql
SELECT COUNT(*) AS alertas_activas
FROM alertas_inventario
WHERE resuelta = FALSE AND fecha >= CURRENT_DATE - INTERVAL '3 days';
```

Productos bajo mínimo:
```sql
SELECT COUNT(*) AS bajo_minimo
FROM stock_vs_minimo
WHERE bajo_minimo = TRUE;
```

Último cierre registrado:
```sql
SELECT fecha, total_ventas, diferencia
FROM cierres_caja
ORDER BY fecha DESC
LIMIT 1;
```

---

## 3. Acceso

Una vez desplegado en EasyPanel:
- URL: `http://tu-servidor:3000` o dominio configurado
- Primera vez: crear cuenta admin en la UI
- Conectar DB: Settings → Databases → Add Database → PostgreSQL

## 4. Permisos recomendados

| Usuario | Acceso |
|---|---|
| Admin | Todo |
| Supervisor (Flor) | Solo Dashboard 2 (Inventario) |
| Cocina | Sin acceso |
