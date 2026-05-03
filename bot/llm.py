import datetime as dt
import json
import logging
from pathlib import Path

from openai import OpenAI

from bot.config import KIMI_API_KEY, KIMI_BASE_URL, KIMI_MODEL

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent

_CLASSIFY_SYSTEM_TEMPLATE = """Eres un clasificador de intenciones para el bot de un restaurante en Nicaragua. Hoy es {today}.

Analiza el mensaje y devuelve JSON con exactamente dos campos: "intent" y "entities".

Intents válidos:
- sales_today: ventas del día actual ("ventas hoy", "cómo van las ventas")
- sales_by_date: ventas de fecha o período específico ("ventas del martes", "ventas 28 abril", "ventas de ayer")
- top_products: ranking de productos más vendidos ("top productos", "qué se vende más")
- closing_status: consulta de cierre de caja ("cierre de ayer", "cómo salió el cierre")
- stock_check: consulta de stock de producto o área ("/inventario", "stock bebidas", "cuánta cerveza hay")
- stock_report: entrada o salida de inventario ("llegaron 10 cajas de coca", "se acabó el vodka")
- stock_alerts: lista de alertas de stock bajo ("/alertas")
- help: ayuda o lista de comandos ("/help", "/ayuda")
- unknown: cualquier otro mensaje

Entities puede contener: date (SIEMPRE en formato ISO YYYY-MM-DD), product, area, quantity, period.
IMPORTANTE: Resuelve fechas relativas usando la fecha de hoy ({today}). "ayer" = {yesterday}. "esta semana" = desde {week_start}.
Responde SOLO con JSON válido, sin texto adicional.
Ejemplos:
{{"intent": "sales_by_date", "entities": {{"date": "{yesterday}"}}}}
{{"intent": "stock_check", "entities": {{"product": "cerveza"}}}}
{{"intent": "stock_report", "entities": {{"product": "coca cola", "quantity": 10, "action": "entry"}}}}
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


def humanize(data: dict, context: str = "") -> str:
    prompt = f"Datos: {json.dumps(data, ensure_ascii=False, default=str)}"
    if context:
        prompt += f"\nContexto: {context}"

    try:
        response = _client.chat.completions.create(
            model=KIMI_MODEL,
            temperature=0.7,
            messages=[
                {"role": "system", "content": _SOUL + _CURRENCY_NOTE},
                {"role": "user", "content": prompt},
            ],
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"humanize error: {e}")
        return "⚠️ No pude generar una respuesta. Intentá de nuevo."
