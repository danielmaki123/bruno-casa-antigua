# Issue #3: LLM Client — Kimi classify + humanize

**Type:** AFK
**Blocked by:** #1 (bot skeleton must exist)

## What to build

Crear `bot/llm.py` — wrapper sobre OpenAI SDK apuntando a Kimi (Moonshot). Dos funciones:

1. `classify_intent(message: str) → dict` — Recibe texto libre del usuario, retorna `{intent: str, entities: dict}`. Intents posibles definidos en PRD-MVP.md sección "Arquitectura de Intents".

2. `humanize(data: dict, context: str) → str` — Recibe datos estructurados (resultado de query) + contexto del grupo/usuario, retorna respuesta natural en español siguiendo el estilo de Bruno (SOUL.md).

Usar OpenAI SDK con:
```python
client = OpenAI(api_key=KIMI_API_KEY, base_url="https://api.moonshot.ai/v1")
```

System prompt para classify: lista de intents válidos + instrucciones de extracción.
System prompt para humanize: cargar de `.hermes/SOUL.md` (personalidad de Bruno).

Modelo configurable via env `KIMI_MODEL` (default: `moonshot-v1-8k`).

Leer `docs/adr/0001-llm-as-conversational-layer.md` — el LLM NUNCA ejecuta acciones, solo clasifica y formatea.

## Acceptance criteria

- [ ] `bot/llm.py` con funciones `classify_intent()` y `humanize()`
- [ ] Usa OpenAI SDK con base_url configurable (Moonshot)
- [ ] `classify_intent("ventas de ayer")` retorna `{intent: "sales_by_date", entities: {date: "yesterday"}}`
- [ ] `classify_intent("cuánta cerveza hay")` retorna `{intent: "stock_check", entities: {product: "cerveza"}}`
- [ ] `humanize()` genera respuestas en español, con emojis de Bruno (✅, ⚠️, 🔴)
- [ ] System prompt cargado de SOUL.md
- [ ] Manejo de errores: si Kimi no responde, retorna intent "unknown" o mensaje de error amigable
- [ ] Temperature = 0.3 para classify (determinístico), 0.7 para humanize (natural)

## References
- `.hermes/SOUL.md` — personalidad y estilo de Bruno
- `docs/adr/0001-llm-as-conversational-layer.md` — decisión arquitectónica
- `docs/PRD-MVP.md` — tabla de intents
- `.env.example` — KIMI_API_KEY, KIMI_BASE_URL
