import asyncio
import logging

from aiohttp import web
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

from bot.config import TELEGRAM_BOT_TOKEN, WEBHOOK_PORT
from scripts.db_migration_fase1 import run_migration
from scripts.inventario_v2_migration import run_migration as run_migration_v2
from bot.handlers import (
    cmd_alertas,
    cmd_cierre,
    cmd_help,
    cmd_inventario,
    cmd_start,
    cmd_ventas,
    handle_message,
)
from bot.webhook import create_app

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def _fix_inventario_unique() -> None:
    import os
    import psycopg2
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"])
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute("""
            DELETE FROM inventario_diario a
            USING inventario_diario b
            WHERE a.fecha = b.fecha
              AND a.producto_id = b.producto_id
              AND a.id < b.id
        """)
        cur.execute("""
            ALTER TABLE inventario_diario
            ADD CONSTRAINT IF NOT EXISTS inventario_diario_fecha_producto_id_key
            UNIQUE (fecha, producto_id)
        """)
        cur.close()
        conn.close()
        logger.info("inventario_diario: dedup + UNIQUE OK")
    except Exception as e:
        logger.error(f"inventario fix error: {e}")


def _run_migration_v2() -> None:
    import os
    import psycopg2
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"])
        run_migration_v2(conn)
        conn.close()
    except Exception as e:
        logger.error(f"DB migration v2 error: {e}")


def _run_migration() -> None:
    import os
    import psycopg2
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"])
        run_migration(conn)
        conn.close()
        logger.info("DB migration Fase 1 OK")
    except Exception as e:
        logger.error(f"DB migration error: {e}")


async def main() -> None:
    logger.info("Bruno iniciando...")
    _run_migration()
    _run_migration_v2()
    _fix_inventario_unique()

    telegram_app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    telegram_app.add_handler(CommandHandler("start", cmd_start))
    telegram_app.add_handler(CommandHandler(["help", "ayuda"], cmd_help))
    telegram_app.add_handler(CommandHandler("ventas", cmd_ventas))
    telegram_app.add_handler(CommandHandler("cierre", cmd_cierre))
    telegram_app.add_handler(CommandHandler("inventario", cmd_inventario))
    telegram_app.add_handler(CommandHandler("alertas", cmd_alertas))
    telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    http_app = create_app(telegram_app)
    runner = web.AppRunner(http_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", WEBHOOK_PORT)
    await site.start()
    logger.info(f"HTTP server en puerto {WEBHOOK_PORT}")

    async with telegram_app:
        await telegram_app.start()
        await telegram_app.updater.start_polling()
        logger.info("Polling activo. Esperando mensajes.")
        try:
            await asyncio.Event().wait()
        finally:
            await telegram_app.updater.stop()
            await telegram_app.stop()

    await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
