# ADR-0003: Schema de DB en 3 fases progresivas

## Status
Accepted

## Context
El MVP Proposal define 16 tablas. Implementarlas todas antes de tener bot funcional retrasa el lanzamiento. Pero las 2 tablas actuales (cierres_caja, ventas_detalle) no cubren inventario ni memoria del bot.

## Decision
**3 fases de schema. Solo se implementa lo que el bot usa activamente.**

### Fase 1 — MVP (bot funcional)
Mantener existentes:
- `cierres_caja` (ya existe, 30+ columnas)
- `ventas_detalle` (ya existe, con vistas analíticas)

Crear nuevas:
- `conversations` — memoria del bot (chat_id, user_id, role, content, created_at)
- `products` — catálogo maestro (name, sku, unit, area, is_active)
- `areas` — zonas operativas (bebidas, cocina, barra, sushi, birria, pizza)
- `stock_rules` — mínimos por producto (product_id, area_id, min_qty, target_qty)
- `inventory_counts` — conteos diarios sincronizados desde Sheets

### Fase 2 — Alertas + compras
- `alerts` — alertas generadas (type, product_id, severity, resolved)
- `purchase_suggestions` — compras sugeridas (product_id, suggested_qty, status)

### Fase 3 — Equipo + calendario
- `employees` — datos del equipo (name, role, area, telegram_id, hire_date)
- `attendance` — registro de asistencia
- `events` — calendario (cumpleaños, pagos, planillas, vacaciones)

## Consequences
- **Bot arranca rápido** — solo 5 tablas nuevas para Fase 1
- **Migraciones simples** — cada fase es un script SQL aditivo, nunca destructivo
- **Las 3 vistas analíticas existentes siguen funcionando** — Metabase no se rompe
- **Trade-off:** algunas funciones (compras sugeridas, asistencia) no están disponibles hasta Fase 2-3
