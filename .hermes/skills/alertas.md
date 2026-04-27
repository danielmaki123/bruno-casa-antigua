# Skill: Alertas Automáticas
# Propósito: Resúmenes diarios y alertas automáticas para Casa Antigua

## Cron Jobs (configurar en Hermes con hermes cron add)
- 08:00 diario → resumen de buenos días en grupo Team
- 22:00 diario → cierre y análisis de diferencias

## Alerta 08:00 — Buenos días equipo

### Grupos destino: Team (-5181251045)

### Paso 1: Leer datos del día
python scripts/sheets_tool.py --action read --sheet EVENTOS_CALENDARIO
python scripts/sheets_tool.py --action get_stock_status

### Paso 2: Filtrar eventos de hoy
De EVENTOS_CALENDARIO, filtrar filas donde fecha = hoy (formato YYYY-MM-DD):
- tipo = "cumpleaños" → incluir en sección Cumpleaños
- tipo = "pago" → incluir en sección Pagos
- tipo = "planilla" → incluir en sección Planilla
- tipo = "vacaciones" con fecha inicio = hoy → incluir en Recordatorios

### Paso 3: Verificar stock crítico
De get_stock_status, si algún item tiene status = "critico":
Agregar sección de alerta de stock al mensaje del grupo Inventario también.

### Paso 4: Formato del mensaje (grupo Team)
---
📅 Buenos días equipo. [NOMBRE_DÍA] [DÍA] de [MES]:

🎂 Cumpleaños:
• [Nombre] ([función]) — ¡Muchas felicidades!
(Si no hay: omitir esta sección)

💰 Pagos que vencen hoy:
• [descripción]: $[monto_estimado]
(Si no hay: "Sin vencimientos hoy ✅")

📋 Planilla:
• [descripción de la planilla]
(Si no hay: omitir esta sección)

📢 Recordatorios:
• [eventos relevantes del mes]
(Ejemplo: "Pedro de vacaciones del 15 al 22 de mayo")

Buen servicio a todos 💪
---

## Alerta 22:00 — Cierre del día

### Grupos destino: Inventario (-5240974489) y Administrativo (-4944632677) si hay diferencias

### Paso 1: Leer datos del día
python scripts/sheets_tool.py --action read --sheet VENTAS_DIARIAS
python scripts/sheets_tool.py --action read --sheet INVENTARIO
python scripts/sheets_tool.py --action read --sheet RECETAS

### Paso 2: Calcular consumo teórico
Para cada fila de VENTAS_DIARIAS con fecha = hoy:
- Buscar la receta en RECETAS (por receta_id)
- Calcular: consumo_teorico[insumo] += cantidad_vendida × cantidad_ingrediente

Ejemplo:
- 2 Lomito saltado (R001): 2 × 8oz carne = 16oz, 2 × 4oz arroz = 8oz, 2 × 4oz papas = 8oz
- 1 Tacos de res (R003): 1 × 8oz carne = 8oz, 1 × 3 tortillas = 3 tortillas
- Total teórico carne: 16 + 8 = 24oz

### Paso 3: Calcular consumo real
Del INVENTARIO de hoy, buscar la diferencia entre el reporte de mañana y el de noche:
consumo_real[insumo] = inventario_inicio_dia - inventario_fin_dia

Si no hay dos reportes del mismo día, usar solo el reporte de mañana como referencia.

### Paso 4: Detectar diferencias
Para cada insumo:
diferencia = consumo_real - consumo_teorico
Si diferencia > consumo_teorico × 0.10 (más de 10% de variación):
→ DIFERENCIA DETECTADA

### Paso 5a: Mensaje CON diferencias
---
📊 Cierre [FECHA] — Análisis consumo vs. ventas:

Ventas registradas hoy:
• [N] [Plato] — [receta_id]

DIFERENCIAS DETECTADAS:

[Insumo]: consumieron [X]oz, ventas explican [Y]oz (diferencia: [Z]oz)
→ Hipótesis ordenadas por probabilidad:
   A) [hipótesis más probable] ([%]%)
   B) [hipótesis alternativa] ([%]%)
   C) [hipótesis menor] ([%]%)
→ Acción sugerida: [qué revisar]

¿Revisar tickets ahora? Contactar a [cajero/encargado].
---

Hipótesis estándar para diferencias de carne/proteína:
A) Orden de plato no registrada en POS (70%)
B) Plato especial fuera de receta estándar (20%)
C) Merma o desperdicio no reportado (8%)
D) Error en conteo de inventario (2%)

Hipótesis para diferencias de bebidas (cerveza/vodka):
A) Cortesías no registradas (50%)
B) Happy hour sin ajuste de inventario (30%)
C) Error de conteo (20%)

### Paso 5b: Mensaje SIN diferencias
---
✅ Cierre [FECHA] — Todo cuadra:
• Ventas: [resumen de platos]
• Consumo dentro del margen esperado (±10%)
• Stock final: [estado general OK/BAJO/CRÍTICO]

Buenas noches equipo 🌙
---

## Alerta Inmediata — Stock Crítico
Se activa cuando cualquier operación devuelve status = "critico" en algún insumo.
Enviar INMEDIATAMENTE a grupo Inventario (-5240974489) Y Administrativo (-4944632677):

---
🔴 ALERTA CRÍTICA — [HORA]:
[Nombre insumo]: [cantidad] [unidad] — CRÍTICO (nivel crítico: [X] [unidad])

Proveedor: [proveedor_default]
Contacto: [contacto]

¿Generar orden urgente? Andrea o Daniel deben responder "aprobar orden [insumo]" para confirmar.
---

## Configuración de cron en Hermes
Para activar las alertas automáticas, ejecutar en Hermes CLI:
hermes cron add "0 8 * * *" "Envía el resumen de buenos días del restaurante Casa Antigua al grupo Team usando el skill de alertas"
hermes cron add "0 22 * * *" "Analiza el cierre del día del restaurante Casa Antigua: cruza ventas vs consumo y envía reporte al grupo Inventario y Administrativo"
