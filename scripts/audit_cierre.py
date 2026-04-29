"""
audit_cierre.py — Audita un cierre de caja, guarda en PostgreSQL y notifica al grupo Admin de Telegram.

Uso:
    python scripts/audit_cierre.py --cierre ruta/CierrePos.pdf --ventas ruta/Venta_Menu.pdf

O como módulo:
    from scripts.audit_cierre import procesar_cierre
    procesar_cierre("CierrePos.pdf", "Venta_Menu.pdf")
"""
import argparse
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

import psycopg2
import requests
from dotenv import load_dotenv

# ── Setup ─────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

sys.path.insert(0, str(ROOT))
from scripts.parse_cierre import parse_cierre_pdf, parse_ventas_pdf

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("audit_cierre")

DATABASE_URL   = os.getenv("DATABASE_URL")
BOT_TOKEN      = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN")
ADMIN_GROUP_ID = os.getenv("GROUP_ID_ADMIN")

# Umbral de diferencia POS para disparar alerta (en córdobas)
UMBRAL_DIFERENCIA = float(os.getenv("UMBRAL_DIFERENCIA_POS", "50"))


# ─── Telegram ─────────────────────────────────────────────────────────────────

def _telegram_send(chat_id: str, text: str) -> bool:
    """Envía un mensaje a un chat de Telegram."""
    if not BOT_TOKEN or not chat_id:
        logger.warning("Telegram no configurado (BOT_TOKEN o chat_id faltante)")
        return False
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    resp = requests.post(url, json={
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }, timeout=15)
    if resp.status_code != 200:
        logger.error(f"Error Telegram: {resp.text}")
        return False
    return True


# ─── PostgreSQL ───────────────────────────────────────────────────────────────

def _get_conn():
    return psycopg2.connect(DATABASE_URL)


def _ya_existe(conn, documento_id: str) -> bool:
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM cierres_caja WHERE documento_id = %s", (documento_id,))
    existe = cur.fetchone() is not None
    cur.close()
    return existe


def _insertar_cierre(conn, cierre: dict, alertas: dict) -> None:
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO cierres_caja (
            documento_id, fecha, cajero, terminal,
            factura_desde, factura_hasta, num_facturas, facturas_anuladas,
            exonerado, gravado, subtotal, descuento, iva, propina, v_total,
            efectivo_cds, efectivo_usd, tarjetas_total, transferencias_total,
            conteo_efectivo_cds, declaracion_pos, apertura_custodio,
            faltante, sobrante, diferencia_pos, tipo_cambio,
            auditado, alerta_diferencia, alerta_faltante, notas_auditoria
        ) VALUES (
            %(documento_id)s, %(fecha)s, %(cajero)s, %(terminal)s,
            %(factura_desde)s, %(factura_hasta)s, %(num_facturas)s, %(facturas_anuladas)s,
            %(exonerado)s, %(gravado)s, %(subtotal)s, %(descuento)s, %(iva)s, %(propina)s, %(v_total)s,
            %(efectivo_cds)s, %(efectivo_usd)s, %(tarjetas_total)s, %(transferencias_total)s,
            %(conteo_efectivo_cds)s, %(declaracion_pos)s, %(apertura_custodio)s,
            %(faltante)s, %(sobrante)s, %(diferencia_pos)s, %(tipo_cambio)s,
            TRUE, %(alerta_diferencia)s, %(alerta_faltante)s, %(notas_auditoria)s
        )
    """, {**cierre, **alertas})
    conn.commit()
    cur.close()


def _insertar_ventas(conn, ventas: list) -> None:
    if not ventas:
        return
    cur = conn.cursor()
    cur.executemany("""
        INSERT INTO ventas_detalle (cierre_id, fecha, categoria, descripcion, cantidad, monto)
        VALUES (%(cierre_id)s, %(fecha)s, %(categoria)s, %(descripcion)s, %(cantidad)s, %(monto)s)
        ON CONFLICT DO NOTHING
    """, ventas)
    conn.commit()
    cur.close()


# ─── Auditoría ────────────────────────────────────────────────────────────────

def _auditar(cierre: dict, ventas: list) -> dict:
    """
    Compara los totales del cierre vs las ventas detalladas.
    Retorna dict con flags de alerta y notas.
    """
    total_ventas_menu = sum(v["monto"] for v in ventas)
    diff_cuadre = abs(cierre["exonerado"] - total_ventas_menu)
    alerta_diferencia = cierre["diferencia_pos"] > UMBRAL_DIFERENCIA
    alerta_faltante   = cierre["faltante"] > 0

    notas = []
    if diff_cuadre > 1:
        notas.append(f"Cuadre cierre vs menu: diferencia C${diff_cuadre:,.2f}")
    if alerta_diferencia:
        notas.append(f"Diferencia POS supera umbral ({UMBRAL_DIFERENCIA} C$)")
    if alerta_faltante:
        notas.append(f"FALTANTE detectado: C${cierre['faltante']:,.2f}")
    if cierre["sobrante"] > 0:
        notas.append(f"Sobrante: C${cierre['sobrante']:,.2f}")

    return {
        "alerta_diferencia": alerta_diferencia,
        "alerta_faltante":   alerta_faltante,
        "notas_auditoria":   " | ".join(notas) if notas else "Sin alertas",
    }


def _build_mensaje(cierre: dict, ventas: list, alertas: dict) -> str:
    """Construye el mensaje de auditoría para Telegram."""
    estado = "✅ OK" if not alertas["alerta_diferencia"] and not alertas["alerta_faltante"] else "⚠️ ALERTA"

    # Top 5 productos del día
    top = sorted(ventas, key=lambda x: x["monto"], reverse=True)[:5]
    top_txt = "\n".join(f"  • {v['descripcion']} x{v['cantidad']} — C${v['monto']:,.2f}" for v in top)

    msg = f"""<b>📊 AUDITORIA CIERRE #{cierre['documento_id']} — {estado}</b>
📅 Fecha: {cierre['fecha']}  |  Cajero: {cierre['cajero']}
━━━━━━━━━━━━━━━━━━━━━━
💰 Venta Total:     C$ {cierre['v_total']:>12,.2f}
🍽️  Exonerado:       C$ {cierre['exonerado']:>12,.2f}
🎁 Propina:         C$ {cierre['propina']:>12,.2f}
💳 Tarjetas:        C$ {cierre['tarjetas_total']:>12,.2f}
🔄 Transferencias:  C$ {cierre['transferencias_total']:>12,.2f}
━━━━━━━━━━━━━━━━━━━━━━
{"🚨 FALTANTE:        C$ " + f"{cierre['faltante']:>12,.2f}" if alertas['alerta_faltante'] else "✅ Sin faltante"}
{"⚠️ Diferencia POS:  C$ " + f"{cierre['diferencia_pos']:>12,.2f}" if alertas['alerta_diferencia'] else f"✅ Diferencia POS:  C$ {cierre['diferencia_pos']:>12,.2f}"}
💹 Sobrante:        C$ {cierre['sobrante']:>12,.2f}
━━━━━━━━━━━━━━━━━━━━━━
🏆 <b>Top 5 del día:</b>
{top_txt}
━━━━━━━━━━━━━━━━━━━━━━
📦 {len(ventas)} productos vendidos  |  💱 TC: {cierre['tipo_cambio']}"""

    return msg


# ─── Main ─────────────────────────────────────────────────────────────────────

def procesar_cierre(cierre_pdf: str, ventas_pdf: str) -> dict:
    """
    Función principal. Parsea, audita, guarda en SQL y notifica.
    Retorna el resultado de la auditoría.
    """
    logger.info(f"Procesando: {cierre_pdf}")

    # 1. Parsear PDFs
    cierre = parse_cierre_pdf(cierre_pdf)
    ventas = parse_ventas_pdf(ventas_pdf)

    # Fix: asegurar que cierre_id en ventas coincida con documento_id del cierre
    for v in ventas:
        v["cierre_id"] = cierre["documento_id"]

    logger.info(f"Cierre #{cierre['documento_id']} | {len(ventas)} productos")

    # 2. Auditar
    alertas = _auditar(cierre, ventas)

    # 3. Guardar en PostgreSQL
    if not DATABASE_URL:
        logger.warning("DATABASE_URL no configurado — saltando guardado en SQL")
    else:
        conn = _get_conn()
        if _ya_existe(conn, cierre["documento_id"]):
            logger.info(f"Cierre #{cierre['documento_id']} ya existe en DB — omitiendo")
            conn.close()
        else:
            _insertar_cierre(conn, cierre, alertas)
            _insertar_ventas(conn, ventas)
            conn.close()
            logger.info(f"Cierre #{cierre['documento_id']} guardado en PostgreSQL")

    # 4. Enviar a Telegram Admin
    mensaje = _build_mensaje(cierre, ventas, alertas)
    if ADMIN_GROUP_ID:
        ok = _telegram_send(ADMIN_GROUP_ID, mensaje)
        logger.info(f"Telegram: {'enviado' if ok else 'error'}")

    return {
        "documento_id": cierre["documento_id"],
        "fecha":        cierre["fecha"],
        "v_total":      cierre["v_total"],
        "alertas":      alertas,
        "mensaje":      mensaje,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Audita y guarda un cierre de caja")
    parser.add_argument("--cierre", required=True, help="Ruta al PDF CierrePos")
    parser.add_argument("--ventas", required=True, help="Ruta al PDF Venta_Menu")
    args = parser.parse_args()

    resultado = procesar_cierre(args.cierre, args.ventas)
    print(f"\n{'='*50}")
    print(resultado["mensaje"])
    print(f"{'='*50}")
    print(f"Alertas: {resultado['alertas']}")
