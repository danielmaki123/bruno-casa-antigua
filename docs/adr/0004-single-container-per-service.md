# ADR-0004: Servicios separados en EasyPanel (no monolito)

## Status
Accepted

## Context
EasyPanel ya tiene los servicios corriendo por separado:
- postgres
- bruno-bot (apagado, pendiente reescritura)
- bruno-monitor (gmail, corriendo)
- bruno-inventario (corriendo)
- metabase
- n8n

Se evaluó consolidar en un solo contenedor con PM2 para simplificar, pero la infraestructura ya está separada y funcional.

## Decision
**Respetar la separación existente. Solo reescribir bruno-bot.**

Los demás servicios (bruno-monitor, bruno-inventario, postgres, metabase, n8n) siguen como están. El bot nuevo se comunica con ellos via:
- PostgreSQL: conexión directa via DATABASE_URL
- bruno-monitor: el monitor envía webhooks HTTP al bot cuando procesa un PDF
- n8n: envía webhooks HTTP al bot para triggers externos
- Metabase: lee Postgres directamente, sin pasar por el bot

## Consequences
- **Mínimo riesgo** — solo se toca un servicio, los demás están probados
- **Restart independiente** — si el bot crashea, gmail_monitor sigue procesando PDFs
- **Dockerfile limpio** — imagen basada en python:3.11-slim, sin Hermes Agent
- **Trade-off:** el bot necesita exponer endpoint HTTP además de Telegram polling (para recibir webhooks), pero python-telegram-bot soporta esto nativo con `Application.run_polling()` + un servidor HTTP ligero
