# Issue #7: Skill Cierres — consultas cierre + alerta automática

**Type:** AFK
**Blocked by:** #5 (message router)

## What to build

Crear `skills/cierres.py` — módulo que consulta cierres de caja y procesa alertas.

Funciones:
1. `cierre_status(fecha: str) → dict` — estado del cierre: totales, pagos por método, validaciones, alertas
2. `procesar_cierre_nuevo(cierre_data: dict, ventas_data: list) → dict` — recibe datos parseados de un PDF nuevo, ejecuta validaciones, guarda en DB, retorna resumen

Validaciones automáticas (ya parcialmente en `skills/admin_auditor.py`):
- `venta_menu.total == cierre.subtotal` (tolerancia ±5)
- `subtotal + propina == total`
- `diferencia_pos > umbral` → alerta
- `faltante > 0` → alerta
- Documento duplicado

Reutilizar:
- `skills/parsers.py` — parse_cierre_pdf, parse_ventas_pdf (tal cual)
- `skills/admin_auditor.py` — auditar_finanzas (adaptar para retornar dict)

Flujo alerta automática (cuando bruno-monitor envía webhook):
```
bruno-monitor detecta PDF → POST /webhook/cierre → handlers.py
→ cierres.procesar_cierre_nuevo(data) → save DB + validar
→ llm.humanize(resultado) → "💰 Cierre 30/04 — C$ 26,123..."
→ Telegram send → grupo Admin
```

## Acceptance criteria

- [ ] `skills/cierres.py` con `cierre_status()` y `procesar_cierre_nuevo()`
- [ ] Validaciones automáticas funcionan (subtotal+propina, diferencia POS, duplicados)
- [ ] Reutiliza `skills/parsers.py` sin modificar
- [ ] Adapta lógica de `skills/admin_auditor.py`
- [ ] Registrado en handlers.py para intent `closing_status`
- [ ] End-to-end: usuario pregunta "cierre de ayer" → recibe datos reales
- [ ] Alerta automática envía resumen al grupo Admin cuando llega cierre nuevo
- [ ] Umbral de diferencia configurable (no hardcoded 50)

## References
- `skills/parsers.py` — PDF parsing existente
- `skills/admin_auditor.py` — auditoría financiera existente
- `scripts/audit_cierre.py` — referencia de flujo completo
- `docs/PRD-MVP.md` — formato de resumen Telegram
