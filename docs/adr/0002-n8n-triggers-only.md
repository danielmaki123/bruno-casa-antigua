# ADR-0002: n8n solo como disparador externo

## Status
Accepted

## Context
n8n está corriendo en el VPS y tiene conexión MCP. La tentación es usarlo para lógica de negocio (parseo, validaciones, formateo de mensajes). El MVP Proposal original proponía 4 workflows complejos con 10-14 nodos cada uno.

Problema: workflows complejos en n8n son difíciles de versionar en git, difíciles de debuggear, y la lógica de negocio ya existe en Python.

## Decision
**n8n solo dispara. Nunca ejecuta lógica ni toca Telegram.**

n8n tiene exactamente 3 responsabilidades:
1. **Gmail watch** — detecta correo nuevo con PDF → POST webhook al bot
2. **Cron schedules** — dispara a hora fija (ej: resumen semanal lunes 8am) → GET endpoint del bot
3. **Sheets change** — detecta cambio en inventario → POST webhook al bot

n8n **nunca**:
- Envía mensajes a Telegram (un solo Bruno, un solo token)
- Parsea PDFs
- Ejecuta queries a Postgres
- Formatea respuestas
- Toma decisiones de negocio

## Consequences
- **Un solo Bruno** — el equipo nunca recibe mensajes de dos fuentes distintas
- **Sin conflictos de token** — solo el bot Python hace polling con el token de Telegram
- **Git-versionable** — toda la lógica está en Python, no en JSON de n8n
- **n8n reemplazable** — si n8n se cae, se puede sustituir por un cron de Linux + script
- **Trade-off:** n8n está subutilizado, pero eso es preferible a tener lógica partida en dos sistemas
