# ADR-0001: LLM como capa conversacional, no como agente

## Status
Accepted

## Context
BrunoBot necesita integrar un LLM (Kimi/Moonshot) para interactuar con el equipo del restaurante. La versión anterior (Hermes Agent) usaba el LLM como agente completo — decidía qué hacer, ejecutaba acciones, formateaba respuestas. Esto resultó en un sistema frágil, opaco y difícil de debuggear.

Tres opciones evaluadas:
- **A) Clasificador puro:** LLM solo detecta intención y extrae entidades. Todo lo demás es código.
- **B) Capa conversacional:** Código ejecuta queries y lógica. LLM humaniza los datos en respuestas naturales.
- **C) Agente completo:** LLM recibe contexto crudo y decide qué hacer (como Hermes).

## Decision
**Opción B — LLM como capa conversacional.**

El flujo es:
1. Usuario manda mensaje
2. Código clasifica intención (con ayuda del LLM si es texto libre)
3. Código ejecuta la query/acción correspondiente
4. Código pasa datos estructurados al LLM
5. LLM genera respuesta natural respetando el estilo de Bruno (SOUL.md)

## Consequences
- **Datos siempre confiables** — vienen de queries reales, no de alucinaciones del LLM
- **Debuggeable** — si la respuesta es incorrecta, sabemos si el error es en la query o en el formato
- **Costo controlado** — ~$10-15/mes en tokens (vs $20-30 con agente completo)
- **El equipo siente que habla con alguien** — no con un menú de comandos
- **Trade-off:** respuestas ligeramente más lentas (doble llamada: classify + format) pero imperceptible
