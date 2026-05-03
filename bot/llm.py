import datetime as dt
import json
import logging
from pathlib import Path

from openai import OpenAI

from bot.config import KIMI_API_KEY, KIMI_BASE_URL, KIMI_MODEL
from bot.memory import get_recent

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent

_CLASSIFY_SYSTEM_TEMPLATE = """Eres un clasificador de intenciones para el bot de un restaurante en Nicaragua. Hoy es {today}.

Analiza el mensaje y devuelve JSON con exactamente dos campos: "intent" y "entities".

Intents válidos:
- sales_today: ventas del día actual ("ventas hoy", "cómo van las ventas")
- sales_by_date: ventas de una fecha específica ("ventas del martes", "ventas 28 abril", "ventas de ayer")
- sales_by_month: ventas de un mes completo ("ventas de diciembre", "todo enero 2025", "resumen de marzo", "de todo el mes")
- top_products: ranking de productos más vendidos ("top productos", "qué se vende más")
- closing_status: consulta de cierre de caja ("cierre de ayer", "cómo salió el cierre")
- stock_check: consulta de stock de producto o área ("/inventario", "stock bebidas", "cuánta cerveza hay")
- stock_report: entrada o salida de inventario ("llegaron 10 cajas de coca", "se acabó el vodka")
- stock_alerts: lista de alertas de stock bajo ("/alertas")
- weekly_order: sugerencia de pedido semanal por proveedor ("pedido de la semana", "que hay que pedir", "pedido miercoles")
- help: ayuda o lista de comandos ("/help", "/ayuda")
- unknown: cualquier otro mensaje

Entities puede contener: date (ISO YYYY-MM-DD), year (int), month (int 1-12), product, area, quantity, period.
IMPORTANTE: Resuelve fechas relativas usando la fecha de hoy ({today}). "ayer" = {yesterday}. "esta semana" = desde {week_start}.
Para sales_by_month extrae year y month como enteros. "diciembre 2025" = year:2025, month:12. Si no hay año usa {year}.
Responde SOLO con JSON válido, sin texto adicional.

Ejemplos variados (lenguaje natural nicaragüense):
"ventas de ayer" → {{"intent": "sales_by_date", "entities": {{"date": "{yesterday}"}}}}
"cómo estamos hoy?" → {{"intent": "sales_today", "entities": {{}}}}
"qué tal el sábado?" → {{"intent": "sales_by_date", "entities": {{"date": "<fecha del sábado pasado>"}}}}
"cuánto vendimos en diciembre?" → {{"intent": "sales_by_month", "entities": {{"year": 2025, "month": 12}}}}
"resumen de navidad" → {{"intent": "sales_by_month", "entities": {{"year": 2025, "month": 12}}}}
"qué tal estuvo enero?" → {{"intent": "sales_by_month", "entities": {{"year": {year}, "month": 1}}}}
"el mes pasado" → {{"intent": "sales_by_month", "entities": {{"year": <año correcto>, "month": <mes pasado>}}}}
"top de la semana" → {{"intent": "top_products", "entities": {{"period": "semana"}}}}
"qué se vendió más en agosto?" → {{"intent": "top_products", "entities": {{"period": "agosto"}}}}
"cómo salió el cierre?" → {{"intent": "closing_status", "entities": {{}}}}
"hay faltante?" → {{"intent": "closing_status", "entities": {{}}}}
"cuánta toña hay?" → {{"intent": "stock_check", "entities": {{"product": "toña"}}}}
"se acabó el vodka" → {{"intent": "stock_report", "entities": {{"product": "vodka", "quantity": 0, "action": "exit"}}}}
"llegaron 2 cajas de cerveza" → {{"intent": "stock_report", "entities": {{"product": "cerveza", "quantity": 2, "action": "entry"}}}}
"pedido de la semana" → {{"intent": "weekly_order", "entities": {{}}}}
"""

_CURRENCY_NOTE = (
    "\nIMPORTANTE: La moneda es Córdobas nicaragüenses (C$). Nunca uses $, MXN, USD ni ninguna otra moneda. Siempre escribe C$ antes del número."
    "\nFORMATO: Respuestas cortas, máximo 6 líneas. Usa saltos de línea para separar datos. Sin párrafos largos."
    "\nRESTRICCIONES: No inventes contexto, recordatorios, ni información que no esté en los datos. Solo responde con lo que está en los datos proporcionados."
)


def _load_soul() -> str:
    try:
        return (ROOT / ".hermes" / "SOUL.md").read_text(encoding="utf-8")
    except Exception:
        return (
            "Eres Bruno, el sistema operativo de Casa Antigua. "
            "Responde siempre en español, de forma breve y directa. "
            "Confirmación: ✅  Alerta: ⚠️  Crítico: 🔴"
        )


_SOUL = _load_soul()
_client = OpenAI(api_key=KIMI_API_KEY, base_url=KIMI_BASE_URL)


def _classify_system() -> str:
    today = dt.date.today()
    yesterday = today - dt.timedelta(days=1)
    week_start = today - dt.timedelta(days=6)
    return _CLASSIFY_SYSTEM_TEMPLATE.format(
        today=today.isoformat(),
        yesterday=yesterday.isoformat(),
        week_start=week_start.isoformat(),
        year=today.year,
    )


def classify_intent(message: str) -> dict:
    try:
        response = _client.chat.completions.create(
            model=KIMI_MODEL,
            temperature=0.3,
            messages=[
                {"role": "system", "content": _classify_system()},
                {"role": "user", "content": message},
            ],
        )
        raw = response.choices[0].message.content.strip()
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.warning(f"classify_intent: JSON inválido de Kimi: {message!r}")
        return {"intent": "unknown", "entities": {}}
    except Exception as e:
        logger.error(f"classify_intent error: {e}")
        return {"intent": "unknown", "entities": {}}


def humanize(data: dict, context: str = "", chat_id: int | None = None) -> str:
    prompt = f"Datos: {json.dumps(data, ensure_ascii=False, default=str)}"
    if context:
        prompt += f"\nContexto: {context}"

    messages = [{"role": "system", "content": _SOUL + _CURRENCY_NOTE}]
    if chat_id is not None:
        recent = get_recent(chat_id, limit=5)
        for msg in recent:
            role = msg.get("role")
            content = msg.get("content")
            if role in {"user", "assistant", "system"} and content:
                messages.append({"role": role, "content": str(content)})
    messages.append({"role": "user", "content": prompt})

    try:
        response = _client.chat.completions.create(
            model=KIMI_MODEL,
            temperature=0.7,
            messages=messages,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"humanize error: {e}")
        return "⚠️ No pude generar una respuesta. Intentá de nuevo."
