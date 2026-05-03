import re
from pypdf import PdfReader
from datetime import datetime

def _normalize(text: str) -> str:
    # Replace non-newline whitespace (tabs, \xa0, thin spaces…) with regular space,
    # then collapse runs of spaces. Keeps newlines so line-anchored patterns still work.
    text = re.sub(r'[^\S\n]', ' ', text)
    text = re.sub(r' +', ' ', text)
    return text


def parse_cierre_pdf(pdf_path):
    reader = PdfReader(pdf_path)
    text = _normalize("\n".join([p.extract_text() or "" for p in reader.pages]))

    def find_val(pattern, group=1):
        match = re.search(pattern, text)
        return match.group(group).replace(',', '').strip() if match else "0"

    raw_fecha = find_val(r"Fechas\s*:\s*\d{2}/\d{2}/\d{4}\s*-\s*(\d{2}/\d{2}/\d{4})")
    try:
        fecha_dt = datetime.strptime(raw_fecha, "%d/%m/%Y")
        fecha_iso = fecha_dt.strftime("%Y-%m-%d")
    except:
        fecha_iso = datetime.now().strftime("%Y-%m-%d")

    v_total = float(find_val(r"V\.\s*Total\s*:\s*([\d,.]+)"))
    propina = float(find_val(r"Propina\s*:\s*([\d,.]+)"))
    subtotal_raw = find_val(r"Sub\s*[Tt]otal\s*:\s*([\d,.]+)")
    subtotal = float(subtotal_raw) if subtotal_raw != "0" else (v_total - propina)

    return {
        "documento_id": find_val(r"Documento:\s*(\d+)"),
        "fecha": fecha_iso,
        "cajero": find_val(r"Cajero\s*:\s*(.*)"),
        "terminal": find_val(r"Terminal\s*:\s*(.+)"),
        "num_facturas": int(find_val(r"#\s*Fact\.\s*:\s*(\d+)") or 0),
        "facturas_anuladas": int(find_val(r"#F\.Anulas\s*:\s*(\d+)") or 0),
        "apertura": find_val(r"Apertura\s*:\s*(.+)"),
        "cierre": find_val(r"Cierre\s*:\s*(.+)"),
        "subtotal": subtotal,
        "propina": propina,
        "v_total": v_total,
        "descuento": float(find_val(r"Descuento\s*:\s*([\d,.]+)")),
        "iva": float(find_val(r"IVA\s*:\s*([\d,.]+)")),
        "efectivo_cds": float(find_val(r"Total\s*C\$\s*:\s*(-?[\d,.]+)").lstrip("-") or 0),
        "tarjetas_total": float(find_val(r"Total\s*Tarjetas\s*C\$:\s*([\d,.]+)")),
        "exonerado": float(find_val(r"Exonerado:\s*([\d,.]+)")),
        "transferencias_total": float(find_val(r"TIPO\s*:TRANSFERENCIA\s*([\d,.]+)")),
        "diferencia_pos": float(find_val(r"Diferenc\.\s*P\.O\.S\s*:\s*([-\d,.]+)")),
        "faltante": float(find_val(r"Faltante\s*:\s*([\d,.]+)")),
        "sobrante": float(find_val(r"Sobrante\s*:\s*([\d,.]+)")),
        "tipo_cambio": float(find_val(r"Tipo\s*Cambio\s*:\s*([\d,.]+)") or 0) or 36.62,
    }

def parse_ventas_pdf(pdf_path):
    reader = PdfReader(pdf_path)
    raw_text = " ".join([p.extract_text() or "" for p in reader.pages])
    clean_text = re.sub(r'\s+', ' ', _normalize(raw_text))
    
    items = []
    # Nuevo Regex: Cantidad (d+) -> Nombre (lo que sea hasta encontrar un precio) -> Precio (d.dd)
    # Ejemplo: 1 CHILAQUILES DE LA ABUELA SALSA ROJA 395.95
    matches = re.finditer(r"(\d+)\s+([A-Z\s´\.\']+?)\s+(\d+[\d,]*\.\d{2})", clean_text)
    
    for m in matches:
        qty = int(m.group(1))
        desc = m.group(2).strip()
        price = float(m.group(3).replace(',', ''))
        
        # Filtros de seguridad para no capturar basura
        if any(x in desc for x in ["SUBT.", "TOTAL", "CATEGORIA", "VENTA", "FECHA"]):
            continue
        if len(desc) < 2:
            continue
            
        items.append({
            "cantidad": qty,
            "descripcion": desc,
            "monto": price
        })
    return items
