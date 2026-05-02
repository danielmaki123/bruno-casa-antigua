# ADR-0006: Captura de inventario — Sheets bridge + Telegram rápido + web app futura

## Status
Accepted

## Context
El equipo hace conteo diario de inventario en Google Sheets (Casa_Antigua_Inventario_v4_DINAMICO). Tres canales evaluados: mantener Sheets, migrar a Telegram, construir web app.

## Decision
**Tres canales coexisten, cada uno para su caso de uso:**

1. **Google Sheets** (bridge, Fase 1-2): conteo completo diario de 30+ productos. El equipo ya lo conoce. n8n detecta cambios y sincroniza a Postgres.

2. **Telegram** (MVP): reportes rápidos durante el día. "Llegaron 10 cajas coca cola", "se acabó el vodka". Kimi extrae producto + cantidad, guarda en Postgres, confirma en grupo.

3. **Web app** (Fase 3): formulario móvil para conteo formal. Reemplaza Sheets como canal principal. Se construye cuando el flujo esté validado.

## Consequences
- **Cero fricción** — el equipo no cambia sus hábitos en Fase 1
- **Datos en Postgres** — independiente del canal de entrada, todo termina en la misma DB
- **Telegram agrega valor inmediato** — movimientos rápidos sin abrir Sheets
- **Trade-off:** sync Sheets→Postgres puede tener latencia y conflictos si alguien edita mientras sincroniza. Mitigación: sync unidireccional (Sheets→Postgres), Sheets es input-only
