import logging

from telegram import Update
from telegram.ext import ContextTypes

from bot import memory
from bot.config import (
    AUTHORIZED_USERS,
    GROUP_ID_ADMIN,
    GROUP_ID_INVENTARIO,
    GROUP_ID_TEAM,
)
from bot.llm import classify_intent, humanize
from skills import cierres, inventario, ventas

logger = logging.getLogger(__name__)

_FINANCIAL_GROUPS = frozenset({GROUP_ID_ADMIN})
_STOCK_GROUPS = frozenset({GROUP_ID_ADMIN, GROUP_ID_INVENTARIO})


def _is_private(chat_id: int) -> bool:
    return chat_id > 0


def _financial_ok(chat_id: int) -> bool:
    return chat_id in _FINANCIAL_GROUPS or _is_private(chat_id)


def _stock_ok(chat_id: int) -> bool:
    return chat_id in _STOCK_GROUPS or _is_private(chat_id)


_HELP = {
    "admin": (
        "📋 *Administrativo / Privado*\n"
        "/ventas \\[fecha\\] — ventas del día\n"
        "/cierre \\[fecha\\] — cierre de caja\n"
        "/inventario \\[área\\] — stock actual\n"
        "/alertas — productos bajo mínimo\n"
        "/help — esta lista"
    ),
    "inventario": (
        "📋 *Inventario*\n"
        "/inventario \\[área\\] — stock actual\n"
        "/alertas — productos bajo mínimo\n"
        "/help — esta lista"
    ),
    "team": "Para consultas usá 👉 Inventario o Administrativo.",
}

_INTENT_PERM = {
    "sales_today": _financial_ok,
    "sales_by_date": _financial_ok,
    "top_products": _financial_ok,
    "closing_status": _financial_ok,
    "stock_check": _stock_ok,
    "stock_report": _stock_ok,
    "stock_alerts": _stock_ok,
}


def _help_text(chat_id: int) -> str:
    if chat_id == GROUP_ID_TEAM:
        return _HELP["team"]
    if _financial_ok(chat_id):
        return _HELP["admin"]
    if chat_id == GROUP_ID_INVENTARIO:
        return _HELP["inventario"]
    return _HELP["admin"]


def _route(intent: str, entities: dict, chat_id: int, user_name: str = "") -> str:
    if intent == "help":
        return _help_text(chat_id)

    if intent == "sales_today":
        data = ventas.ventas_dia()
        return humanize(data, context="consulta de ventas del día")

    if intent == "sales_by_date":
        fecha = entities.get("date") or entities.get("fecha")
        data = ventas.ventas_dia(fecha)
        return humanize(data, context=f"consulta de ventas para {fecha or 'hoy'}")

    if intent == "top_products":
        rango = entities.get("period", "semana")
        data = ventas.top_productos(rango)
        return humanize({"top_productos": data, "rango": rango}, context="ranking de productos")

    if intent == "closing_status":
        fecha = entities.get("date") or entities.get("fecha")
        data = cierres.cierre_status(fecha)
        return humanize(data, context="estado de cierre de caja")

    if intent == "stock_check":
        area = entities.get("area")
        data = inventario.stock_check(area)
        return humanize(data, context=f"stock de inventario{' - ' + area if area else ''}")

    if intent == "stock_report":
        result = inventario.registrar_movimiento(entities, user_name)
        if result.get("ok"):
            prod = result.get("producto", "")
            qty = result.get("cantidad_movimiento", 0)
            nuevo = result.get("stock_nuevo", 0)
            return f"✅ Registrado: {qty} {prod} — {user_name}. Stock actual: {nuevo}"
        return result.get("mensaje") or "⚠️ No pude registrar el movimiento."

    if intent == "stock_alerts":
        area = entities.get("area")
        alertas = inventario.check_alerts(area)
        return humanize({"alertas": alertas, "area": area}, context="alertas de stock bajo mínimo")

    return "No entendí tu consulta. Escribí /help para ver qué puedo hacer."


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not update.message:
        return
    user = update.effective_user
    if user.id not in AUTHORIZED_USERS:
        return
    await update.message.reply_text(
        f"Hola {user.first_name} 👋 Soy Bruno, el sistema operativo de Casa Antigua."
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not update.message:
        return
    user = update.effective_user
    chat_id = update.effective_chat.id
    if user.id not in AUTHORIZED_USERS:
        return
    await update.message.reply_text(_help_text(chat_id), parse_mode="MarkdownV2")


async def cmd_ventas(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not update.message:
        return
    user = update.effective_user
    chat_id = update.effective_chat.id
    if user.id not in AUTHORIZED_USERS:
        return
    if not _financial_ok(chat_id):
        await update.message.reply_text("⚠️ Comando disponible solo en Administrativo o privado.")
        return
    fecha = context.args[0] if context.args else None
    data = ventas.ventas_dia(fecha)
    response = humanize(data, context=f"consulta de ventas para {fecha or 'hoy'}")
    await update.message.reply_text(response)


async def cmd_cierre(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not update.message:
        return
    user = update.effective_user
    chat_id = update.effective_chat.id
    if user.id not in AUTHORIZED_USERS:
        return
    if not _financial_ok(chat_id):
        await update.message.reply_text("⚠️ Comando disponible solo en Administrativo o privado.")
        return
    fecha = context.args[0] if context.args else None
    data = cierres.cierre_status(fecha)
    response = humanize(data, context="estado de cierre de caja")
    await update.message.reply_text(response)


async def cmd_inventario(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not update.message:
        return
    user = update.effective_user
    chat_id = update.effective_chat.id
    if user.id not in AUTHORIZED_USERS:
        return
    if not _stock_ok(chat_id):
        await update.message.reply_text("⚠️ Comando no disponible en este grupo.")
        return
    area = context.args[0] if context.args else None
    data = inventario.stock_check(area)
    response = humanize(data, context=f"stock de inventario{' - ' + area if area else ''}")
    await update.message.reply_text(response)


async def cmd_alertas(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not update.message:
        return
    user = update.effective_user
    chat_id = update.effective_chat.id
    if user.id not in AUTHORIZED_USERS:
        return
    if not _stock_ok(chat_id):
        await update.message.reply_text("⚠️ Comando no disponible en este grupo.")
        return
    area = context.args[0] if context.args else None
    alertas = inventario.check_alerts(area)
    response = humanize({"alertas": alertas, "area": area}, context="alertas de stock bajo mínimo")
    await update.message.reply_text(response)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_user:
        return

    user = update.effective_user
    chat_id = update.effective_chat.id
    text = update.message.text or ""

    logger.info(f"[{chat_id}] {user.full_name} ({user.id}): {text!r}")

    if chat_id == GROUP_ID_TEAM:
        await update.message.reply_text(_HELP["team"])
        return

    if user.id not in AUTHORIZED_USERS:
        logger.warning(f"No autorizado: {user.id} ({user.full_name})")
        return

    memory.save(chat_id, user.id, user.full_name, "user", text)

    result = classify_intent(text)
    intent = result.get("intent", "unknown")
    entities = result.get("entities", {})
    logger.info(f"Intent={intent} entities={entities}")

    perm_fn = _INTENT_PERM.get(intent)
    if perm_fn and not perm_fn(chat_id):
        response = "⚠️ No tenés acceso a esa información en este grupo."
        await update.message.reply_text(response)
        memory.save(chat_id, None, "Bruno", "assistant", response)
        return

    response = _route(intent, entities, chat_id, user_name=user.full_name)
    await update.message.reply_text(response)
    memory.save(chat_id, None, "Bruno", "assistant", response)
