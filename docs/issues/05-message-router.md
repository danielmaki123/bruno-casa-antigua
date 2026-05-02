# Issue #5: Message Router — permisos por grupo + validación usuarios

**Type:** AFK
**Blocked by:** #1 (bot skeleton), #3 (LLM client para classify)

## What to build

Crear `bot/handlers.py` — router central que recibe cada mensaje de Telegram y decide qué hacer.

Flujo:
1. Recibe `Update` de Telegram
2. Identifica grupo origen (Inventario / Admin / Team / Privado)
3. Valida usuario contra lista `AUTHORIZED_USERS` de env
4. Si grupo Team → ignorar mensaje del usuario O responder "Usá el grupo correspondiente"
5. Si es comando (`/help`, `/inventario`, etc.) → ejecutar handler directo
6. Si es texto libre → llamar `llm.classify_intent()` → rutear al skill correspondiente
7. Verificar permisos: info financiera solo en Admin/Privado, stock en Inventario/Admin/Privado
8. Guardar mensaje en memory (Issue #4)
9. Enviar respuesta

Leer `CONTEXT.md` sección "Telegram Groups" y "Access Control" para reglas de permisos.

Comandos MVP:
- `/help` o `/ayuda` — lista de capacidades según grupo
- `/inventario [area]` — stock actual (solo en Inventario, Admin, Privado)
- `/alertas` — productos bajo mínimo (solo en Inventario, Admin, Privado)
- `/ventas [fecha]` — ventas del día (solo en Admin, Privado)
- `/cierre [fecha]` — estado del cierre (solo en Admin, Privado)

## Acceptance criteria

- [ ] `bot/handlers.py` con función principal `handle_message(update, context)`
- [ ] Detecta grupo origen por `chat.id` comparando con GROUP_IDs de config
- [ ] Rechaza usuarios no autorizados con mensaje amigable
- [ ] En grupo Team: ignora mensajes o redirige al grupo correcto
- [ ] Comandos `/help` retorna lista de comandos disponibles según grupo actual
- [ ] Texto libre pasa por `classify_intent()` y rutea al skill
- [ ] Info financiera bloqueada fuera de Admin/Privado
- [ ] Cada mensaje se guarda en memory via `memory.save()`
- [ ] Registrado en `main.py` como handler del bot

## References
- `CONTEXT.md` — grupos, permisos, roles
- `.hermes/SOUL.md` — IDs de grupos reales
- `docs/adr/0001-llm-as-conversational-layer.md` — flujo classify → query → humanize
- `docs/PRD-MVP.md` — tabla de intents y permisos por grupo
