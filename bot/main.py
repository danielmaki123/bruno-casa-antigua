import logging

from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

from bot.config import TELEGRAM_BOT_TOKEN
from bot.handlers import (
    cmd_alertas,
    cmd_cierre,
    cmd_help,
    cmd_inventario,
    cmd_start,
    cmd_ventas,
    handle_message,
)

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def main() -> None:
    logger.info("Bruno iniciando...")
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler(["help", "ayuda"], cmd_help))
    app.add_handler(CommandHandler("ventas", cmd_ventas))
    app.add_handler(CommandHandler("cierre", cmd_cierre))
    app.add_handler(CommandHandler("inventario", cmd_inventario))
    app.add_handler(CommandHandler("alertas", cmd_alertas))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Polling activo. Esperando mensajes.")
    app.run_polling()


if __name__ == "__main__":
    main()
