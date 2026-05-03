import datetime as dt
import logging

from database.postgres import execute_query

logger = logging.getLogger(__name__)

_RANGO_DAYS = {"hoy": 0, "semana": 6, "mes": 29}


def ventas_dia(fecha: str = None) -> dict:
    try:
        target = dt.date.fromisoformat(fecha) if fecha else dt.date.today()
    except ValueError:
        target = dt.date.today()

    try:
        rows = execute_query(
            """
            SELECT
                fecha,
                COALESCE(v_total, 0)              AS total,
                COALESCE(efectivo_cds, 0)          AS efectivo,
                COALESCE(tarjetas_total, 0)        AS tarjetas,
                COALESCE(transferencias_total, 0)  AS transferencias,
                COALESCE(propina, 0)               AS propina,
                COALESCE(diferencia_pos, 0)        AS diferencia_pos,
                COALESCE(num_facturas, 0)          AS tickets,
                cajero
            FROM cierres_caja
            WHERE fecha = %s
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (target,),
            fetch=True,
        )
        if not rows:
            return {"fecha": str(target), "sin_datos": True}
        r = dict(rows[0])
        r["fecha"] = str(r["fecha"])
        return r
    except Exception as e:
        logger.error(f"ventas_dia error: {e}")
        return {"error": str(e)}


def ventas_mes(year: int, month: int) -> dict:
    try:
        rows = execute_query(
            """
            SELECT
                fecha,
                COALESCE(v_total, 0)             AS total,
                COALESCE(efectivo_cds, 0)         AS efectivo,
                COALESCE(tarjetas_total, 0)       AS tarjetas,
                COALESCE(transferencias_total, 0) AS transferencias,
                COALESCE(propina, 0)              AS propina,
                COALESCE(num_facturas, 0)         AS tickets
            FROM cierres_caja
            WHERE EXTRACT(YEAR FROM fecha) = %s
              AND EXTRACT(MONTH FROM fecha) = %s
            ORDER BY fecha ASC
            """,
            (year, month),
            fetch=True,
        )
        dias = [dict(r) | {"fecha": str(r["fecha"])} for r in (rows or [])]
        total = sum(float(d.get("total", 0)) for d in dias)
        propina = sum(float(d.get("propina", 0)) for d in dias)
        tickets = sum(int(d.get("tickets", 0)) for d in dias)
        return {
            "year": year, "month": month,
            "dias": len(dias),
            "total_mes": total,
            "propina_mes": propina,
            "tickets_mes": tickets,
            "detalle": dias,
            "sin_datos": len(dias) == 0,
        }
    except Exception as e:
        logger.error(f"ventas_mes error: {e}")
        return {"error": str(e)}


def ventas_semana() -> dict:
    try:
        rows = execute_query(
            """
            SELECT
                fecha,
                COALESCE(SUM(v_total), 0)       AS total,
                COALESCE(SUM(efectivo_cds), 0)   AS efectivo,
                COALESCE(SUM(tarjetas_total), 0) AS tarjetas,
                COUNT(*)                          AS cierres
            FROM cierres_caja
            WHERE fecha >= CURRENT_DATE - INTERVAL '6 days'
              AND fecha <= CURRENT_DATE
            GROUP BY fecha
            ORDER BY fecha ASC
            """,
            fetch=True,
        )
        dias = [dict(r) | {"fecha": str(r["fecha"])} for r in (rows or [])]
        total = sum(float(d.get("total", 0)) for d in dias)
        return {"dias": dias, "total_semana": total, "sin_datos": len(dias) == 0}
    except Exception as e:
        logger.error(f"ventas_semana error: {e}")
        return {"error": str(e)}


def top_productos(rango: str = "semana") -> list[dict]:
    days_back = _RANGO_DAYS.get(rango, 6)
    try:
        rows = execute_query(
            """
            SELECT
                descripcion,
                categoria,
                SUM(cantidad) AS unidades,
                SUM(monto)    AS total_monto
            FROM ventas_detalle
            WHERE fecha >= CURRENT_DATE - (%s * INTERVAL '1 day')
            GROUP BY descripcion, categoria
            ORDER BY total_monto DESC
            LIMIT 10
            """,
            (days_back,),
            fetch=True,
        )
        return [dict(r) for r in (rows or [])]
    except Exception as e:
        logger.error(f"top_productos error: {e}")
        return []
