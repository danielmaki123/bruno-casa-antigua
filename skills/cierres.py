import datetime as dt
import logging
import os

from database.postgres import execute_query

logger = logging.getLogger(__name__)

_DIFF_UMBRAL = float(os.getenv("CIERRE_DIFF_UMBRAL", "50"))


def cierre_status(fecha: str = None) -> dict:
    try:
        target = dt.date.fromisoformat(fecha) if fecha else dt.date.today() - dt.timedelta(days=1)
    except ValueError:
        target = dt.date.today() - dt.timedelta(days=1)

    try:
        rows = execute_query(
            """
            SELECT
                documento_id, fecha, cajero,
                COALESCE(v_total, 0)              AS total,
                COALESCE(subtotal, 0)             AS subtotal,
                COALESCE(propina, 0)              AS propina,
                COALESCE(efectivo_cds, 0)         AS efectivo,
                COALESCE(tarjetas_total, 0)       AS tarjetas,
                COALESCE(transferencias_total, 0) AS transferencias,
                COALESCE(faltante, 0)             AS faltante,
                COALESCE(sobrante, 0)             AS sobrante,
                COALESCE(diferencia_pos, 0)       AS diferencia_pos,
                alerta_diferencia, alerta_faltante
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
        logger.error(f"cierre_status error: {e}")
        return {"error": str(e)}


def procesar_cierre_nuevo(cierre_data: dict, ventas_data: list) -> dict:
    """
    Valida y guarda un cierre nuevo. Retorna resumen con alertas.
    cierre_data: output de skills/parsers.parse_cierre_pdf()
    ventas_data: output de skills/parsers.parse_ventas_pdf()
    """
    alertas = []
    resultado = {"ok": True, "alertas": alertas}

    # Validar duplicado
    try:
        doc_id = cierre_data.get("documento_id")
        existing = execute_query(
            "SELECT id FROM cierres_caja WHERE documento_id = %s",
            (doc_id,),
            fetch=True,
        )
        if existing:
            resultado["ok"] = False
            resultado["duplicado"] = True
            resultado["mensaje"] = f"Cierre {doc_id} ya existe en DB."
            return resultado
    except Exception as e:
        logger.error(f"procesar_cierre_nuevo check duplicado: {e}")

    # Validación 1: subtotal + propina == total (tolerancia ±5)
    subtotal = float(cierre_data.get("subtotal", 0))
    propina = float(cierre_data.get("propina", 0))
    total = float(cierre_data.get("v_total", 0))
    if abs((subtotal + propina) - total) > 5:
        alertas.append(f"⚠️ subtotal+propina ({subtotal+propina:.2f}) ≠ total ({total:.2f})")

    # Validación 2: diferencia_pos > umbral
    diferencia_pos = float(cierre_data.get("diferencia_pos", 0))
    if abs(diferencia_pos) > _DIFF_UMBRAL:
        alertas.append(f"🔴 Diferencia POS: C$ {diferencia_pos:.2f} (umbral: {_DIFF_UMBRAL})")

    # Validación 3: faltante
    faltante = float(cierre_data.get("faltante", 0))
    if faltante > 0:
        alertas.append(f"⚠️ Faltante de caja: C$ {faltante:.2f}")

    # Guardar en DB
    try:
        _save_cierre(cierre_data, bool(alertas))
        if ventas_data:
            _save_ventas(cierre_data.get("documento_id"), cierre_data.get("fecha"), ventas_data)
    except Exception as e:
        logger.error(f"procesar_cierre_nuevo save error: {e}")
        resultado["ok"] = False
        resultado["error"] = str(e)
        return resultado

    resultado.update({
        "documento_id": doc_id,
        "fecha": str(cierre_data.get("fecha", "")),
        "total": total,
        "alertas": alertas,
        "tiene_alertas": bool(alertas),
    })
    return resultado


def _save_cierre(data: dict, tiene_alerta: bool) -> None:
    execute_query(
        """
        INSERT INTO cierres_caja (
            documento_id, fecha, cajero, terminal,
            num_facturas, facturas_anuladas, apertura, cierre,
            subtotal, propina, v_total, descuento, iva,
            efectivo_cds, tarjetas_total, transferencias_total,
            faltante, sobrante, diferencia_pos, tipo_cambio,
            alerta_diferencia, alerta_faltante
        ) VALUES (
            %(documento_id)s, %(fecha)s, %(cajero)s, %(terminal)s,
            %(num_facturas)s, %(facturas_anuladas)s, %(apertura)s, %(cierre)s,
            %(subtotal)s, %(propina)s, %(v_total)s, %(descuento)s, %(iva)s,
            %(efectivo_cds)s, %(tarjetas_total)s, %(transferencias_total)s,
            %(faltante)s, %(sobrante)s, %(diferencia_pos)s, %(tipo_cambio)s,
            %(alerta_diferencia)s, %(alerta_faltante)s
        )
        ON CONFLICT (documento_id) DO NOTHING
        """,
        {
            "documento_id": data.get("documento_id"),
            "fecha": data.get("fecha"),
            "cajero": data.get("cajero"),
            "terminal": data.get("terminal"),
            "num_facturas": data.get("num_facturas", 0),
            "facturas_anuladas": data.get("facturas_anuladas", 0),
            "apertura": data.get("apertura"),
            "cierre": data.get("cierre"),
            "subtotal": data.get("subtotal", 0),
            "propina": data.get("propina", 0),
            "v_total": data.get("v_total", 0),
            "descuento": data.get("descuento", 0),
            "iva": data.get("iva", 0),
            "efectivo_cds": data.get("efectivo_cds", 0),
            "tarjetas_total": data.get("tarjetas_total", 0),
            "transferencias_total": data.get("transferencias_total", 0),
            "faltante": data.get("faltante", 0),
            "sobrante": data.get("sobrante", 0),
            "diferencia_pos": data.get("diferencia_pos", 0),
            "tipo_cambio": data.get("tipo_cambio", 0),
            "alerta_diferencia": tiene_alerta,
            "alerta_faltante": float(data.get("faltante", 0)) > 0,
        },
    )


def _save_ventas(documento_id: str, fecha, ventas: list) -> None:
    for item in ventas:
        execute_query(
            """
            INSERT INTO ventas_detalle (cierre_id, fecha, categoria, descripcion, cantidad, monto)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
            """,
            (
                documento_id,
                fecha,
                item.get("categoria"),
                item.get("descripcion"),
                item.get("cantidad", 0),
                item.get("monto", 0),
            ),
        )
