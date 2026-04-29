import os
import sys
import json
import logging
import requests
import base64
import tempfile
import time
from pathlib import Path
from dotenv import load_dotenv

# Setup paths
ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
sys.path.insert(0, str(ROOT))

from scripts.inventario_monitor import _get_access_token
from scripts.audit_cierre import parse_cierre_pdf, parse_ventas_pdf, _insertar_cierre, _insertar_ventas, _auditar, _get_conn, _ya_existe

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("backfill")

GMAIL_API = "https://gmail.googleapis.com/gmail/v1/users/me"
DATABASE_URL = os.getenv("DATABASE_URL")

def get_headers():
    return {"Authorization": f"Bearer {_get_access_token()}"}

def list_messages(query):
    all_messages = []
    page_token = None
    while True:
        params = {"q": query, "maxResults": 100}
        if page_token:
            params["pageToken"] = page_token
        
        resp = requests.get(f"{GMAIL_API}/messages", headers=get_headers(), params=params)
        resp.raise_for_status()
        data = resp.json()
        all_messages.extend(data.get("messages", []))
        page_token = data.get("nextPageToken")
        if not page_token:
            break
    return all_messages

def get_message(msg_id):
    resp = requests.get(f"{GMAIL_API}/messages/{msg_id}", headers=get_headers())
    resp.raise_for_status()
    return resp.json()

def get_attachment(msg_id, att_id):
    resp = requests.get(f"{GMAIL_API}/messages/{msg_id}/attachments/{att_id}", headers=get_headers())
    resp.raise_for_status()
    data = resp.json().get("data", "")
    return base64.urlsafe_b64decode(data + "==")

def extract_pdfs(msg):
    found = {}
    def walk_parts(parts):
        for p in parts:
            fname = p.get("filename", "")
            if fname.lower().endswith(".pdf"):
                aid = p.get("body", {}).get("attachmentId")
                if aid:
                    if "cierre" in fname.lower(): found["cierre"] = (fname, aid)
                    elif "venta" in fname.lower() or "menu" in fname.lower(): found["ventas"] = (fname, aid)
            if "parts" in p: walk_parts(p["parts"])
    payload = msg.get("payload", {})
    if "parts" in payload: walk_parts(payload["parts"])
    return found

def run_backfill(after="2026/01/01"):
    query = f"subject:\"Cierre de Caja\" after:{after}"
    logger.info(f"Buscando correos: {query}")
    messages = list_messages(query)
    logger.info(f"Encontrados {len(messages)} correos para procesar")

    conn = _get_conn()
    processed_count = 0
    skipped_count = 0
    error_count = 0

    for m in messages:
        msg_id = m['id']
        try:
            msg = get_message(msg_id)
            pdfs = extract_pdfs(msg)
            
            if "cierre" not in pdfs or "ventas" not in pdfs:
                logger.warning(f"Mensaje {msg_id} no tiene los PDFs requeridos")
                skipped_count += 1
                continue

            with tempfile.TemporaryDirectory() as tmpdir:
                c_fn, c_id = pdfs["cierre"]
                v_fn, v_id = pdfs["ventas"]
                c_path = Path(tmpdir) / c_fn
                v_path = Path(tmpdir) / v_fn
                
                c_path.write_bytes(get_attachment(msg_id, c_id))
                v_path.write_bytes(get_attachment(msg_id, v_id))

                # Parsear
                cierre = parse_cierre_pdf(str(c_path))
                ventas = parse_ventas_pdf(str(v_path))
                
                if not cierre.get("documento_id"):
                    logger.warning(f"No se pudo obtener documento_id de {msg_id}")
                    skipped_count += 1
                    continue

                if _ya_existe(conn, cierre["documento_id"]):
                    # logger.info(f"Cierre {cierre['documento_id']} ya existe. Saltando.")
                    skipped_count += 1
                    continue

                # Fix ID mismatch
                for v in ventas:
                    v["cierre_id"] = cierre["documento_id"]

                # Auditar (para sacar alertas)
                alertas = _auditar(cierre, ventas)
                
                # Insertar
                _insertar_cierre(conn, cierre, alertas)
                _insertar_ventas(conn, ventas)
                
                processed_count += 1
                logger.info(f"[{processed_count}] Guardado cierre {cierre['documento_id']} de fecha {cierre['fecha']}")

        except Exception as e:
            logger.error(f"Error procesando mensaje {msg_id}: {e}")
            error_count += 1
            # Reintentar conexión si es error de DB
            if "psycopg2" in str(type(e)):
                conn = _get_conn()

    conn.close()
    logger.info(f"BACKFILL COMPLETADO: {processed_count} procesados, {skipped_count} saltados, {error_count} errores.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Backfill cierres desde Gmail")
    parser.add_argument("--after", default="2026/01/01", help="Fecha inicio YYYY/MM/DD")
    args = parser.parse_args()
    
    run_backfill(after=args.after)
