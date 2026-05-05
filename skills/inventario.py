import datetime as dt
import logging

from database.postgres import execute_query

logger = logging.getLogger(__name__)


def stock_check(area: str = None) -> dict:
    """Returns current stock for all products, optionally filtered by area."""
    try:
        if area:
            rows = execute_query(
                """
                SELECT
                    p.name AS producto,
                    a.name AS area,
                    p.unit AS unidad,
                    COALESCE(ic.counted_qty, 0) AS stock_actual,
                    COALESCE(sr.min_qty, 0)     AS stock_minimo,
                    COALESCE(sr.target_qty, 0)  AS stock_objetivo,
                    ic.date AS ultimo_conteo
                FROM products p
                JOIN areas a ON a.id = p.area_id
                LEFT JOIN stock_rules sr ON sr.product_id = p.id AND sr.area_id = p.area_id
                LEFT JOIN LATERAL (
                    SELECT counted_qty, date
                    FROM inventory_counts
                    WHERE product_id = p.id
                    ORDER BY date DESC, id DESC
                    LIMIT 1
                ) ic ON TRUE
                WHERE p.is_active = TRUE
                  AND LOWER(a.name) = LOWER(%s)
                ORDER BY p.name
                """,
                (area,),
                fetch=True,
            )
        else:
            rows = execute_query(
                """
                SELECT
                    p.name AS producto,
                    a.name AS area,
                    p.unit AS unidad,
                    COALESCE(ic.counted_qty, 0) AS stock_actual,
                    COALESCE(sr.min_qty, 0)     AS stock_minimo,
                    COALESCE(sr.target_qty, 0)  AS stock_objetivo,
                    ic.date AS ultimo_conteo
                FROM products p
                JOIN areas a ON a.id = p.area_id
                LEFT JOIN stock_rules sr ON sr.product_id = p.id AND sr.area_id = p.area_id
                LEFT JOIN LATERAL (
                    SELECT counted_qty, date
                    FROM inventory_counts
                    WHERE product_id = p.id
                    ORDER BY date DESC, id DESC
                    LIMIT 1
                ) ic ON TRUE
                WHERE p.is_active = TRUE
                ORDER BY a.name, p.name
                """,
                fetch=True,
            )

        productos = []
        for r in (rows or []):
            actual = float(r["stock_actual"] or 0)
            minimo = float(r["stock_minimo"] or 0)
            if minimo > 0:
                status = "critico" if actual < minimo * 0.5 else ("bajo" if actual < minimo else "ok")
            else:
                status = "ok"
            productos.append({
                "producto": r["producto"],
                "area": r["area"],
                "unidad": r["unidad"],
                "stock_actual": actual,
                "stock_minimo": minimo,
                "status": status,
                "ultimo_conteo": str(r["ultimo_conteo"]) if r["ultimo_conteo"] else None,
            })

        return {"productos": productos, "area": area, "sin_datos": len(productos) == 0}
    except Exception as e:
        logger.error(f"stock_check error: {e}")
        return {"error": str(e)}


def registrar_movimiento(entities: dict, user_name: str) -> dict:
    """
    Registers an inventory movement from pre-extracted entities.
    entities: {product, quantity, action: 'entry'|'exit'|'waste'}
    """
    product_name = entities.get("product", "")
    quantity_raw = entities.get("quantity")
    quantity = float(quantity_raw or 0)
    action = entities.get("action", "entry")

    if not product_name:
        return {"ok": False, "mensaje": "No pude entender el producto o la cantidad."}

    try:
        # Find product by name (case-insensitive)
        product_rows = execute_query(
            "SELECT id, name, area_id FROM products WHERE LOWER(name) ILIKE LOWER(%s) AND is_active = TRUE LIMIT 1",
            (f"%{product_name}%",),
            fetch=True,
        )
        if not product_rows:
            return {"ok": False, "mensaje": f"No encontré '{product_name}' en el catálogo."}

        product = dict(product_rows[0])
        product_id = product["id"]
        area_id = product["area_id"]

        # Get latest count
        latest = execute_query(
            """
            SELECT counted_qty FROM inventory_counts
            WHERE product_id = %s
            ORDER BY date DESC, id DESC
            LIMIT 1
            """,
            (product_id,),
            fetch=True,
        )
        current_qty = float(latest[0]["counted_qty"]) if latest else 0.0

        if quantity_raw is None or quantity == 0:
            return {
                "ok": True,
                "producto": product["name"],
                "cantidad_movimiento": 0,
                "accion": "query",
                "stock_anterior": current_qty,
                "stock_nuevo": current_qty,
                "usuario": user_name,
            }

        if quantity < 0:
            return {"ok": False, "mensaje": "No pude entender el producto o la cantidad."}

        if action == "entry":
            new_qty = current_qty + quantity
        elif action in ("exit", "waste"):
            new_qty = max(current_qty - quantity, 0)
        else:
            new_qty = quantity  # absolute count

        today = dt.date.today()
        execute_query(
            """
            INSERT INTO inventory_counts (date, area_id, product_id, counted_qty, reported_by, source)
            VALUES (%s, %s, %s, %s, %s, 'telegram')
            ON CONFLICT (date, product_id, source) DO UPDATE
                SET counted_qty = EXCLUDED.counted_qty,
                    reported_by = EXCLUDED.reported_by
            """,
            (today, area_id, product_id, new_qty, user_name),
        )

        return {
            "ok": True,
            "producto": product["name"],
            "cantidad_movimiento": quantity,
            "accion": action,
            "stock_anterior": current_qty,
            "stock_nuevo": new_qty,
            "usuario": user_name,
        }
    except Exception as e:
        logger.error(f"registrar_movimiento error: {e}")
        return {"ok": False, "error": str(e)}


def check_alerts(area: str = None) -> list[dict]:
    """Returns products below minimum stock threshold."""
    try:
        if area:
            rows = execute_query(
                """
                SELECT
                    p.name AS producto,
                    a.name AS area,
                    p.unit AS unidad,
                    COALESCE(ic.counted_qty, 0) AS stock_actual,
                    sr.min_qty AS stock_minimo
                FROM products p
                JOIN areas a ON a.id = p.area_id
                JOIN stock_rules sr ON sr.product_id = p.id
                LEFT JOIN LATERAL (
                    SELECT counted_qty FROM inventory_counts
                    WHERE product_id = p.id
                    ORDER BY date DESC, id DESC LIMIT 1
                ) ic ON TRUE
                WHERE p.is_active = TRUE
                  AND LOWER(a.name) = LOWER(%s)
                  AND COALESCE(ic.counted_qty, 0) < sr.min_qty
                ORDER BY (COALESCE(ic.counted_qty, 0) / NULLIF(sr.min_qty, 0)) ASC
                """,
                (area,),
                fetch=True,
            )
        else:
            rows = execute_query(
                """
                SELECT
                    p.name AS producto,
                    a.name AS area,
                    p.unit AS unidad,
                    COALESCE(ic.counted_qty, 0) AS stock_actual,
                    sr.min_qty AS stock_minimo
                FROM products p
                JOIN areas a ON a.id = p.area_id
                JOIN stock_rules sr ON sr.product_id = p.id
                LEFT JOIN LATERAL (
                    SELECT counted_qty FROM inventory_counts
                    WHERE product_id = p.id
                    ORDER BY date DESC, id DESC LIMIT 1
                ) ic ON TRUE
                WHERE p.is_active = TRUE
                  AND COALESCE(ic.counted_qty, 0) < sr.min_qty
                ORDER BY a.name, (COALESCE(ic.counted_qty, 0) / NULLIF(sr.min_qty, 0)) ASC
                """,
                fetch=True,
            )

        return [
            {
                "producto": r["producto"],
                "area": r["area"],
                "unidad": r["unidad"],
                "stock_actual": float(r["stock_actual"] or 0),
                "stock_minimo": float(r["stock_minimo"] or 0),
            }
            for r in (rows or [])
        ]
    except Exception as e:
        logger.error(f"check_alerts error: {e}")
        return []


def pedido_semanal() -> dict:
    try:
        provider_in_products = execute_query(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = 'products' AND column_name = 'provider_name'
            LIMIT 1
            """,
            fetch=True,
        )
        provider_expr = (
            "COALESCE(sr.provider_name, p.provider_name, 'Sin proveedor')"
            if provider_in_products
            else "COALESCE(sr.provider_name, 'Sin proveedor')"
        )

        rows = execute_query(
            f"""
            WITH latest_stock AS (
                SELECT DISTINCT ON (ic.product_id)
                    ic.product_id,
                    ic.counted_qty AS stock_actual
                FROM inventory_counts ic
                ORDER BY ic.product_id, ic.date DESC, ic.id DESC
            ),
            week_counts AS (
                SELECT product_id, COALESCE(SUM(counted_qty), 0) AS sum_counts_semana
                FROM inventory_counts
                WHERE date >= CURRENT_DATE - INTERVAL '7 days'
                GROUP BY product_id
            ),
            week_entries AS (
                SELECT product_id, COALESCE(SUM(qty), 0) AS sum_entries_semana
                FROM inventory_entries
                WHERE date >= CURRENT_DATE - INTERVAL '7 days'
                GROUP BY product_id
            )
            SELECT
                p.name AS producto,
                p.unit AS unidad,
                {provider_expr} AS proveedor,
                COALESCE(ls.stock_actual, 0) AS stock_actual,
                COALESCE(sr.min_qty, 0) AS stock_minimo,
                (COALESCE(wc.sum_counts_semana, 0) - COALESCE(ls.stock_actual, 0) + COALESCE(we.sum_entries_semana, 0)) AS consumo_semana
            FROM products p
            LEFT JOIN stock_rules sr ON sr.product_id = p.id AND sr.area_id = p.area_id
            LEFT JOIN latest_stock ls ON ls.product_id = p.id
            LEFT JOIN week_counts wc ON wc.product_id = p.id
            LEFT JOIN week_entries we ON we.product_id = p.id
            WHERE p.is_active = TRUE
            ORDER BY proveedor, p.name
            """,
            fetch=True,
        )

        resultado = {}
        for r in rows or []:
            stock_actual = float(r["stock_actual"] or 0)
            stock_minimo = float(r["stock_minimo"] or 0)
            consumo_semana = float(r["consumo_semana"] or 0)
            a_pedir = max((consumo_semana + stock_minimo) - stock_actual, 0.0)
            if a_pedir <= 0:
                continue
            proveedor = r["proveedor"] or "Sin proveedor"
            resultado.setdefault(proveedor, []).append(
                {
                    "producto": r["producto"],
                    "stock_actual": stock_actual,
                    "stock_minimo": stock_minimo,
                    "consumo_semana": consumo_semana,
                    "a_pedir": a_pedir,
                    "unidad": r["unidad"],
                }
            )

        return resultado
    except Exception as e:
        logger.error(f"pedido_semanal error: {e}")
        return {}
