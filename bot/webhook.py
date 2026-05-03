import base64
import logging
import os
import tempfile
import time

from aiohttp import web

from bot.config import GROUP_ID_ADMIN, GROUP_ID_INVENTARIO, WEBHOOK_SECRET
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

    silent = request.rel_url.query.get("silent", "0") == "1"
    if not silent and not resultado.get("duplicado"):
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
    fecha = body.get("fecha")
    logger.info(f"Webhook /sheets: {len(rows)} filas, fecha={fecha}")

    if not rows:
        return web.json_response({"ok": True, "synced": 0})

    from database.postgres import execute_query
    import datetime as dt

    sync_date = fecha or str(dt.date.today())
    synced = 0
    skipped = 0

    for row in rows:
        producto = str(row.get("producto") or row.get("product") or "").strip()
        external_id = str(
            row.get("external_id")
            or row.get("codigo")
            or row.get("code")
            or ""
        ).strip()
        area_name = str(row.get("area") or "").strip().lower()
        cantidad = row.get("cantidad") or row.get("quantity")
        tipo = str(row.get("tipo") or row.get("type") or "count").strip().lower()
        stock_min = row.get("stock_min")
        responsable = str(row.get("responsable") or row.get("usuario") or "sheets").strip() or "sheets"
        source = str(row.get("source") or "sheets").strip() or "sheets"

        if (not producto and not external_id) or cantidad is None:
            skipped += 1
            continue

        try:
            cantidad = float(cantidad)
        except (TypeError, ValueError):
            skipped += 1
            continue

        try:
            product_rows = execute_query(
                """
                SELECT p.id, p.area_id FROM products p
                JOIN areas a ON a.id = p.area_id
                WHERE p.is_active = TRUE
                  AND (
                    (%s <> '' AND p.external_id = %s)
                    OR LOWER(p.name) ILIKE LOWER(%s)
                  )
                  AND (%s = '' OR LOWER(a.name) = %s)
                LIMIT 1
                """,
                (external_id, external_id, f"%{producto}%", area_name, area_name),
                fetch=True,
            )
            if not product_rows:
                logger.warning(f"Sheets sync: producto no encontrado '{producto or external_id}'")
                skipped += 1
                continue

            product_id = product_rows[0]["id"]
            area_id = product_rows[0]["area_id"]

            if tipo == "entry":
                execute_query(
                    """
                    INSERT INTO inventory_entries (date, product_id, qty, responsable, source)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (date, product_id, source) DO UPDATE
                        SET qty = EXCLUDED.qty,
                            responsable = EXCLUDED.responsable
                    """,
                    (sync_date, product_id, cantidad, responsable, source),
                )
            else:
                execute_query(
                    """
                    INSERT INTO inventory_counts (date, area_id, product_id, counted_qty, reported_by, source)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (date, product_id, source) DO UPDATE
                        SET counted_qty = EXCLUDED.counted_qty,
                            reported_by = EXCLUDED.reported_by
                    """,
                    (sync_date, area_id, product_id, cantidad, responsable, source),
                )

            if stock_min is not None and str(stock_min).strip() != "":
                try:
                    min_qty = float(stock_min)
                    execute_query(
                        """
                        INSERT INTO stock_rules (product_id, area_id, min_qty)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (product_id, area_id) DO UPDATE
                            SET min_qty = EXCLUDED.min_qty
                        """,
                        (product_id, area_id, min_qty),
                    )
                except (TypeError, ValueError):
                    logger.warning(f"Sheets sync: stock_min inválido para '{producto or external_id}'")
            synced += 1
        except Exception as e:
            logger.error(f"Sheets sync row error ({producto or external_id}): {e}")
            skipped += 1

    logger.info(f"Sheets sync completo: {synced} guardados, {skipped} omitidos")
    return web.json_response({"ok": True, "synced": synced, "skipped": skipped, "fecha": sync_date})


async def handle_stock_alerts(request: web.Request) -> web.Response:
    if not _auth_ok(request):
        return web.json_response({"error": "Unauthorized"}, status=401)

    from skills import inventario as inv
    from bot.llm import humanize
    from bot.config import GROUP_ID_INVENTARIO

    alertas = inv.check_alerts()
    if not alertas:
        logger.info("Stock alerts: todo ok, sin notificación")
        return web.json_response({"ok": True, "alertas": 0})

    criticos = [a for a in alertas if a.get("stock_actual", 0) == 0]
    bajos = [a for a in alertas if a.get("stock_actual", 0) > 0]

    mensaje = humanize(
        {"alertas": alertas, "criticos": len(criticos), "bajos": len(bajos)},
        context="alerta automática de stock bajo mínimo post-sincronización"
    )

    telegram_app = request.app["telegram_app"]
    try:
        await telegram_app.bot.send_message(chat_id=GROUP_ID_INVENTARIO, text=mensaje)
        logger.info(f"Stock alerts enviado: {len(alertas)} productos ({len(criticos)} críticos)")
    except Exception as e:
        logger.error(f"handle_stock_alerts send_message error: {e}")

    return web.json_response({"ok": True, "alertas": len(alertas), "criticos": len(criticos)})


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


async def handle_pedido_semanal(request: web.Request) -> web.Response:
    if not _auth_ok(request):
        return web.json_response({"error": "Unauthorized"}, status=401)

    from skills import inventario as inv

    data = inv.pedido_semanal()
    mensaje = humanize(data, context="pedido semanal sugerido por proveedor para miercoles")
    telegram_app = request.app["telegram_app"]
    try:
        await telegram_app.bot.send_message(chat_id=GROUP_ID_INVENTARIO, text=mensaje)
    except Exception as e:
        logger.error(f"handle_pedido_semanal send_message error: {e}")
        return web.json_response({"ok": False, "error": str(e)}, status=500)

    return web.json_response({"ok": True, "proveedores": len(data)})


def create_app(telegram_app) -> web.Application:
    app = web.Application(client_max_size=20 * 1024 * 1024)  # 20MB for PDF base64 payloads
    app["telegram_app"] = telegram_app
    app.router.add_get("/health", handle_health)
    app.router.add_post("/webhook/cierre", handle_cierre)
    app.router.add_post("/webhook/cierre/pdf", handle_cierre_pdf)
    app.router.add_post("/webhook/sheets", handle_sheets)
    app.router.add_post("/webhook/stock-alerts", handle_stock_alerts)
    app.router.add_get("/cron/resumen-semanal", handle_resumen_semanal)
    app.router.add_get("/cron/pedido-semanal", handle_pedido_semanal)
    return app
