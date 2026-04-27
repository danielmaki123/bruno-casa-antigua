# BrunoBot v2 — Arquitectura Completa

> **Fecha:** 2026-04-27  
> **Estado:** Documento de arquitectura para revisión antes de implementación  
> **Objetivo:** Reemplazar Hermes Agent por un bot propio 100% controlado, con las mismas (y mejores) capacidades para el restaurante.

---

## 1. Filosofía de Diseño

| Principio | Explicación |
|---|---|
| **Sin frameworks opacos** | No dependemos de imágenes Docker de terceros con bugs inaccesibles. |
| **Código sobre prompts** | Las "skills" de Hermes eran texto. Acá son funciones Python que hacen cosas reales. |
| **Modelo libre** | Elegimos exactamente qué modelo usar (Kimi, Gemini, OpenRouter) y cuándo cambiarlo. |
| **Memoria real** | PostgreSQL guarda conversaciones y hechos, no SQLite efímero dentro de un contenedor. |
| **Deploy simple** | Un servicio Docker en Easy Panel. Punto. |

---

## 2. Stack Tecnológico

| Capa | Tecnología | ¿Por qué? |
|---|---|---|
| **Lenguaje** | Python 3.11 | Ya lo tenemos, simple, maduro. |
| **Bot Telegram** | `python-telegram-bot` v20+ | Estándar de la industria, async, estable. |
| **LLM** | OpenAI SDK + endpoint de Kimi/Moonshot | Kimi es compatible OpenAI. Un solo cliente sirve para múltiples providers. |
| **Base de datos operativa** | Google Sheets | El restaurante ya la usa. No rompemos lo que funciona. |
| **Memoria / Historial** | PostgreSQL | Ya tenemos `DATABASE_URL` en Easy Panel. Persistente, consultable. |
| **Infraestructura** | Docker + Easy Panel | Mismo deploy que ahora, pero con nuestra propia imagen. |
| **Auth Google** | `google-auth` + `google-api-python-client` | Ya está en `requirements.txt`. |

---

## 3. Estructura de Archivos

```
BrunoBot/
├── .env                          # Variables de entorno (igual que ahora)
├── .env.example                  # Plantilla
├── docker-compose.yml            # Orquestación para Easy Panel
├── Dockerfile                    # Imagen propia del bot
├── requirements.txt              # Dependencias actualizadas
├── README.md                     # Cómo deployar
│
├── docs/
│   └── sheets_structure.md       # Documentación de tablas (ya existe)
│
├── skills/                       # Skills como código Python (no .md)
│   ├── __init__.py
│   ├── inventario.py             # Reportar stock, consultar inventario
│   ├── empleados.py              # Asistencia, vacaciones, cumpleaños
│   ├── recetas.py                # Consultar recetas, calcular costos
│   ├── ventas.py                 # Comparar ventas vs consumo
│   └── recordatorios.py          # Eventos, pagos, tareas programadas
│
├── bot/
│   ├── __init__.py
│   ├── main.py                   # Entry point. Arranca el bot.
│   ├── config.py                 # Lee .env, valida config
│   ├── llm.py                    # Cliente LLM (Kimi/Gemini/etc)
│   ├── brain.py                  # Orquestador: recibe msg → decide qué skill usar
│   ├── memory.py                 # PostgreSQL: guardar/leer conversaciones
│   ├── sheets.py                 # Google Sheets API: leer/escribir tablas
│   ├── telegram_handlers.py      # Handlers de mensajes y comandos
│   └── prompts.py                # System prompts y contexto de Bruno
│
├── scripts/                      # Utilidades (ya existen, se mantienen)
│   ├── authenticate_google.py
│   ├── initialize_google_sheets.py
│   └── ...
│
└── tests/                        # Tests básicos (fase 2)
```

---

## 4. Flujo de Datos (Cómo funciona)

```
┌─────────────────┐
│   Usuario       │
│   Telegram      │
└────────┬────────┘
         │ mensaje
         ▼
┌─────────────────────────────┐
│  telegram_handlers.py       │
│  • Detecta grupo            │
│  • Detecta comando (/xyz)   │
│  • O mensaje libre          │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│  brain.py                   │
│  "¿Qué hay que hacer?"      │
│  • ¿Es comando directo?     │
│    → Ejecutar skill         │
│  • ¿Es pregunta/libre?      │
│    → Consultar contexto     │
│    → Llamar LLM             │
│    → Ejecutar acción si     │
│      la respuesta lo pide   │
└────────┬────────────────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌────────┐ ┌─────────────┐
│ skills │ │   llm.py    │
│ .py    │ │  (Kimi API) │
└───┬────┘ └──────┬──────┘
    │             │
    ▼             ▼
┌─────────────┐ ┌─────────────┐
│ sheets.py   │ │ memory.py   │
│ Google      │ │ PostgreSQL  │
│ Sheets      │ │             │
└──────┬──────┘ └──────┬──────┘
       │               │
       └───────┬───────┘
               ▼
        ┌─────────────┐
        │  Telegram   │
        │  Respuesta  │
        └─────────────┘
```

---

## 5. Componentes Detallados

### 5.1 `bot/config.py`

Lee y valida todas las variables de entorno:

```python
TELEGRAM_TOKEN
KIMI_API_KEY (o OPENAI_API_KEY, GEMINI_API_KEY)
LLM_PROVIDER          # "kimi", "gemini", "openrouter"
LLM_MODEL             # "kimi-k2.5", "gemini-2.5-flash", etc.
LLM_BASE_URL          # opcional, para custom endpoints
GOOGLE_SHEETS_ID
DATABASE_URL
GROUP_ID_INVENTARIO
GROUP_ID_ADMIN
GROUP_ID_TEAM
HERMES_SYSTEM_PROMPT  # renombrar a BRUNO_SYSTEM_PROMPT
```

**Ventaja:** Un solo lugar para cambiar de modelo. Querés probar Gemini? Cambiás `LLM_PROVIDER` y `LLM_MODEL`. Listo.

---

### 5.2 `bot/llm.py`

Cliente unificado para cualquier provider OpenAI-compatible:

```python
client = OpenAI(api_key=KEY, base_url=BASE_URL)

response = client.chat.completions.create(
    model=config.LLM_MODEL,
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message}
    ],
    temperature=0.3,
    max_tokens=4096
)
```

**Soporta:** Kimi, Gemini (vía endpoint OpenAI), OpenRouter, OpenAI, Anthropic (vía proxy), etc.

---

### 5.3 `bot/brain.py`

El cerebro. Recibe cada mensaje y decide el camino:

```
Mensaje entrante
    │
    ├──► ¿Empieza con /? → Comando directo
    │       ├── /reportar → skill_inventario.reportar()
    │       ├── /inventario → skill_inventario.consultar()
    │       ├── /asistencia → skill_empleados.asistencia()
    │       └── /help → lista de comandos
    │
    └──► Mensaje libre
            ├── Construir contexto (memoria + sheets + prompt)
            ├── Llamar LLM
            ├── Si LLM pide "guardar en sheets" → sheets.append()
            └── Responder al usuario
```

**No es magia.** Es código Python con `if/elif/else` y llamadas a funciones.

---

### 5.4 `bot/memory.py`

Guarda todo en PostgreSQL (que ya tenés en Easy Panel):

**Tablas:**

```sql
CREATE TABLE conversations (
    id SERIAL PRIMARY KEY,
    chat_id BIGINT NOT NULL,
    user_id BIGINT,
    user_name TEXT,
    role TEXT,              -- 'user' | 'assistant' | 'system'
    content TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE sessions (
    id SERIAL PRIMARY KEY,
    chat_id BIGINT UNIQUE,
    title TEXT,             -- título de la sesión (lo generamos nosotros)
    context_summary TEXT,   -- resumen para no perder el hilo
    last_active TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE facts (
    id SERIAL PRIMARY KEY,
    key TEXT UNIQUE,        -- ej: "maria_cumpleaños"
    value TEXT,             -- ej: "1985-04-12"
    source TEXT,            -- quién lo dijo
    created_at TIMESTAMP DEFAULT NOW()
);
```

**Ventaja:** La memoria sobrevive a reinicios. Es real, no un SQLite dentro de un contenedor.

---

### 5.5 `bot/sheets.py`

Wrapper sobre la API de Google Sheets. Funciones claras:

```python
def append_inventario(fecha, turno, area, insumo_id, cantidad, responsable, notas):
    """Agrega una fila a la pestaña INVENTARIO."""

def get_inventario_actual():
    """Devuelve todo el inventario como lista de diccionarios."""

def get_insumo(insumo_id):
    """Busca un insumo por ID en la pestaña INSUMOS."""

def get_empleado(telegram_id):
    """Busca un empleado por telegram_id."""
```

**No más prompts pidiéndole a la IA que "adivine" qué hacer.** Llamadas directas a la API.

---

### 5.6 `skills/*.py` (Skills como código)

#### `skills/inventario.py`

```python
async def reportar(user_msg: str, user_name: str) -> str:
    """
    Procesa un mensaje de inventario.
    Ej: "Llegaron 10kg de pollo" 
    → extrae: producto=pollo, cantidad=10, unidad=kg
    → identifica área=Cocina
    → guarda en Sheets
    → devuelve: "✅ Registrado: 10kg de pollo en Cocina"
    """

async def consultar_stock(insumo: str) -> str:
    """
    Consulta el stock actual de un insumo.
    → lee Sheets
    → resume cantidades
    → devuelve respuesta legible
    """
```

#### `skills/empleados.py`

```python
async def registrar_asistencia(telegram_id: str, estado: str) -> str:
    """Marca presente/ausente/vacaciones."""

async def proximo_cumpleanos() -> str:
    """Consulta quién cumple próximamente."""
```

#### `skills/ventas.py`

```python
async def analizar_diferencias(fecha: str) -> str:
    """
    Compara ventas del POS vs consumo real de inventario.
    Detecta diferencias y sugiere causas.
    """
```

---

## 6. Lógica por Grupo de Telegram

| Grupo | ID (actual) | Qué puede hacer Bruno |
|---|---|---|
| **Inventario** | `-5240974489` | `/reportar`, consultar stock, alertas de niveles bajos |
| **Administrativo** | `-4944632677` | `/ordenes`, `/aprobar`, reportes de diferencias, pagos |
| **Team** | `-5181251045` | `/asistencia`, `/vacaciones`, cumpleaños, anuncios, memes |

El `brain.py` detecta en qué grupo está hablando y ajusta el contexto:
- En Inventario: prioriza datos de stock, alertas
- En Admin: prioriza números, aprobaciones, diferencias
- En Team: tono más relajado, recordatorios del equipo

---

## 7. System Prompt (Personalidad de Bruno)

Mismo `HERMES_SYSTEM_PROMPT` que ya tenés, pero mejorado:

```
Eres Bruno, el sistema operativo inteligente del restaurante Casa Antigua.
- Hablas 100% español, directo y proactivo.
- Confirmás acciones con ✅ y un resumen breve.
- No usás jerga técnica ("API", "webhook", "SQL").
- Tenés memoria: recordás quién es quién, stock histórico, patrones.
- Cuando detectás diferencias, explicás por qué pasó y qué revisar.
- Presentás opciones, no decidís solo.

CONTEXTO ACTUAL DEL RESTAURANTE:
- Inventario se reporta en el grupo Inventario.
- Órdenes y pagos van por el grupo Administrativo.
- Anuncios del equipo van por el grupo Team.

HERRAMIENTAS DISPONIBLES:
- Google Sheets (inventario, empleados, recetas, ventas).
- Puedes guardar datos, consultar tablas, calcular diferencias.
- No accedes a bancos, cajas físicas, ni cámaras.
```

---

## 8. Plan de Implementación (Fases)

### Fase 1: Fundación (1-2 días)
- [ ] `Dockerfile` + `docker-compose.yml` propios
- [ ] `config.py` leyendo `.env`
- [ ] `llm.py` conectando a Kimi
- [ ] `telegram_handlers.py` recibiendo mensajes
- [ ] Responder "Hola" con la personalidad de Bruno

### Fase 2: Memoria + Sheets (2-3 días)
- [ ] `memory.py` con PostgreSQL
- [ ] `sheets.py` leyendo/escribiendo
- [ ] `brain.py` con contexto de conversaciones

### Fase 3: Skills (3-5 días)
- [ ] `skills/inventario.py` — reportar y consultar
- [ ] `skills/empleados.py` — asistencia básica
- [ ] `skills/recetas.py` — consultar recetas
- [ ] `skills/ventas.py` — diferencias básicas

### Fase 4: Producción (1 día)
- [ ] Deploy en Easy Panel
- [ ] Test en los 3 grupos
- [ ] Monitoreo de logs

---

## 9. Deploy en Easy Panel

El `docker-compose.yml` va a ser simple:

```yaml
version: '3.8'

services:
  bruno:
    build: .
    container_name: bruno-bot
    restart: always
    environment:
      - TELEGRAM_TOKEN=${TELEGRAM_TOKEN}
      - KIMI_API_KEY=${KIMI_API_KEY}
      - LLM_PROVIDER=kimi
      - LLM_MODEL=kimi-k2.5
      - GOOGLE_SHEETS_ID=${GOOGLE_SHEETS_ID}
      - DATABASE_URL=${DATABASE_URL}
      - GROUP_ID_INVENTARIO=${GROUP_ID_INVENTARIO}
      - GROUP_ID_ADMIN=${GROUP_ID_ADMIN}
      - GROUP_ID_TEAM=${GROUP_ID_TEAM}
      - HERMES_SYSTEM_PROMPT=${HERMES_SYSTEM_PROMPT}
    volumes:
      - ./.env:/app/.env
      - ./token.json:/app/token.json
      - ./client_secret.json:/app/client_secret.json
```

**No más imágenes de terceros.** Build local, 100% nuestro código.

---

## 10. ¿Qué necesito de vos para empezar?

1. **¿OK con esta arquitectura?** ¿Algo querés cambiar, agregar o sacar?
2. **¿Seguimos con Kimi como LLM principal?** (podemos cambiar después con solo editar `.env`)
3. **¿La base de datos PostgreSQL que tenés en Easy Panel está vacía o tiene datos de Hermes?** (necesito saber si creo tablas nuevas o migro algo)
4. **¿Querés que empiece con la Fase 1 ahora?**

---

> **Nota:** Este documento es el plan. Una vez que vos des el OK, empiezo a escribir el código archivo por archivo, probando cada pieza antes de seguir.
