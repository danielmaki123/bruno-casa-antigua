-- Deduplicar inventario_diario y prevenir duplicados futuros
-- Mantiene la fila con mayor id para cada (fecha, producto_id)

DELETE FROM inventario_diario a
USING inventario_diario b
WHERE a.fecha = b.fecha
  AND a.producto_id = b.producto_id
  AND a.id < b.id;

ALTER TABLE inventario_diario
ADD CONSTRAINT inventario_diario_fecha_producto_id_key
UNIQUE (fecha, producto_id);
