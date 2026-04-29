"""
sheets_tool.py — Puente Bruno <-> Google Sheets
Usa solo `requests` (incluido en Hermes). Sin dependencias externas.
Token: /app/token.json | GOOGLE_SHEETS_ID env var
"""
import argparse
import datetime
import json
import logging
import os
import sys
from pathlib import Path

import requests

SHEETS_API = "https://sheets.googleapis.com/v4/spreadsheets"

def _find_token_path() -> Path:
    """Busca token.json en varios lugares (funciona local y en Docker)."""
    # 1. Variable de entorno explícita
    env_path = os.getenv("SHEETS_TOKEN_PATH")
    if env_path and Path(env_path).exists():
        return Path(env_path)
    # 2. Ruta del contenedor Docker
    if Path("/app/token.json").exists():
        return Path("/app/token.json")
    # 3. Raíz del proyecto (local: carpeta padre de scripts/)
    local = Path(__file__).resolve().parent.parent / "token.json"
    if local.exists():
        return local
    # 4. Directorio actual
    cwd = Path.cwd() / "token.json"
    if cwd.exists():
        return cwd
    raise RuntimeError("No se encontró token.json. Pon el archivo en la raíz del proyecto o define SHEETS_TOKEN_PATH.")

TOKEN_PATH = _find_token_path()

logging.basicConfig(level=logging.INFO, stream=sys.stderr, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("sheets_tool")


# ─── Auth ───────────────────────────────────────────────────────────────────

def _get_access_token() -> str:
    """Devuelve un access_token válido, refrescando si está expirado."""
    data = json.loads(TOKEN_PATH.read_text())

    # Comprobar expiración (60 s de margen)
    expiry_str = data.get("expiry", "")
    if expiry_str:
        try:
            exp = datetime.datetime.fromisoformat(expiry_str.replace("Z", "+00:00"))
            if exp - datetime.datetime.now(datetime.timezone.utc) > datetime.timedelta(seconds=60):
                return data["token"]
        except Exception:
            pass

    # Refrescar token
    resp = requests.post(
        data["token_uri"],
        data={
            "client_id": data["client_id"],
            "client_secret": data["client_secret"],
            "refresh_token": data["refresh_token"],
            "grant_type": "refresh_token",
        },
        timeout=15,
    )
    resp.raise_for_status()
    new = resp.json()

    # Guardar token actualizado
    data["token"] = new["access_token"]
    exp = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=new.get("expires_in", 3600))
    data["expiry"] = exp.strftime("%Y-%m-%dT%H:%M:%SZ")
    TOKEN_PATH.write_text(json.dumps(data))

    return new["access_token"]


def _auth_headers() -> dict:
    return {"Authorization": f"Bearer {_get_access_token()}", "Content-Type": "application/json"}


def _spreadsheet_id() -> str:
    sid = os.getenv("GOOGLE_SHEETS_ID")
    if not sid:
        raise RuntimeError("GOOGLE_SHEETS_ID no está configurado")
    return sid


# ─── Sheets helpers ──────────────────────────────────────────────────────────

def _read_sheet(sid: str, sheet: str) -> list:
    url = f"{SHEETS_API}/{sid}/values/{sheet}"
    r = requests.get(url, headers=_auth_headers(), timeout=15)
    r.raise_for_status()
    values = r.json().get("values", [])
    if not values:
        return []
    headers = [str(h).strip() for h in values[0]]
    return [
        {headers[i]: (row[i] if i < len(row) else "") for i in range(len(headers))}
        for row in values[1:]
    ]


def _get_header_row(sid: str, sheet: str) -> list:
    url = f"{SHEETS_API}/{sid}/values/{sheet}!1:1"
    r = requests.get(url, headers=_auth_headers(), timeout=15)
    r.raise_for_status()
    values = r.json().get("values", [])
    return [str(h).strip() for h in values[0]] if values else []


def _append_row(sid: str, sheet: str, payload: dict) -> dict:
    headers = _get_header_row(sid, sheet)

    # Si la hoja está vacía, escribir encabezados primero
    if not headers:
        headers = list(payload.keys())
        r = requests.put(
            f"{SHEETS_API}/{sid}/values/{sheet}!1:1",
            headers=_auth_headers(),
            params={"valueInputOption": "RAW"},
            json={"values": [headers]},
            timeout=15,
        )
        r.raise_for_status()

    row = [str(payload.get(h, "")) for h in headers]
    r = requests.post(
        f"{SHEETS_API}/{sid}/values/{sheet}:append",
        headers=_auth_headers(),
        params={"valueInputOption": "USER_ENTERED", "insertDataOption": "INSERT_ROWS"},
        json={"values": [row]},
        timeout=15,
    )
    r.raise_for_status()
    updates = r.json().get("updates", {})
    return {
        "success": True,
        "sheet": sheet,
        "updatedRange": updates.get("updatedRange"),
        "updatedRows": updates.get("updatedRows", 0),
    }


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Puente Bruno <-> Google Sheets")
    parser.add_argument("--action", required=True, choices=["read", "append"], help="Acción a ejecutar")
    parser.add_argument("--sheet", help="Nombre de la hoja")
    parser.add_argument("--data", help="JSON con datos a insertar (solo para append)")
    args = parser.parse_args()

    try:
        sid = _spreadsheet_id()

        if args.action == "read":
            if not args.sheet:
                raise RuntimeError("--sheet es obligatorio para read")
            print(json.dumps(_read_sheet(sid, args.sheet), ensure_ascii=False))

        elif args.action == "append":
            if not args.sheet:
                raise RuntimeError("--sheet es obligatorio para append")
            if not args.data:
                raise RuntimeError("--data es obligatorio para append")
            payload = json.loads(args.data)
            if not isinstance(payload, dict):
                raise RuntimeError("--data debe ser un JSON object")
            print(json.dumps(_append_row(sid, args.sheet, payload), ensure_ascii=False))

    except Exception as exc:
        logger.exception("Error en sheets_tool")
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
