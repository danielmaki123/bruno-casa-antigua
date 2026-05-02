# PRD: BrunoBot MVP — Sistema Operativo del Restaurante Casa Antigua

**Status:** Draft
**Date:** 2026-05-02
**Author:** Makim + Claude (architecture), Sonnet (implementation)
**Label:** needs-triage

---

## Problem Statement

Casa Antigua es un restaurante en Nicaragua con operaciones diarias complejas: cierres de caja (POS), inventario multi-área (bebidas, cocina, barra, sushi, birria, pizza), y un equipo de 6+ personas que necesita coordinación.

Hoy existen scripts funcionales que parsean PDFs de cierre, monitorean Gmail, y generan reportes CLI. Pero **no hay bot funcional**: el equipo no puede consultar ventas, recibir alertas, ni reportar stock desde Telegram. El bot anterior (Hermes Agent) era un framework de terceros opaco que se rompió y no se pudo arreglar.

El equipo necesita un Bruno que funcione: confiable, rápido, útil desde día 1.

---

## Solution

Un bot Telegram escrito en Python puro que:

1. **Responde consultas** del equipo en lenguaje natural (powered by Kimi LLM como capa conversacional — ADR-0001)
2. **Recibe alertas automáticas** cuando llegan PDFs de cierre vía Gmail (disparados por n8n — ADR-0002)
3. **Trackea inventario** sincronizado desde Google Sheets + reportes rápidos por Telegram (ADR-0006)
4. **Guarda todo en PostgreSQL** como fuente de verdad (ADR-0003)
5. **Corre como servicio independiente** en EasyPanel (ADR-0004) usando polling de Telegram (ADR-0005)

El bot reutiliza código existente (PDF parsers, DB connector, Gmail monitor) y solo construye las piezas faltantes: Telegram handlers, LLM client, memoria, y router de mensajes.

---

## User Stories

### Consultas de Ventas (Grupo Admin + Privado)
1. Como administrador, quiero preguntar "¿cómo van las ventas hoy?" y recibir un resumen con totales y top productos, para tomar decisiones sin abrir Metabase.
2. Como Andrea, quiero preguntar "ventas de la semana pasada" y recibir totales desglosados por día, para comparar rendimiento.
3. Como Daniel, quiero preguntar "top 5 productos esta semana" y ver ranking con cantidades y montos, para saber qué se está moviendo.
4. Como administrador, quiero preguntar "ventas del martes" y recibir datos específicos de esa fecha, para investigar un día particular.

### Cierres de Caja (Grupo Admin)
5. Como administrador, quiero recibir automáticamente un resumen cuando llega un cierre de caja por Gmail, para no tener que abrir el PDF manualmente.
6. Como Andrea, quiero que Bruno me alerte si el cierre tiene diferencia POS mayor al umbral, para investigar inmediatamente.
7. Como Daniel, quiero preguntar "¿cómo salió el cierre de ayer?" y ver totales, propinas, pagos por método, y estado de validación.
8. Como administrador, quiero que el resumen de cierre incluya validaciones automáticas (subtotal+propina=total, faltante/sobrante, diferencia POS), para detectar problemas sin calcular a mano.

### Inventario (Grupo Inventario)
9. Como bartender (Jean), quiero reportar rápido "llegaron 10 cajas coca cola" y que Bruno confirme con ✅, para registrar entradas sin abrir Sheets.
10. Como mesero (Jorge), quiero decir "se acabó el vodka" y que Bruno registre stock=0 y alerte, para que Admin se entere inmediato.
11. Como supervisora (Flor), quiero preguntar "/inventario bebidas" y ver stock actual con niveles de alerta, para saber qué falta antes de abrir.
12. Como administrador, quiero recibir alerta automática cuando un producto baja del stock mínimo, para ordenar antes de que se acabe.
13. Como equipo de cocina, quiero ver confirmación de cada movimiento de inventario en el grupo, para que todos estén al tanto de entradas y salidas.
14. Como administrador, quiero que el inventario diario de Sheets se sincronice a Postgres automáticamente, para tener datos en Metabase sin doble entrada.

### Grupo Team (Broadcast)
15. Como miembro del equipo, quiero recibir notificaciones de turnos y rotaciones en el grupo Team, para saber mi horario sin preguntar.
16. Como administrador, quiero que Bruno solo escriba en Team (no responda mensajes del equipo ahí), para mantener el canal limpio.
17. Como miembro del equipo, si escribo en Team, quiero que Bruno me diga "usá el grupo correspondiente", para redirigirme al canal correcto.

### Memoria y Contexto
18. Como administrador, quiero que Bruno recuerde conversaciones anteriores del mismo día, para no repetir contexto en cada pregunta.
19. Como Andrea, quiero preguntar "¿qué alertas hubo hoy?" y que Bruno consulte el historial del día, para tener resumen rápido.

### Seguridad y Acceso
20. Como administrador, quiero que Bruno solo responda a usuarios registrados, para evitar que desconocidos consulten datos del restaurante.
21. Como administrador, quiero que información financiera (cierres, diferencias) solo aparezca en Admin y privado, nunca en Team ni Inventario.
22. Como staff, quiero poder consultar stock en Inventario y en privado, pero no ver datos financieros.

### Operaciones
23. Como administrador, quiero un comando "/help" que liste qué puede hacer Bruno en cada grupo, para capacitar al equipo.
24. Como administrador, quiero que Bruno responda en español 100%, sin jerga técnica, para que todo el equipo lo entienda.
25. Como administrador, quiero ver logs de errores cuando algo falle, para poder diagnosticar problemas.

---

## Implementation Decisions

### Módulos a Construir

#### 1. Bot Core (NUEVO)
- Entry point con `python-telegram-bot` v20+ async
- Polling loop de Telegram
- Servidor HTTP interno (aiohttp) para recibir webhooks de n8n y bruno-monitor
- Carga de configuración desde `.env`
- Interfaz: `start()` inicia polling + HTTP server

#### 2. Message Router (NUEVO)
- Recibe cada mensaje de Telegram
- Determina: grupo origen → permisos → tipo (comando vs texto libre)
- Si es comando (`/inventario`, `/help`, etc.) → ejecuta handler directo
- Si es texto libre → pasa a LLM para clasificación de intención
- Si es grupo Team → ignora o redirige
- Valida usuario contra lista de autorizados
- Interfaz: `route(update, context) → response`

#### 3. LLM Client (NUEVO)
- Wrapper sobre OpenAI SDK apuntando a `api.moonshot.ai/v1`
- Dos funciones principales:
  - `classify_intent(message) → {intent, entities}` — detecta qué quiere el usuario
  - `humanize(data, context) → str` — convierte datos estructurados en respuesta natural
- System prompt cargado de SOUL.md
- Modelo: `moonshot-v1-8k` (configurable via env)
- Interfaz simple, sin abstracciones innecesarias

#### 4. Memory (NUEVO)
- Tabla `conversations` en PostgreSQL
- Guarda cada mensaje (user + assistant) con chat_id y timestamp
- Recupera últimos N mensajes del chat para contexto del LLM
- Limpieza automática de conversaciones > 30 días
- Interfaz: `save(chat_id, role, content)`, `get_context(chat_id, limit=10)`

#### 5. Sheets Sync (REUTILIZAR + ADAPTAR)
- Extraer funciones útiles de `scripts/manage_sheets.py` y `scripts/inventario_monitor.py`
- Leer inventario desde Google Sheets → insertar en tabla `inventory_counts`
- Endpoint HTTP que n8n llama cuando Sheets cambia
- Interfaz: `sync_inventory(sheet_data) → {synced, alerts}`

#### 6. Skills — Ventas (REUTILIZAR)
- Adaptar queries de `scripts/reporte_tool.py`
- Funciones: `ventas_dia(fecha)`, `ventas_semana()`, `top_productos(rango)`
- Retorna datos estructurados (dict), no texto formateado
- Interfaz: `query(intent, entities) → dict`

#### 7. Skills — Cierres (REUTILIZAR)
- Adaptar `skills/parsers.py` + `skills/admin_auditor.py`
- Funciones: `cierre_status(fecha)`, `procesar_cierre_nuevo(pdf_data)`
- Validaciones automáticas (subtotal+propina=total, diferencia POS, duplicados)
- Interfaz: `query(intent, entities) → dict`

#### 8. Skills — Inventario (NUEVO + REUTILIZAR)
- Consulta stock: lee `inventory_counts` + `stock_rules` de Postgres
- Reporte rápido via Telegram: Kimi extrae producto+cantidad → guarda
- Alertas bajo mínimo: compara conteo vs `stock_rules.min_qty`
- Interfaz: `query(intent, entities) → dict`, `registrar(producto, cantidad, user) → confirmation`

#### 9. Database Layer (EXPANDIR)
- Mantener `database/postgres.py` existente
- Agregar migration script para tablas Fase 1 (conversations, products, areas, stock_rules, inventory_counts)
- Seed data para áreas y productos desde Excel existente
- Interfaz: sin cambios a `execute_query()`, solo nuevas tablas

#### 10. Dockerfile (REESCRIBIR)
- Base: `python:3.11-slim` (eliminar Hermes Agent)
- Instalar solo requirements.txt
- Entry point: `python bot/main.py`
- Sin PM2 (servicio único), sin Node.js

### Arquitectura de Intents

| Intent | Trigger | Skill | Grupos permitidos |
|---|---|---|---|
| `sales_today` | "ventas hoy", "cómo van las ventas" | ventas | Admin, Privado |
| `sales_by_date` | "ventas del martes", "ventas 28 abril" | ventas | Admin, Privado |
| `top_products` | "top productos", "qué se vende más" | ventas | Admin, Privado |
| `closing_status` | "cierre de ayer", "cómo salió el cierre" | cierres | Admin, Privado |
| `stock_check` | "/inventario", "stock bebidas", "cuánta cerveza hay" | inventario | Inventario, Admin, Privado |
| `stock_report` | "llegaron 10 cajas...", "se acabó el vodka" | inventario | Inventario |
| `stock_alerts` | "/alertas" | inventario | Inventario, Admin, Privado |
| `help` | "/help", "/ayuda" | core | Todos |
| `unknown` | cualquier otro | LLM responde con contexto | Según grupo |

### Schema Fase 1

```sql
-- Nuevas tablas (las existentes no se tocan)

CREATE TABLE conversations (
    id SERIAL PRIMARY KEY,
    chat_id BIGINT NOT NULL,
    user_id BIGINT,
    user_name TEXT,
    role TEXT NOT NULL,  -- 'user' | 'assistant'
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE areas (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL  -- bebidas, cocina, barra, sushi, birria, pizza
);

CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    sku_internal VARCHAR(50),
    unit VARCHAR(20) NOT NULL,  -- oz, caja, botella, unidad, kg
    area_id INT REFERENCES areas(id),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE stock_rules (
    id SERIAL PRIMARY KEY,
    product_id INT REFERENCES products(id),
    area_id INT REFERENCES areas(id),
    min_qty NUMERIC(10,2) NOT NULL,
    target_qty NUMERIC(10,2),
    UNIQUE(product_id, area_id)
);

CREATE TABLE inventory_counts (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    area_id INT REFERENCES areas(id),
    product_id INT REFERENCES products(id),
    counted_qty NUMERIC(10,2) NOT NULL,
    reported_by TEXT,
    source VARCHAR(20) DEFAULT 'sheets',  -- 'sheets' | 'telegram'
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(date, product_id, source)
);

CREATE INDEX idx_conversations_chat ON conversations(chat_id, created_at DESC);
CREATE INDEX idx_inventory_date ON inventory_counts(date, area_id);
```

### Comunicación entre servicios (EasyPanel)

```
bruno-monitor → HTTP POST /webhook/cierre → bruno-bot (procesa PDF, guarda, alerta)
n8n           → HTTP POST /webhook/sheets  → bruno-bot (sync inventario)
n8n           → HTTP GET  /cron/resumen    → bruno-bot (genera resumen semanal)
bruno-bot     → PostgreSQL                 → queries directos
bruno-bot     → Kimi API                   → classify + humanize
bruno-bot     → Telegram API               → polling + send messages
metabase      → PostgreSQL                 → dashboards (independiente)
```

---

## Testing Decisions

### Qué hace un buen test
- Testea comportamiento externo (input → output), no detalles de implementación
- Usa datos realistas del restaurante (no "foo", "bar")
- No depende de servicios externos (mock Kimi API, mock Telegram, test DB)

### Módulos a testear

| Módulo | Tipo de test | Qué valida |
|---|---|---|
| **LLM Client** | Unit + mock | `classify_intent()` retorna intent correcto para 20+ frases comunes |
| **Message Router** | Unit | Permisos por grupo, redirección Team, validación de usuario |
| **Skills/Ventas** | Integration (test DB) | Queries retornan datos correctos de Postgres con datos seed |
| **Skills/Cierres** | Unit | Parser extrae campos correctos de PDF de ejemplo |
| **Skills/Inventario** | Unit + Integration | Registro rápido, alertas bajo mínimo, sync de Sheets |
| **Memory** | Integration (test DB) | Save/load conversaciones, límite de contexto, cleanup |

### No testear
- Telegram handlers (dependen de API externa, validar manualmente)
- Dockerfile (validar con build + smoke test)
- n8n workflows (validar manualmente en la UI)

---

## Out of Scope

| Feature | Razón | Cuándo |
|---|---|---|
| Compras sugeridas automáticas | Requiere stock_rules poblados + historial | Fase 2 |
| Resumen semanal automático | Requiere cron n8n + endpoint | Fase 2 |
| Diferencias ventas vs consumo explicadas | Requiere tabla v2_recipes poblada | Fase 2 |
| Asistencia del equipo | Requiere tabla employees + attendance | Fase 3 |
| Cumpleaños y recordatorios | Requiere tabla events + cron | Fase 3 |
| Planillas y liquidaciones | Requiere tabla employees + cálculos HR | Fase 3 |
| Web app de inventario | Requiere frontend + subdominio | Fase 3 |
| Migración a Ollama local | Requiere VPS dedicado + evaluación de modelo | Fase 5 |
| Chatbot de clientes | Fuera del scope de Bruno completamente | Never |
| Acceso a cuentas bancarias | Prohibido por diseño (SOUL.md) | Never |

---

## Further Notes

### Documentos de referencia para Sonnet
- **CONTEXT.md** — Glosario, grupos, roles, flujo de datos
- **docs/adr/** — 6 ADRs con decisiones de arquitectura
- **SOUL.md** (`.hermes/SOUL.md`) — Personalidad y system prompt de Bruno
- **scripts/reporte_tool.py** — Referencia de queries existentes (8 acciones)
- **skills/parsers.py** — Parser de PDFs de cierre y venta menú
- **database/postgres.py** — Connector de DB (reutilizar tal cual)
- **scripts/db_setup.py** — Schema existente (no modificar, solo agregar)

### Orden de implementación sugerido
1. `bot/config.py` + `Dockerfile` nuevo → validar que arranca
2. `bot/main.py` con polling básico → Bruno responde "Hola" en Telegram
3. `bot/llm.py` → conectar Kimi, validar classify + humanize
4. `bot/memory.py` + migration SQL → conversaciones persisten
5. `bot/handlers.py` → router por grupo + permisos
6. Skills ventas → consultas funcionan
7. Skills cierres → cierre_status funciona
8. Skills inventario → stock_check + reporte rápido
9. Webhook HTTP → bruno-monitor puede avisar de cierres nuevos
10. Testing + deploy en EasyPanel

### Variables de entorno requeridas
```
TELEGRAM_BOT_TOKEN=xxx
KIMI_API_KEY=xxx
KIMI_BASE_URL=https://api.moonshot.ai/v1
KIMI_MODEL=moonshot-v1-8k
DATABASE_URL=postgres://user:pass@host:port/brunobot
GOOGLE_SHEETS_ID=xxx
GROUP_ID_INVENTARIO=-5240974489
GROUP_ID_ADMIN=-4944632677
GROUP_ID_TEAM=-5181251045
AUTHORIZED_USERS=id1,id2,id3
WEBHOOK_SECRET=random_string_for_internal_webhooks
```
