# Skill: Google Sheets — Leer y Escribir Datos
# Propósito: Puente entre Bruno y la base de datos del restaurante en Google Sheets

## Cuándo usar este skill
- Siempre que necesito leer datos del restaurante (inventario, insumos, empleados, ventas)
- Siempre que necesito guardar un registro nuevo

## Herramientas
- Terminal: ejecutar scripts/sheets_tool.py

## Comandos exactos disponibles

### Ver estado de stock actual (más útil)
python scripts/sheets_tool.py --action get_stock_status
Devuelve JSON con estado de cada insumo: ok/bajo/critico, cantidad actual, mínimo, crítico.

### Leer inventario completo
python scripts/sheets_tool.py --action read --sheet INVENTARIO
Devuelve JSON con todas las filas de inventario históricas.

### Leer catálogo de insumos
python scripts/sheets_tool.py --action read --sheet INSUMOS
Devuelve insumo_id, nombre, unidad_base, stock_minimo, stock_critico, proveedor, área.

### Leer empleados
python scripts/sheets_tool.py --action read --sheet EMPLEADOS

### Leer eventos del calendario
python scripts/sheets_tool.py --action read --sheet EVENTOS_CALENDARIO
Devuelve cumpleaños, pagos, planillas, vacaciones con fecha, tipo, descripcion, monto_estimado, estado.

### Leer ventas del día
python scripts/sheets_tool.py --action read --sheet VENTAS_DIARIAS

### Guardar reporte de inventario
python scripts/sheets_tool.py --action append --sheet INVENTARIO --data '{"fecha":"FECHA_HOY","turno":"mañana","area":"Cocina","insumo_id":"I002","cantidad_fisica":"423","responsable":"María","notas":""}'

IMPORTANTE: cantidad_fisica siempre en la unidad base del insumo (oz para carnes, unidades para tortillas, cajas para cerveza, botellas para vodka).

## Mapeo de insumos (nombre común → insumo_id → área)
- pollo, chicken, pechuga → I002 → Cocina
- carne, res, beef, bistec → I001 → Cocina
- papas, papa, potato → I003 → Cocina
- arroz, rice → I004 → Cocina
- tortilla, tortillas → I005 → Cocina
- cerveza, beer, lager → I006 → Barra
- vodka → I007 → Barra
- refresco, cola, soda → I008 → Barra

## Conversión de unidades
- 1 kg = 35.274 oz (para carnes y papas: multiplicar kg × 35.274)
- 1 lb = 16 oz
- 1 gr = 0.035 oz
- Tortillas: siempre en unidades (piezas)
- Cerveza: siempre en cajas
- Vodka: siempre en botellas

## Proveedores de referencia
- I001 Carne: Carnicería López — Tel: 5587654321
- I002 Pollo: Don José — Tel: 5512345678
- I003 Papas: Mercado Central — mercado@email.com
- I004 Arroz: Surtidora Central — surtidora@email.com
- I005 Tortilla: Tortillería Doña María — Tel: 5567890123
- I006 Cerveza: Cervecería del Valle — Tel: 5578912345
- I007 Vodka: Distribuidora Licores — Tel: 5566778899
- I008 Refresco: Coca-Cola regional — Tel: 5544332211

## Manejo de errores
Si el script devuelve {"error": "..."}, reportar al usuario en lenguaje claro.
No mostrar mensajes técnicos al usuario, traducir el error.
