"""
reporte_tool.py - Reportes de ventas e inventario para Bruno.
"""
import argparse
import datetime as dt
import os
import sys
from pathlib import Path
from urllib.parse import urlparse, urlunparse

import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
if not DATABASE_URL:
    print("Error: DATABASE_URL no está configurada en las variables de entorno.", file=sys.stderr)
    sys.exit(1)

DIAS = ["Lun", "Mar", "Mie", "Jue", "Vie", "Sab", "Dom"]


def fmt_money(value) -> str:
    amount = float(value or 0)
    sign = "-" if amount < 0 else ""
    return f"{sign}C${abs(amount):,.0f}"


def fmt_qty(value) -> str:
    amount = float(value or 0)
    if amount.is_integer():
        return f"{int(amount)}"
    return f"{amount:.1f}".rstrip("0").rstrip(".")


def fmt_date_short(date_value: dt.date) -> str:
    return date_value.strftime("%d/%m")


def connect():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


def log_action(action: str) -> None:
    print(f"[INFO] Ejecutando acción: {action}", file=sys.stderr)


def mask_database_url(url: str) -> str:
    try:
        parsed = urlparse(url)
        if not parsed.password:
            return url
        masked_netloc = parsed.netloc.replace(f":{parsed.password}@", ":***@")
        return urlunparse(parsed._replace(netloc=masked_netloc))
    except Exception:
        return url


def db_host_port_from_url(url: str):
    parsed = urlparse(url)
    return parsed.hostname or "desconocido", parsed.port or "desconocido"


def print_db_error(error: Exception) -> None:
    msg = str(error).lower()
    host, port = db_host_port_from_url(DATABASE_URL)
    if "connection refused" in msg:
        print(f"Error: No se puede conectar a la DB. Host: {host} Puerto: {port}")
    elif "password authentication failed" in msg or "authentication failed" in msg:
        print("Error: Credenciales incorrectas para la DB.")
    else:
        print(f"Error DB: {str(error)}")


def q_ventas_semana(conn) -> str:
    log_action("ventas_semana")
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                fecha,
                COALESCE(SUM(v_total), 0) AS total_ventas,
                COALESCE(SUM(efectivo_cds), 0) AS efectivo,
                COALESCE(SUM(tarjetas_total), 0) AS tarjeta
            FROM cierres_caja
            WHERE fecha >= CURRENT_DATE - INTERVAL '6 days'
              AND fecha <= CURRENT_DATE
            GROUP BY fecha
            ORDER BY fecha ASC
            """
        )
        rows = cur.fetchall()

    if not rows:
        desde = (dt.date.today() - dt.timedelta(days=6)).isoformat()
        hasta = dt.date.today().isoformat()
        return f"Sin datos para el período solicitado (tabla: cierres_caja, fecha: {desde} - {hasta})"

    lines = ["📊 Ventas - Últimos 7 días:"]
    for row in rows:
        fecha = row["fecha"]
        day = DIAS[fecha.weekday()]
        lines.append(
            f"• {day} {fmt_date_short(fecha)}: {fmt_money(row['total_ventas'])}  "
            f"(Efectivo: {fmt_money(row['efectivo'])} | Tarjeta: {fmt_money(row['tarjeta'])})"
        )

    total_semana = sum(float(r["total_ventas"] or 0) for r in rows)
    promedio = total_semana / len(rows) if rows else 0
    mejor = max(rows, key=lambda r: float(r["total_ventas"] or 0))
    mejor_label = f"{DIAS[mejor['fecha'].weekday()]} {fmt_date_short(mejor['fecha'])}"

    lines.extend(
        [
            "━━━━━━━━━━━━━━━━",
            f"Total semana: {fmt_money(total_semana)}",
            f"Promedio diario: {fmt_money(promedio)}",
            f"Mejor día: {mejor_label} con {fmt_money(mejor['total_ventas'])}",
        ]
    )
    return "\n".join(lines)


def q_ventas_hoy(conn) -> str:
    log_action("ventas_hoy")
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                fecha,
                COALESCE(v_total, 0) AS total_ventas,
                COALESCE(efectivo_cds, 0) AS efectivo_declarado,
                COALESCE(diferencia_pos, 0) AS diferencia
            FROM cierres_caja
            WHERE fecha = CURRENT_DATE
            ORDER BY created_at DESC
            LIMIT 1
            """
        )
        row = cur.fetchone()

    if not row:
        hoy = dt.date.today().isoformat()
        return f"Sin datos para el período solicitado (tabla: cierres_caja, fecha: {hoy} - {hoy})"

    tarjeta = max(float(row["total_ventas"] or 0) - float(row["efectivo_declarado"] or 0), 0)
    diff = float(row["diferencia"] or 0)
    status = "✅" if abs(diff) < 0.01 else "⚠️"
    return "\n".join(
        [
            f"📊 Ventas hoy ({row['fecha'].strftime('%d/%m')}):",
            f"Total: {fmt_money(row['total_ventas'])}",
            f"Efectivo: {fmt_money(row['efectivo_declarado'])} | Tarjeta: {fmt_money(tarjeta)}",
            f"Diferencia caja: {fmt_money(diff)} {status}",
        ]
    )


def q_ventas_categorias(conn, fecha: str = None) -> str:
    log_action("ventas_categorias")
    target = dt.date.fromisoformat(fecha) if fecha else dt.date.today()
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT categoria, total_unidades, total_monto
            FROM ventas_por_categoria
            WHERE fecha = %s
            ORDER BY total_monto DESC
            """,
            (target,),
        )
        rows = cur.fetchall()

    if not rows:
        return f"Sin datos de categorías para el día {fmt_date_short(target)} (tabla: ventas_por_categoria)"

    lines = [f"📦 Ventas por Categoría ({fmt_date_short(target)}):", ""]
    total_dia = 0
    for row in rows:
        monto = float(row["total_monto"] or 0)
        total_dia += monto
        lines.append(f"• <b>{(row['categoria'] or 'VARIOS').upper()}:</b> {fmt_money(monto)} ({int(row['total_unidades'])} items)")

    lines.append("━━━━━━━━━━━━━━━━")
    lines.append(f"Total Categorizado: {fmt_money(total_dia)}")
    
    return "\n".join(lines)


def q_cierre(conn, fecha: str) -> str:
    log_action("cierre")
    target = dt.date.fromisoformat(fecha)
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                fecha,
                COALESCE(v_total, 0) AS total_ventas,
                COALESCE(efectivo_cds, 0) AS efectivo_declarado,
                COALESCE(tarjetas_total, 0) AS efectivo_esperado,
                COALESCE(diferencia_pos, 0) AS diferencia,
                COALESCE(cajero, '') AS responsable
            FROM cierres_caja
            WHERE fecha = %s
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (target,),
        )
        row = cur.fetchone()

    if not row:
        date_iso = target.isoformat()
        return f"Sin datos para el período solicitado (tabla: cierres_caja, fecha: {date_iso} - {date_iso})"

    diff = float(row["diferencia"] or 0)
    estado = "OK ✅" if abs(diff) < 0.01 else "ALERTA ⚠️"
    responsable = row["responsable"] if row["responsable"] else "No registrado"
    return "\n".join(
        [
            f"📋 Cierre {row['fecha'].strftime('%d/%m/%Y')}:",
            f"Ventas totales: {fmt_money(row['total_ventas'])}",
            f"Efectivo declarado: {fmt_money(row['efectivo_declarado'])}",
            f"Efectivo esperado: {fmt_money(row['efectivo_esperado'])}",
            f"Diferencia: {fmt_money(diff)} ({estado})",
            f"Responsable: {responsable}",
        ]
    )


def q_stock_bajo(conn) -> str:
    log_action("stock_bajo")
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT producto, categoria, stock_actual, stock_minimo
            FROM stock_vs_minimo
            WHERE bajo_minimo = TRUE OR (stock_actual <= 0 AND stock_minimo >= 0)
            ORDER BY categoria, producto
            """
        )
        rows = cur.fetchall()

    if not rows:
        return "Sin datos para el período solicitado (tabla: stock_vs_minimo, condición: bajo_minimo = TRUE)"

    lines = ["⚠️ Productos bajo mínimo:"]
    for row in rows:
        actual = float(row["stock_actual"] or 0)
        minimo = float(row["stock_minimo"] or 0)
        icon = "🔴" if minimo > 0 and actual / minimo < 0.75 else "⚠️"
        unidad = "oz" if actual % 1 else "unidades"
        lines.append(
            f"• {row['producto']}: {fmt_qty(actual)} {unidad} (mín: {fmt_qty(minimo)} {unidad}) {icon}"
        )
    return "\n".join(lines)


def q_inventario_actual(conn) -> str:
    log_action("inventario_actual")
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                c.categoria,
                c.producto,
                c.unidad_tipo,
                i.cantidad_normalizada AS stock_actual,
                c.stock_minimo
            FROM inventario_catalogo c
            JOIN LATERAL (
                SELECT id2.cantidad_normalizada, id2.fecha
                FROM inventario_diario id2
                WHERE id2.producto_id = c.id
                ORDER BY id2.fecha DESC, id2.id DESC
                LIMIT 1
            ) i ON TRUE
            WHERE c.activo = TRUE
            ORDER BY c.categoria, c.producto
            """
        )
        rows = cur.fetchall()

    if not rows:
        return "Sin datos para el período solicitado (tabla: inventario_diario, condición: última lectura por producto)"

    fecha_ref = dt.date.today().strftime("%d/%m")
    lines = [f"📦 Inventario actual ({fecha_ref}):", ""]
    categoria_actual = None
    for row in rows:
        categoria = (row["categoria"] or "SIN CATEGORIA").upper()
        if categoria != categoria_actual:
            if categoria_actual is not None:
                lines.append("")
            lines.append(f"{categoria}:")
            categoria_actual = categoria

        actual = float(row["stock_actual"] or 0)
        minimo = float(row["stock_minimo"] or 0)
        unidad_tipo = (row["unidad_tipo"] or "").lower()
        if "oz" in unidad_tipo:
            unidad = "oz"
        elif "uni" in unidad_tipo:
            unidad = "unidades"
        else:
            unidad = "unidades"

        status = "✅" if actual >= minimo else "⚠️"
        lines.append(f"• {row['producto']}: {fmt_qty(actual)} {unidad} {status}")

    return "\n".join(lines)


def q_discrepancias(conn, dias: int) -> str:
    log_action("discrepancias")
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                a.fecha,
                COALESCE(c.producto, 'Producto desconocido') AS producto,
                a.mensaje
            FROM alertas_inventario a
            LEFT JOIN inventario_catalogo c ON c.id = a.producto_id
            WHERE a.fecha >= CURRENT_DATE - (%s::int - 1) * INTERVAL '1 day'
              AND a.fecha <= CURRENT_DATE
            ORDER BY a.fecha DESC, a.id DESC
            """,
            (dias,),
        )
        rows = cur.fetchall()

    if not rows:
        desde = (dt.date.today() - dt.timedelta(days=dias - 1)).isoformat()
        hasta = dt.date.today().isoformat()
        return f"Sin datos para el período solicitado (tabla: alertas_inventario, fecha: {desde} - {hasta})"

    lines = [f"🔍 Discrepancias últimos {dias} días:"]
    for row in rows:
        msg = (row["mensaje"] or "").strip()
        if not msg:
            msg = "discrepancia detectada"
        lines.append(f"• {row['fecha'].strftime('%d/%m')} - {row['producto']}: {msg} ⚠️")
    return "\n".join(lines)


def q_resumen(conn) -> str:
    log_action("resumen")
    ventas = q_ventas_hoy(conn)
    stock = q_stock_bajo(conn)
    return f"🧾 Resumen del día\n\n{ventas}\n\n{stock}"


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Reportes de ventas e inventario")
    parser.add_argument("--test", action="store_true", help="Probar conexión a DB y salir")
    parser.add_argument(
        "--action",
        choices=[
            "ventas_semana",
            "ventas_hoy",
            "cierre",
            "stock_bajo",
            "inventario_actual",
            "discrepancias",
            "resumen",
            "ventas_categorias",
        ],
    )
    parser.add_argument("--fecha", help="Fecha YYYY-MM-DD para accion cierre o ventas_categorias")
    parser.add_argument("--dias", type=int, default=7, help="Dias para discrepancias (default: 7)")
    args = parser.parse_args()

    print(f"[DEBUG] Conectando a: {mask_database_url(DATABASE_URL)}")

    try:
        conn = connect()
    except Exception as e:
        print_db_error(e)
        return

    if args.test:
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT COUNT(*) AS num_tables
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                    """
                )
                row = cur.fetchone()
            num_tables = int((row or {}).get("num_tables", 0))
            print(f"✅ Conexión DB OK - {num_tables} tablas encontradas")
        except Exception as e:
            print_db_error(e)
        finally:
            conn.close()
        return

    if not args.action:
        print("Debes enviar --action para ejecutar un reporte (o usar --test).")
        conn.close()
        return

    if args.action == "cierre" and not args.fecha:
        print("Debes enviar --fecha YYYY-MM-DD para la acción cierre.")
        conn.close()
        return

    if args.action == "discrepancias" and args.dias <= 0:
        print("--dias debe ser mayor que 0.")
        conn.close()
        return

    try:
        with conn:
            if args.action == "ventas_semana":
                print(q_ventas_semana(conn))
            elif args.action == "ventas_hoy":
                print(q_ventas_hoy(conn))
            elif args.action == "cierre":
                print(q_cierre(conn, args.fecha))
            elif args.action == "stock_bajo":
                print(q_stock_bajo(conn))
            elif args.action == "inventario_actual":
                print(q_inventario_actual(conn))
            elif args.action == "discrepancias":
                print(q_discrepancias(conn, args.dias))
            elif args.action == "resumen":
                print(q_resumen(conn))
            elif args.action == "ventas_categorias":
                print(q_ventas_categorias(conn, args.fecha))
    except Exception as e:
        print(f"Error DB: {str(e)}")


if __name__ == "__main__":
    main()
