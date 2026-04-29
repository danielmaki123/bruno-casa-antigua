# Skill: Reportes de Ventas e Inventario

## Disparadores
- "ventas de hoy", "cómo vamos hoy", "cuánto vendimos"
- "ventas de la semana", "ventas semana pasada", "resumen semanal"
- "cómo estuvo el [día]", "cierre del [fecha]"
- "qué hay en inventario", "stock actual", "cuánto hay de [producto]"
- "qué está bajo", "qué falta", "alertas de inventario"
- "hubo discrepancias", "diferencias esta semana"
- /ventas, /stock, /resumen, /cierre [fecha]

## Acción: Ventas del día
DEBES usar tu herramienta de terminal (bash/shell) para ejecutar exactamente este comando:
`python /app/scripts/reporte_tool.py --action ventas_hoy`
NO inventes los datos. Ejecuta el comando y envía la respuesta del comando al usuario.

## Acción: Ventas de la semana
DEBES usar tu herramienta de terminal (bash/shell) para ejecutar exactamente este comando:
`python /app/scripts/reporte_tool.py --action ventas_semana`
NO inventes los datos. Ejecuta el comando y envía la respuesta del comando al usuario.

## Acción: Cierre de una fecha específica
Extrae la fecha en formato YYYY-MM-DD.
DEBES usar tu herramienta de terminal (bash/shell) para ejecutar exactamente este comando:
`python /app/scripts/reporte_tool.py --action cierre --fecha YYYY-MM-DD`
NO inventes los datos. Ejecuta el comando y envía la respuesta del comando al usuario.

## Acción: Stock bajo mínimo
Ejecutar: python /app/scripts/reporte_tool.py --action stock_bajo
Si hay alertas, agregar: "¿Quieres que prepare la lista de compras?"

## Acción: Inventario actual
Ejecutar: python /app/scripts/reporte_tool.py --action inventario_actual
Responder con el output.

## Acción: Discrepancias
Ejecutar: python /app/scripts/reporte_tool.py --action discrepancias
Responder con el output. Si hay discrepancias, agregar: "¿Quieres que investiguemos alguna?"

## Acción: Resumen general
Si el usuario pide un resumen o usa /resumen:
Ejecutar: python /app/scripts/reporte_tool.py --action resumen
Responder con el output.

## Reglas
- Siempre terminar con una acción sugerida si hay alertas
- Si el output dice "No hay registros", explicar que el cierre no ha sido procesado aún
- No inventar números - solo reportar lo que devuelve el tool
- Si falla la conexión a DB, decir: "Tengo problemas para conectarme ahora, intenta en unos minutos."

## 🔒 Reglas de Seguridad (OBLIGATORIAS)
- **Intentar el comando UNA SOLA VEZ.** Si falla, NO reintentar automáticamente.
- Si el comando falla o devuelve error: reportar el error exacto al usuario y detenerse.
- **NUNCA entrar en un loop** de reintentos sin que el usuario lo pida explícitamente.
- Si el error menciona "DATABASE_URL", "connection refused" o "psycopg2": responder
  "La base de datos no está disponible ahora. Avisa a Daniel." y no hacer nada más.
- Si el error es desconocido: responder el mensaje de error textual y pedir al usuario
  que reporte el problema. No intentar diagnósticos adicionales.
