"""
parse_cierre.py — Parsea CierrePos.pdf y Venta_Menu.pdf de Casa Antigua
Devuelve dos dicts: cierre_data y ventas_data, listos para insertar en PostgreSQL.

Uso:
    from scripts.parse_cierre import parse_cierre_pdf, parse_ventas_pdf
    cierre = parse_cierre_pdf("ruta/CierrePos.pdf")
    ventas = parse_ventas_pdf("ruta/Venta_Menu.pdf")
"""
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import pdfplumber


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _num(text: str) -> float:
    """Convierte texto a float. Soporta comas y espacios."""
    if not text:
        return 0.0
    cleaned = text.strip().replace(",", "").replace(" ", "")
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def _extract_text(pdf_path: str) -> str:
    """Extrae todo el texto de un PDF como string único."""
    with pdfplumber.open(pdf_path) as pdf:
        pages = [p.extract_text() or "" for p in pdf.pages]
    return "\n".join(pages)


def _find(pattern: str, text: str, group: int = 1, default: str = "") -> str:
    """Busca un patrón y devuelve el grupo capturado o default."""
    m = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
    return m.group(group).strip() if m else default


# ─── Parser: CierrePos.pdf ────────────────────────────────────────────────────

def parse_cierre_pdf(pdf_path: str) -> Dict[str, Any]:
    """
    Parsea el PDF de cierre de caja y devuelve un dict con todos los campos.
    El dict está listo para insertar en la tabla cierres_caja.
    """
    text = _extract_text(pdf_path)

    # Identificación
    documento_id = _find(r"Documento\s*:\s*(\d+)", text)
    fecha_str    = _find(r"Fechas\s*:\s*(\d{2}/\d{2}/\d{4})", text)
    cajero       = _find(r"Cajero\s*:\s*(.+)", text)
    terminal     = _find(r"Terminal\s*:\s*(.+)", text)
    fact_desde   = _find(r"Facturas\s*:\s*(\w+)\s*-", text)
    fact_hasta   = _find(r"Facturas\s*:\s*\w+\s*-\s*(\w+)", text)
    num_facturas = int(_find(r"#\s*Fact\.\s*:\s*(\d+)", text) or 0)
    fact_anulas  = int(_find(r"#F\.Anulas\s*:\s*(\d+)", text) or 0)

    # Timestamps (apertura / cierre)
    apertura_str = _find(r"Apertura\s*:\s*(.+)", text)
    cierre_str   = _find(r"Cierre\s*:\s*(.+)", text)

    # Datos de venta
    exonerado = _num(_find(r"Exonerado\s*:\s*([\d,.\-]+)", text))
    gravado   = _num(_find(r"Gravado\s*:\s*([\d,.\-]+)", text))
    subtotal  = _num(_find(r"Subtotal\s*:\s*([\d,.\-]+)", text))
    descuento = _num(_find(r"Descuento\s*:\s*([\d,.\-]+)", text))
    iva       = _num(_find(r"IVA\s*:\s*([\d,.\-]+)", text))
    propina   = _num(_find(r"Propina\s*:\s*([\d,.\-]+)", text))
    v_total   = _num(_find(r"V\.\s*Total\s*:\s*([\d,.\-]+)", text))

    # Efectivo
    efect_cds = _num(_find(r"Fact\. Contado en efectivo\.\s*C\$\s*U\$\s*([\d,.\-]+)", text))
    efect_usd = _num(_find(r"Fact\. Contado en efectivo\.\s*C\$\s*U\$\s*[\d,.\-]+\s+([\d,.\-]+)", text))

    # Tarjetas y transferencias
    tarjetas_total      = _num(_find(r"Total Tarjetas C\$\s*:\s*([\d,.\-]+)", text))
    transferencias_total = _num(_find(r"Total Ot\. Mtdos\s*:\s*([\d,.\-]+)\s+([\d,.\-]+)", text))

    # Conteo de efectivo
    conteo_cds = _num(_find(r"Total Conteo Cordobas\s*:\s*([\d,.\-]+)", text))

    # Declaración POS / apertura / auditoría
    declar_pos  = _num(_find(r"Declaraci[oó]n Cierres P\.O\.S fisico\s*C\$\s*([\d,.\-]+)", text))
    aper_cust   = _num(_find(r"Efectivo de Apertura/Custodio\s*C\$\s*([\d,.\-]+)", text))
    faltante    = _num(_find(r"Faltante\s*:\s*([\d,.\-]+)", text))
    sobrante    = _num(_find(r"Sobrante\s*:\s*([\d,.\-]+)", text))
    dif_pos     = _num(_find(r"Diferenc\.\s*P\.O\.S\s*:\s*([\d,.\-]+)", text))
    tipo_cambio = _num(_find(r"Tipo Cambio\s*:\s*([\d,.\-]+)", text))

    # Convertir fecha DD/MM/YYYY → YYYY-MM-DD para PostgreSQL
    fecha_iso = ""
    if fecha_str:
        parts = fecha_str.split("/")
        if len(parts) == 3:
            fecha_iso = f"{parts[2]}-{parts[1]}-{parts[0]}"

    return {
        "documento_id":          documento_id,
        "fecha":                 fecha_iso,
        "cajero":                cajero,
        "terminal":              terminal,
        "factura_desde":         fact_desde,
        "factura_hasta":         fact_hasta,
        "num_facturas":          num_facturas,
        "facturas_anuladas":     fact_anulas,
        "apertura":              apertura_str,
        "cierre":                cierre_str,
        "exonerado":             exonerado,
        "gravado":               gravado,
        "subtotal":              subtotal,
        "descuento":             descuento,
        "iva":                   iva,
        "propina":               propina,
        "v_total":               v_total,
        "efectivo_cds":          efect_cds,
        "efectivo_usd":          efect_usd,
        "tarjetas_total":        tarjetas_total,
        "transferencias_total":  transferencias_total,
        "conteo_efectivo_cds":   conteo_cds,
        "declaracion_pos":       declar_pos,
        "apertura_custodio":     aper_cust,
        "faltante":              faltante,
        "sobrante":              sobrante,
        "diferencia_pos":        dif_pos,
        "tipo_cambio":           tipo_cambio,
    }


# ─── Parser: Venta_Menu.pdf ───────────────────────────────────────────────────

def parse_ventas_pdf(pdf_path: str) -> List[Dict[str, Any]]:
    """
    Parsea el PDF de ventas por menú y devuelve una lista de dicts.
    Cada dict representa una fila de ventas_detalle.
    """
    text = _extract_text(pdf_path)

    # Extraer cierre_id y fecha del encabezado
    cierre_id = _find(r"#\s*Cierre\s*:\s*(\d+)", text)
    # Normalizar: quitar ceros a la izquierda si es necesario
    # (el PDF tiene 0100000289, el cierre tiene 00000289 — tomamos los últimos 8 dígitos)
    cierre_id_short = cierre_id.lstrip("0") if cierre_id else ""
    cierre_id_short = cierre_id_short.zfill(8)  # rellenar a 8 dígitos: 00000289

    fecha_str = _find(r"FECHA\s*:\s*(\d{2}/\d{2}/\d{4})", text)
    fecha_iso = ""
    if fecha_str:
        parts = fecha_str.split("/")
        if len(parts) == 3:
            fecha_iso = f"{parts[2]}-{parts[1]}-{parts[0]}"

    ventas: List[Dict[str, Any]] = []
    current_category = "SIN CATEGORIA"

    # Procesar línea por línea
    lines = text.splitlines()
    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Detectar nueva categoría (línea SIN números al inicio)
        # Las categorías son líneas en MAYÚSCULAS sin cantidad al principio
        if re.match(r'^[A-ZÁÉÍÓÚÑÜ][A-ZÁÉÍÓÚÑÜ\s\-]+$', line) and not re.match(r'^\d', line):
            # Excluir encabezados del PDF
            if line not in ("CANT.", "DESCRIPCION MENU SUB.", "VENTA-", "FIN"):
                current_category = line
            continue

        # Detectar línea de producto: empieza con número(s)
        # Formato: "3 CANTARITOS 857.85" o "23 LIMONADA DE FRESA 2229.85"
        m = re.match(r'^(\d+)\s+(.+?)\s+([\d,]+\.?\d*)$', line)
        if m:
            cantidad  = int(m.group(1))
            descripcion = m.group(2).strip()
            monto     = _num(m.group(3))

            # Ignorar subtotales de categoría
            if "Subt. Categoria" in descripcion or "Total" in descripcion:
                continue

            ventas.append({
                "cierre_id":   cierre_id_short,
                "fecha":       fecha_iso,
                "categoria":   current_category,
                "descripcion": descripcion,
                "cantidad":    cantidad,
                "monto":       monto,
            })

    return ventas


# ─── Test rápido ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import json
    import sys

    BASE = Path(__file__).resolve().parent.parent / "datos casa antigua"
    cierre_pdf = str(BASE / "CierrePos.pdf")
    ventas_pdf = str(BASE / "Venta_Menu.pdf")

    print("=== CIERRE DE CAJA ===")
    cierre = parse_cierre_pdf(cierre_pdf)
    for k, v in cierre.items():
        print(f"  {k}: {v}")

    print(f"\n=== VENTAS DETALLE ({len(parse_ventas_pdf(ventas_pdf))} items) ===")
    ventas = parse_ventas_pdf(ventas_pdf)
    for v in ventas[:5]:
        print(f"  {v}")
    print(f"  ... ({len(ventas)} productos en total)")

    # Auditoría rápida
    print("\n=== AUDITORIA ===")
    total_ventas_menu = sum(v["monto"] for v in ventas)
    print(f"  Exonerado cierre : C$ {cierre['exonerado']:,.2f}")
    print(f"  Total venta menu : C$ {total_ventas_menu:,.2f}")
    diff = abs(cierre["exonerado"] - total_ventas_menu)
    estado = "OK" if diff < 1 else f"DIFERENCIA: C$ {diff:,.2f}"
    print(f"  Cuadre           : {estado}")
    print(f"  Diferencia POS   : C$ {cierre['diferencia_pos']:,.2f}")
    print(f"  Faltante         : C$ {cierre['faltante']:,.2f}")
    print(f"  Sobrante         : C$ {cierre['sobrante']:,.2f}")
