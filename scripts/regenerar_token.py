"""
regenerar_token.py — Regenera token.json con scopes completos incluyendo Drive.
Ejecutar una sola vez en la PC donde tengas acceso al navegador.
"""
import json
import os
import webbrowser
import urllib.parse
import http.server
import threading
from pathlib import Path
from datetime import datetime, timezone, timedelta

import requests

ROOT = Path(__file__).resolve().parent.parent
CLIENT_SECRET_FILE = ROOT / "client_secret.json"
TOKEN_FILE = ROOT / "token.json"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/drive",          # <-- scope completo
]

REDIRECT_URI = "http://localhost:8765"
auth_code = None


class OAuthHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        auth_code = params.get("code", [None])[0]
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"<h2>Autorizado correctamente. Puedes cerrar esta ventana.</h2>")

    def log_message(self, *args):
        pass


def main():
    if not CLIENT_SECRET_FILE.exists():
        print(f"[ERROR] No se encontro {CLIENT_SECRET_FILE}")
        return

    secret = json.loads(CLIENT_SECRET_FILE.read_text(encoding="utf-8"))
    creds = secret.get("installed") or secret.get("web")
    if not creds:
        print("[ERROR] Formato de client_secret.json no reconocido")
        return

    client_id = creds["client_id"]
    client_secret = creds["client_secret"]
    token_uri = creds.get("token_uri", "https://oauth2.googleapis.com/token")
    auth_uri = creds.get("auth_uri", "https://accounts.google.com/o/oauth2/auth")

    # Construir URL de autorización
    auth_params = {
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
    }
    auth_url = f"{auth_uri}?{urllib.parse.urlencode(auth_params)}"

    # Iniciar servidor local para capturar el code
    server = http.server.HTTPServer(("localhost", 8765), OAuthHandler)
    thread = threading.Thread(target=server.handle_request)
    thread.daemon = True
    thread.start()

    print("\n[INFO] Abriendo navegador para autorizar...")
    print(f"[INFO] Si no se abre automáticamente, ve a:\n{auth_url}\n")
    webbrowser.open(auth_url)

    thread.join(timeout=120)

    if not auth_code:
        print("[ERROR] No se recibio el codigo de autorización (timeout 120s)")
        return

    # Intercambiar code por tokens
    s = requests.Session()
    s.trust_env = False
    resp = s.post(token_uri, data={
        "code": auth_code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    }, timeout=30)
    resp.raise_for_status()
    tokens = resp.json()

    if "error" in tokens:
        print(f"[ERROR] {tokens}")
        return

    # Guardar token.json
    expiry = datetime.now(timezone.utc) + timedelta(seconds=int(tokens.get("expires_in", 3600)))
    token_data = {
        "token": tokens["access_token"],
        "refresh_token": tokens.get("refresh_token"),
        "token_uri": token_uri,
        "client_id": client_id,
        "client_secret": client_secret,
        "scopes": SCOPES,
        "expiry": expiry.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    TOKEN_FILE.write_text(json.dumps(token_data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[OK] token.json guardado en {TOKEN_FILE}")
    print(f"[OK] Scopes autorizados: {', '.join(SCOPES)}")


if __name__ == "__main__":
    main()
