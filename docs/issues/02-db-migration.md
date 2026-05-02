# Issue #2: DB Migration Fase 1 — 5 tablas nuevas + seed data

**Type:** AFK
**Blocked by:** None — can start immediately (parallel with #1)

## What to build

Crear script de migración que agrega las 5 tablas nuevas de Fase 1 a PostgreSQL. NO modificar tablas existentes (`cierres_caja`, `ventas_detalle`). Solo agregar.

Tablas nuevas:
- `conversations` — memoria del bot
- `areas` — zonas operativas del restaurante
- `products` — catálogo de insumos
- `stock_rules` — mínimos por producto/área
- `inventory_counts` — conteos diarios

Leer `docs/PRD-MVP.md` sección "Schema Fase 1" para DDL exacto. Leer `docs/adr/0003-db-schema-phased.md` para la decisión.

Además, crear seed data para `areas` con los 6 valores reales: bebidas, cocina, barra, sushi, birria, pizza.

El archivo `Casa_Antigua_Inventario_v4_DINAMICO (1).xlsx` contiene productos reales — usarlo como referencia para seed de `products` si es posible leerlo con pandas/openpyxl.

## Acceptance criteria

- [ ] `scripts/db_migration_fase1.py` crea las 5 tablas (idempotente con IF NOT EXISTS)
- [ ] Tablas existentes (`cierres_caja`, `ventas_detalle`) no se tocan
- [ ] `areas` tiene seed con 6 áreas reales
- [ ] `products` tiene seed con al menos 20 productos del Excel
- [ ] `stock_rules` tiene seed con mínimos para los productos principales
- [ ] Índices creados: `idx_conversations_chat`, `idx_inventory_date`
- [ ] Script se puede correr múltiples veces sin error (idempotente)
- [ ] Vistas existentes (`ventas_por_categoria`, `top_productos`, `resumen_financiero`) siguen funcionando

## References
- `scripts/db_setup.py` — referencia de cómo se hizo antes (misma estructura)
- `docs/PRD-MVP.md` — DDL exacto en sección "Schema Fase 1"
- `Casa_Antigua_Inventario_v4_DINAMICO (1).xlsx` — datos reales de productos
- `database/postgres.py` — connector existente (reutilizar)
