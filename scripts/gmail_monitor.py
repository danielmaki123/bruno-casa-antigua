"""
gmail_monitor.py — Monitorea Gmail y procesa cierres de caja automáticamente.

Busca correos con el asunto del Cierre de Caja de CIELO POS,
descarga los PDFs adjuntos y llama a audit_cierre.py.

Uso (ejecución continua):
    python scripts/gmail_monitor.py

Uso (una sola verificación):
    python scripts/gmail_monitor.py --once

Variables de entorno requeridas:
    DATABASE_URL, TELEGRAM_BOT_TOKEN, GROUP_ID_ADMIN, GOOGLE_SHEETS_ID
    Opcionales: GMAIL_CHECK_INTERVAL (segundos, default 300)
                GMAIL_SUBJECT_FILTER (default: "Cierre de Caja")
"""
import argparse
import base64
import json
import logging
import os
import sys
import time
import tempfile
from pathlib import Path

import requests
from dotenv import load_dotenv

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
CHECK_INTERVAL   = int(os.getenv("GMAIL_CHECK_INTERVAL", "300"))  # segundos entre checks
SUBJECT_FILTER   = os.getenv("GMAIL_SUBJECT_FILTER", "Cierre de Caja")
GMAIL_API        = "https://gmail.googleapis.com/gmail/v1/users/me"
PROCESSED_FILE   = Path(tempfile.gettempdir()) / "brunobot_processed_emails.json"

# Nombres esperados de los PDFs adjuntos
PDF_CIERRE_KEYWORDS = ["cierre", "cierrepos", "cierre_pos", "cierredepos"]
PDF_VENTAS_KEYWORDS = ["venta", "menu", "venta_menu", "ventamenu"]

# Sesión global sin lectura de .netrc (evita Permission denied en OneDrive)
_session = requests.Session()
_session.trust_env = False


# ─── Auth (reusa token.json de Google) ────────────────────────────────────────

def _find_token_path() -> Path:
    env_val = os.getenv("SHEETS_TOKEN_PATH", "").strip()
    candidates = [
        Path(env_val) if env_val else None,   # solo si está definida
        Path("/app/token.json"),
        ROOT / "token.json",
        Path.cwd() / "token.json",
    ]
    for p in candidates:
        if p is not None and p.exists():
            return p
    raise RuntimeError("No se encontró token.json")


def _get_access_token() -> str:
    import datetime
    token_path = _find_token_path()
    data = json.loads(token_path.read_text())

    expiry_str = data.get("expiry", "")
    if expiry_str:
        try:
            exp = datetime.datetime.fromisoformat(expiry_str.replace("Z", "+00:00"))
            if exp - datetime.datetime.now(datetime.timezone.utc) > datetime.timedelta(seconds=60):
                return data["token"]
        except Exception:
            pass

    # Refrescar
    resp = _session.post(data["token_uri"], data={
        "client_id":     data["client_id"],
        "client_secret": data["client_secret"],
        "refresh_token": data["refresh_token"],
        "grant_type":    "refresh_token",
    }, timeout=15)
    resp.raise_for_status()
    new = resp.json()

    import datetime
    data["token"] = new["access_token"]
    exp = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=new.get("expires_in", 3600))
    data["expiry"] = exp.strftime("%Y-%m-%dT%H:%M:%SZ")
    token_path.write_text(json.dumps(data))
    return new["access_token"]


def _auth_headers() -> dict:
    return {"Authorization": f"Bearer {_get_access_token()}"}


# ─── Persistencia de emails procesados ────────────────────────────────────────

def _load_processed() -> set:
    PROCESSED_FILE.parent.mkdir(parents=True, exist_ok=True)
    if PROCESSED_FILE.exists():
        return set(json.loads(PROCESSED_FILE.read_text()))
    return set()


def _save_processed(ids: set) -> None:
    PROCESSED_FILE.write_text(json.dumps(list(ids)))


# ─── Gmail API ────────────────────────────────────────────────────────────────

def _list_messages(query: str) -> list:
    """Lista mensajes que coinciden con el query de Gmail."""
    resp = _session.get(
        f"{GMAIL_API}/messages",
        headers=_auth_headers(),
        params={"q": query, "maxResults": 10},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json().get("messages", [])


def _get_message(msg_id: str) -> dict:
    """Obtiene el detalle completo de un mensaje."""
    resp = _session.get(
        f"{GMAIL_API}/messages/{msg_id}",
        headers=_auth_headers(),
        params={"format": "full"},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def _get_attachment(msg_id: str, attachment_id: str) -> bytes:
    """Descarga un adjunto y retorna los bytes."""
    resp = _session.get(
        f"{GMAIL_API}/messages/{msg_id}/attachments/{attachment_id}",
        headers=_auth_headers(),
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json().get("data", "")
    return base64.urlsafe_b64decode(data + "==")


def _classify_pdf(filename: str) -> str:
    """Clasifica un PDF como 'cierre', 'ventas' o None."""
    name = filename.lower().replace(" ", "_").replace("-", "_")
    for kw in PDF_CIERRE_KEYWORDS:
        if kw in name:
            return "cierre"
    for kw in PDF_VENTAS_KEYWORDS:
        if kw in name:
            return "ventas"
    return None


def _extract_pdfs(msg: dict) -> dict:
    """
    Extrae los PDFs adjuntos del mensaje.
    Retorna {"cierre": bytes, "ventas": bytes} o None si faltan.
    """
    pdfs = {}
    parts = msg.get("payload", {}).get("parts", [])

    def _walk(parts_list):
        for part in parts_list:
            if part.get("parts"):
                _walk(part["parts"])
            filename = part.get("filename", "")
            if filename.lower().endswith(".pdf"):
                kind = _classify_pdf(filename)
                if kind and kind not in pdfs:
                    att_id = part.get("body", {}).get("attachmentId")
                    if att_id:
                        pdfs[kind] = (filename, att_id)

    _walk(parts)
    return pdfs


# ─── Procesamiento ────────────────────────────────────────────────────────────

def _check_and_process() -> int:
    """
    Revisa Gmail una vez. Retorna número de cierres procesados.
    """
    query = f'subject:"{SUBJECT_FILTER}" has:attachment'
    logger.info(f"Buscando: {query}")

    try:
        messages = _list_messages(query)
    except Exception as e:
        logger.error(f"Error listando Gmail: {e}")
        return 0

    if not messages:
        logger.info("No hay mensajes nuevos con cierre de caja.")
        return 0

    processed = _load_processed()
    count = 0

    for m in messages:
        msg_id = m["id"]
        if msg_id in processed:
            continue

        try:
            msg = _get_message(msg_id)
            pdfs = _extract_pdfs(msg)

            if "cierre" not in pdfs or "ventas" not in pdfs:
                logger.warning(f"Mensaje {msg_id}: no tiene ambos PDFs ({list(pdfs.keys())}). Marcando como procesado.")
                processed.add(msg_id)
                continue

            # Descargar PDFs a archivos temporales
            with tempfile.TemporaryDirectory() as tmpdir:
                cierre_filename, cierre_att_id = pdfs["cierre"]
                ventas_filename, ventas_att_id = pdfs["ventas"]

                cierre_path = Path(tmpdir) / cierre_filename
                ventas_path = Path(tmpdir) / ventas_filename

                cierre_path.write_bytes(_get_attachment(msg_id, cierre_att_id))
                ventas_path.write_bytes(_get_attachment(msg_id, ventas_att_id))

                logger.info(f"PDFs descargados: {cierre_filename}, {ventas_filename}")

                # Procesar
                resultado = procesar_cierre(str(cierre_path), str(ventas_path))
                logger.info(f"Cierre #{resultado['documento_id']} procesado — alertas: {resultado['alertas']}")
                count += 1

            processed.add(msg_id)

        except Exception as e:
            logger.error(f"Error procesando mensaje {msg_id}: {e}", exc_info=True)

    _save_processed(processed)
    return count


# ─── Entry point ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Monitor de Gmail para cierres de caja")
    parser.add_argument("--once", action="store_true", help="Verificar una sola vez y salir")
    args = parser.parse_args()

    # Crear carpeta de logs si no existe
    (ROOT / "logs").mkdir(exist_ok=True)

    if args.once:
        count = _check_and_process()
        print(f"[OK] {count} cierres procesados.")
        return

    # Modo continuo
    logger.info(f"Monitor iniciado. Revisando cada {CHECK_INTERVAL}s | Filtro: '{SUBJECT_FILTER}'")
    while True:
        try:
            _check_and_process()
        except Exception as e:
            logger.error(f"Error en ciclo principal: {e}", exc_info=True)
        logger.info(f"Siguiente revision en {CHECK_INTERVAL}s...")
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
