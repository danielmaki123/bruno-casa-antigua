import base64
import logging
import os
import tempfile
import time

from aiohttp import web

from bot.config import GROUP_ID_ADMIN, WEBHOOK_SECRET
from bot.llm import humanize
from skills import cierres, ventas
from skills.parsers import parse_cierre_pdf, parse_ventas_pdf

logger = logging.getLogger(__name__)

_start_time = time.time()


def _auth_ok(request: web.Request) -> bool:
    if not WEBHOOK_SECRET:
        return True
    return request.headers.get("X-Webhook-Secret") == WEBHOOK_SECRET


async def handle_health(request: web.Request) -> web.Response:
    return web.json_response({"status": "ok", "uptime": int(time.time() - _start_time)})


async def handle_cierre(request: web.Request) -> web.Response:
    if not _auth_ok(request):
        logger.warning("Webhook /cierre: auth fallida")
        return web.json_response({"error": "Unauthorized"}, status=401)

    try:
        body = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    cierre_data = body.get("cierre_data", {})
    ventas_data = body.get("ventas_data", [])
    doc_id = cierre_data.get("documento_id", "unknown")
    logger.info(f"Webhook /cierre: documento {doc_id}")

    resultado = cierres.procesar_cierre_nuevo(cierre_data, ventas_data)

    telegram_app = request.app["telegram_app"]
    mensaje = humanize(resultado, context="nuevo cierre de caja procesado")
    try:
        await telegram_app.bot.send_message(chat_id=GROUP_ID_ADMIN, text=mensaje)
    except Exception as e:
        logger.error(f"handle_cierre send_message error: {e}")

    return web.json_response({"ok": True, "documento_id": doc_id})


async def handle_cierre_pdf(request: web.Request) -> web.Response:
    if not _auth_ok(request):
        return web.json_response({"error": "Unauthorized"}, status=401)

    try:
        body = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    attachments = body.get("attachments", [])
    if not attachments:
        return web.json_response({"error": "No attachments"}, status=400)

    cierre_data = None
    ventas_data = []

    for att in attachments:
        filename = att.get("filename", "").lower()
        pdf_b64 = att.get("data", "")
        try:
            pdf_bytes = base64.b64decode(pdf_b64)
        except Exception:
            logger.warning(f"handle_cierre_pdf: base64 decode failed for {filename}")
            continue

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(pdf_bytes)
            tmp_path = f.name

        try:
            if "venta" in filename or "menu" in filename:
                ventas_data = parse_ventas_pdf(tmp_path)
                logger.info(f"Ventas PDF parsed: {len(ventas_data)} items")
            elif cierre_data is None and "cierre" in filename:
                cierre_data = parse_cierre_pdf(tmp_path)
                logger.info(f"Cierre PDF parsed: doc {cierre_data.get('documento_id')}")
            else:
                logger.info(f"Skipping non-cierre PDF: {filename}")
        except Exception as e:
            logger.error(f"handle_cierre_pdf parse error ({filename}): {e}")
        finally:
            os.unlink(tmp_path)

    if not cierre_data:
        return web.json_response({"error": "No cierre PDF found or parse failed"}, status=400)

    resultado = cierres.procesar_cierre_nuevo(cierre_data, ventas_data)

    telegram_app = request.app["telegram_app"]
    mensaje = humanize(resultado, context="nuevo cierre de caja procesado")
    try:
        await telegram_app.bot.send_message(chat_id=GROUP_ID_ADMIN, text=mensaje)
    except Exception as e:
        logger.error(f"handle_cierre_pdf send_message error: {e}")

    return web.json_response({"ok": True, "documento_id": cierre_data.get("documento_id")})


async def handle_sheets(request: web.Request) -> web.Response:
    if not _auth_ok(request):
        return web.json_response({"error": "Unauthorized"}, status=401)

    try:
        body = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    rows = body.get("rows", [])
    logger.info(f"Webhook /sheets: {len(rows)} filas recibidas")
    # Sheets sync implementado en Fase 2
    return web.json_response({"ok": True, "synced": 0, "note": "sheets sync pending Fase 2"})


async def handle_resumen_semanal(request: web.Request) -> web.Response:
    logger.info("Cron /resumen-semanal disparado")
    data = ventas.ventas_semana()
    mensaje = humanize(data, context="resumen semanal de ventas")

    telegram_app = request.app["telegram_app"]
    try:
        await telegram_app.bot.send_message(chat_id=GROUP_ID_ADMIN, text=mensaje)
    except Exception as e:
        logger.error(f"handle_resumen_semanal send_message error: {e}")
        return web.json_response({"ok": False, "error": str(e)}, status=500)

    return web.json_response({"ok": True})


def create_app(telegram_app) -> web.Application:
    app = web.Application(client_max_size=20 * 1024 * 1024)  # 20MB for PDF base64 payloads
    app["telegram_app"] = telegram_app
    app.router.add_get("/health", handle_health)
    app.router.add_post("/webhook/cierre", handle_cierre)
    app.router.add_post("/webhook/cierre/pdf", handle_cierre_pdf)
    app.router.add_post("/webhook/sheets", handle_sheets)
    app.router.add_get("/cron/resumen-semanal", handle_resumen_semanal)
    return app
