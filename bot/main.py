import logging
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from bot.config import (
    TELEGRAM_BOT_TOKEN,
    AUTHORIZED_USERS,
    GROUP_ID_TEAM,
)

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not update.message:
        return
    user = update.effective_user
    logger.info(f"/start de {user.full_name} ({user.id})")
    if user.id not in AUTHORIZED_USERS:
        return
    await update.message.reply_text(
        f"Hola {user.first_name} 👋 Soy Bruno, el sistema operativo de Casa Antigua."
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_user:
        return

    user = update.effective_user
    chat_id = update.effective_chat.id
    text = update.message.text or ""

    logger.info(f"[{chat_id}] {user.full_name} ({user.id}): {text!r}")

    if chat_id == GROUP_ID_TEAM:
        await update.message.reply_text(
            "Para consultas usá el grupo correspondiente 👉 Inventario o Administrativo."
        )
        return

    if user.id not in AUTHORIZED_USERS:
        logger.warning(f"Usuario no autorizado ignorado: {user.id} ({user.full_name})")
        return

    await update.message.reply_text(f"Hola {user.first_name} 👋")


def main() -> None:
    logger.info("Bruno iniciando...")
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", handle_start))
    app.add_handler(MessageHandler(filters.ALL, handle_message))

    logger.info("Polling activo. Esperando mensajes.")
    app.run_polling()


if __name__ == "__main__":
    main()
