# SKILL: ventas (STRICT COMMAND CONTRACT)

## IMMUTABLE_EXECUTABLE
`/app/scripts/reporte_tool.py`

## COMMAND_MAP (ONLY ALLOWED COMMANDS)
- ventas_hoy -> `python /app/scripts/reporte_tool.py --action ventas_hoy`
- ventas_semana -> `python /app/scripts/reporte_tool.py --action ventas_semana`
- cierre_fecha(YYYY-MM-DD) -> `python /app/scripts/reporte_tool.py --action cierre --fecha YYYY-MM-DD`
- stock_bajo -> `python /app/scripts/reporte_tool.py --action stock_bajo`
- inventario_actual -> `python /app/scripts/reporte_tool.py --action inventario_actual`
- discrepancias -> `python /app/scripts/reporte_tool.py --action discrepancias`
- resumen -> `python /app/scripts/reporte_tool.py --action resumen`
- ventas_categorias -> `python /app/scripts/reporte_tool.py --action ventas_categorias`
- ventas_categorias_fecha(YYYY-MM-DD) -> `python /app/scripts/reporte_tool.py --action ventas_categorias --fecha YYYY-MM-DD`

## HARD RULES (FOR THE AGENT)
1. NEVER create, infer, or guess filenames.
2. NEVER use relative paths like `scripts/*.py`.
3. If the user asks for "ventas", "stock", or "inventario", pick the matching command from the map above.
4. Execute the command using the `terminal` tool.
5. Return the exact stdout of the command to the user.
6. Single attempt only. If it fails, report the error.

## TRIGGER PHRASES
- "ventas de hoy", "ventas de la semana", "cuanto vendimos", "stock", "inventario", "discrepancias", "/ventas", "/stock", "ventas por categoría", "categorías"
