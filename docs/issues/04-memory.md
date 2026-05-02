# Issue #4: Memory — save/load conversaciones en PostgreSQL

**Type:** AFK
**Blocked by:** #1 (bot skeleton), #2 (DB migration — tabla conversations)

## What to build

Crear `bot/memory.py` — módulo de memoria persistente que guarda y recupera conversaciones del bot en PostgreSQL.

Funciones:
1. `save(chat_id, user_id, user_name, role, content)` — guarda un mensaje
2. `get_context(chat_id, limit=10) → list[dict]` — recupera últimos N mensajes del chat para pasar al LLM como contexto
3. `cleanup(days=30)` — elimina conversaciones antiguas (llamar desde cron interno)

Usa la tabla `conversations` creada en Issue #2. Reutiliza `database/postgres.py` para queries.

El contexto se pasa al LLM en `humanize()` para que Bruno "recuerde" la conversación del día.

## Acceptance criteria

- [ ] `bot/memory.py` con `save()`, `get_context()`, `cleanup()`
- [ ] `save()` inserta en tabla `conversations` con timestamp automático
- [ ] `get_context(chat_id, limit=10)` retorna lista de `{role, content, created_at}` ordenada cronológicamente
- [ ] `cleanup(days=30)` elimina registros > 30 días
- [ ] Reutiliza `database/postgres.py` (no crear nuevo connector)
- [ ] Manejo de errores: si DB falla, loguea error pero no crashea el bot

## References
- `database/postgres.py` — connector existente
- `docs/PRD-MVP.md` — schema de tabla conversations
- `docs/issues/02-db-migration.md` — tabla se crea ahí
