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
    quantity = float(entities.get("quantity", 0))
    action = entities.get("action", "entry")

    if not product_name or quantity <= 0:
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
