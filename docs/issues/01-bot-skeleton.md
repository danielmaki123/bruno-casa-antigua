# Issue #1: Bot skeleton — config + polling + Dockerfile

**Type:** AFK
**Blocked by:** None — can start immediately

## What to build

Crear el entry point del bot Telegram con polling funcional. Bruno debe arrancar, conectarse a Telegram, y responder "Hola" a cualquier mensaje. Incluye:

- `bot/config.py` — carga todas las env vars, valida que existan
- `bot/main.py` — `Application.run_polling()` con python-telegram-bot v20+
- `Dockerfile` nuevo basado en `python:3.11-slim` (eliminar Hermes Agent)
- Handler catch-all que responde con el nombre del usuario y un saludo

Leer `.env.example` para las variables requeridas. Leer `CONTEXT.md` para entender la estructura del proyecto. Leer `docs/adr/0005-polling-not-webhook.md` para la decisión de polling.

El Dockerfile anterior usa `nousresearch/hermes-agent:latest` — REEMPLAZAR completamente. No PM2, no Node.js. Entry point: `python bot/main.py`.

## Acceptance criteria

- [ ] `bot/config.py` carga y valida: TELEGRAM_BOT_TOKEN, KIMI_API_KEY, DATABASE_URL, GROUP_IDs
- [ ] `bot/main.py` arranca polling y responde a mensajes
- [ ] Dockerfile basado en `python:3.11-slim`, instala requirements.txt, CMD `python bot/main.py`
- [ ] `docker build -t brunobot .` compila sin errores
- [ ] Bot responde "Hola [nombre]" en Telegram cuando se le escribe
- [ ] Bot loguea mensajes entrantes a stdout
- [ ] `__init__.py` en `bot/` para imports limpios

## References
- `.env.example` — variables requeridas
- `docs/adr/0005-polling-not-webhook.md` — decisión polling
- `docs/adr/0004-single-container-per-service.md` — servicio independiente
- `requirements.txt` — dependencias (ya incluye python-telegram-bot)
