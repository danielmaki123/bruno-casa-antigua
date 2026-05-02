# Issue #8: Skill Inventario — stock check + reporte rápido Telegram

**Type:** AFK
**Blocked by:** #2 (DB migration — tablas products, stock_rules, inventory_counts), #5 (message router)

## What to build

Crear `skills/inventario.py` — módulo de inventario con dos flujos:

### Flujo 1: Consulta de stock
`stock_check(area: str = None) → dict` — lista productos con cantidad actual, nivel mínimo, y estado (ok/bajo/crítico).

Query: `inventory_counts` (último conteo por producto) JOIN `stock_rules` (mínimos).

### Flujo 2: Reporte rápido via Telegram
`registrar_movimiento(message: str, user_name: str) → dict` — recibe texto libre ("llegaron 10 cajas coca cola"), usa LLM para extraer producto + cantidad + tipo (entrada/salida/merma), guarda en `inventory_counts`, retorna confirmación.

### Flujo 3: Alertas bajo mínimo
`check_alerts(area: str = None) → list[dict]` — compara conteos actuales vs `stock_rules.min_qty`, retorna lista de productos bajo mínimo.

Flujo end-to-end (consulta):
```
Flor: "/inventario bebidas"
→ classify → {intent: "stock_check", entities: {area: "bebidas"}}
→ inventario.stock_check("bebidas") → [{product: "Coca Cola", qty: 5, min: 12, status: "bajo"}, ...]
→ llm.humanize(data) → "📦 Inventario Bebidas:\n🚨 Coca Cola: 5 (mín 12)..."
```

Flujo end-to-end (reporte rápido):
```
Jean: "llegaron 10 cajas coca cola"
→ classify → {intent: "stock_report", entities: {product: "coca cola", qty: 10, unit: "cajas"}}
→ inventario.registrar_movimiento(...) → {ok: true, product: "Coca Cola", new_qty: 15}
→ "✅ Registrado: 10 cajas Coca Cola — Jean. Stock actual: 15"
```

## Acceptance criteria

- [ ] `skills/inventario.py` con `stock_check()`, `registrar_movimiento()`, `check_alerts()`
- [ ] `stock_check()` consulta tablas `inventory_counts` + `stock_rules` + `products`
- [ ] `registrar_movimiento()` usa LLM para extraer entidades de texto libre
- [ ] Guarda en `inventory_counts` con source='telegram'
- [ ] `check_alerts()` retorna productos donde `counted_qty < min_qty`
- [ ] Registrado en handlers.py para intents: `stock_check`, `stock_report`, `stock_alerts`
- [ ] End-to-end funciona en grupo Inventario
- [ ] Confirmación visible en grupo para que todos vean los movimientos

## References
- `scripts/reporte_tool.py` — acción `stock_bajo` e `inventario_actual`
- `skills/inventory_auditor.py` — lógica de auditoría existente
- `docs/PRD-MVP.md` — schema inventory_counts
- `Casa_Antigua_Inventario_v4_DINAMICO (1).xlsx` — productos reales
