# HANDOFF — BrunoBot MVP Implementation

> Este documento es tu punto de entrada. Leelo completo antes de escribir una línea de código.

## Qué es esto

BrunoBot es el sistema operativo del restaurante Casa Antigua (Nicaragua). Bot de Telegram que automatiza: consultas de ventas, alertas de cierres de caja, y tracking de inventario.

**Estado actual:** 30% implementado. Scripts de soporte funcionan (PDF parsing, DB, Gmail monitor). Falta el core del bot (Telegram handlers, LLM, memoria, skills).

## Documentos que DEBES leer (en orden)

1. **`CONTEXT.md`** — Glosario, grupos Telegram, roles, flujo de datos. Lee primero.
2. **`docs/adr/`** — 6 decisiones de arquitectura. Todas están aceptadas. No las cambies sin razón.
3. **`docs/PRD-MVP.md`** — PRD completo con user stories, schema, intents, y plan de implementación.
4. **`docs/issues/`** — 10 issues verticales ordenados por dependencia. Cada uno es autocontenido.
5. **`.hermes/SOUL.md`** — Personalidad de Bruno (system prompt para el LLM).
6. **`CLAUDE.md`** — Guía de desarrollo del proyecto.

## Qué código ya funciona (NO reescribir)

| Archivo | Qué hace | Acción |
|---|---|---|
| `database/postgres.py` | Connector PostgreSQL | Reutilizar tal cual |
| `skills/parsers.py` | Parser regex de PDFs cierre + venta menú | Reutilizar tal cual |
| `skills/admin_auditor.py` | Auditoría financiera POS vs banco | Adaptar (retornar dict, no solo guardar) |
| `skills/inventory_auditor.py` | Consumo teórico desde recetas | Adaptar cuando haya recetas en DB |
| `scripts/reporte_tool.py` | 8 queries de reportes CLI | Copiar queries relevantes a skills/ |
| `scripts/db_setup.py` | Schema original (2 tablas + vistas) | NO tocar. Agregar tablas nuevas en script separado |

## Qué código hay que crear

| Archivo | Issue | Prioridad |
|---|---|---|
| `bot/__init__.py` | #1 | Alta |
| `bot/config.py` | #1 | Alta |
| `bot/main.py` | #1 | Alta |
| `bot/llm.py` | #3 | Alta |
| `bot/memory.py` | #4 | Alta |
| `bot/handlers.py` | #5 | Alta |
| `skills/ventas.py` | #6 | Media |
| `skills/cierres.py` | #7 | Media |
| `skills/inventario.py` | #8 | Media |
| `Dockerfile` (reescribir) | #1 | Alta |
| `scripts/db_migration_fase1.py` | #2 | Alta |

## Qué código hay que ELIMINAR

| Archivo/Dir | Razón |
|---|---|
| `.hermes/config.yaml` | Config de Hermes Agent (deprecated) |
| `.hermes/skills/` | Skills .md de Hermes (reemplazados por Python) |
| `ecosystem.config.js` | PM2 config (bruno-bot ya no usa PM2) |
| `bot/brain.py` actual | Es un script CLI, no un bot. Reemplazar con `bot/main.py` |

**MANTENER `.hermes/SOUL.md`** — se usa como system prompt del LLM.

## Orden de implementación

```
Paralelo 1:  Issue #1 (bot skeleton)  +  Issue #2 (DB migration)
Paralelo 2:  Issue #3 (LLM client)   +  Issue #4 (memory)
Secuencial:  Issue #5 (message router)
Paralelo 3:  Issue #6 (ventas) + Issue #7 (cierres) + Issue #8 (inventario)
Secuencial:  Issue #9 (webhook HTTP)
HITL:        Issue #10 (deploy) ← requiere humano
```

## Stack

| Capa | Tecnología |
|---|---|
| Bot | python-telegram-bot v20+ (async) |
| LLM | OpenAI SDK → api.moonshot.ai/v1 (Kimi) |
| DB | PostgreSQL via psycopg2 |
| Sheets | google-api-python-client |
| HTTP server | aiohttp (para webhooks internos) |
| Deploy | Docker (python:3.11-slim) |

## Variables de entorno

```
TELEGRAM_BOT_TOKEN      # Token del bot @BrunoRestBot
KIMI_API_KEY             # API key de Moonshot
KIMI_BASE_URL            # https://api.moonshot.ai/v1
KIMI_MODEL               # moonshot-v1-8k
DATABASE_URL             # postgres://...
GOOGLE_SHEETS_ID         # ID del sheet de inventario
GROUP_ID_INVENTARIO      # -5240974489
GROUP_ID_ADMIN           # -4944632677
GROUP_ID_TEAM            # -5181251045
AUTHORIZED_USERS         # telegram_user_ids separados por coma
WEBHOOK_PORT             # 8080 (default)
WEBHOOK_SECRET           # string random para auth de webhooks
```

## Herramientas de apoyo

Cuando necesites ayuda con tareas complejas:

- **`/codex:review`** — Antes de dar por terminado un issue, pide code review a Codex
- **`/codex:adversarial-review`** — Para validación de seguridad (SQL injection, token exposure)
- **Gemini CLI** — Para búsqueda web si necesitás documentación de python-telegram-bot v20 o Kimi API

## Si te quedás sin tokens

Cada issue es autocontenido. Si el contexto se agota:
1. Guardá progreso (commit lo que funciona)
2. Documentá en el issue qué quedó pendiente
3. El siguiente agente lee el issue + código existente y continúa

**Regla:** cada commit debe dejar el bot en estado funcional. No commits a medias que rompan el polling.

## Reglas de código

- Python 3.11, async/await
- Sin comentarios innecesarios
- Sin abstracciones prematuras
- Queries parametrizados (prevenir SQL injection)
- Errores se loguean pero no crashean el bot
- Respuestas siempre en español
- Emojis según SOUL.md: ✅ ok, ⚠️ warning, 🔴 crítico
