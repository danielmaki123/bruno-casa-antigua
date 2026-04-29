"""
generate_token.py — Genera token.json para Google Sheets usando OAuth 2.0
Solo usa requests + webbrowser (stdlib). Sin dependencias externas.

Ejecutar: python scripts/generate_token.py
"""
import json
import os
import sys
import webbrowser
from pathlib import Path
from urllib.parse import urlencode, urlparse, parse_qs

import requests

# ── Config ────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent

# Busca el client_secret: primero el de bruno-drive, luego el genérico
CLIENT_SECRET_PATH = (
    ROOT / "client_secret_725038131281-7oe8e623pk5bibe195j37m82jt7gav2k.apps.googleusercontent.com.json"
    if (ROOT / "client_secret_725038131281-7oe8e623pk5bibe195j37m82jt7gav2k.apps.googleusercontent.com.json").exists()
    else ROOT / "client_secret.json"
)

TOKEN_OUTPUT = ROOT / "token_brunodrv.json"

SCOPES = " ".join([
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
])

# ── Leer credenciales ─────────────────────────────────────────────────────────
secret_data = json.loads(CLIENT_SECRET_PATH.read_text())["installed"]
CLIENT_ID     = secret_data["client_id"]
CLIENT_SECRET = secret_data["client_secret"]
TOKEN_URI     = secret_data["token_uri"]
REDIRECT_URI  = "urn:ietf:wg:oauth:2.0:oob"  # modo "copy-paste"

# ── Paso 1: Generar URL de autorización ──────────────────────────────────────
params = {
    "client_id": CLIENT_ID,
    "redirect_uri": REDIRECT_URI,
    "response_type": "code",
    "scope": SCOPES,
    "access_type": "offline",
    "prompt": "consent",
}
auth_url = "https://accounts.google.com/o/oauth2/auth?" + urlencode(params)

print("=" * 65)
print("PASO 1: Abri este link en tu navegador y autoriza la app:")
print("=" * 65)
print(auth_url)
print()

try:
    webbrowser.open(auth_url)
    print("[Abriendo navegador automaticamente...]")
except Exception:
    print("[Abre el link manualmente en tu navegador]")

# ── Paso 2: Pegar el código ───────────────────────────────────────────────────
print()
print("=" * 65)
code = input("PASO 2: Pega el codigo que te dio Google y presiona Enter:\n> ").strip()

# ── Paso 3: Intercambiar código por token ────────────────────────────────────
resp = requests.post(
    TOKEN_URI,
    data={
        "code": code,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    },
    timeout=15,
)

if resp.status_code != 200:
    print(f"\n[ERROR] {resp.status_code}: {resp.text}")
    sys.exit(1)

token = resp.json()

# ── Guardar token ─────────────────────────────────────────────────────────────
import datetime
expiry = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=token.get("expires_in", 3600))

token_data = {
    "token":         token["access_token"],
    "refresh_token": token.get("refresh_token", ""),
    "token_uri":     TOKEN_URI,
    "client_id":     CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "scopes":        SCOPES.split(),
    "universe_domain": "googleapis.com",
    "account": "",
    "expiry":  expiry.strftime("%Y-%m-%dT%H:%M:%SZ"),
}

TOKEN_OUTPUT.write_text(json.dumps(token_data, indent=2))

print()
print("=" * 65)
print(f"[OK] Token guardado en: {TOKEN_OUTPUT}")
print("Ahora renombralo a token.json y usalo en EasyPanel.")
print("=" * 65)
