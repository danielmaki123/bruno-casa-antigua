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
PROCESSED_FILE   = Path(os.getenv("PROCESSED_EMAILS_PATH", "data/processed_emails.json"))
DATABASE_URL     = os.getenv("DATABASE_URL")
ADMIN_GROUP_ID   = os.getenv("GROUP_ID_ADMIN")
BOT_TOKEN        = os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")

# Configuración de Bancos
BANK_FILTERS = [
    {"banco": "BAC", "from": "baccom-enlinea@ec-credomatic.com.ni", "subject": "Aplicacion de Liquidacion"},
    {"banco": "BANPRO", "from": "COMERCIOPREMIA@ecbanpro.com.ni", "subject": "Aplicacion de Liquidacion"}
]

# ─── Auth ─────────────────────────────────────────────────────────────────────

def _get_access_token() -> str:
    """Obtiene el access token de Google. Decoplado de otros scripts para evitar fallos en cadena."""
    try:
        from scripts.inventario_monitor import _get_access_token as get_token
        return get_token()
    except Exception as e:
        _notify_admin(f"🚨 <b>Error Crítico de Autenticación</b>\nNo se pudo obtener el token de Google: {e}")
        raise

def _notify_admin(text: str):
    """Envía una notificación de salud del sistema al administrador."""
    if BOT_TOKEN and ADMIN_GROUP_ID:
        try:
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", 
                          json={"chat_id": ADMIN_GROUP_ID, "text": text, "parse_mode": "HTML"},
                          timeout=10)
        except Exception as e:
            logger.error(f"Error enviando notificación a Telegram: {e}")

def _auth_headers() -> dict:
    return {"Authorization": f"Bearer {_get_access_token()}"}

# ─── Persistencia ─────────────────────────────────────────────────────────────

def _load_processed() -> set:
    PROCESSED_FILE.parent.mkdir(parents=True, exist_ok=True)
    if PROCESSED_FILE.exists():
        try:
            content = PROCESSED_FILE.read_text().strip()
            if not content: return set()
            return set(json.loads(content))
        except Exception as e: 
            logger.error(f"Error cargando IDs procesados: {e}")
            _notify_admin(f"⚠️ <b>Alerta de Sistema</b>\nEl archivo de persistencia está corrupto. Bruno podría duplicar notificaciones.")
            return set()
    return set()

def _save_processed(ids: set) -> None:
    try:
        PROCESSED_FILE.write_text(json.dumps(list(ids)))
    except Exception as e:
        logger.error(f"Error guardando IDs procesados: {e}")

# ─── Gmail API ────────────────────────────────────────────────────────────────

def _list_messages(query: str) -> list:
    try:
        resp = requests.get(f"{GMAIL_API}/messages", headers=_auth_headers(), params={"q": query, "maxResults": 20}, timeout=15)
        resp.raise_for_status()
        return resp.json().get("messages", [])
    except Exception as e:
        logger.error(f"Error listando mensajes de Gmail: {e}")
        if "401" in str(e) or "invalid_grant" in str(e).lower():
            _notify_admin("🔑 <b>Token Expirado</b>\nBruno no puede leer el correo. Por favor refresca las credenciales de Google.")
        raise

def _get_message(msg_id: str) -> dict:
    resp = requests.get(f"{GMAIL_API}/messages/{msg_id}", headers=_auth_headers(), params={"format": "full"}, timeout=15)
    resp.raise_for_status()
    return resp.json()

def _get_attachment(msg_id: str, attachment_id: str) -> bytes:
    resp = requests.get(f"{GMAIL_API}/messages/{msg_id}/attachments/{attachment_id}", headers=_auth_headers(), timeout=30)
    resp.raise_for_status()
    data = resp.json().get("data", "")
    return base64.urlsafe_b64decode(data + "==")

def _extract_pdfs(msg: dict) -> dict:
    """Retorna { 'cierre': (filename, id), 'ventas': (filename, id) }"""
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
    if "parts" in payload:
        walk_parts(payload["parts"])
    else:
        walk_parts([payload])
    return found

# ─── PDF Parsing ──────────────────────────────────────────────────────────────

def _parse_money(text: str) -> float:
    """Limpia strings de dinero como '2.628,40' o '2,628.40'."""
    if not text: return 0.0
    clean = text.replace("C$", "").replace("$", "").replace("\xa0", "").strip()
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
        text = "\n".join([p.extract_text() for p in reader.pages if p.extract_text()])
        
        monto = 0.0
        fecha = None
        liq_id = "N/D"

        if banco == "BAC":
            # Pattern más flexible para BAC: busca "TOTAL DE VENTAS" con posibles espacios o caracteres extra
            match = re.search(r"TOTAL\s+DE\s+VENTAS\s*[:\-]?\s*([\d,.]+)", text, re.IGNORECASE)
            if match: monto = _parse_money(match.group(1))
            
            match_id = re.search(r"N[uú]mero\s+de\s+Liquidaci[oó]n\s*[:\-]?\s*([\d]+)", text, re.IGNORECASE)
            if match_id: liq_id = match_id.group(1)
            
            match_f = re.search(r"(\d{1,2}\s+[A-Z]{3,}\s+\d{2,4})", text, re.IGNORECASE)
            if match_f: fecha = match_f.group(1)

        elif banco == "BANPRO":
            # Pattern más flexible para BANPRO: busca "Monto a Pagar"
            match = re.search(r"Monto\s+a\s+Pagar\s*[:\-]?\s*([\d,.]+)", text, re.IGNORECASE)
            if match: monto = _parse_money(match.group(1))
            
            match_id = re.search(r"No\s+Liquidaci[oó]n\s*[:\-]?\s*(\d+)", text, re.IGNORECASE)
            if match_id: liq_id = match_id.group(1)
            
            match_f = re.search(r"(\d{2}/\d{2}/\d{2,4})", text)
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
        _notify_admin(f"❌ <b>Error DB</b>\nNo se pudo guardar la liquidación de {banco} en PostgreSQL.")

# ─── Procesamiento ────────────────────────────────────────────────────────────

def _process_message(msg_id: str, processed: set):
    try:
        msg = _get_message(msg_id)
        headers = {h['name'].lower(): h['value'] for h in msg.get('payload', {}).get('headers', [])}
        subject = headers.get('subject', '')
        sender = headers.get('from', '')

        # 1. ¿Es un Cierre de Caja (POS)?
        if SUBJECT_FILTER.lower() in subject.lower():
            pdfs = _extract_pdfs(msg)
            if "cierre" not in pdfs or "ventas" not in pdfs:
                missing = [k for k in ("cierre", "ventas") if k not in pdfs]
                logger.warning(f"Correo {msg_id} sin adjuntos requeridos: {missing} — no se marca procesado")
                _notify_admin(f"⚠️ <b>Cierre incompleto</b>\nCorreo sin adjuntos: {missing}. Se reintentará en el próximo ciclo.")
                return
            try:
                with tempfile.TemporaryDirectory() as tmpdir:
                    c_fn, c_id = pdfs["cierre"]
                    v_fn, v_id = pdfs["ventas"]
                    c_path = Path(tmpdir) / c_fn
                    v_path = Path(tmpdir) / v_fn
                    c_path.write_bytes(_get_attachment(msg_id, c_id))
                    v_path.write_bytes(_get_attachment(msg_id, v_id))
                    procesar_cierre(str(c_path), str(v_path))
                processed.add(msg_id)
            except Exception as e:
                logger.error(f"Error procesando cierre {msg_id}: {e} — no se marca procesado")
                _notify_admin(f"⚠️ <b>Error procesando cierre</b>\n{e}. Se reintentará en el próximo ciclo.")
            return

        # 2. ¿Es una Liquidación Bancaria?
        for cfg in BANK_FILTERS:
            # Priorizar coincidencia de SENDER para evitar falsos positivos de BAC/BANPRO
            is_match = False
            if cfg['from'].lower() in sender.lower():
                is_match = True
            elif cfg['subject'].lower() in subject.lower() and sender.lower().endswith(".ni"):
                # Si el subject coincide y el remitente es de Nicaragua (.ni), pero no es el específico de arriba
                # Solo marcamos como match si no coincide con el remitente de OTRA configuración
                otros_senders = [c['from'].lower() for c in BANK_FILTERS if c['banco'] != cfg['banco']]
                if not any(o in sender.lower() for o in otros_senders):
                    is_match = True
                
            if is_match:
                parts = msg.get("payload", {}).get("parts", [])
                if not parts and "body" in msg.get("payload", {}): parts = [msg["payload"]] # Caso un solo part
                
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
                                text = f"🏦 <b>Liquidación {cfg['banco']} Detectada</b>\n💰 Monto: C$ {data['monto']:,.2f}\n📄 ID: {data['liquidacion_id']}"
                                _notify_admin(text)
                            os.unlink(tmp_path)
                processed.add(msg_id)
                return
    except Exception as e:
        logger.error(f"Fallo procesando mensaje {msg_id}: {e}")
        _notify_admin(f"⚠️ <b>Fallo de Procesamiento</b>\nOcurrió un error con un correo de {sender}. Revisa los logs.")

def _check_and_process():
    processed = _load_processed()
    # Query amplia para capturar todo lo relevante
    query = f'"{SUBJECT_FILTER}" OR from:{BANK_FILTERS[0]["from"]} OR from:{BANK_FILTERS[1]["from"]}'
    try:
        messages = _list_messages(query)
    except:
        return 0 # Ya notificado en _list_messages
    
    count = 0
    for m in messages:
        if m['id'] not in processed:
            _process_message(m['id'], processed)
            count += 1
    
    _save_processed(processed)
    return count

def main():
    logger.info("Monitor de Gmail iniciado (Estandar ECC)")
    _notify_admin("🚀 <b>Bruno Monitor Iniciado</b>\nEl servicio de Gmail está activo y vigilando cierres.")
    
    consecutive_errors = 0
    while True:
        try:
            _check_and_process()
            consecutive_errors = 0
        except Exception as e:
            consecutive_errors += 1
            logger.error(f"Error loop (intento {consecutive_errors}): {e}")
            if consecutive_errors >= 3:
                _notify_admin(f"🚑 <b>Crisis de Sistema</b>\nEl monitor ha fallado 3 veces seguidas. Error: {e}")
                consecutive_errors = 0 # Reset para no spamear
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
