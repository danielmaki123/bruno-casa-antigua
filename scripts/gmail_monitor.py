"""
gmail_monitor.py — Monitorea Gmail y procesa cierres de caja y liquidaciones bancarias.

Busca correos de:
1. CIELO POS (Cierres de caja)
2. BAC (Liquidaciones)
3. BANPRO (Liquidaciones)

Uso (ejecución continua):
    python scripts/gmail_monitor.py
"""
import argparse
import base64
import json
import logging
import os
import re
import sys
import time
import tempfile
import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
sys.path.insert(0, str(ROOT))

from scripts.audit_cierre import procesar_cierre

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("gmail_monitor")

# ── Config ────────────────────────────────────────────────────────────────────
CHECK_INTERVAL   = int(os.getenv("GMAIL_CHECK_INTERVAL", "300"))
SUBJECT_FILTER   = os.getenv("GMAIL_SUBJECT_FILTER", "Cierre de Caja")
GMAIL_API        = "https://gmail.googleapis.com/gmail/v1/users/me"
PROCESSED_FILE   = Path(os.getenv("PROCESSED_EMAILS_PATH", "/app/data/processed_emails.json"))
DATABASE_URL     = os.getenv("DATABASE_URL")
ADMIN_GROUP_ID   = os.getenv("GROUP_ID_ADMIN")
BOT_TOKEN        = os.getenv("TELEGRAM_BOT_TOKEN")

# Configuración de Bancos
BANK_FILTERS = [
    {"banco": "BAC", "from": "baccom-enlinea@ec-credomatic.com.ni", "subject": "Aplicacion de Liquidacion"},
    {"banco": "BANPRO", "from": "COMERCIOPREMIA@ecbanpro.com.ni", "subject": "Aplicacion de Liquidacion"}
]

# ─── Auth ─────────────────────────────────────────────────────────────────────

def _get_access_token() -> str:
    from scripts.inventario_monitor import _get_access_token as get_token
    return get_token()

def _auth_headers() -> dict:
    return {"Authorization": f"Bearer {_get_access_token()}"}

# ─── Persistencia ─────────────────────────────────────────────────────────────

def _load_processed() -> set:
    PROCESSED_FILE.parent.mkdir(parents=True, exist_ok=True)
    if PROCESSED_FILE.exists():
        try:
            return set(json.loads(PROCESSED_FILE.read_text()))
        except: return set()
    return set()

def _save_processed(ids: set) -> None:
    PROCESSED_FILE.write_text(json.dumps(list(ids)))

# ─── Gmail API ────────────────────────────────────────────────────────────────

def _list_messages(query: str) -> list:
    resp = requests.get(f"{GMAIL_API}/messages", headers=_auth_headers(), params={"q": query, "maxResults": 20}, timeout=15)
    resp.raise_for_status()
    return resp.json().get("messages", [])

def _get_message(msg_id: str) -> dict:
    resp = requests.get(f"{GMAIL_API}/messages/{msg_id}", headers=_auth_headers(), params={"format": "full"}, timeout=15)
    resp.raise_for_status()
    return resp.json()

def _get_attachment(msg_id: str, attachment_id: str) -> bytes:
    resp = requests.get(f"{GMAIL_API}/messages/{msg_id}/attachments/{attachment_id}", headers=_auth_headers(), timeout=30)
    resp.raise_for_status()
    data = resp.json().get("data", "")
    return base64.urlsafe_b64decode(data + "==")

# ─── PDF Parsing ──────────────────────────────────────────────────────────────

def _parse_money(text: str) -> float:
    """Limpia strings de dinero como '2.628,40' o '2,628.40'."""
    if not text: return 0.0
    clean = text.replace("C$", "").replace("$", "").strip()
    # Si hay coma y punto, asumimos formato americano (comma=miles, dot=decimal)
    if "," in clean and "." in clean:
        clean = clean.replace(",", "")
    elif "," in clean: # Solo coma -> decimal
        clean = clean.replace(",", ".")
    try:
        return float(clean)
    except: return 0.0

def _extract_bank_data(pdf_path: str, banco: str) -> dict:
    """Extrae monto y fecha de un PDF bancario."""
    try:
        reader = PdfReader(pdf_path)
        text = "\n".join([p.extract_text() for p in reader.pages])
        
        monto = 0.0
        fecha = None
        liq_id = "N/D"

        if banco == "BAC":
            # Pattern: TOTAL DE VENTAS 2,628.40
            match = re.search(r"TOTAL DE VENTAS\s+([\d,.]+)", text)
            if match: monto = _parse_money(match.group(1))
            
            match_id = re.search(r"Nmero de Liquidacin\s+([\d]+)", text)
            if match_id: liq_id = match_id.group(1)
            
            # Fecha: 27 ABR 26
            match_f = re.search(r"(\d{1,2}\s+[A-Z]{3}\s+\d{2})", text)
            if match_f: fecha = match_f.group(1)

        elif banco == "BANPRO":
            # Pattern: Monto a Pagar : 7,875.89
            match = re.search(r"Monto a Pagar\s*:\s+([\d,.]+)", text)
            if match: monto = _parse_money(match.group(1))
            
            match_id = re.search(r"No Liquidacin:\s*(\d+)", text)
            if match_id: liq_id = match_id.group(1)
            
            # Fecha: 27/04/2026
            match_f = re.search(r"(\d{2}/\d{2}/\d{4})", text)
            if match_f: fecha = match_f.group(1)

        return {"monto": monto, "fecha": fecha, "liquidacion_id": liq_id, "text": text[:500]}
    except Exception as e:
        logger.error(f"Error parseando PDF de {banco}: {e}")
        return None

# ─── Database ─────────────────────────────────────────────────────────────────

def _save_bank_liq(banco: str, data: dict):
    if not DATABASE_URL or not data: return
    import psycopg2
    try:
        with psycopg2.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO liquidaciones_banco (fecha, banco, monto, liquidacion_id, raw_text)
                    VALUES (CURRENT_DATE, %s, %s, %s, %s)
                    ON CONFLICT (fecha, banco, liquidacion_id) DO NOTHING
                """, (banco, data['monto'], data['liquidacion_id'], data['text']))
        logger.info(f"Liquidacion {banco} guardada: C${data['monto']}")
    except Exception as e:
        logger.error(f"Error guardando liquidacion en DB: {e}")

# ─── Procesamiento ────────────────────────────────────────────────────────────

def _process_message(msg_id: str, processed: set):
    msg = _get_message(msg_id)
    headers = {h['name'].lower(): h['value'] for h in msg.get('payload', {}).get('headers', [])}
    subject = headers.get('subject', '')
    sender = headers.get('from', '')

    # 1. ¿Es un Cierre de Caja (POS)?
    if SUBJECT_FILTER.lower() in subject.lower():
        from scripts.gmail_monitor import _extract_pdfs, _get_attachment
        pdfs = _extract_pdfs(msg)
        if "cierre" in pdfs and "ventas" in pdfs:
            with tempfile.TemporaryDirectory() as tmpdir:
                c_fn, c_id = pdfs["cierre"]
                v_fn, v_id = pdfs["ventas"]
                c_path = Path(tmpdir) / c_fn
                v_path = Path(tmpdir) / v_fn
                c_path.write_bytes(_get_attachment(msg_id, c_id))
                v_path.write_bytes(_get_attachment(msg_id, v_id))
                procesar_cierre(str(c_path), str(v_path))
        processed.add(msg_id)
        return

    # 2. ¿Es una Liquidación Bancaria?
    for cfg in BANK_FILTERS:
        if cfg['from'].lower() in sender.lower() or cfg['subject'].lower() in subject.lower():
            parts = msg.get("payload", {}).get("parts", [])
            for part in parts:
                filename = part.get("filename", "")
                if filename.lower().endswith(".pdf"):
                    att_id = part.get("body", {}).get("attachmentId")
                    if att_id:
                        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                            tmp.write(_get_attachment(msg_id, att_id))
                            tmp_path = tmp.name
                        data = _extract_bank_data(tmp_path, cfg['banco'])
                        if data:
                            _save_bank_liq(cfg['banco'], data)
                            # Notificar al momento
                            text = f"🏦 <b>Liquidación {cfg['banco']} Detectada</b>\n💰 Monto: C$ {data['monto']:,.2f}\n📄 ID: {data['liquidacion_id']}"
                            if BOT_TOKEN and ADMIN_GROUP_ID:
                                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", 
                                              json={"chat_id": ADMIN_GROUP_ID, "text": text, "parse_mode": "HTML"})
                        os.unlink(tmp_path)
            processed.add(msg_id)
            return

def _check_and_process():
    processed = _load_processed()
    # Query amplia para capturar todo lo relevante
    query = f'"{SUBJECT_FILTER}" OR from:{BANK_FILTERS[0]["from"]} OR from:{BANK_FILTERS[1]["from"]}'
    messages = _list_messages(query)
    
    count = 0
    for m in messages:
        if m['id'] not in processed:
            try:
                _process_message(m['id'], processed)
                count += 1
            except Exception as e:
                logger.error(f"Error en msg {m['id']}: {e}")
    
    _save_processed(processed)
    return count

def main():
    logger.info("Monitor de Gmail iniciado (POS + Bancos)")
    while True:
        try:
            _check_and_process()
        except Exception as e:
            logger.error(f"Error loop: {e}")
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
