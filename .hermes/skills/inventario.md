# Skill: Inventario del Restaurante
# Propósito: Detectar, registrar y consultar inventario de Casa Antigua

## Disparadores (Triggers)
- Mensajes en grupo Inventario con cantidades: "pollo 12kg", "carne 3kg papas 8kg"
- Mensajes con palabras clave: "llegaron", "tenemos", "hay", "stock de", "quedamos con"
- Comando /reportar [producto] [cantidad] [unidad]
- Comando /inventario [área opcional]
- Comando /alertas
- Comando /stock [insumo]

## Paso 1: Identificar si el mensaje es un reporte de inventario
Buscar patrones: [número] [unidad] de [producto] O [producto] [número][unidad]
Ejemplos válidos:
- "pollo 12kg, carne 3kg, papas 8kg"
- "Llegaron 18 cajas de cerveza y 10 botellas de vodka"
- "Tenemos 120 oz de carne"
- "/reportar pollo 12 kg"

Ejemplos que NO son reportes (ignorar o clarificar):
- "faltan papas" → es consumo, no entrada. Preguntar: ¿Cuántas papas quedan?
- "se acabó el pollo" → stock cero, confirmar y alertar
- "deberíamos pedir carne" → sugerencia, no reporte

## Paso 2: Extraer productos del mensaje
Para cada producto mencionado, extraer:
- nombre del producto
- cantidad (número)
- unidad (kg, oz, lb, caja, botella, unidad, pieza)

## Paso 3: Mapear a insumo_id y área
pollo, pechuga, chicken → I002, Cocina
carne, res, beef, bistec → I001, Cocina
papas, papa, potato → I003, Cocina
arroz, rice → I004, Cocina
tortilla, tortillas → I005, Cocina
cerveza, beer, lager → I006, Barra
vodka → I007, Barra
refresco, cola, soda, bebida → I008, Barra

Si el insumo no se reconoce: "No conozco [producto]. ¿Es un insumo nuevo? Dime el área (Cocina/Barra/Almacén) y la unidad de medida."

## Paso 4: Convertir a unidad base
1 kg = 35.274 oz → multiplicar cantidad_kg × 35.274, redondear a entero
1 lb = 16 oz
Tortillas: ya en unidades
Cerveza: ya en cajas
Vodka: ya en botellas

Ejemplos:
- 12 kg pollo → 12 × 35.274 = 423 oz → cantidad_fisica: "423"
- 3 kg carne → 3 × 35.274 = 105 oz → cantidad_fisica: "105"
- 8 kg papas → 8 × 35.274 = 282 oz → cantidad_fisica: "282"
- 18 cajas cerveza → cantidad_fisica: "18"

## Paso 5: Determinar turno según hora del mensaje
06:00 - 13:00 → turno: "mañana"
13:00 - 20:00 → turno: "tarde"
20:00 - 02:00 → turno: "noche"

## Paso 6: Guardar en Sheets
Para cada insumo, ejecutar:
python scripts/sheets_tool.py --action append --sheet INVENTARIO --data '{"fecha":"[HOY]","turno":"[TURNO]","area":"[AREA]","insumo_id":"[ID]","cantidad_fisica":"[CANTIDAD]","responsable":"[NOMBRE_USUARIO]","notas":""}'

## Paso 7: Verificar stock
python scripts/sheets_tool.py --action get_stock_status

Interpretar resultado:
- status: "ok" → ✅
- status: "bajo" → ⚠️ BAJO (cerca del mínimo, monitorear)
- status: "critico" → 🔴 CRÍTICO (actuar urgente)

## Paso 8: Responder con confirmación

Formato de respuesta después de registrar:
✅ Reporte registrado — [TURNO] [FECHA] — por [NOMBRE]:
• [Producto]: [cantidad_original] ([oz]) ✅ OK
• [Producto]: [cantidad_original] ([oz]) ⚠️ BAJO — mín: [X] oz. Proveedor: [nombre] [tel]
• [Producto]: [cantidad_original] ([oz]) 🔴 CRÍTICO — mín: [X] oz. Llamar urgente: [nombre] [tel]

## Comando /inventario
1. Ejecutar: python scripts/sheets_tool.py --action get_stock_status
2. Formatear por área:

📦 Stock actual [HORA]:

COCINA:
• Pollo: [X] oz ✅ / ⚠️ / 🔴
• Carne de res: [X] oz ✅ / ⚠️ / 🔴
• Papas: [X] oz ✅ / ⚠️ / 🔴
• Arroz: [X] oz ✅ / ⚠️ / 🔴
• Tortillas: [X] unidades ✅ / ⚠️ / 🔴

BARRA:
• Cerveza lager: [X] cajas ✅ / ⚠️ / 🔴
• Vodka: [X] botellas ✅ / ⚠️ / 🔴
• Refresco cola: [X] cajas ✅ / ⚠️ / 🔴

## Alertas inmediatas de stock crítico
Si get_stock_status devuelve cualquier item con status "critico":
Enviar INMEDIATAMENTE a grupo Inventario Y grupo Administrativo:

🔴 ALERTA CRÍTICA — [HORA]:
[Insumo]: [cantidad] [unidad] — Por debajo del nivel crítico ([critico] [unidad] mín)
Proveedor sugerido: [proveedor] — [contacto]
¿Generar orden urgente? Responder "sí" para confirmar a Andrea/Daniel.
