# Issue #9: Webhook HTTP — endpoint interno para n8n y bruno-monitor

**Type:** AFK
**Blocked by:** #1 (bot skeleton)

## What to build

Agregar servidor HTTP interno al bot para recibir webhooks de servicios hermanos (n8n, bruno-monitor). No necesita ser público — solo accesible dentro de la red de EasyPanel.

Endpoints:
1. `POST /webhook/cierre` — bruno-monitor envía datos de PDF procesado. Bot ejecuta `cierres.procesar_cierre_nuevo()` y envía alerta a grupo Admin.
2. `POST /webhook/sheets` — n8n avisa que inventario cambió en Sheets. Bot ejecuta sync a Postgres.
3. `GET /cron/resumen-semanal` — n8n dispara cada lunes 8am. Bot genera resumen y envía a grupo Admin.
4. `GET /health` — health check para EasyPanel.

Implementar con `aiohttp` (ya compatible con asyncio de python-telegram-bot). Correr en puerto configurable via env `WEBHOOK_PORT` (default: 8080).

Seguridad: validar header `X-Webhook-Secret` contra env `WEBHOOK_SECRET` en endpoints POST. GET /health sin auth.

## Acceptance criteria

- [ ] Servidor HTTP corre en paralelo con Telegram polling (mismo process, asyncio)
- [ ] `POST /webhook/cierre` recibe JSON, procesa, envía alerta a Telegram
- [ ] `POST /webhook/sheets` recibe notificación, dispara sync
- [ ] `GET /cron/resumen-semanal` genera y envía resumen
- [ ] `GET /health` retorna `{"status": "ok", "uptime": N}`
- [ ] Validación de `X-Webhook-Secret` en POSTs
- [ ] Puerto configurable via env
- [ ] Logs de cada request recibido

## References
- `docs/adr/0002-n8n-triggers-only.md` — n8n solo dispara, bot ejecuta
- `docs/adr/0004-single-container-per-service.md` — comunicación entre servicios
- `docs/PRD-MVP.md` — diagrama de comunicación entre servicios
