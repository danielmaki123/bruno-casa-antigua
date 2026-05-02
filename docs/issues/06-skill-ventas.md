# Issue #6: Skill Ventas — consultas de ventas end-to-end

**Type:** AFK
**Blocked by:** #5 (message router)

## What to build

Crear `skills/ventas.py` — módulo que consulta ventas en PostgreSQL y retorna datos estructurados.

Funciones:
1. `ventas_dia(fecha: str) → dict` — total ventas, tickets, propinas de un día
2. `ventas_semana() → dict` — resumen de los últimos 7 días
3. `top_productos(rango: str) → list[dict]` — top 5-10 productos por monto

Reutilizar queries de `scripts/reporte_tool.py` (ya tiene 8 acciones probadas). Las tablas `cierres_caja` y `ventas_detalle` ya existen con datos reales.

Cada función retorna `dict` con datos crudos. El router pasa estos datos a `llm.humanize()` para generar la respuesta natural.

Flujo completo end-to-end:
```
Usuario: "¿cómo van las ventas hoy?"
→ handlers.py detecta texto libre
→ llm.classify_intent() → {intent: "sales_today"}
→ ventas.ventas_dia(hoy) → {total: 24173, tickets: 22, top: [...]}
→ llm.humanize(data) → "💰 Ventas hoy: C$ 24,173..."
→ Telegram reply
```

## Acceptance criteria

- [ ] `skills/ventas.py` con `ventas_dia()`, `ventas_semana()`, `top_productos()`
- [ ] Queries usan tablas existentes (`cierres_caja`, `ventas_detalle`)
- [ ] Retorna dicts, no texto formateado (la capa LLM formatea)
- [ ] Registrado en handlers.py para intents: `sales_today`, `sales_by_date`, `top_products`
- [ ] End-to-end funciona: usuario pregunta en Telegram → recibe respuesta con datos reales
- [ ] Si no hay datos para la fecha, retorna dict vacío (no error)
- [ ] Usa `database/postgres.py` para queries

## References
- `scripts/reporte_tool.py` — queries existentes (copiar/adaptar, NO importar el script)
- `scripts/db_setup.py` — schema de tablas y vistas
- `docs/PRD-MVP.md` — intents y permisos
