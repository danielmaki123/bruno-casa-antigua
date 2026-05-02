# ADR-0005: Telegram polling (no webhook)

## Status
Accepted

## Context
El dominio casaantiguanic.com está en uso por la web del restaurante. No hay subdominios configurados. Configurar un subdominio para webhook de Telegram requiere DNS + SSL + reverse proxy — trabajo de infra que no aporta al MVP.

## Decision
**Polling para Telegram. Webhook se evalúa cuando se configure subdominio para web app de inventario.**

`python-telegram-bot` v20+ soporta polling nativo con `Application.run_polling()`. El bot pregunta a Telegram cada ~2 segundos si hay mensajes nuevos.

## Consequences
- **Zero configuración de infra** — funciona detrás de firewall, sin dominio, sin SSL
- **Trade-off:** ~200ms más lento que webhook — imperceptible para el equipo
- **Migración futura fácil** — cambiar a webhook es 3 líneas de código cuando haya subdominio
- **El bot igual necesita servidor HTTP interno** para recibir webhooks de n8n y bruno-monitor, pero este no necesita ser público
